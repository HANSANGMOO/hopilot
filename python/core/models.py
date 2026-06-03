from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union
from datetime import datetime
import json

# 도메인 모델의 기준이 되는 현재 스키마 버전 (DB 계층이 이를 참조합니다)
SCHEMA_VERSION = 1

# ==========================================
# Level 1: Payloads (최하위 다형성 데이터 요소)
# ==========================================
class PayloadBase(BaseModel):
    type: str

class TextPayload(PayloadBase):
    type: str = "text"
    text: str

class ImagePayload(PayloadBase):
    type: str = "image"
    image_url: str  # URL or base64 encoded string

class ThoughtPayload(PayloadBase):
    type: str = "thought"
    thought: str

class ToolCallPayload(PayloadBase):
    type: str = "tool_call"
    tool_name: str
    tool_args: dict

class ToolOutputPayload(PayloadBase):
    type: str = "tool_output"
    tool_name: str
    output: str

class StreamPayload(PayloadBase):
    type: str = "stream_end"
    finish_reason: Optional[str] = None

# Union type to allow any specific payload type
Payload = Union[
    TextPayload,
    ImagePayload,
    ThoughtPayload,
    ToolCallPayload,
    ToolOutputPayload,
    StreamPayload
]

# ==========================================
# Level 2: HOChunk (단일 Payload 전송 단위)
# ==========================================
class HOChunk(BaseModel):
    chunk_id: str = Field(..., description="Unique identifier for the chunk to ensure ordering")
    payload: Payload = Field(..., description="The single payload carried by this chunk")

# ==========================================
# Level 3: HOMessage (조립된 단일 메시지 단위)
# ==========================================
class HOMessage(BaseModel):
    message_id: str
    role: str = Field(..., description="'user', 'ai', or 'system'")
    payloads: List[Payload] = Field(default_factory=list, description="Ordered list of payloads comprising this message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# ==========================================
# Level 4: HOreAct (추론/행동 논리적 묶음)
# ==========================================
class HOreAct(BaseModel):
    step_id: str
    messages: List[HOMessage] = Field(default_factory=list, description="Messages belonging to this logical ReAct cycle")
    status: str = Field(default="pending", description="'pending', 'running', 'completed', or 'failed'")

# ==========================================
# Level 5: HOSession (전체 대화 세션)
# ==========================================
class HOSession(BaseModel):
    session_id: str
    title: str = Field(default="New Session")
    messages: List[HOMessage] = Field(default_factory=list, description="Full chat history of the session")
    meta: dict = Field(default_factory=dict, description="Prompt, workspace, tool_list 등 기능적 설정값")
    schema_version: int = Field(default=SCHEMA_VERSION, description="세션 생성 당시의 DB 스키마 버전")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_db_dict(self) -> dict:
        """DB 저장을 위해 중첩된 객체(messages, meta)를 JSON 문자열로 변환한 딕셔너리를 반환합니다."""
        dumped = self.model_dump(mode='json')
        return {
            "id": self.session_id,
            "title": self.title,
            "meta": json.dumps(dumped.get("meta", {}), ensure_ascii=False),
            "messages": json.dumps(dumped.get("messages", []), ensure_ascii=False),
            "schema_version": dumped.get("schema_version"),
            "created_at": dumped.get("created_at"),
            "updated_at": dumped.get("updated_at")
        }

    @classmethod
    def from_db_dict(cls, data: dict) -> "HOSession":
        """DB에서 조회한 딕셔너리(JSON 문자열 포함)를 파싱하여 HOSession 객체로 복원합니다."""
        parsed_data = dict(data)
        
        # DB 컬럼 'id'를 Pydantic 모델의 'session_id'로 매핑
        if "id" in parsed_data:
            parsed_data["session_id"] = parsed_data.pop("id")
            
        # JSON 문자열 역직렬화
        if isinstance(parsed_data.get("meta"), str):
            try:
                parsed_data["meta"] = json.loads(parsed_data["meta"])
            except json.JSONDecodeError:
                parsed_data["meta"] = {}
                
        if isinstance(parsed_data.get("messages"), str):
            try:
                parsed_data["messages"] = json.loads(parsed_data["messages"])
            except json.JSONDecodeError:
                parsed_data["messages"] = []
                
        return cls.model_validate(parsed_data)

# ==========================================
# Data Transfer Objects (DTOs)
# ==========================================
class CopilotRequestDTO(BaseModel):
    """
    Handler 계층에서 Service 계층으로 데이터를 넘길 때 사용하는 순수 데이터 전송 객체입니다.
    """
    session_id: str
    query: str

class CopilotRequest(BaseModel):
    """
    Service/Engine 계층에서 처리되는 내부 도메인 모델입니다.
    """
    session_id: str
    system_instructions: str
    history: List[HOMessage] = Field(default_factory=list)
    context: dict = Field(default_factory=dict)
    query: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

