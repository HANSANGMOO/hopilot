from pydantic import BaseModel
from contracts.signal import BaseInboundRequestSignal


class ModelListSignal(BaseInboundRequestSignal):
    """사용 가능한 LLM 모델 목록을 요청하는 신호입니다."""
    method: str = "model/list"
    params: dict = {}


class ModelDTO(BaseModel):
    """프론트엔드 모델 선택 UI에 필요한 최소 DTO입니다."""
    id: str
    display_name: str
    provider: str
    is_available: bool
    is_default: bool = False
