from typing import AsyncGenerator

from api.api_manager import ApiManager
from core.bus import EventBus
from core.models import (
    CopilotChunkDTO,
    CopilotInput,
    CopilotTask,
    HOChunk,
    HOMessage,
    HOreAct,
    HopilotPayload,
    TextPayload,
)
from engine.agent_worker import AgentWorker
from engine.payload_engine import PayloadEngine


class CopilotService:
    """
    Core business logic for the Copilot AI engine.
    Orchestrates the LLM API calls, manages the ReAct cycle, and streams chunks.
    """

    def __init__(
        self,
        event_bus: EventBus,
        api_manager: ApiManager,
        payload_engine: PayloadEngine,
        agent_worker: AgentWorker,
    ):
        self.event_bus = event_bus
        self.api_manager = api_manager
        self.payload_engine = payload_engine
        self.agent_worker = agent_worker

    async def process_user_request(
        self, dto: CopilotInput
    ) -> AsyncGenerator[CopilotChunkDTO, None]:  # noqa: E501
        """
        사용자의 요청을 받아 시스템 메시지와 사용자 메시지를 생성하고 내부 이벤트를 발생시킵니다.
        """
        # 0. HOreAct 사이클 초기화
        react = HOreAct()

        # 1. User Message 생성 및 이벤트 퍼블리시
        user_payload = TextPayload(text=dto.query)
        user_chunk = HOChunk(payload=user_payload)
        user_msg = HOMessage(role="user", chunks=[user_chunk], react_id=react.react_id)
        react.messages.append(user_msg)

        yield CopilotChunkDTO(
            chunk=user_msg.chunks[0],
            msg_id=user_msg.message_id,
            session_id=dto.session.session_id,
            role=user_msg.role,
        )

        # 2. System Message 생성 및 이벤트 퍼블리시
        system_payload = TextPayload(text="요청을 처리하는 중입니다. 잠시만 기다려주세요...")
        system_chunk = HOChunk(payload=system_payload)
        system_msg = HOMessage(role="system", chunks=[system_chunk], react_id=react.react_id)
        react.messages.append(system_msg)

        yield CopilotChunkDTO(
            chunk=system_msg.chunks[0],
            msg_id=system_msg.message_id,
            session_id=dto.session.session_id,
            role=system_msg.role,
        )

        # 3. AI Message (Placeholder) 생성 (이벤트 퍼블리시는 생략)
        ai_msg = HOMessage(role="ai", react_id=react.react_id)
        react.messages.append(ai_msg)

        # 4. CopilotTask 생성 (평탄화 및 매핑)
        task = CopilotTask(
            session_id=dto.session.session_id,
            memory=dto.session.messages,
            model=dto.model,
            react=react,
        )

        # 5. AgentWorker용 콜백 정의 (Closure Pattern)
        payload_engine = self.payload_engine
        api_manager = self.api_manager

        class Callbacks:
            async def payload_builder(self, task) -> HopilotPayload:
                return await payload_engine.build_payload(task)

            def stream_opener(self, payload: HopilotPayload):
                return api_manager.generate_stream(payload, model_info=task.model)

        callbacks = Callbacks()

        # 6. AgentWorker의 AI 스트림을 그대로 중계 (return ❌ → async for + yield ✅)
        async for chunk_dto in self.agent_worker.run(task=task, callbacks=callbacks):
            yield chunk_dto
