from typing import Any, Dict, List, Literal, Optional, TypedDict

EXAONE_TOOL_ID = "id"


class ExaoneFunctionDef(TypedDict, total=False):
    name: str
    description: Optional[str]
    parameters: Optional[Dict[str, Any]]


class ExaoneToolDeclaration(TypedDict):
    type: Literal["function"]
    function: ExaoneFunctionDef


class ExaoneFunctionCall(TypedDict):
    name: str
    arguments: str


class ExaoneToolCall(TypedDict):
    id: str
    type: Literal["function"]
    function: ExaoneFunctionCall


class ExaoneMessage(TypedDict, total=False):
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str]
    tool_calls: List[ExaoneToolCall]
    tool_call_id: str


class ExaoneConfig(TypedDict, total=False):
    max_tokens: int
    temperature: float
    top_p: float
    reasoning_effort: Literal["low", "high", "max"]


class ExaonePayload(TypedDict, total=False):
    model: str
    stream: bool
    max_tokens: int
    temperature: float
    top_p: float
    reasoning_effort: str
    messages: List[ExaoneMessage]
    tools: List[ExaoneToolDeclaration]
