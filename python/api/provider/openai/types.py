from typing import Any, Dict, List, Optional, Union
from typing_extensions import Literal, TypedDict

OPENAI_REASONING_SIGNATURE = "reasoning_id"
OPENAI_CALL_ID             = "call_id"
OPENAI_RESPONSE_ID         = "response_id"


# ── Part (message 내부 content 조각) ───────────────────────────────────────────

class OpenAIInputTextPart(TypedDict, total=False):
    type: Literal["input_text"]
    text: str


class OpenAIOutputTextPart(TypedDict, total=False):
    type: Literal["output_text"]
    text: str


class OpenAIInputImagePart(TypedDict, total=False):
    type: Literal["input_image"]
    detail: Literal["low", "high", "auto", "original"]
    image_url: Optional[str]
    file_id: Optional[str]


class OpenAIInputFilePart(TypedDict, total=False):
    type: Literal["input_file"]
    file_data: str
    file_id: Optional[str]
    file_url: str
    filename: str


OpenAIPart = Union[OpenAIInputTextPart, OpenAIOutputTextPart, OpenAIInputImagePart, OpenAIInputFilePart]


# ── Item (input 배열 최상위 원소) ──────────────────────────────────────────────

class OpenAIMessageItem(TypedDict, total=False):
    type: Literal["message"]
    role: Literal["user", "assistant", "system", "developer"]
    content: List[OpenAIPart]


class OpenAIFunctionCallItem(TypedDict, total=False):
    type: Literal["function_call"]
    id: str
    call_id: str
    name: str
    arguments: str


class OpenAIFunctionOutputItem(TypedDict, total=False):
    type: Literal["function_call_output"]
    call_id: str
    output: Union[str, List[OpenAIPart]]


class OpenAIReasoningItem(TypedDict, total=False):
    """stateless 멀티턴 시 input에 포함해야 하는 reasoning item."""
    type: Literal["reasoning"]
    id: str
    summary: List[Dict[str, str]]  # [{type: "summary_text", text: str}]
    encrypted_content: Optional[str]


OpenAIItem = Union[OpenAIMessageItem, OpenAIFunctionCallItem, OpenAIFunctionOutputItem, OpenAIReasoningItem]


# ── Tool definition ────────────────────────────────────────────────────────────

class OpenAIFunctionDef(TypedDict, total=False):
    type: Literal["function"]
    name: str
    description: Optional[str]
    parameters: Optional[Dict[str, Any]]
    strict: Optional[bool]


# ── Reasoning config ───────────────────────────────────────────────────────────

class OpenAIReasoningConfig(TypedDict, total=False):
    effort: Literal["low", "medium", "high"]
    summary: Literal["auto", "concise", "detailed"]


# ── Text config (출력 형식/길이 제어) ───────────────────────────────────────────

class OpenAITextFormatText(TypedDict, total=False):
    type: Literal["text"]


class OpenAITextFormatJsonSchema(TypedDict, total=False):
    type: Literal["json_schema"]
    name: str
    schema: Dict[str, Any]
    strict: Optional[bool]
    description: Optional[str]


OpenAITextFormat = Union[OpenAITextFormatText, OpenAITextFormatJsonSchema]


class OpenAITextConfig(TypedDict, total=False):
    format: OpenAITextFormat
    verbosity: Literal["low", "medium", "high"]


# ── Configuration (provider → formatter 전달 설정) ─────────────────────────────

class OpenAIConfiguration(TypedDict, total=False):
    model: str
    max_output_tokens: int
    reasoning: OpenAIReasoningConfig
    truncation: Literal["auto", "disabled"]
    include: List[str]
    text: OpenAITextConfig


# ── Payload (요청 전체) ────────────────────────────────────────────────────────

class OpenAIPayload(TypedDict, total=False):
    model: str
    input: List[OpenAIItem]
    instructions: str
    stream: bool
    store: bool
    previous_response_id: str
    max_output_tokens: int
    reasoning: OpenAIReasoningConfig
    tools: List[OpenAIFunctionDef]
    include: List[str]
    truncation: Literal["auto", "disabled"]
    text: OpenAITextConfig
