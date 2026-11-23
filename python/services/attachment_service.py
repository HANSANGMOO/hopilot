import asyncio
from pathlib import Path
from typing import Dict, List, Optional

import config
from core.errors import AttachmentLoadError, DocumentLoadError, ImageLoadError
from core.models import (
    BINARY_MIME_TYPES,
    IMAGE_MIME_TYPES,
    TEXT_MIME_TYPES,
    Attachment,
    BinaryAttachment,
    ImageAttachment,
    TextAttachment,
    to_local_path,
)
from engine.document_processor import DocumentProcessor
from engine.image_processor import ImageProcessor
from utils.mime import resolve_mime_type

_TOKEN_LIMIT = 10_000
_BYTES_PER_TOKEN = 4  # 영어 기준 보수적 추정 (한국어는 더 token-dense)
_BINARY_SIZE_LIMIT = 10 * 1024 * 1024  # 10MB


class AttachmentService:
    def __init__(self) -> None:
        self._store: Dict[str, Attachment] = {}
        self._image_processor = ImageProcessor()
        self._document_processor = DocumentProcessor()

    async def load(
        self, path: str, mime_type: str, name: str, data: Optional[str] = None
    ) -> Attachment:
        """파일을 읽어 메모리에 올리고 스토어에 등록합니다."""
        resolved_mime = resolve_mime_type(path, hint=mime_type)
        if not resolved_mime:
            raise AttachmentLoadError(f"MIME 타입을 감지할 수 없습니다: {path}")

        if resolved_mime in IMAGE_MIME_TYPES:
            attachment: Attachment = await self._load_image(
                path, resolved_mime, name, data=data
            )
        elif resolved_mime in TEXT_MIME_TYPES:
            attachment = await self._load_text(path, resolved_mime, name)
        elif resolved_mime in BINARY_MIME_TYPES:
            attachment = await self._load_binary(path, resolved_mime, name)
        else:
            raise AttachmentLoadError(f"지원하지 않는 파일 형식입니다: {resolved_mime}")

        self._store[attachment.id] = attachment
        return attachment

    async def _load_image(
        self,
        path: str,
        mime_type: str,
        name: str,
        data: Optional[str] = None,
    ) -> ImageAttachment:
        if data:
            saved_path = await self._image_processor.create(data, mime_type, config.IMAGE_DIR)
            size = await asyncio.to_thread(lambda: saved_path.stat().st_size)
            return ImageAttachment(
                path=saved_path,
                name=name,
                mime_type=mime_type,
                size=size,
                data=data,
            )

        local_path = to_local_path(path)
        try:
            size = await asyncio.to_thread(lambda: local_path.stat().st_size)
            b64 = await self._image_processor.process(str(local_path), mime_type)
        except (FileNotFoundError, PermissionError) as e:
            raise ImageLoadError(
                f"이미지 파일을 불러오지 못했습니다: {local_path.name}"
            ) from e
        return ImageAttachment(
            path=local_path,
            name=name,
            mime_type=mime_type,
            size=size,
            data=b64,
        )

    async def _stat_document(self, local_path: Path) -> int:
        try:
            return await asyncio.to_thread(lambda: local_path.stat().st_size)
        except (FileNotFoundError, PermissionError) as e:
            raise DocumentLoadError(
                f"문서 파일을 불러오지 못했습니다: {local_path.name}"
            ) from e

    async def _process_document(self, local_path: Path, mime_type: str) -> tuple[str, str]:
        try:
            return await self._document_processor.process(str(local_path), mime_type)
        except (FileNotFoundError, PermissionError) as e:
            raise DocumentLoadError(
                f"문서 파일을 불러오지 못했습니다: {local_path.name}"
            ) from e
        except ValueError as e:
            raise DocumentLoadError(str(e)) from e

    async def _load_text(self, path: str, mime_type: str, name: str) -> TextAttachment:
        local_path = to_local_path(path)
        size = await self._stat_document(local_path)
        estimated = size // _BYTES_PER_TOKEN
        if estimated > _TOKEN_LIMIT:
            raise DocumentLoadError(
                f"문서가 너무 큽니다 (약 {estimated:,} 토큰 추정, 최대 {_TOKEN_LIMIT:,}). "
                "MCP Vector RAG를 통해 대용량 문서를 처리하세요."
            )
        data, encoding = await self._process_document(local_path, mime_type)
        return TextAttachment(
            path=local_path,
            name=name,
            mime_type=mime_type,
            size=size,
            data=data,
            encoding=encoding,
        )

    async def _load_binary(self, path: str, mime_type: str, name: str) -> BinaryAttachment:
        local_path = to_local_path(path)
        size = await self._stat_document(local_path)
        if size > _BINARY_SIZE_LIMIT:
            max_mb = _BINARY_SIZE_LIMIT // 1024 // 1024
            raise DocumentLoadError(
                f"파일이 너무 큽니다 ({size / 1024 / 1024:.1f}MB, 최대 {max_mb}MB). "
                "MCP Vector RAG를 통해 대용량 문서를 처리하세요."
            )
        data, encoding = await self._process_document(local_path, mime_type)
        return BinaryAttachment(
            path=local_path,
            name=name,
            mime_type=mime_type,
            size=size,
            data=data,
            encoding=encoding,  # type: ignore[arg-type]
        )

    def unload(self, id: str) -> None:
        """단건을 스토어에서 제거합니다."""
        self._store.pop(id, None)

    async def delete(self, id: str) -> None:
        """단건을 스토어에서 제거하고, IMAGE_DIR 내 이미지 파일이면 디스크에서도 삭제합니다.
        문서는 사용자 원본 파일이므로 스토어 제거만 수행합니다.
        """
        attachment = self._store.pop(id, None)
        if isinstance(attachment, ImageAttachment):
            if attachment.path.is_relative_to(config.IMAGE_DIR):
                await asyncio.to_thread(attachment.path.unlink, missing_ok=True)

    def get(self, id: str) -> Optional[Attachment]:
        """단건 조회. 없으면 None을 반환합니다."""
        return self._store.get(id)

    def list(self) -> List[Attachment]:
        """현재 메모리에 올라온 전체 목록을 반환합니다."""
        return list(self._store.values())

    async def resolve(self, ids: List[str]) -> List[Attachment]:
        """ID 목록으로 Attachment 목록을 반환합니다."""
        return [a for id in ids if (a := self._store.get(id))]

    def clear(self) -> None:
        """스토어 전체를 비웁니다."""
        self._store.clear()
