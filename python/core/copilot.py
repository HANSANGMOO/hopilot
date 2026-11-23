import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
from enum import Enum
from pathlib import Path
from typing import (
    Annotated,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    Union,
)

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict

SCHEMA_VERSION = 2


class Tape(TypedDict):
    """객체 참조를 보관하는 세 공간. 런타임에는 일반 dict로 사용합니다."""

    history_space: dict[str, object]
    code_space: dict[str, object]
    io_space: dict[str, object]


def create_tape() -> Tape:
    """호출마다 독립적인 Tape와 공간을 생성합니다."""
    return {
        "history_space": {},
        "code_space": {},
        "io_space": {},
    }


class EType(str, Enum):
    MESSAGE_START = "message_start"
    MESSAGE_END   = "message_end"
    REACT_START   = "react_start"
    REACT_END     = "react_end"
    ERROR         = "error"


def generate_id(prefix: str, length: int = 8) -> Callable[[], str]:
    return lambda: f"{prefix}_{uuid.uuid4().hex[:length]}"


# ==========================================
# Payloads (최하위 다형성 데이터 요소)
# ==========================================
class PayloadBase(BaseModel):
    """
    Base class for all payloads.

    [Known Provider-specific Extra Attributes]
    - Gemini: `thoughtSignature` (Used to maintain reasoning and tool calls in multi-turn)
    """
    model_config = ConfigDict(extra="allow")
    type: str


class TextPayload(PayloadBase):
    type: Literal["text"] = "text"
    text: str


class ImagePayload(PayloadBase):
    type: Literal["image"] = "image"
    source_type: Literal["uri", "url", "inline"]
    encoding: Optional[Literal["base64"]] = None
    ref: str  # DB 저장용: 파일 경로(uri), URL(url), base64(inline)
    data: Optional[str] = None  # LLM API 전송용: base64 또는 URL (DB 저장 시 제외)
    mime_type: Optional[str] = None


class DocumentPayload(PayloadBase):
    type: Literal["document"] = "document"
    ref: str
    name: Optional[str] = None
    data: Optional[str] = None  # LLM API 전송용 (DB 저장 시 제외)
    mime_type: Optional[str] = None
    encoding: Optional[str] = None


class ThoughtPayload(PayloadBase):
    type: Literal["thought"] = "thought"
    thought: str


class ToolCallPayload(PayloadBase):
    type: Literal["tool_call"] = "tool_call"
    tool_name: str
    tool_args: dict


class ToolMediaItem(BaseModel):
    """도구 실행 결과에 포함된 미디어(이미지, 오디오 등) 바이너리 데이터."""
    type: Literal["image", "audio", "resource"]
    data: Optional[str] = None  # Base64 encoded media data (DB 저장 시 strip될 수 있음)
    mime_type: Optional[str] = None
    uri: Optional[str] = None


_TOOL_OUTPUT_MAX_LEN = 20000


class ToolOutputPayload(PayloadBase):
    type: Literal["tool_output"] = "tool_output"
    tool_name: str
    output: str = ""
    media: List[ToolMediaItem] = Field(default_factory=list)
    truncated: bool = False

    def __init__(self, **data):
        super().__init__(**data)
        if len(self.output) > _TOOL_OUTPUT_MAX_LEN:
            object.__setattr__(self, "output", self.output[:_TOOL_OUTPUT_MAX_LEN])
            object.__setattr__(self, "truncated", True)


class StreamPayload(PayloadBase):
    type: Literal["stream"] = "stream"
    event: EType
    finish_reason: Optional[str] = None  # message_end 시점에만 의미 있음
    error_message: Optional[str] = None  # error 시점에만 의미 있음


class UsagePayload(PayloadBase):
    """
    LLM API 호출 1회의 토큰 사용량을 담는 Payload.

    [필드 정규화 규칙]
    - output_tokens : 순수 출력 토큰 (thinking 제외)
                      Gemini → candidatesTokenCount
                      Claude → output_tokens - thinking_tokens
                      OpenAI → output_tokens - reasoning_tokens
    - thinking_tokens: 사고 과정 토큰 (항상 output과 분리)
                      Gemini → thoughtsTokenCount
                      Claude → output_tokens_details.thinking_tokens
                      OpenAI → output_tokens_details.reasoning_tokens
    - total_tokens          : 제공 시 원본 사용, 없으면 input + output + thinking 으로 계산
    - cached_tokens         : 캐시에서 읽은 토큰 (input_tokens에 포함된 값, 절감 지표)
                              Claude → cache_read_input_tokens
                              OpenAI → input_tokens_details.cached_tokens
    - cache_creation_tokens : 캐시를 새로 생성한 토큰 (비용 발생, Claude 전용)
                              Claude → cache_creation_input_tokens
    - raw                   : Provider 원본 usage 딕셔너리 (디버그/감사 전용)
    """
    type: Literal["usage"] = "usage"
    input_tokens: int
    output_tokens: int
    thinking_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None
    cache_creation_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    raw: Optional[dict] = None


Payload = Annotated[
    Union[
        TextPayload, ImagePayload, DocumentPayload, ThoughtPayload, ToolCallPayload,
        ToolOutputPayload, StreamPayload, UsagePayload,
    ],
    Field(discriminator="type"),
]


# ==========================================
# HO* 대화 구조 계층
# ==========================================
class HOChunk(BaseModel):
    payload: Payload = Field(..., description="The single payload carried by this chunk")


class HOMessage(BaseModel):
    message_id: str = Field(default_factory=generate_id("msg"))
    react_id: Optional[str] = Field(
        default=None, description="Trace ID for the ReAct cycle this message belongs to"
    )
    role: str = Field(..., description="'user', 'ai', or 'system'")
    chunks: List[HOChunk] = Field(
        default_factory=list, description="Ordered list of chunks comprising this message"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(KST))
    model_name: Optional[str] = Field(
        default=None, description="AI 응답 생성에 사용된 모델의 display_name (ai 메시지에만 설정)"
    )

    def append_chunk(self, chunk: HOChunk) -> None:
        """청크를 추가하되, 연속된 text/thought는 마지막 청크에 병합합니다.
        단, 새 청크에 model_extra가 있으면 provider 메타데이터 보존을 위해 병합하지 않습니다."""
        if self.chunks and not chunk.payload.model_extra:
            last = self.chunks[-1]
            if isinstance(chunk.payload, TextPayload) and isinstance(last.payload, TextPayload):
                last.payload.text += chunk.payload.text
                return
            if isinstance(chunk.payload, ThoughtPayload) and isinstance(last.payload, ThoughtPayload):
                last.payload.thought += chunk.payload.thought
                return
        self.chunks.append(chunk)

    def append_notice(self, text: str) -> None:
        """병합 없이 독립 텍스트 청크를 추가합니다. 취소·오류 안내 등 종단 메시지에 사용합니다."""
        self.chunks.append(HOChunk(payload=TextPayload(text=text)))


class HOreAct(BaseModel):
    react_id: str = Field(default_factory=generate_id("rct"))
    messages: List[HOMessage] = Field(
        default_factory=list, description="Messages in this ReAct cycle"
    )
    status: str = Field(
        default="pending", description="'pending', 'running', 'completed', or 'failed'"
    )

    def add_message(self, msg: "HOMessage") -> None:
        self.messages.append(msg)


def _strip_attachment_data(messages: list) -> None:
    """DB 직렬화 시 대용량 첨부 Payload의 data 필드를 제거합니다 (ref는 보존).

    - image: 항상 strip (크기 제한 없음)
    - document + base64: strip (대용량 PDF, 파일에서 재읽기)
    - document + 텍스트: 보존 (10K 토큰 이하 검증됨)
    """
    for msg in messages:
        for chunk in msg.get("chunks", []):
            payload = chunk.get("payload", {})
            if not isinstance(payload, dict):
                continue
            ptype = payload.get("type")
            if ptype == "image":
                payload.pop("data", None)
            elif ptype == "document" and payload.get("encoding") == "base64":
                payload.pop("data", None)
            elif ptype == "tool_output" and "media" in payload:
                for m in payload.get("media", []):
                    if isinstance(m, dict):
                        m.pop("data", None)


class HOSession(BaseModel):
    session_id: str = Field(default_factory=generate_id("sess"))
    project_id: Optional[str] = Field(default=None)
    title: str = Field(default="New Session")
    messages: List[HOMessage] = Field(
        default_factory=list, description="Full chat history of the session"
    )
    meta: dict = Field(
        default_factory=dict, description="Prompt, workspace, tool_list 등 기능적 설정값"
    )
    schema_version: int = Field(
        default=SCHEMA_VERSION, description="세션 생성 당시의 DB 스키마 버전"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(KST))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(KST))

    def to_db_dict(self) -> dict:
        """DB 저장을 위해 중첩된 객체(messages, meta)를 JSON 문자열로 변환한 딕셔너리를 반환합니다."""  # noqa: E501
        dumped = self.model_dump(mode="json")
        _strip_attachment_data(dumped.get("messages", []))
        return {
            "id": self.session_id,
            "project_id": self.project_id,
            "title": self.title,
            "meta": json.dumps(dumped.get("meta", {}), ensure_ascii=False),
            "messages": json.dumps(dumped.get("messages", []), ensure_ascii=False),
            "schema_version": dumped.get("schema_version"),
            "created_at": dumped.get("created_at"),
            "updated_at": dumped.get("updated_at"),
        }

    @classmethod
    def from_db_dict(cls, data: dict) -> "HOSession":
        """DB에서 조회한 딕셔너리(JSON 문자열 포함)를 파싱하여 HOSession 객체로 복원합니다."""
        parsed_data = dict(data)

        if "id" in parsed_data:
            parsed_data["session_id"] = parsed_data.pop("id")

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


class HOProject(BaseModel):
    project_id: str = Field(default_factory=generate_id("proj"))
    name: str = Field(default="New Project")
    workspace: Path
    created_at: datetime = Field(default_factory=lambda: datetime.now(KST))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(KST))

    def to_db_dict(self) -> dict:
        dumped = self.model_dump(mode="json")
        return {
            "id": self.project_id,
            "name": self.name,
            "workspace": str(self.workspace),
            "created_at": dumped.get("created_at"),
            "updated_at": dumped.get("updated_at"),
        }

    @classmethod
    def from_db_dict(cls, data: dict) -> "HOProject":
        parsed = dict(data)
        if "id" in parsed:
            parsed["project_id"] = parsed.pop("id")
        if parsed.get("workspace"):
            parsed["workspace"] = Path(parsed["workspace"])
        return cls.model_validate(parsed)


# ==========================================
# Attachment DTOs
# ==========================================
class AttachmentBase(BaseModel):
    id: str
    path: str
    name: str
    restriction: Optional[Literal["encrypted", "drm", "permission", "mip"]] = None


class ImageAttachment(AttachmentBase):
    type: Literal["image"] = "image"
    source_type: Literal["uri", "url", "inline"]
    encoding: Optional[Literal["base64"]] = None  # uri/inline일 때 "base64", url이면 None
    data: str
    mime_type: Optional[str] = None

    def as_payload(self) -> ImagePayload:
        return ImagePayload(
            source_type=self.source_type,
            encoding=self.encoding,
            ref=self.path,
            data=self.data,
            mime_type=self.mime_type,
        )


class DocumentAttachment(AttachmentBase):
    type: Literal["document"] = "document"
    source_type: Literal["uri", "url"]
    document_type: Literal["text", "binary"]
    encoding: Optional[str] = "unknown"  # 직렬화 방식: "utf-8", "cp949", "base64" / None: 해당 없음 / "unknown": 감지 전
    ref: str   # DB 저장용: 파일 경로(uri), URL(url)
    data: Optional[str] = None  # LLM API 전송용 (DB 저장 시 제외)
    mime_type: Optional[str] = None

    def as_payload(self) -> DocumentPayload:
        return DocumentPayload(
            ref=self.ref,
            name=self.name,
            data=self.data,
            mime_type=self.mime_type,
            encoding=self.encoding,
        )


ProcessedAttachment = Annotated[
    Union[ImageAttachment, DocumentAttachment],
    Field(discriminator="type"),
]


# ==========================================
# Tool
# ==========================================
McpTemplateVars = Dict[str, str]


class ToolSchema(BaseModel):
    """도구 스키마. LLM function calling 스키마로 전달됩니다."""
    name: str
    description: str
    parameters: Dict[str, Any]


class BaseTool(ABC):
    """도구 실행기 추상화. 구현체는 execute()에 실제 로직을 작성합니다."""
    id: str
    name: str
    description: str
    input_schema: Type[BaseModel]
    dependencies: List[Type] = []

    @abstractmethod
    def get_tool_schema(self) -> ToolSchema:
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        ...


class ToolGroup(BaseModel):
    """출처(MCP 서버 또는 built-in)로 묶인 도구 실행기 그룹."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    source: str
    tools: List[BaseTool] = Field(default_factory=list)
    error: Optional[str] = None


class ToolParameters(BaseModel):
    """Request-scoped values injected into tool.execute() at call time."""
    kg_jsonl_path: Optional[Path] = None


class ToolDTO(BaseModel):
    """ToolService → AgentWorker로 전달되는 tool 실행 번들."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    tools: List[BaseTool] = Field(default_factory=list)
    execute_tools: Callable


# ==========================================
# Model
# ==========================================
class ModelInfo(BaseModel):
    id: str
    provider: str
    display_name: str
    api_key: Optional[str] = Field(
        default=None, repr=False, description="API Key for the provider. Hidden in logs."
    )
    options: Dict[str, Any] = Field(
        default_factory=dict, description="Provider 전용 옵션 (llm_config.yaml에서 로드)"
    )


# ==========================================
# Context
# ==========================================
class Entity(BaseModel):
    id: str = Field(default_factory=generate_id("ent"))
    name: str
    entityType: str
    observations: List[str] = Field(default_factory=list)

    def add_observations(self, observations: List[str]) -> None:
        existing = set(self.observations)
        self.observations.extend(o for o in observations if o not in existing)

    def remove_observations(self, observations: List[str]) -> None:
        to_delete = set(observations)
        self.observations = [o for o in self.observations if o not in to_delete]


class Relation(BaseModel):
    id: str = Field(default_factory=generate_id("rel"))
    from_: str = Field(alias="from")
    to: str
    relationType: str

    model_config = {"populate_by_name": True}


class KnowledgeGraph(BaseModel):
    entities: List[Entity] = Field(default_factory=list)
    relations: List[Relation] = Field(default_factory=list)

    def add_entities(self, entities: List["Entity"]) -> List["Entity"]:
        existing = {e.id for e in self.entities}
        new_items = [e for e in entities if e.id not in existing]
        self.entities.extend(new_items)
        return new_items

    def remove_entities(self, ids: List[str]) -> None:
        id_set = set(ids)
        removed_names = {e.name for e in self.entities if e.id in id_set}
        self.entities = [e for e in self.entities if e.id not in id_set]
        self.relations = [
            r for r in self.relations
            if r.from_ not in removed_names and r.to not in removed_names
        ]

    def add_relations(self, relations: List["Relation"]) -> List["Relation"]:
        existing = {r.id for r in self.relations}
        new_items = [r for r in relations if r.id not in existing]
        self.relations.extend(new_items)
        return new_items

    def remove_relations(self, ids: List[str]) -> None:
        id_set = set(ids)
        self.relations = [r for r in self.relations if r.id not in id_set]

    def search_nodes(self, query: str) -> List["Entity"]:
        q = query.lower()
        return [
            e for e in self.entities
            if q in e.name.lower()
            or q in e.entityType.lower()
            or any(q in o.lower() for o in e.observations)
        ]

    def open_nodes(self, names: List[str]) -> List["Entity"]:
        name_set = set(names)
        return [e for e in self.entities if e.name in name_set]

    def resolve_entity(self, entity_id: str) -> "Entity":
        entity = next((e for e in self.entities if e.id == entity_id), None)
        if entity is None:
            raise ValueError(f"Entity '{entity_id}' not found.")
        return entity


class ContextPaths(BaseModel):
    """context 파일 경로 쌍."""
    static: Path
    dynamic: Path


class ContextDTO(BaseModel):
    static: str = ""
    dynamic: Path = Field(default_factory=lambda: Path())


class ContextSchema(BaseModel):
    """ContextDTO → PayloadEngine 변환 결과. HopilotPayload에 포함되어 Provider로 전달됩니다."""
    system_instructions: str = ""


# ==========================================
# Copilot DTOs
# ==========================================
class CopilotInput(BaseModel):
    """Handler 계층에서 Service 계층으로 데이터를 넘길 때 사용하는 순수 데이터 전송 객체입니다."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    session: HOSession
    ask: str
    model: Optional[ModelInfo] = None
    tool_set: Optional[ToolDTO] = None
    context: Optional[ContextDTO] = None
    attachments: Optional[List[ProcessedAttachment]] = None


class CopilotTask(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    task_id: str = Field(default_factory=generate_id("task"))
    session_id: str
    memory: List[HOMessage] = Field(default_factory=list)
    model: Optional[ModelInfo] = None
    tools: Optional[List[BaseTool]] = None
    react: HOreAct
    attachments: Optional[List[ProcessedAttachment]] = None
    context: Optional[ContextDTO] = None


class HopilotPayload(BaseModel):
    """Hopilot에서 LLM API로 전달하기 위한 공통 프롬프트 명세(Payload)입니다."""
    context: ContextSchema = Field(default_factory=ContextSchema)
    memory: List[HOMessage] = Field(default_factory=list)
    query: List[HOMessage] = Field(default_factory=list)
    tools: List[ToolSchema] = Field(default_factory=list, description="LLM이 호출할 수 있는 도구 스키마 목록")


# ==========================================
# Domain Interfaces (추상 계약)
# ==========================================
@dataclass
class AgentCallbacks:
    """AgentWorker에 주입되는 전략 번들 DTO. 각 필드는 교체 가능한 함수 포인터입니다."""
    payload_builder: Callable[[CopilotTask], Awaitable[HopilotPayload]]
    stream_opener: Callable[[HopilotPayload], AsyncGenerator[HOChunk, None]]
    tool_executor: Optional[Callable[[List[ToolCallPayload], Dict[str, BaseTool]], AsyncGenerator[HOChunk, None]]] = None
