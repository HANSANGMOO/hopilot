from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union
from datetime import datetime

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
    role: str = Field(..., description="'user', 'assistant', or 'system'")
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
    settings: dict = Field(default_factory=dict, description="Session-specific settings (e.g., target model, temperature)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
