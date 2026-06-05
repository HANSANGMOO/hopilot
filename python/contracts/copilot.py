from pydantic import BaseModel, Field
from typing import Protocol, AsyncGenerator
from contracts.signal import BaseSignal
from core.models import HOChunk, CopilotTask, CopilotRequest

class AgentCallbacks(Protocol):
    """AgentWorker가 작업을 수행할 때 호출하는 콜백(포인터)들의 집합입니다."""
    
    async def build_request(self, task: CopilotTask) -> CopilotRequest:
        """CopilotTask를 받아서 LLM API 요청용 모델(CopilotRequest)로 변환합니다."""
        ...
        
    def stream_opener(self, request: CopilotRequest) -> AsyncGenerator[HOChunk, None]:
        """LLM API 스트림을 열고 실시간 청크를 생성합니다."""
        ...

class CopilotChunkDTO(BaseModel):
    """
    AgentWorker가 내부적으로 생성하여 Handler 계층으로 전달하는 스트리밍 청크 데이터입니다.
    """
    chunk: HOChunk
    msg_id: str
    session_id: str
    role: str = Field(..., description="'user', 'ai', or 'system'")

class SendUserRequestSignal(BaseSignal):
    """사용자가 프론트엔드에서 입력한 요구사항(Prompt)을 백엔드 에이전트로 전송하는 외부 시그널입니다. (SignalBus용)"""
    session_id: str = Field(..., description="현재 대화 세션의 고유 ID")
    query: str = Field(..., description="사용자가 입력한 요구사항 텍스트")

class CopilotChunkSignal(BaseSignal):
    """백엔드 Copilot 에이전트가 생성한 출력(청크)을 프론트엔드로 전송하는 외부 시그널입니다. (SignalBus용)"""
    session_id: str = Field(..., description="현재 대화 세션의 고유 ID")
    message_id: str = Field(..., description="이 청크가 속한 메시지의 고유 ID")
    role: str = Field(default="ai", description="'user', 'ai', or 'system'")
    chunk: HOChunk = Field(..., description="순수 도메인 청크 데이터")
