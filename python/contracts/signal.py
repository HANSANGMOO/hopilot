from typing import Union
from typing_extensions import TypedDict

from core.bus.signal import (
    BaseEventSignal,
    BaseInboundRequestSignal,
    BaseOutboundRequestSignal,
    BaseSignal,
    BaseStreamSignal,
)

__all__ = [
    "BaseSignal",
    "BaseInboundRequestSignal",
    "BaseOutboundRequestSignal",
    "BaseEventSignal",
    "BaseStreamSignal",
    "CancelEventSignal",
]


class CancelRequestParams(TypedDict):
    id: Union[str, int]


class CancelEventSignal(BaseEventSignal):
    """
    프론트엔드에서 백엔드의 특정 태스크(id) 취소를 요청하는 시그널입니다.
    LSP의 `$/cancelRequest` 규격을 모방합니다.
    """
    method: str = "$/cancelRequest"
    params: CancelRequestParams
