import asyncio
from typing import AsyncGenerator

from api.api_manager import ApiManager
from core.bus import EventBus
from contracts.copilot import CopilotRunStreamDTO
from core.models import (
    AgentCallbacks,
    CopilotInput,
    CopilotTask,
    HOChunk,
    HOMessage,
    HOreAct,
    TextPayload,
)
from engine.agent_worker import AgentWorker
from engine.payload_engine import PayloadEngine


class CopilotService:
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
    ) -> AsyncGenerator[CopilotRunStreamDTO, None]:
        session     = dto.session
        ask         = dto.ask
        model       = dto.model
        tool_set    = dto.tool_set
        context     = dto.context
        attachments = dto.attachments

        react = HOreAct()

        # 1. User message (attachment chunks + text)
        attachment_chunks = [HOChunk(payload=a.as_payload()) for a in (attachments or [])]
        user_msg = HOMessage(
            role="user",
            chunks=attachment_chunks + [HOChunk(payload=TextPayload(text=ask))],
            react_id=react.react_id,
        )
        react.messages.append(user_msg)
        for chunk in user_msg.chunks:
            yield CopilotRunStreamDTO(
                chunk=chunk,
                msg_id=user_msg.message_id,
                session_id=session.session_id,
                role=user_msg.role,
                timestamp=user_msg.timestamp.isoformat(),
            )

        # 2. System message
        system_msg = HOMessage(
            role="system",
            chunks=[HOChunk(payload=TextPayload(text="요청을 처리하는 중입니다. 잠시만 기다려주세요..."))],
            react_id=react.react_id,
        )
        yield CopilotRunStreamDTO(
            chunk=system_msg.chunks[0],
            msg_id=system_msg.message_id,
            session_id=session.session_id,
            role=system_msg.role,
            timestamp=system_msg.timestamp.isoformat(),
        )

        # 3. AI message (placeholder, chunks filled during streaming)
        ai_msg = HOMessage(
            role="ai",
            react_id=react.react_id,
            model_name=model.display_name if model else None,
        )
        react.messages.append(ai_msg)

        # 4. Task 생성
        payload_engine = self.payload_engine
        api_manager    = self.api_manager

        task = CopilotTask(
            session_id=session.session_id,
            memory=session.messages,
            model=model,
            tools=tool_set.tools if tool_set else None,
            react=react,
            attachments=attachments,
            context=context,
        )

        # 5. Callbacks
        callbacks = AgentCallbacks(
            payload_builder=payload_engine.build_payload,
            stream_opener=lambda p: api_manager.generate_stream(p, model_info=task.model),
            tool_executor=tool_set.execute_tools if tool_set else None,
        )

        # 6. 스트리밍
        try:
            async for chunk_dto in self.agent_worker.run(task=task, callbacks=callbacks):
                yield chunk_dto
        except asyncio.CancelledError:
            ai_msg.append_notice("\n\n사용자의 요청에 의해 취소 되었습니다.")
            raise
        finally:
            # 7. 정상 완료 또는 취소 모두 react 메시지(부분 포함)를 세션에 병합
            session.messages.extend(react.messages)
