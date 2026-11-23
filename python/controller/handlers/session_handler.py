from urllib.parse import unquote
from pathlib import PurePosixPath

from contracts.session import (
    BlockDTO,
    MessageDTO,
    SessionCreateSignal,
    SessionDeleteSignal,
    SessionDetailDTO,
    SessionForkSignal,
    SessionListSignal,
    SessionLoadSignal,
    SessionMetaDTO,
    SessionTruncateSignal,
    SessionUpdateSignal,
    TokensDTO,
    ToolBlockDTO,
)
from core.errors import SessionNotFoundError
from core.models import HOChunk, HOMessage, HOSession, DocumentPayload, ImagePayload, TextPayload, ThoughtPayload, ToolCallPayload, ToolOutputPayload, UsagePayload
from services.session_service import SessionService
from utils import get_logger

logger = get_logger("SessionHandler")

_UI_PAYLOAD_TYPES = {"text", "thought", "tool_call", "image", "document", "usage"}


class SessionHandler:
    def __init__(self, session_service: SessionService):
        self.session_service = session_service

    async def handle_list(self, signal: SessionListSignal) -> list:
        metas = await self.session_service.list_sessions()
        return [SessionMetaDTO(**m).model_dump() for m in metas]

    async def handle_load(self, signal: SessionLoadSignal) -> dict:
        session_id = signal.params["session_id"]
        session = await self.session_service.get_session(session_id)
        if not session:
            raise SessionNotFoundError(f"Session {session_id} not found.")
        return self._to_detail_dto(session).model_dump()

    async def handle_create(self, signal: SessionCreateSignal) -> dict:
        session = await self.session_service.create_session(
            title=signal.params["title"],
            project_id=signal.params.get("project_id"),
        )
        return self._to_meta_dto(session).model_dump()

    async def handle_update(self, signal: SessionUpdateSignal) -> dict:
        session_id = signal.params["session_id"]
        patch = signal.params["patch"]
        session = await self.session_service.update_session(session_id, patch)
        return self._to_meta_dto(session).model_dump()

    async def handle_delete(self, signal: SessionDeleteSignal) -> dict:
        await self.session_service.delete_session(signal.params["session_id"])
        return {}

    async def handle_fork(self, signal: SessionForkSignal) -> dict:
        forked = await self.session_service.fork_session(
            signal.params["session_id"],
            signal.params["message_id"],
            signal.params.get("project_id"),
        )
        return self._to_meta_dto(forked).model_dump()

    async def handle_truncate(self, signal: SessionTruncateSignal) -> dict:
        await self.session_service.truncate_messages(
            signal.params["session_id"],
            signal.params["message_id"],
        )
        return {}

    # ── DTO 변환 헬퍼 ──────────────────────────────────────────────────────────

    def _to_meta_dto(self, session: HOSession) -> SessionMetaDTO:
        return SessionMetaDTO(
            id=session.session_id,
            title=session.title,
            updated_at=session.updated_at.isoformat(),
            project_id=session.project_id,
        )

    def _to_detail_dto(self, session: HOSession) -> SessionDetailDTO:
        message_dtos: list[MessageDTO] = []
        for msg in session.messages:
            # ToolOutputPayload만 가진 user 메시지는 직전 AI 메시지의 tool 블록에 output 병합
            is_tool_result_msg = (
                msg.role == "user"
                and msg.chunks
                and all(isinstance(c.payload, ToolOutputPayload) for c in msg.chunks)
            )
            if is_tool_result_msg and message_dtos and message_dtos[-1].role == "ai":
                for chunk in msg.chunks:
                    payload = chunk.payload
                    if isinstance(payload, ToolOutputPayload):
                        for block in reversed(message_dtos[-1].blocks):
                            if block.type == "tool" and block.tool and block.tool.name == payload.tool_name and block.tool.output is None:
                                block.tool.output = payload.output
                                break
            else:
                message_dtos.append(self._to_message_dto(msg))

        return SessionDetailDTO(
            id=session.session_id,
            title=session.title,
            updated_at=session.updated_at.isoformat(),
            messages=message_dtos,
        )

    def _to_message_dto(self, message: HOMessage) -> MessageDTO:
        blocks = [
            self._to_block_dto(chunk)
            for chunk in message.chunks
            if chunk.payload.type in _UI_PAYLOAD_TYPES
        ]
        return MessageDTO(
            id=message.message_id,
            role=message.role,
            blocks=blocks,
            timestamp=message.timestamp.isoformat(),
            model_name=message.model_name,
        )

    def _to_block_dto(self, chunk: HOChunk) -> BlockDTO:
        payload = chunk.payload
        if isinstance(payload, TextPayload):
            return BlockDTO(type="text", text=payload.text)
        if isinstance(payload, ThoughtPayload):
            return BlockDTO(type="thought", thought=payload.thought)
        if isinstance(payload, ToolCallPayload):
            return BlockDTO(type="tool", tool=ToolBlockDTO(name=payload.tool_name, args=payload.tool_args))
        if isinstance(payload, UsagePayload):
            return BlockDTO(
                type="usage",
                tokens=TokensDTO(
                    input=payload.input_tokens,
                    output=payload.output_tokens,
                    thinking=payload.thinking_tokens,
                    cached=payload.cached_tokens,
                    cache_creation=payload.cache_creation_tokens,
                    total=payload.total_tokens,
                ),
            )
        if isinstance(payload, ImagePayload):
            return BlockDTO(type="image", ref=payload.ref)
        if isinstance(payload, DocumentPayload):
            name = unquote(PurePosixPath(payload.ref).name) if payload.ref else None
            return BlockDTO(type="document", ref=payload.ref, name=name, mime_type=payload.mime_type)
        return BlockDTO(type=payload.type)
