from api.api_manager import ApiManager
from api.provider.exaone import ExaoneProvider
from api.provider.exaone.formatter import format_payload
from api.provider.exaone.parser import ExaoneParser
from api.provider.exaone.types import EXAONE_TOOL_ID, ExaoneConfig
from core.models import (
    ContextSchema,
    DocumentPayload,
    EType,
    HOChunk,
    HOMessage,
    HopilotPayload,
    ImagePayload,
    StreamPayload,
    TextPayload,
    ThoughtPayload,
    ToolCallPayload,
    ToolOutputPayload,
    ToolSchema,
    UsagePayload,
)


def _make_payload(
    system: str = "",
    memory: list[HOMessage] | None = None,
    query: list[HOMessage] | None = None,
    tools: list[ToolSchema] | None = None,
) -> HopilotPayload:
    return HopilotPayload(
        context=ContextSchema(system_instructions=system),
        memory=memory or [],
        query=query or [],
        tools=tools or [],
    )


def test_provider_registration_and_http_spec():
    manager = ApiManager()
    assert "exaone" in manager.get_supported_providers()

    provider = manager.create_provider(
        "exaone",
        "test-key",
        "k-exaone_v2.5",
        {"reasoning_effort": "low", "temperature": 0.0},
    )
    assert isinstance(provider, ExaoneProvider)
    assert provider.build_url() == "https://api.exaone.ai/v1/chat/completions"
    assert provider.build_headers() == {
        "Authorization": "Bearer test-key",
        "Content-Type": "application/json",
    }

    spec = provider.build_http_spec(
        _make_payload(
            query=[HOMessage(role="user", chunks=[HOChunk(payload=TextPayload(text="안녕"))])]
        )
    )
    assert spec.method == "POST"
    assert spec.url == "https://api.exaone.ai/v1/chat/completions"
    assert spec.json_body["model"] == "k-exaone_v2.5"
    assert spec.json_body["reasoning_effort"] == "low"
    assert spec.json_body["temperature"] == 0.0

    custom = manager.create_provider(
        "exaone",
        "test-key",
        "k-exaone_v2.5",
        {"base_url": "https://custom.exaone.test/v1/chat/completions"},
    )
    assert custom.build_url() == "https://custom.exaone.test/v1/chat/completions"


def test_format_payload_messages_and_media():
    memory = [
        HOMessage(role="system", chunks=[HOChunk(payload=TextPayload(text="ignored"))]),
        HOMessage(role="user", chunks=[HOChunk(payload=TextPayload(text="first question"))]),
        HOMessage(
            role="ai",
            chunks=[
                HOChunk(payload=ThoughtPayload(thought="internal reasoning")),
                HOChunk(payload=TextPayload(text="first answer")),
            ],
        ),
    ]
    query = [
        HOMessage(
            role="user",
            chunks=[
                HOChunk(
                    payload=ImagePayload(
                        source_type="uri",
                        encoding="base64",
                        ref="file:///tmp/pic.png",
                        data="AAAA",
                        mime_type="image/png",
                    )
                ),
                HOChunk(
                    payload=DocumentPayload(
                        ref="file:///tmp/report.pdf",
                        name="report.pdf",
                        data="BBBB",
                        encoding="base64",
                        mime_type="application/pdf",
                    )
                ),
                HOChunk(
                    payload=DocumentPayload(
                        ref="file:///tmp/notes.txt",
                        name="notes.txt",
                        data="[notes content]\n",
                        encoding="utf-8",
                        mime_type="text/plain",
                    )
                ),
                HOChunk(payload=TextPayload(text="summarize this")),
            ],
        ),
        HOMessage(role="ai", chunks=[]),  # empty placeholder must be dropped
    ]

    payload = _make_payload(system="System instructions", memory=memory, query=query)
    body = format_payload(payload, "k-exaone_v2.5", ExaoneConfig(max_tokens=16384))

    assert body["model"] == "k-exaone_v2.5"
    assert body["stream"] is True
    assert body["max_tokens"] == 16384
    assert "temperature" not in body
    assert "top_p" not in body
    assert "reasoning_effort" not in body
    assert "stream_options" not in body

    assert body["messages"] == [
        {"role": "system", "content": "System instructions"},
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
        {"role": "user", "content": "[notes content]\nsummarize this"},
    ]
    assert isinstance(body["messages"][-1]["content"], str)


def test_format_payload_tools_and_options():
    tool_schema = ToolSchema(
        name="execute_python",
        description="Run python",
        parameters={"type": "object", "properties": {"code": {"type": "string"}}},
    )
    query = [
        HOMessage(role="user", chunks=[HOChunk(payload=TextPayload(text="calc 1+1"))]),
        HOMessage(
            role="ai",
            chunks=[
                HOChunk(
                    payload=ToolCallPayload(
                        tool_name="execute_python",
                        tool_args={"code": "print(1+1)"},
                        **{EXAONE_TOOL_ID: "call_1"},
                    )
                )
            ],
        ),
        HOMessage(
            role="user",
            chunks=[
                HOChunk(
                    payload=ToolOutputPayload(
                        tool_name="execute_python",
                        output="x" * 20005,
                        **{EXAONE_TOOL_ID: "call_1"},
                    )
                )
            ],
        ),
        HOMessage(role="ai", chunks=[]),
    ]

    config = ExaoneConfig(
        max_tokens=8192,
        temperature=1.0,
        top_p=0.95,
        reasoning_effort="high",
    )
    body = format_payload(_make_payload(query=query, tools=[tool_schema]), "k-exaone_v2.5", config)

    assert body["max_tokens"] == 8192
    assert body["temperature"] == 1.0
    assert body["top_p"] == 0.95
    assert body["reasoning_effort"] == "high"
    assert body["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "execute_python",
                "description": "Run python",
                "parameters": {"type": "object", "properties": {"code": {"type": "string"}}},
            },
        }
    ]
    assert body["messages"][0] == {"role": "user", "content": "calc 1+1"}
    assert body["messages"][1] == {
        "role": "assistant",
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "execute_python",
                    "arguments": '{"code": "print(1+1)"}',
                },
            }
        ],
    }
    tool_msg = body["messages"][2]
    assert tool_msg["role"] == "tool"
    assert tool_msg["tool_call_id"] == "call_1"
    assert tool_msg["content"].endswith(
        "\n[결과가 너무 길어 잘렸습니다. 더 좁은 범위로 재시도하거나 다른 방법을 사용하세요.]"
    )


def test_parser_quickstart_stream():
    parser = ExaoneParser()
    base = (
        '{"id": "2fa2bf0467cf4d758fe4c4dba28f2b18", '
        '"created": 1793947427, "model": "k-exaone_v2.5", '
        '"object": "chat.completion.chunk", '
    )
    lines = [
        (
            f'data: {base}"choices": [{{"delta": '
            '{"content": "", "role": "assistant"}, "index": 0}]}'
        ),
        f'data: {base}"choices": [{{"delta": {{"reasoning_content": "We"}}, "index": 0}}]}}',
        f'data: {base}"choices": [{{"delta": {{"reasoning_content": " need"}}, "index": 0}}]}}',
        f'data: {base}"choices": [{{"delta": {{"content": "how"}}, "index": 0}}]}}',
        (
            f'data: {base}"choices": [{{"delta": '
            '{"content": " can I help you today?"}, "index": 0}]}'
        ),
        (
            f'data: {base}"choices": [{{"delta": {{}}, '
            '"finish_reason": "stop", "index": 0, "matched_stop": 53}]}'
        ),
        (
            f'data: {base}"choices": [], '
            '"usage": {"completion_tokens": 234, "prompt_tokens": 22, '
            '"total_tokens": 256, "reasoning_tokens": 216}}'
        ),
        "data: [DONE]",
    ]

    emitted = [c.payload for line in lines for c in parser.parse_sse_event(line)]

    starts = [p for p in emitted if isinstance(p, StreamPayload) and p.event == EType.MESSAGE_START]
    ends = [p for p in emitted if isinstance(p, StreamPayload) and p.event == EType.MESSAGE_END]
    thoughts = [p.thought for p in emitted if isinstance(p, ThoughtPayload)]
    texts = [p.text for p in emitted if isinstance(p, TextPayload)]
    usages = [p for p in emitted if isinstance(p, UsagePayload)]

    assert len(starts) == 1
    assert len(ends) == 1
    assert ends[0].finish_reason == "stop"
    assert thoughts == ["We", " need"]
    assert texts == ["how", " can I help you today?"]
    assert len(usages) == 1
    assert usages[0].input_tokens == 22
    assert usages[0].output_tokens == 18
    assert usages[0].thinking_tokens == 216
    assert usages[0].total_tokens == 256


def test_parser_chunked_multi_tool_calls():
    parser = ExaoneParser()
    tc0_start = (
        '{"index": 0, "id": "call_a", '
        '"function": {"name": "alpha", "arguments": "{\\"x\\":"}}'
    )
    tc1_full = (
        '{"index": 1, "id": "call_b", '
        '"function": {"name": "beta", "arguments": "{\\"y\\": 2}"}}'
    )
    tc0_end = '{"index": 0, "function": {"arguments": " 1}"}}'
    lines = [
        f'data: {{"choices": [{{"index": 0, "delta": {{"tool_calls": [{tc0_start}]}}}}]}}',
        f'data: {{"choices": [{{"index": 0, "delta": {{"tool_calls": [{tc1_full}]}}}}]}}',
        f'data: {{"choices": [{{"index": 0, "delta": {{"tool_calls": [{tc0_end}]}}}}]}}',
        'data: {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}',
        "data: [DONE]",
    ]

    emitted = [c.payload for line in lines for c in parser.parse_sse_event(line)]
    tool_calls = [p for p in emitted if isinstance(p, ToolCallPayload)]
    ends = [p for p in emitted if isinstance(p, StreamPayload) and p.event == EType.MESSAGE_END]

    assert len(tool_calls) == 2
    assert tool_calls[0].tool_name == "alpha"
    assert tool_calls[0].tool_args == {"x": 1}
    assert tool_calls[0].model_extra == {EXAONE_TOOL_ID: "call_a"}
    assert tool_calls[1].tool_name == "beta"
    assert tool_calls[1].tool_args == {"y": 2}
    assert tool_calls[1].model_extra == {EXAONE_TOOL_ID: "call_b"}
    assert len(ends) == 1
    assert ends[0].finish_reason == "tool_calls"


def test_parser_done_without_finish_reason():
    parser = ExaoneParser()
    lines = [
        'data: {"choices": [{"index": 0, "delta": {"content": "hello"}}]}',
        "data: [DONE]",
    ]
    emitted = [c.payload for line in lines for c in parser.parse_sse_event(line)]
    ends = [p for p in emitted if isinstance(p, StreamPayload) and p.event == EType.MESSAGE_END]
    assert len(ends) == 1
    assert ends[0].finish_reason == "stop"


def test_parser_error_and_malformed_lines():
    parser = ExaoneParser()

    err1 = parser.parse_sse_event('data: {"result_code": 500, "description": "temporary issue"}')
    assert len(err1) == 1
    assert isinstance(err1[0].payload, StreamPayload)
    assert err1[0].payload.event == EType.ERROR
    assert err1[0].payload.error_message == "temporary issue"

    err2 = parser.parse_sse_event('data: {"error": {"message": "bad key"}}')
    assert len(err2) == 1
    assert isinstance(err2[0].payload, StreamPayload)
    assert err2[0].payload.event == EType.ERROR
    assert err2[0].payload.error_message == "bad key"

    assert parser.parse_sse_event("") == []
    assert parser.parse_sse_event("event: ping") == []
    assert parser.parse_sse_event(": keepalive") == []
    assert parser.parse_sse_event("data: ") == []
    assert parser.parse_sse_event("data: {not-json") == []
