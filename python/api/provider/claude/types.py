from typing import Any, Dict, List, Literal, TypedDict

ANTHROPIC_VERSION = "2023-06-01"
CLAUDE_SIGNATURE  = "signature"
CLAUDE_TOOL_ID    = "id"

ThinkingMode    = Literal["adaptive", "extended"]
EffortLevel     = Literal["low", "medium", "high", "xhigh", "max"]
ThinkingDisplay = Literal["summarized", "omitted"]


class CacheControl(TypedDict):
    type: Literal["ephemeral"]


class ClaudeContentBlock(TypedDict, total=False):
    type: str
    text: str
    thinking: str
    signature: str
    id: str
    name: str
    input: Dict[str, Any]
    tool_use_id: str
    content: Any
    cache_control: CacheControl


class ClaudeSystemBlock(TypedDict, total=False):
    type: Literal["text"]
    text: str
    cache_control: CacheControl


class ClaudeMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: List[ClaudeContentBlock]


class ClaudeThinkingConfig(TypedDict, total=False):
    type: Literal["adaptive", "enabled"]
    budget_tokens: int       # extended thinking (Haiku) 전용
    display: ThinkingDisplay


class ClaudeConfig(TypedDict, total=False):
    max_tokens: int
    thinking_mode: ThinkingMode
    effort: EffortLevel
    thinking_display: ThinkingDisplay
    budget_tokens: int       # extended thinking (Haiku) 전용


class ClaudePayload(TypedDict, total=False):
    model: str
    max_tokens: int
    stream: bool
    system: Any
    messages: List[ClaudeMessage]
    thinking: ClaudeThinkingConfig
    output_config: Dict[str, str]
    tools: List[Dict[str, Any]]
