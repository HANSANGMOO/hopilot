from typing import List, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel

from contracts.signal import BaseInboundRequestSignal


# ==========================================
# Request Params (TypedDict)
# ==========================================

class SessionLoadParams(TypedDict):
    session_id: str

class SessionCreateParams(TypedDict, total=False):
    title: str
    project_id: Optional[str]

class SessionDeleteParams(TypedDict):
    session_id: str

class SessionPatch(TypedDict, total=False):
    title: str
    project_id: Optional[str]

class SessionUpdateParams(TypedDict):
    session_id: str
    patch: SessionPatch

class SessionTruncateParams(TypedDict):
    session_id: str
    message_id: str  # 이 메시지부터 끝까지 제거

class SessionForkParams(TypedDict, total=False):
    session_id: str
    message_id: str  # 이 메시지 직전까지 복사
    project_id: Optional[str]  # 지정 시 원본 세션의 project_id 대신 사용


# ==========================================
# Request Signals
# ==========================================

class SessionListSignal(BaseInboundRequestSignal):
    """세션 목록을 요청하는 신호입니다."""
    method: str = "session/list"
    params: dict = {}

class SessionLoadSignal(BaseInboundRequestSignal):
    """특정 세션의 전체 데이터(메시지 포함)를 요청하는 신호입니다."""
    method: str = "session/load"
    params: SessionLoadParams

class SessionCreateSignal(BaseInboundRequestSignal):
    """새 세션을 생성하는 신호입니다."""
    method: str = "session/create"
    params: SessionCreateParams

class SessionDeleteSignal(BaseInboundRequestSignal):
    """세션을 삭제하는 신호입니다."""
    method: str = "session/delete"
    params: SessionDeleteParams

class SessionUpdateSignal(BaseInboundRequestSignal):
    """세션 정보를 변경하는 신호입니다."""
    method: str = "session/update"
    params: SessionUpdateParams

class SessionTruncateSignal(BaseInboundRequestSignal):
    """특정 메시지부터 끝까지 제거하는 신호입니다."""
    method: str = "session/truncate"
    params: SessionTruncateParams

class SessionForkSignal(BaseInboundRequestSignal):
    """특정 메시지 직전까지 복사하여 새 세션을 생성하는 신호입니다."""
    method: str = "session/fork"
    params: SessionForkParams


# ==========================================
# Response DTOs
# ==========================================

class TokensDTO(BaseModel):
    """UsagePayload 토큰 수치를 묶는 서브 DTO."""
    input: int
    output: int
    thinking: Optional[int] = None
    cached: Optional[int] = None
    cache_creation: Optional[int] = None
    total: Optional[int] = None


class ToolBlockDTO(BaseModel):
    """tool 타입 블록의 서브 DTO."""
    name: str
    args: dict = {}
    output: Optional[str] = None


class BlockDTO(BaseModel):
    """HOChunk.payload를 평탄화한 DTO. 프론트엔드 ContentBlock에 대응합니다."""
    type: str                           # 'text' | 'thought' | 'tool' | 'image' | 'document' | 'usage'
    text: Optional[str] = None          # type: 'text'
    thought: Optional[str] = None       # type: 'thought'
    tool: Optional[ToolBlockDTO] = None  # type: 'tool'
    tokens: Optional[TokensDTO] = None  # type: 'usage'
    ref: Optional[str] = None           # type: 'image' | 'document'
    name: Optional[str] = None          # type: 'document'
    mime_type: Optional[str] = None     # type: 'document'


class MessageDTO(BaseModel):
    """HOMessage의 UI 필요 필드만 노출하는 DTO. 프론트엔드 Message에 대응합니다."""
    id: str               # HOMessage.message_id
    role: str             # 'user' | 'ai' | 'system'
    blocks: List[BlockDTO]
    timestamp: str        # ISO 8601
    model_name: Optional[str] = None  # AI 메시지 생성에 사용된 모델 display_name


class SessionMetaDTO(BaseModel):
    """세션 목록 표시용 최소 DTO (NavPanel용)."""
    id: str        # HOSession.session_id
    title: str
    updated_at: str  # ISO 8601
    project_id: Optional[str] = None


class SessionDetailDTO(BaseModel):
    """세션 전체 데이터 DTO (CopilotBody용)."""
    id: str
    title: str
    messages: List[MessageDTO]
    updated_at: str
