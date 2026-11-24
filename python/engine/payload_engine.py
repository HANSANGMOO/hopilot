from core.models import ContextDTO, ContextSchema, HOMessage, HopilotPayload, CopilotTask, ToolSchema
from utils import get_logger

logger = get_logger("PayloadEngine")


class PayloadEngine:
    """
    사용자의 메시지 및 컨텍스트(CopilotTask)를 각 LLM Provider가 이해할 수 있는
    표준 프롬프트 페이로드 모델(HopilotPayload)로 변환하는 역할을 담당합니다.
    """

    def __init__(self):
        logger.info("PayloadEngine initialized.")

    async def build_payload(self, task: CopilotTask) -> HopilotPayload:
        """
        CopilotTask를 받아서 내부 도메인 모델인 HopilotPayload로 변환합니다.
        """
        context:     ContextDTO | None          = task.context
        memory:      list[HOMessage]            = task.memory
        query:       list[HOMessage]            = task.react.messages
        tools:       list[ToolSchema]           = [t.get_tool_schema() for t in (task.tools or [])]

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