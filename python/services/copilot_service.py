import uuid
import asyncio
from core.models import CopilotRequestDTO, HOMessage, TextPayload, HOChunk
from contracts.copilot import ChunkGenerationEvent
from core.bus import EventBus
from api.api_manager import ApiManager
from engine.request_engine import RequestEngine
from engine.agent_worker import AgentWorker

class CopilotService:
    """
    Core business logic for the Copilot AI engine.
    Orchestrates the LLM API calls, manages the ReAct cycle, and streams chunks.
    """
    
    def __init__(self, event_bus: EventBus, api_manager: ApiManager, request_engine: RequestEngine, agent_worker: AgentWorker):
        self.event_bus = event_bus
        self.api_manager = api_manager
        self.request_engine = request_engine
        self.agent_worker = agent_worker
        
    async def process_user_request(self, dto: CopilotRequestDTO):
        """
        사용자의 요청을 받아 시스템 메시지와 사용자 메시지를 생성하고 내부 이벤트를 발생시킵니다.
        """
        # 1. User Message 생성 및 이벤트 퍼블리시
        user_msg_id = str(uuid.uuid4())
        user_payload = TextPayload(text=dto.query)
        
        user_chunk = HOChunk(chunk_id=str(uuid.uuid4()), payload=user_payload)
        self.event_bus.publish(ChunkGenerationEvent(
            chunk=user_chunk,
            msg_id=user_msg_id,
            session_id=dto.session_id,
            role="user"
        ))
        
        # 2. System Message 생성 및 이벤트 퍼블리시
        system_msg_id = str(uuid.uuid4())
        system_payload = TextPayload(text="요청을 처리하는 중입니다. 잠시만 기다려주세요...")
        
        system_chunk = HOChunk(chunk_id=str(uuid.uuid4()), payload=system_payload)
        self.event_bus.publish(ChunkGenerationEvent(
            chunk=system_chunk,
            msg_id=system_msg_id,
            session_id=dto.session_id,
            role="system"
        ))
        
        # 3. Agent Worker에게 비동기 작업 위임 (콜백 주입)
        # 웹소켓 핸들러의 응답성을 위해 백그라운드 태스크로 띄웁니다.
        asyncio.create_task(
            self.agent_worker.run(
                dto=dto,
                request_builder=self.request_engine.build_messages,
                stream_opener=self.api_manager.stream_generate
            )
        )
