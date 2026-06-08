from typing import AsyncGenerator

from contracts.copilot import SendUserRequestSignal
from core.models import CopilotChunkDTO, CopilotInput, ModelInfo
from services.copilot_service import CopilotService
from services.llm_model_service import LlmModelService
from services.session_service import SessionService
from utils import get_logger

logger = get_logger("CopilotHandler")

class CopilotHandler:
    def __init__(self, copilot_service: CopilotService, session_service: SessionService, llm_model_service: LlmModelService):
        self.copilot_service = copilot_service
        self.session_service = session_service
        self.llm_model_service = llm_model_service

    async def handle_user_request(self, signal: SendUserRequestSignal) -> AsyncGenerator[CopilotChunkDTO, None]:
        """
        웹소켓으로 들어온 사용자의 외부 시그널(SendUserRequestSignal)을 
        내부 비즈니스 로직용 순수 데이터(CopilotInput)로 번역하여 전달합니다.
        스트림 응답 시 SignalBus가 자동으로 JSON-RPC Notification으로 포장해주므로
        도메인 스트림(CopilotChunkDTO)을 변환 없이 그대로 배출합니다.
        """
        params = signal.params or {}
        session_id = params.get("session_id")
        query = params.get("query", "")
        model_id = params.get("model_id")

        logger.info(f"Processing user request: '{query}' for session {session_id}")

        # 1. 세션 조회 또는 생성
        session = None
        if session_id:
            session = await self.session_service.get_session(session_id)

        if not session:
            logger.info(f"Session '{session_id}' not found or empty. Creating a new session.")
            session = await self.session_service.create_session()

        # 2. 모델 정보 구성
        model_info = None
        if model_id:
            available_models = self.llm_model_service.load_models()
            matched_model = next((m for m in available_models if m.get("id") == model_id), None)
            if matched_model:
                provider = matched_model.get("provider", "")
                api_key = self.llm_model_service.get_api_key(provider)
                model_info = ModelInfo(
                    id=matched_model.get("id", ""),
                    provider=provider,
                    display_name=matched_model.get("display_name", ""),
                    api_key=api_key
                )
            else:
                logger.warning(f"Model ID '{model_id}' not found in configuration.")
        else:
            default_model = self.llm_model_service.get_default_model()
            if default_model:
                provider = default_model.get("provider", "")
                api_key = self.llm_model_service.get_api_key(provider)
                model_info = ModelInfo(
                    id=default_model.get("id", ""),
                    provider=provider,
                    display_name=default_model.get("display_name", ""),
                    api_key=api_key
                )

        # 3. DTO 생성 (번역 작업)
        input_dto = CopilotInput(
            session=session,
            query=query,
            model=model_info
        )

        # 4. Service 계층으로 DTO 전달 및 Generator 반환받기
        domain_stream = self.copilot_service.process_user_request(input_dto)

        # 5. 도메인 스트림(CopilotChunkDTO)을 그대로 배출
        async for response_dto in domain_stream:
            yield response_dto
