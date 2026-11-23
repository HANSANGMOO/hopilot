from typing import Any, Dict, List, Literal, TypedDict

GEMINI_THOUGHT_SIGNATURE = "thoughtSignature"
GEMINI_TOOL_ID = "id"


class GeminiFunctionCall(TypedDict, total=False):
    name: str
    args: Dict[str, Any]
    id: str


class GeminiFunctionResponse(TypedDict, total=False):
    name: str
    response: Any
    id: str


class GeminiPart(TypedDict, total=False):
    text: str
    thought: bool
    functionCall: GeminiFunctionCall
    functionResponse: GeminiFunctionResponse
    thoughtSignature: str
    # inlineData: dict (이미지용, 필요 시 확장)


class GeminiContent(TypedDict):
    role: Literal["user", "model"]
    parts: List[GeminiPart]


class GeminiSystemInstruction(TypedDict):
    parts: List[GeminiPart]


class GeminiThinkingConfig(TypedDict, total=False):
    thinkingLevel: str
    includeThoughts: bool


class GeminiGenerationConfig(TypedDict, total=False):
    temperature: float
    maxOutputTokens: int
    thinkingConfig: GeminiThinkingConfig


class GeminiFunctionDeclaration(TypedDict, total=False):
    name: str
    description: str
    parameters: Dict[str, Any]


class GeminiTool(TypedDict, total=False):
    functionDeclarations: List[GeminiFunctionDeclaration]
    googleSearch: Dict[str, Any]
    codeExecution: Dict[str, Any]


class GeminiPayload(TypedDict, total=False):
    systemInstruction: GeminiSystemInstruction
    contents: List[GeminiContent]
    tools: List[GeminiTool]
    generationConfig: GeminiGenerationConfig
