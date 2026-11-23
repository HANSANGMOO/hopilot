from typing import Optional
from typing_extensions import TypedDict
from pydantic import BaseModel

from contracts.signal import BaseInboundRequestSignal


# ==========================================
# Request Params (TypedDict)
# ==========================================

class ProjectCreateParams(TypedDict):
    name: str
    workspace: str

class ProjectLoadParams(TypedDict):
    project_id: str

class ProjectDeleteParams(TypedDict):
    project_id: str

class ProjectPatch(TypedDict, total=False):
    name: str
    workspace: str

class ProjectUpdateParams(TypedDict):
    project_id: str
    patch: ProjectPatch


# ==========================================
# Request Signals
# ==========================================

class ProjectListSignal(BaseInboundRequestSignal):
    method: str = "project/list"
    params: dict = {}

class ProjectCreateSignal(BaseInboundRequestSignal):
    method: str = "project/create"
    params: ProjectCreateParams

class ProjectLoadSignal(BaseInboundRequestSignal):
    method: str = "project/load"
    params: ProjectLoadParams

class ProjectDeleteSignal(BaseInboundRequestSignal):
    method: str = "project/delete"
    params: ProjectDeleteParams

class ProjectUpdateSignal(BaseInboundRequestSignal):
    method: str = "project/update"
    params: ProjectUpdateParams


# ==========================================
# Response DTOs
# ==========================================

class ProjectMetaDTO(BaseModel):
    id: str
    name: str
    workspace: str
    updated_at: str

class ProjectDetailDTO(BaseModel):
    id: str
    name: str
    workspace: str
    updated_at: str
