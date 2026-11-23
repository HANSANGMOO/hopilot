from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

LOCAL_TOOL_ID = "id"


class LocalFunctionDef(TypedDict, total=False):
    name: str
    description: Optional[str]
    parameters: Optional[Dict[str, Any]]


class LocalToolDeclaration(TypedDict):
    type: Literal["function"]
    function: LocalFunctionDef


class LocalFunctionCall(TypedDict):
    name: str
    arguments: str


class LocalToolCall(TypedDict):
    id: str
    type: Literal["function"]
    function: LocalFunctionCall


class LocalMessage(TypedDict, total=False):
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str]
    tool_calls: List[LocalToolCall]
    tool_call_id: str


class LocalConfig(TypedDict, total=False):
    max_tokens: int


class LocalPayload(TypedDict, total=False):
    model: str
    stream: bool
    max_tokens: int
    messages: List[LocalMessage]
    tools: List[LocalToolDeclaration]
