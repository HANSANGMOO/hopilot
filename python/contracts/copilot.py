from typing import List
from typing_extensions import TypedDict

from pydantic import BaseModel, Field

from contracts.signal import BaseStreamSignal
from core.models import HOChunk


class CopilotRunParams(TypedDict, total=False):
    session_id: str
    query: str
    model_id: str
    project_id: str
    attachment_ids: List[str]
    tool_ids: List[str]


class CopilotRunStreamSignal(BaseStreamSignal):
    """사용자의 쿼리를 Copilot 에이전트로 전송하고 스트리밍 응답을 받는 신호입니다."""

    method: str = "copilot/run"
    params: CopilotRunParams


class CopilotRunStreamDTO(BaseModel):
    """AgentWorker가 생성하여 Handler 계층으로 전달하는 스트리밍 청크 데이터입니다."""

    chunk: HOChunk
    msg_id: str
    session_id: str
    role: str = Field(..., description="'user', 'ai', or 'system'")
    timestamp: str = Field(..., description="메시지 생성 시각 (ISO 8601)")
