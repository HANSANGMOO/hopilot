import asyncio

from contracts.copilot import CopilotRunStreamDTO
from core.bus import EventBus
from core.errors import HopilotError
from core.models import (
    AgentCallbacks,
    CopilotTask,
    EType,
    HOChunk,
    HOMessage,
    StreamPayload,
    ToolCallPayload,
)
from utils import get_logger

logger = get_logger("AgentWorker")


def _make_error_dto(message: str, session_id: str, ai_message: HOMessage = None) -> CopilotRunStreamDTO:
    msg = ai_message or HOMessage(role="ai", chunks=[])
    return CopilotRunStreamDTO(
        chunk=HOChunk(payload=StreamPayload(event=EType.ERROR, error_message=message)),
        msg_id=msg.message_id,
        session_id=session_id,
        role=msg.role,
        timestamp=msg.timestamp.isoformat(),
    )


class AgentWorker:
    """
    LLM 생성을 수행하고 실시간 스트리밍(Chunk)을 EventBus에 퍼블리시하는 워커 객체.
    스레드 없이 비동기(async)로 동작합니다.
    """
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        logger.info("AgentWorker initialized with EventBus.")

    async def run(
        self,
        task: CopilotTask,
        callbacks: AgentCallbacks
    ):
        """
        Task와 콜백 인터페이스(AgentCallbacks)를 받아
        실시간으로 Chunk를 생성하고 AsyncGenerator 형태로 배출(yield)합니다.
        """
        logger.info(f"[AgentWorker] 스트리밍 시작 - 태스크: {task.task_id}")

        session_id      = task.session_id
        model           = task.model
        react           = task.react
        payload_builder = callbacks.payload_builder
        stream_opener   = callbacks.stream_opener
        tool_executor   = callbacks.tool_executor

        try:
            payload = await payload_builder(task)
            payload.query = react.messages
            tool_map = {t.name: t for t in (task.tools or [])}
            ai_message = react.messages[-1]

            while True:
                async for chunk in stream_opener(payload):
                    ai_message.append_chunk(chunk)
                    yield CopilotRunStreamDTO(
                        chunk=chunk,
                        msg_id=ai_message.message_id,
                        session_id=session_id,
                        role=ai_message.role,
                        timestamp=ai_message.timestamp.isoformat(),
                    )

                tool_calls = [
                    c.payload for c in ai_message.chunks
                    if isinstance(c.payload, ToolCallPayload)
                ]
                if not tool_calls or not tool_executor:
                    break

                tool_result_msg = HOMessage(role="user", chunks=[], react_id=react.react_id)
                react.add_message(tool_result_msg)

                async for chunk in tool_executor(tool_calls, tool_map):
                    tool_result_msg.chunks.append(chunk)
                    yield CopilotRunStreamDTO(
                        chunk=chunk,
                        msg_id=ai_message.message_id,
                        session_id=session_id,
                        role=ai_message.role,
                        timestamp=tool_result_msg.timestamp.isoformat(),
                    )

                ai_message = HOMessage(
                    role="ai",
                    react_id=react.react_id,
                    model_name=model.display_name if model else None,
                )
                react.add_message(ai_message)

            logger.info(f"[AgentWorker] 스트리밍 완료 - 태스크: {task.task_id}")

        except asyncio.CancelledError:
            raise

        except HopilotError as e:
            logger.error(f"[AgentWorker] 에러 - 태스크: {task.task_id}, {e}")
            yield _make_error_dto(str(e), session_id, ai_message)

        except Exception as e:
            logger.error(f"[AgentWorker] 예상치 못한 에러 - 태스크: {task.task_id}", exc_info=True)
            yield _make_error_dto("알 수 없는 오류가 발생했습니다.", session_id, ai_message)
