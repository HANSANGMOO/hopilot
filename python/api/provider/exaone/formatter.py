import json
from typing import List, Literal

from core.models import HOChunk, HOMessage, HopilotPayload
from utils import get_logger

from .types import (
    EXAONE_TOOL_ID,
    ExaoneConfig,
    ExaoneFunctionCall,
    ExaoneMessage,
    ExaonePayload,
    ExaoneToolCall,
    ExaoneToolDeclaration,
)

logger = get_logger("ExaoneFormatter")


def format_payload(payload: HopilotPayload, model: str, config: ExaoneConfig) -> ExaonePayload:
    """HopilotPayload를 EXAONE Chat Completions 요청(body)으로 변환합니다."""
    request: ExaonePayload = {
        "model": model,
        "stream": True,
        "max_tokens": config.get("max_tokens", 16384),
    }

    if (temperature := config.get("temperature")) is not None:
        request["temperature"] = temperature
    if (top_p := config.get("top_p")) is not None:
        request["top_p"] = top_p
    if (reasoning_effort := config.get("reasoning_effort")) is not None:
        request["reasoning_effort"] = reasoning_effort

    messages: List[ExaoneMessage] = []
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


def _format_message(msg: HOMessage) -> List[ExaoneMessage]:
    """단일 HOMessage를 1개 이상의 ExaoneMessage로 변환합니다."""
    if msg.chunks and all(c.payload.type == "tool_output" for c in msg.chunks):
        return [_format_tool_output_message(c) for c in msg.chunks]

    role: Literal["user", "assistant"] = "assistant" if msg.role == "ai" else "user"
    text_parts: List[str] = []
    tool_calls: List[ExaoneToolCall] = []

    for chunk in msg.chunks:
        p = chunk.payload

        if p.type == "tool_call":
            tool_calls.append(_format_tool_call(p))
        elif p.type == "tool_output":
            continue
        elif p.type == "thought":
            continue
        elif p.type == "text":
            text_parts.append(p.text)
        elif p.type == "document":
            if p.data is None:
                continue
            if p.encoding == "base64":
                logger.warning("EXAONE k-exaone_v2.5 does not support base64 binary documents.")
                continue
            text_parts.append(p.data)
        elif p.type == "image":
            logger.warning("EXAONE k-exaone_v2.5 is text-only and does not support image inputs.")
            continue

    if not text_parts and not tool_calls:
        return []

    message: ExaoneMessage = {"role": role}

    if text_parts:
        message["content"] = "".join(text_parts)
    elif not tool_calls:
        message["content"] = ""

    if tool_calls:
        message["tool_calls"] = tool_calls

    return [message]


def _format_tool_call(payload) -> ExaoneToolCall:
    call_id = payload.model_extra.get(EXAONE_TOOL_ID) if payload.model_extra else None
    function: ExaoneFunctionCall = {
        "name": payload.tool_name,
        "arguments": json.dumps(payload.tool_args, ensure_ascii=False),
    }
    return {"id": call_id or "", "type": "function", "function": function}


def _format_tool_output_message(chunk: HOChunk) -> ExaoneMessage:
    p = chunk.payload
    call_id = p.model_extra.get(EXAONE_TOOL_ID) if p.model_extra else None
    output = p.output
    if p.truncated:
        output += (
            "\n[결과가 너무 길어 잘렸습니다. 더 좁은 범위로 재시도하거나 다른 방법을 사용하세요.]"
        )
    return {"role": "tool", "tool_call_id": call_id or "", "content": output}


def _format_tool_declarations(tools) -> List[ExaoneToolDeclaration]:
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
