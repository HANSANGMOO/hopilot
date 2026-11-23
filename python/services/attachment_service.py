import asyncio
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Union
from urllib.parse import unquote

import config
from core.errors import AttachmentLoadError, DocumentLoadError, ImageLoadError
from core.models import DocumentAttachment, ImageAttachment, ProcessedAttachment, generate_id
from engine.document_processor import DocumentProcessor
from engine.image_processor import ImageProcessor

_GENERIC_MIME_TYPES = frozenset({"application/octet-stream", "binary/octet-stream"})

_TOKEN_LIMIT = 10_000
_BYTES_PER_TOKEN = 4  # 영어 기준 보수적 추정 (한국어는 더 token-dense)
_TEXT_MIME_TYPES = frozenset({"text/plain", "text/csv", "text/html", "application/json"})
_BINARY_SIZE_LIMIT = 10 * 1024 * 1024  # 10MB

def _to_local_path(path: str) -> str:
    """file:/// prefix 제거 후 URL 디코딩하여 로컬 경로 반환."""
    return unquote(path.removeprefix("file:///"))


_EXT_MIME_OVERRIDES: dict[str, str] = {
    ".ts":   "text/typescript",
    ".tsx":  "text/typescript",
}

_MAGIC_BYTES: list[tuple[bytes, str]] = [
    (b'\x25\x50\x44\x46', "application/pdf"),                                                    # %PDF
    (b'\x89\x50\x4e\x47', "image/png"),                                                          # PNG
    (b'\xff\xd8\xff',     "image/jpeg"),                                                          # JPEG
    (b'\x47\x49\x46\x38', "image/gif"),                                                          # GIF8
    (b'\x50\x4b\x03\x04', "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),  # ZIP계열 — 확장자 없으면 docx로 fallback
]


def _resolve_mime_type(path: str, mime_type: Optional[str]) -> str:
    """MIME 타입을 확정합니다. 없거나 generic이면 확장자 → magic bytes 순으로 감지합니다."""
    ext = Path(path).suffix.lower()
    if ext in _EXT_MIME_OVERRIDES:
        return _EXT_MIME_OVERRIDES[ext]

    if mime_type and mime_type not in _GENERIC_MIME_TYPES:
        return mime_type

    guessed, _ = mimetypes.guess_type(path)
    if guessed:
        return guessed

    if path.startswith("http://") or path.startswith("https://"):
        raise AttachmentLoadError(f"URL에서 MIME 타입을 감지할 수 없습니다: {path}")

    local = _to_local_path(path)
    try:
        header = Path(local).read_bytes()[:8]
        for magic, detected in _MAGIC_BYTES:
            if header.startswith(magic):
                return detected
    except OSError:
        pass

    raise AttachmentLoadError(f"MIME 타입을 감지할 수 없습니다: {path}")


class AttachmentService:
    def __init__(self) -> None:
        self._store: Dict[str, Union[ImageAttachment, DocumentAttachment]] = {}
        self._image_processor = ImageProcessor()
        self._document_processor = DocumentProcessor()

    def validate_size(self, path: str, mime_type: str) -> None:
        """텍스트 파일에 한해 파일 크기로 토큰 수를 추정해 제한을 초과하면 DocumentLoadError를 발생시킵니다.
        바이너리 문서는 DocumentProcessor.process() 내에서 추출 후 체크합니다.
        """
        if path.startswith(("http://", "https://")):
            return
        local = _to_local_path(path)
        try:
            size = Path(local).stat().st_size
        except OSError:
            return
        if mime_type in _TEXT_MIME_TYPES:
            estimated = size // _BYTES_PER_TOKEN
            if estimated > _TOKEN_LIMIT:
                raise DocumentLoadError(
                    f"문서가 너무 큽니다 (약 {estimated:,} 토큰 추정, 최대 {_TOKEN_LIMIT:,}). "
                    "MCP Vector RAG를 통해 대용량 문서를 처리하세요."
                )
        else:
            if size > _BINARY_SIZE_LIMIT:
                raise DocumentLoadError(
                    f"파일이 너무 큽니다 ({size / 1024 / 1024:.1f}MB, 최대 {_BINARY_SIZE_LIMIT // 1024 // 1024}MB). "
                    "MCP Vector RAG를 통해 대용량 문서를 처리하세요."
                )

    def validate_support(self, mime_type: str) -> None:
        """지원하지 않는 MIME 타입이면 AttachmentLoadError를 발생시킵니다."""
        if (
            mime_type not in ImageProcessor.SUPPORTED_MIME_TYPES
            and mime_type not in DocumentProcessor.SUPPORTED_MIME_TYPES
        ):
            raise AttachmentLoadError(f"지원하지 않는 파일 형식입니다: {mime_type}")

    async def load(self, path: str, mime_type: str, name: str, data: Optional[str] = None) -> ProcessedAttachment:
        """파일을 읽어 메모리에 올리고 스토어에 등록합니다."""
        mime_type = _resolve_mime_type(path, mime_type)
        self.validate_support(mime_type)
        if mime_type.startswith("image/"):
            return await self._load_image(
                path, mime_type, name,
                source_type="inline" if data else None,
                data=data,
            )
        return await self._load_document(path, mime_type, name)

    async def _load_image(
        self,
        path: str,
        mime_type: str,
        name: str,
        source_type: Optional[str] = None,
        data: Optional[str] = None,
    ) -> ImageAttachment:
        match source_type or self._image_processor.classify(path):
            case "url":
                source_type, encoding, ref, data = "url", None, path, path
            case "uri":
                local_path = _to_local_path(path)
                try:
                    b64 = await self._image_processor.process(local_path, mime_type)
                except (FileNotFoundError, PermissionError) as e:
                    raise ImageLoadError(f"이미지 파일을 불러오지 못했습니다: {Path(local_path).name}") from e
                source_type, encoding, ref, data = "uri", "base64", path, b64
            case "inline":
                saved_path = await self._image_processor.create(data, mime_type, config.IMAGE_DIR)
                source_type, encoding, ref = "uri", "base64", f"file:///{saved_path}"
        attachment = ImageAttachment(
            id=generate_id("att")(),
            path=ref,
            name=name,
            mime_type=mime_type,
            source_type=source_type,
            encoding=encoding,
            data=data,
        )
        self._store[attachment.id] = attachment
        return attachment

    async def _load_document(self, path: str, mime_type: str, name: str) -> DocumentAttachment:
        self.validate_size(path, mime_type)
        source_type = self._document_processor.classify(path)
        match source_type:
            case "url":
                ref, data, document_type, encoding = path, None, "text", None
            case "uri":
                local_path = _to_local_path(path) if path.startswith("file:///") else path
                document_type = "text" if mime_type.startswith("text/") else "binary"
                try:
                    data, encoding = await self._document_processor.process(local_path, mime_type)
                except (FileNotFoundError, PermissionError) as e:
                    raise DocumentLoadError(f"문서 파일을 불러오지 못했습니다: {Path(local_path).name}") from e
                except ValueError as e:
                    raise DocumentLoadError(str(e)) from e
                ref = Path(local_path).as_uri()
        attachment = DocumentAttachment(
            id=generate_id("att")(),
            path=ref,
            name=name,
            mime_type=mime_type,
            source_type=source_type,
            document_type=document_type,
            encoding=encoding,
            ref=ref,
            data=data,
        )
        self._store[attachment.id] = attachment
        return attachment

    def unload(self, id: str) -> None:
        """단건을 스토어에서 제거합니다."""
        self._store.pop(id, None)

    async def delete(self, id: str) -> None:
        """단건을 스토어에서 제거하고, IMAGE_DIR 내 이미지 파일이면 디스크에서도 삭제합니다.
        문서는 사용자 원본 파일이므로 스토어 제거만 수행합니다.
        """
        attachment = self._store.pop(id, None)
        if isinstance(attachment, ImageAttachment):
            file = Path(_to_local_path(attachment.path))
            if file.is_relative_to(config.IMAGE_DIR):
                await asyncio.to_thread(file.unlink, missing_ok=True)

    def get(self, id: str) -> Optional[ProcessedAttachment]:
        """단건 조회. 없으면 None을 반환합니다."""
        return self._store.get(id)

    def list(self) -> List[ProcessedAttachment]:
        """현재 메모리에 올라온 전체 목록을 반환합니다."""
        return list(self._store.values())

    async def resolve(self, ids: List[str]) -> List[ProcessedAttachment]:
        """ID 목록으로 ProcessedAttachment 목록을 반환합니다."""
        return [a for id in ids if (a := self._store.get(id))]

    def clear(self) -> None:
        """스토어 전체를 비웁니다."""
        self._store.clear()
