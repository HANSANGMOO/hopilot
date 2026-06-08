from core.models import CopilotPrompt, CopilotTask
from utils import get_logger

logger = get_logger("PromptEngine")


class PromptEngine:
    """
    사용자의 요청(Query)과 컨텍스트를 바탕으로 LLM에게 보낼 프롬프트를 구성하고,
    ReAct 사이클에 필요한 파라미터나 시스템 프롬프트를 조립하는 엔진입니다.
    """

    def __init__(self):
        logger.info("PromptEngine initialized.")

    async def build_request(self, task: CopilotTask) -> CopilotPrompt:
        """
        CopilotTask를 받아서 내부 도메인 모델인 CopilotPrompt로 변환합니다.
        """
        return CopilotPrompt(
            system_instructions="당신은 유능한 AI Copilot입니다.",
            history=task.memory,
            context={"type": "default_hardcoded_context"},
            query=task.query,
        )
