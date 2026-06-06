from utils import get_logger
from core.bus import EventBus
from core.models import CopilotTask, CopilotRequest, HOMessage, HOChunk, AgentCallbacks, CopilotChunkDTO

logger = get_logger("AgentWorker")

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
        
        try:
            # 1. 프롬프트 조립 콜백 실행 (Request Engine 위임)
            request = await callbacks.build_request(task)
            
            # 2. task.react에 담긴 마지막 메시지(AI Placeholder)와 세션 객체 획득
            ai_message = task.react.messages[-1]
            session = task.input_dto.session
            
            # 3. 스트림 오픈 콜백 실행 및 순회 (Api Manager 위임)
            async for chunk in callbacks.stream_opener(request):
                
                # 4. 부모 메시지의 chunks 리스트에 방금 온 조각 추가 (상태 업데이트)
                ai_message.chunks.append(chunk)
                
                # 5. 프론트엔드 라우팅 정보를 포함한 DTO 조립 및 배출
                yield CopilotChunkDTO(
                    chunk=chunk,
                    msg_id=ai_message.message_id,
                    session_id=session.session_id,
                    role=ai_message.role
                )
                
            logger.info(f"[AgentWorker] 스트리밍 완료 - 태스크: {task.task_id}")
            
        except Exception as e:
            logger.error(f"[AgentWorker] 스트리밍 중 에러 발생: {e}")
