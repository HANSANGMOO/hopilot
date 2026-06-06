from pydantic import BaseModel, Field
from contracts.signal import BaseSignal, BaseRequestSignal, BaseEventSignal, BaseStreamSignal
from core.models import HOChunk

class SendUserRequestSignal(BaseStreamSignal):
    """사용자가 프론트엔드에서 입력한 요구사항(Prompt)을 백엔드 에이전트로 전송하는 외부 시그널입니다. (SignalBus용)"""
    session_id: str = Field(..., description="현재 대화 세션의 고유 ID")
    query: str = Field(..., description="사용자가 입력한 요구사항 텍스트")

class CopilotChunkSignal(BaseSignal):
    """백엔드 Copilot 에이전트가 생성한 출력(청크)을 프론트엔드로 전송하는 외부 시그널입니다. (SignalBus용)"""
    session_id: str = Field(..., description="현재 대화 세션의 고유 ID")
    message_id: str = Field(..., description="이 청크가 속한 메시지의 고유 ID")
    role: str = Field(default="ai", description="'user', 'ai', or 'system'")
    chunk: HOChunk = Field(..., description="순수 도메인 청크 데이터")
