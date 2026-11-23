import json
from typing import Any, Dict, List, Literal, Optional

from core.models import HOChunk, HOMessage, HopilotPayload

from .types import (
    LOCAL_TOOL_ID,
    LocalConfig,
    LocalFunctionCall,
    LocalMessage,
    LocalPayload,
    LocalToolCall,
    LocalToolDeclaration,
)


def format_payload(payload: HopilotPayload, model: str, config: LocalConfig) -> LocalPayload:
    """HopilotPayload를 OpenAI Chat Completions 호환 요청(body)으로 변환합니다."""
    request: LocalPayload = {
        "model": model,
        "stream": True,
        "max_tokens": config.get("max_tokens", 16000),
    }

    messages: List[LocalMessage] = []
    if payload.context.system_instructions:
        messages.append({"role": "system", "content": payload.context.system_instructions})

    for msg in [*payload.memory, *payload.query]:
        if msg.role == "system":
            continue
        messages.extend(_format_message(msg))

    request["messages"] = messages

    if payload.tools:
        request["tools"] = _format_tool_declarations(payload.tools)

    return request


def _format_message(msg: HOMessage) -> List[LocalMessage]:
    """단일 HOMessage를 1개 이상의 LocalMessage로 변환합니다.

    tool_output 청크로만 구성된 메시지(agent_worker의 HOMessage(role="user", chunks=[...ToolOutputPayload]))는
    role="tool" 독립 메시지로 분리합니다. 로컬 게이트웨이는 tool 결과를 content 블록이 아닌
    별도의 {"role": "tool", "tool_call_id": ..., "content": ...} 메시지로 요구합니다.
    """
    if msg.chunks and all(c.payload.type == "tool_output" for c in msg.chunks):
        return [_format_tool_output_message(c) for c in msg.chunks]

    role: Literal["user", "assistant"] = "assistant" if msg.role == "ai" else "user"
    text_parts: List[str] = []
    other_parts: List[Dict[str, Any]] = []
    tool_calls: List[LocalToolCall] = []

    for chunk in msg.chunks:
        p = chunk.payload

        if p.type == "tool_call":
            tool_calls.append(_format_tool_call(p))
        elif p.type == "tool_output":
            # 혼합 메시지 방어: tool_output은 위에서 단독 메시지로만 처리
            continue
        elif p.type == "thought":
            # 로컬 게이트웨이는 reasoning 재입력을 지원하지 않음 → 제외
            continue
        elif p.type == "text":
            text_parts.append(p.text)
        elif p.type in ("image", "document"):
            part = _format_media_chunk(p)
            if part:
                other_parts.append(part)

    if not text_parts and not other_parts and not tool_calls:
        return []

    message: LocalMessage = {"role": role}

    if other_parts:
        content_list = [{"type": "text", "text": t} for t in text_parts if t] + other_parts
        message["content"] = content_list  # type: ignore[typeddict-item]
    elif text_parts:
        message["content"] = "".join(text_parts)
    elif not tool_calls:
        message["content"] = ""

    if tool_calls:
        message["tool_calls"] = tool_calls

    return [message]


def _format_tool_call(payload) -> LocalToolCall:
    call_id = payload.model_extra.get(LOCAL_TOOL_ID) if payload.model_extra else None
    function: LocalFunctionCall = {
        "name": payload.tool_name,
        "arguments": json.dumps(payload.tool_args, ensure_ascii=False),
    }
    return {"id": call_id or "", "type": "function", "function": function}


def _format_tool_output_message(chunk: HOChunk) -> LocalMessage:
    p = chunk.payload
    call_id = p.model_extra.get(LOCAL_TOOL_ID) if p.model_extra else None
    output = p.output
    if p.truncated:
        output += "\n[결과가 너무 길어 잘렸습니다. 더 좁은 범위로 재시도하거나 다른 방법을 사용하세요.]"
    return {"role": "tool", "tool_call_id": call_id or "", "content": output}


def _format_media_chunk(payload) -> Optional[Dict[str, Any]]:
    if payload.type == "image":
        if payload.data is None:
            return None
        url = f"data:{payload.mime_type};base64,{payload.data}" if payload.encoding == "base64" else payload.data
        return {"type": "image_url", "image_url": {"url": url}}

    if payload.type == "document":
        if payload.data is None or payload.encoding == "base64":
            return None
        return {"type": "text", "text": payload.data}

    return None


def _format_tool_declarations(tools) -> List[LocalToolDeclaration]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]
