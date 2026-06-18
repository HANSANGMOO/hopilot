from core.models import HopilotPayload, CopilotTask
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
        # memory(과거 대화) + react(현재 턴의 첫 번째 메시지인 user_msg)
        combined_messages = task.memory + [task.react.messages[0]]
        
        return HopilotPayload(
            system_instructions="당신은 유능한 AI Copilot입니다.",
            messages=combined_messages,
            context={"type": "default_hardcoded_context"},
        )
