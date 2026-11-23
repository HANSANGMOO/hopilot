"""
Unit tests for format_payload()

Single responsibility: HopilotPayload → GeminiPayload 변환이 올바른가

Test cases:
  - system_instructions → systemInstruction
  - memory + query      → contents
  - tools               → functionDeclarations
  - config              → generationConfig
"""
from api.provider.gemini.formatter import format_payload
from api.provider.gemini.types import GeminiGenerationConfig, GeminiThinkingConfig
from core.models import HOChunk, HOMessage, HopilotPayload, TextPayload, ToolSchema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text_msg(role: str, text: str) -> HOMessage:
    gemini_role = "ai" if role == "model" else role
    return HOMessage(
        role=gemini_role,
        chunks=[HOChunk(payload=TextPayload(text=text))],
    )


def _make_config() -> GeminiGenerationConfig:
    return GeminiGenerationConfig(
        temperature=1.0,
        maxOutputTokens=8192,
        thinkingConfig=GeminiThinkingConfig(thinkingLevel="high", includeThoughts=True),
    )


def _make_payload(
    system: str = "system prompt",
    memory: list = None,
    query: list = None,
    tools: list = None,
) -> HopilotPayload:
    return HopilotPayload(
        system_instructions=system,
        memory=memory or [],
        query=query or [],
        tools=tools or [],
    )


# ---------------------------------------------------------------------------
# system_instructions → systemInstruction
# ---------------------------------------------------------------------------

def test_system_instructions_converted():
    payload = _make_payload(system="You are a helpful assistant.")
    result = format_payload(payload, _make_config())

    assert "systemInstruction" in result
    assert result["systemInstruction"]["parts"][0]["text"] == "You are a helpful assistant."


def test_empty_system_instructions_omitted():
    payload = _make_payload(system="")
    result = format_payload(payload, _make_config())

    assert "systemInstruction" not in result


# ---------------------------------------------------------------------------
# memory + query → contents
# ---------------------------------------------------------------------------

def test_memory_and_query_merged_into_contents():
    memory = [_text_msg("user", "hello"), _text_msg("model", "hi")]
    query  = [_text_msg("user", "how are you?")]
    payload = _make_payload(memory=memory, query=query)
    result = format_payload(payload, _make_config())

    assert len(result["contents"]) == 3
    assert result["contents"][0]["role"] == "user"
    assert result["contents"][1]["role"] == "model"
    assert result["contents"][2]["role"] == "user"


def test_memory_prefix_stable_when_query_changes():
    memory = [_text_msg("user", "hello"), _text_msg("model", "hi")]
    query_a = [_text_msg("user", "question A")]
    query_b = [_text_msg("user", "question B")]

    result_a = format_payload(_make_payload(memory=memory, query=query_a), _make_config())
    result_b = format_payload(_make_payload(memory=memory, query=query_b), _make_config())

    # memory 부분(앞 2개)은 동일해야 함 — 캐싱 핵심
    assert result_a["contents"][:2] == result_b["contents"][:2]
    # query 부분(마지막)은 달라야 함
    assert result_a["contents"][-1] != result_b["contents"][-1]


def test_system_role_message_excluded_from_contents():
    system_msg = HOMessage(
        role="system",
        chunks=[HOChunk(payload=TextPayload(text="ignored"))],
    )
    payload = _make_payload(query=[system_msg])
    result = format_payload(payload, _make_config())

    assert result["contents"] == []


def test_empty_memory_and_query_produces_empty_contents():
    payload = _make_payload()
    result = format_payload(payload, _make_config())

    assert result["contents"] == []


# ---------------------------------------------------------------------------
# tools → functionDeclarations
# ---------------------------------------------------------------------------

def test_tools_converted_to_function_declarations():
    tools = [ToolSchema(name="search", description="Search the web", parameters={"type": "object", "properties": {}})]
    payload = _make_payload(tools=tools)
    result = format_payload(payload, _make_config())

    assert "tools" in result
    declarations = result["tools"][0]["functionDeclarations"]
    assert len(declarations) == 1
    assert declarations[0]["name"] == "search"
    assert declarations[0]["description"] == "Search the web"


def test_no_tools_omits_tools_field():
    payload = _make_payload(tools=[])
    result = format_payload(payload, _make_config())

    assert "tools" not in result


# ---------------------------------------------------------------------------
# config → generationConfig
# ---------------------------------------------------------------------------

def test_generation_config_passed_through():
    config = _make_config()
    payload = _make_payload()
    result = format_payload(payload, config)

    assert result["generationConfig"] == config
