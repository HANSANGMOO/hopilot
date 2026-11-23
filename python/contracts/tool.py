from typing import List, Optional

from pydantic import BaseModel
from contracts.signal import BaseInboundRequestSignal


class ToolListSignal(BaseInboundRequestSignal):
    """사용 가능한 Tool 목록을 요청하는 신호입니다."""
    method: str = "tool/list"
    params: dict = {}


class ToolItemDTO(BaseModel):
    """단일 도구 정보 DTO입니다."""
    id: str
    name: str
    description: str


class ToolGroupDTO(BaseModel):
    """출처(MCP 서버 또는 built-in)로 묶인 도구 그룹 DTO입니다."""
    source: str
    tools: List[ToolItemDTO]
    error: Optional[str] = None
