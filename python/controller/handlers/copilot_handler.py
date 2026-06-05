from utils import get_logger
from services.copilot_service import CopilotService
from services.session_service import SessionService
from contracts.copilot import SendUserRequestSignal, CopilotChunkSignal
from typing import AsyncGenerator
from core.models import CopilotInput

logger = get_logger("CopilotHandler")

class CopilotHandler:
    def __init__(self, copilot_service: CopilotService, session_service: SessionService):
        self.copilot_service = copilot_service
        self.session_service = session_service

    async def handle_user_request(self, signal: SendUserRequestSignal) -> AsyncGenerator[CopilotChunkSignal, None]:
        """
        웹소켓으로 들어온 사용자의 외부 시그널(SendUserRequestSignal)을 
        내부 비즈니스 로직용 순수 데이터(CopilotInput)로 번역하여 전달합니다.
        또한, 반환되는 도메인 스트림을 다시 외부 시그널(CopilotChunkSignal)로 래핑하여 배출합니다.
        """
        logger.info(f"Processing user request: '{signal.query}' for session {signal.session_id}")
        
        # 1. 세션 조회 또는 생성
        session = None
        if signal.session_id:
            session = await self.session_service.get_session(signal.session_id)
            
        if not session:
            logger.info(f"Session '{signal.session_id}' not found or empty. Creating a new session.")
            session = await self.session_service.create_session()

        # 2. DTO 생성 (번역 작업)
        input_dto = CopilotInput(
            session=session,
            query=signal.query
        )
        
        # 3. Service 계층으로 DTO 전달 및 Generator 반환받기
        domain_stream = self.copilot_service.process_user_request(input_dto)
        
        # 4. 도메인 스트림(AgentChunkDTO)을 외부 시그널(CopilotChunkSignal)로 매핑하여 리턴
        async for response_dto in domain_stream:
            yield CopilotChunkSignal(
                session_id=response_dto.session_id,
                message_id=response_dto.msg_id,
                role=response_dto.role,
                chunk=response_dto.chunk
            )
