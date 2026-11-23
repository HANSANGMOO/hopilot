import asyncio
from pathlib import Path

from core.errors import AttachmentLoadError, DocumentLoadError, ImageLoadError
from core.models import ContextDTO, ContextSchema, HOMessage, HopilotPayload, CopilotTask, DocumentPayload, ImagePayload, TextPayload, ToolSchema
from engine.image_processor import ImageProcessor
from utils import get_logger

logger = get_logger("PayloadEngine")


class PayloadEngine:
    """
    사용자의 메시지 및 컨텍스트(CopilotTask)를 각 LLM Provider가 이해할 수 있는
    표준 프롬프트 페이로드 모델(HopilotPayload)로 변환하는 역할을 담당합니다.
    """

    def __init__(self):
        self._image_processor = ImageProcessor()
        logger.info("PayloadEngine initialized.")

    async def build_payload(self, task: CopilotTask) -> HopilotPayload:
        """
        CopilotTask를 받아서 내부 도메인 모델인 HopilotPayload로 변환합니다.
        DB에서 로드된 memory의 ImagePayload는 data=None이므로 ref를 통해 hydrate합니다.
        """
        context:     ContextDTO | None          = task.context
        memory:      list[HOMessage]            = task.memory
        query:       list[HOMessage]            = task.react.messages
        tools:       list[ToolSchema]           = [t.get_tool_schema() for t in (task.tools or [])]

        await self._hydrate_memory(memory)

        logger.info(f"[PayloadEngine] tools({len(tools)}): {[t.name for t in tools]}")

        return HopilotPayload(
            context=self._build_context_schema(context),
            memory=memory,
            query=query,
            tools=tools,
        )

    def _build_context_schema(self, context: ContextDTO | None) -> ContextSchema:
        if context is None:
            return ContextSchema()
        return ContextSchema(system_instructions=context.static)

    async def _hydrate_memory(self, memory: list[HOMessage]) -> None:
        """memory 내 첨부 Payload의 data 필드가 None이면 ref를 통해 복원합니다.
        파일이 없거나 이동된 경우 해당 chunk를 안내 텍스트로 대체합니다.
        """
        for msg in memory:
            for chunk in msg.chunks:
                if isinstance(chunk.payload, ImagePayload) and chunk.payload.data is None:
                    try:
                        await self._hydrate_image(chunk.payload)
                    except AttachmentLoadError:
                        name = Path(chunk.payload.ref.removeprefix("file:///")).name
                        chunk.payload = TextPayload(text=f"[첨부파일을 찾을 수 없습니다: {name}]")
                elif isinstance(chunk.payload, DocumentPayload) and chunk.payload.data is None:
                    try:
                        await self._hydrate_document(chunk.payload)
                    except AttachmentLoadError:
                        name = Path(chunk.payload.ref.removeprefix("file:///")).name
                        chunk.payload = TextPayload(text=f"[첨부파일을 찾을 수 없습니다: {name}]")

    async def _hydrate_image(self, payload: ImagePayload) -> None:
        match payload.source_type:
            case "uri":
                local_path = payload.ref.removeprefix("file:///")
                try:
                    payload.data = await self._image_processor.process(local_path, payload.mime_type or "")
                except (FileNotFoundError, PermissionError) as e:
                    raise ImageLoadError(f"이미지 파일을 불러오지 못했습니다: {Path(local_path).name}") from e
            case "url" | "inline":
                payload.data = payload.ref

    async def _hydrate_document(self, payload: DocumentPayload) -> None:
        if payload.ref.startswith(("http://", "https://")):
            payload.data = payload.ref
            return
        local_path = Path(payload.ref.removeprefix("file:///"))
        try:
            raw = await asyncio.to_thread(local_path.read_bytes)
        except (FileNotFoundError, PermissionError) as e:
            raise DocumentLoadError(f"문서 파일을 불러오지 못했습니다: {local_path.name}") from e
        payload.data = self._image_processor.encode(raw)
