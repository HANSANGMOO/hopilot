from typing import Literal, Optional
from typing_extensions import NotRequired, TypedDict

from pydantic import BaseModel

from contracts.signal import BaseEventSignal, BaseInboundRequestSignal


# ==========================================
# Request Params (TypedDict)
# ==========================================

class AttachmentLoadParams(TypedDict):
    path: str
    name: str
    mime_type: str
    data: NotRequired[str]  # base64 — present for inline (clipboard paste)


class AttachmentUnloadParams(TypedDict):
    id: str


class AttachmentGetParams(TypedDict):
    id: str


class AttachmentDeleteParams(TypedDict):
    id: str


# ==========================================
# Request Signals
# ==========================================

class AttachmentLoadSignal(BaseInboundRequestSignal):
    """파일을 읽어 메모리에 올리고 처리 결과를 반환하는 신호입니다."""
    method: str = "attachment/load"
    params: AttachmentLoadParams


class AttachmentUnloadSignal(BaseEventSignal):
    """메모리에서 첨부 파일을 제거하는 신호입니다."""
    method: str = "attachment/unload"
    params: AttachmentUnloadParams


class AttachmentGetSignal(BaseInboundRequestSignal):
    """메모리에서 첨부 파일 데이터를 조회하는 신호입니다."""
    method: str = "attachment/get"
    params: AttachmentGetParams


class AttachmentDeleteSignal(BaseEventSignal):
    """메모리에서 제거하고 디스크 파일도 삭제하는 신호입니다 (inline 전용)."""
    method: str = "attachment/delete"
    params: AttachmentDeleteParams


# ==========================================
# Response DTOs
# ==========================================

class AttachmentLoadDTO(BaseModel):
    """첨부 파일 처리 결과 DTO."""
    id: str
    restriction: Optional[Literal["encrypted", "drm", "permission", "mip"]] = None


class AttachmentGetDTO(BaseModel):
    """첨부 파일 데이터 조회 결과 DTO."""
    id: str
    name: str
    data: str
    mime_type: str
    type: Literal["image", "document"]
    encoding: Optional[str] = None
    ref: Optional[str] = None
