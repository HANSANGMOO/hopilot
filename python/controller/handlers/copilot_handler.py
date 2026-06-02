from utils import get_logger
from services.copilot_service import CopilotService
from contracts.copilot import SendUserRequestSignal
from core.models import CopilotRequestDTO

logger = get_logger("CopilotHandler")

class CopilotHandler:
    def __init__(self, copilot_service: CopilotService):
        self.copilot_service = copilot_service

    async def handle_user_request(self, signal: SendUserRequestSignal) -> None:
        """
        웹소켓으로 들어온 사용자의 외부 시그널(SendUserRequestSignal)을 
        내부 비즈니스 로직용 순수 데이터(CopilotRequestDTO)로 번역하여 전달합니다.
        """
        logger.info(f"Processing user request: '{signal.query}' for session {signal.session_id}")
        
        # 1. DTO 생성 (번역 작업)
        dto = CopilotRequestDTO(
            session_id=signal.session_id,
            query=signal.query
        )
        
        # 2. Service 계층으로 DTO 전달
        await self.copilot_service.process_user_request(dto)
