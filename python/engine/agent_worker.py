import uuid
from typing import Callable, AsyncGenerator, Awaitable, List
from utils import get_logger
from core.bus import EventBus
from core.models import CopilotRequestDTO, HOMessage, HOChunk
from contracts.copilot import ChunkGenerationEvent

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
        dto: CopilotRequestDTO, 
        request_builder: Callable[[CopilotRequestDTO], Awaitable[List[HOMessage]]], 
        stream_opener: Callable[[List[HOMessage]], AsyncGenerator[HOChunk, None]]
    ):
        """
        DTO와 두 개의 콜백(프롬프트 조립, 스트림 오픈)을 받아 
        실시간으로 Chunk를 생성하고 EventBus로 퍼블리시합니다.
        """
        logger.info(f"[AgentWorker] 스트리밍 시작 - 세션: {dto.session_id}")
        
        try:
            # 1. 프롬프트 조립 콜백 실행 (Request Engine 위임)
            request = await request_builder(dto)
            
            # 2. 메시지 고유 ID (생성되는 모든 청크가 이 ID를 공유)
            msg_id = str(uuid.uuid4())
            
            # 3. 스트림 오픈 콜백 실행 및 순회 (Api Manager 위임)
            async for chunk in stream_opener(request):
                self.event_bus.publish(ChunkGenerationEvent(
                    chunk=chunk,
                    msg_id=msg_id,
                    session_id=dto.session_id,
                    role="ai"
                ))
                
            logger.info(f"[AgentWorker] 스트리밍 완료 - 세션: {dto.session_id}")
            
        except Exception as e:
            logger.error(f"[AgentWorker] 스트리밍 중 에러 발생: {e}")
