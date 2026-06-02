from pydantic import Field
from core.bus import BaseEvent
from contracts.signal import BaseSignal
from core.models import HOChunk

class ChunkGenerationEvent(BaseEvent):
    """
    LLM의 스트리밍 청크가 생성되었을 때 발생하는 내부 이벤트입니다. (EventBus용)
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
    chunk: str = Field(..., description="LLM 텍스트 청크")
    is_done: bool = Field(default=False, description="스트리밍 완료 여부")
