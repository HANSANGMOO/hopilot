from typing import assert_never

from contracts.attachment import (
    AttachmentDeleteSignal,
    AttachmentGetDTO,
    AttachmentGetSignal,
    AttachmentLoadDTO,
    AttachmentLoadSignal,
    AttachmentUnloadSignal,
)
from core.errors import AttachmentNotFoundError
from core.models import BinaryAttachment, ImageAttachment, TextAttachment
from services.attachment_service import AttachmentService
from utils import get_logger

logger = get_logger("AttachmentHandler")


class AttachmentHandler:
    def __init__(self, attachment_service: AttachmentService):
        self.attachment_service = attachment_service

    async def handle_load(self, signal: AttachmentLoadSignal) -> dict:
        params = signal.params
        result = await self.attachment_service.load(
            path=params["path"],
            name=params["name"],
            mime_type=params["mime_type"],
            data=params.get("data"),
        )
        return AttachmentLoadDTO(id=result.id, restriction=result.restriction).model_dump()

    async def handle_unload(self, signal: AttachmentUnloadSignal) -> None:
        self.attachment_service.unload(signal.params["id"])

    async def handle_delete(self, signal: AttachmentDeleteSignal) -> None:
        await self.attachment_service.delete(signal.params["id"])

    async def handle_get(self, signal: AttachmentGetSignal) -> dict:
        attachment = self.attachment_service.get(signal.params["id"])
        if attachment is None:
            raise AttachmentNotFoundError(f"Attachment {signal.params['id']} not found.")

        match attachment:
            case ImageAttachment():
                dto = AttachmentGetDTO(
                    id=attachment.id,
                    name=attachment.name,
                    data=attachment.data,
                    mime_type=attachment.mime_type,
                    type="image",
                )
            case TextAttachment() | BinaryAttachment():
                dto = AttachmentGetDTO(
                    id=attachment.id,
                    name=attachment.name,
                    data=attachment.data,
                    mime_type=attachment.mime_type,
                    type="document",
                    encoding=attachment.encoding,
                    ref=attachment.uri,
                )
            case _:
                assert_never(attachment)

        return dto.model_dump()
