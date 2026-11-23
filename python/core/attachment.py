import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal, Optional, Union
from urllib.parse import unquote

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.copilot import DocumentPayload, ImagePayload


def _generate_attachment_id() -> str:
    return f"att_{uuid.uuid4().hex[:8]}"


def to_local_path(path: str) -> Path:
    """file:/// URI 또는 로컬 경로 문자열을 Path 객체로 변환합니다."""
    if path.startswith("file:///"):
        return Path(unquote(path.removeprefix("file:///")))
    return Path(path)


IMAGE_MIME_TYPES: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/tiff",
})
TEXT_MIME_TYPES: frozenset[str] = frozenset({
    "text/plain",
    "text/x-python",
    "text/typescript",
    "text/javascript",
    "text/html",
    "text/csv",
    "text/markdown",
    "application/json",
})
BINARY_MIME_TYPES: frozenset[str] = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
})
DOCUMENT_MIME_TYPES: frozenset[str] = TEXT_MIME_TYPES | BINARY_MIME_TYPES


# ==========================================
# Attachment Models
# ==========================================
class BaseAttachment(BaseModel):
    """로드 완료된 로컬 첨부파일의 공통 도메인 모델."""

    id: str = Field(default_factory=_generate_attachment_id)
    path: Path
    name: str
    mime_type: str
    size: int
    restriction: Optional[Literal["encrypted", "drm", "permission", "mip"]] = None

    @property
    def uri(self) -> str:
        resolved = self.path if self.path.is_absolute() else self.path.resolve()
        return resolved.as_uri()


class ImageAttachment(BaseAttachment):
    type: Literal["image"] = "image"
    data: str
    encoding: Literal["base64"] = "base64"

    def as_payload(self) -> "ImagePayload":
        from core.copilot import ImagePayload

        return ImagePayload(
            source_type="uri",
            encoding=self.encoding,
            ref=self.uri,
            data=self.data,
            mime_type=self.mime_type,
        )


class TextAttachment(BaseAttachment):
    type: Literal["text"] = "text"
    data: str
    encoding: str = "utf-8"

    def as_payload(self) -> "DocumentPayload":
        from core.copilot import DocumentPayload

        return DocumentPayload(
            ref=self.uri,
            name=self.name,
            data=self.data,
            mime_type=self.mime_type,
            encoding=self.encoding,
        )


class BinaryAttachment(BaseAttachment):
    type: Literal["binary"] = "binary"
    data: str
    encoding: Literal["base64", "utf-8"]

    @property
    def is_raw_binary(self) -> bool:
        return self.encoding == "base64"

    def as_payload(self) -> "DocumentPayload":
        from core.copilot import DocumentPayload

        return DocumentPayload(
            ref=self.uri,
            name=self.name,
            data=self.data,
            mime_type=self.mime_type,
            encoding=self.encoding,
        )


Attachment = Annotated[
    Union[ImageAttachment, TextAttachment, BinaryAttachment],
    Field(discriminator="type"),
]
