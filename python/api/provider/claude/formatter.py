from typing import Any, Dict, List, Literal, Union

from core.models import HOChunk, HopilotPayload, ToolOutputPayload

from .types import (
    CLAUDE_SIGNATURE,
    CLAUDE_TOOL_ID,
    ClaudeConfig,
    ClaudeContentBlock,
    ClaudeMessage,
    ClaudePayload,
    ClaudeThinkingConfig,
)


def format_payload(payload: HopilotPayload, model: str, config: ClaudeConfig) -> ClaudePayload:
    """HopilotPayload를 Anthropic Messages 요청(body)으로 변환합니다.
    캐싱 마커(cache_control)는 optimizer에서 별도 처리합니다.
    """
    request: ClaudePayload = {
        "model": model,
        "max_tokens": config.get("max_tokens", 16000),
        "stream": True,
    }

    # 1. System Instruction
    if payload.context.system_instructions:
        request["system"] = payload.context.system_instructions

    # 2. Messages 구성
    messages: List[ClaudeMessage] = []
    for msg in [*payload.memory, *payload.query]:
        if msg.role == "system":
            continue

        role: Literal["user", "assistant"] = "assistant" if msg.role == "ai" else "user"
        blocks: List[ClaudeContentBlock] = []

        for chunk in msg.chunks:
            block = _format_chunk(chunk)
            if block:
                blocks.append(block)

        if blocks:
            messages.append({"role": role, "content": blocks})

    request["messages"] = messages

    # 3. Thinking config (모델 능력에 따라 adaptive / extended 분기)
    request["thinking"] = _build_thinking_config(config)

    # 4. output_config (effort) — adaptive 전용, extended(Haiku)는 미지원
    if config.get("thinking_mode", "adaptive") == "adaptive":
        if effort := config.get("effort"):
            request["output_config"] = {"effort": effort}

    # 5. Tools
    if payload.tools:
        request["tools"] = [
            {"name": t.name, "description": t.description, "input_schema": t.parameters}
            for t in payload.tools
        ]

    return request


def _build_thinking_config(config: ClaudeConfig) -> ClaudeThinkingConfig:
    """ClaudeConfig의 thinking_mode에 따라 API 요청용 thinking 블록을 생성합니다."""
    if config.get("thinking_mode", "adaptive") == "extended":
        return {
            "type": "enabled",
            "budget_tokens": config.get("budget_tokens", 8000),
        }

    thinking: ClaudeThinkingConfig = {"type": "adaptive"}
    if display := config.get("thinking_display"):
        thinking["display"] = display
    return thinking


def _format_tool_output_content(payload: ToolOutputPayload) -> Union[str, List[Dict[str, Any]]]:
    """ToolOutputPayload의 output 및 media 리스트를 Anthropic tool_result content 형식으로 변환합니다."""
    # 미디어가 없는 일반적인 경우 -> 기존처럼 단일 문자열 반환
    if not payload.media:
        content = payload.output
        if payload.truncated:
            content += "\n[결과가 너무 길어 잘렸습니다. 더 좁은 범위로 재시도하거나 다른 방법을 사용하세요.]"
        return content

    # 미디어가 포함된 경우 -> content 블록 배열 구성
    blocks: List[Dict[str, Any]] = []

    # 1. 텍스트가 있으면 text 블록 추가
    if payload.output:
        text = payload.output
        if payload.truncated:
            text += "\n[결과가 너무 길어 잘렸습니다. 더 좁은 범위로 재시도하거나 다른 방법을 사용하세요.]"
        blocks.append({"type": "text", "text": text})

    # 2. 미디어 블록 추가 (data가 존재하는 경우에만)
    for item in payload.media:
        if not item.data:
            continue
        mime = item.mime_type or "application/octet-stream"
        if item.type == "image" or mime.startswith("image/"):
            blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime,
                    "data": item.data,
                },
            })
        elif mime == "application/pdf":
            blocks.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": mime,
                    "data": item.data,
                },
            })
        else:
            # 지원되지 않는 바이너리 형식은 안내 텍스트로 대체
            blocks.append({
                "type": "text",
                "text": f"[{item.type} 미디어 첨부: {mime}]",
            })

    return blocks


def _format_chunk(chunk: HOChunk) -> ClaudeContentBlock:
    """단일 HOChunk를 Anthropic content 블록으로 변환합니다."""
    block: ClaudeContentBlock = {}
    payload = chunk.payload

    if payload.type == "text":
        block["type"] = "text"
        block["text"] = payload.text

    elif payload.type == "thought":
        sig = payload.model_extra.get(CLAUDE_SIGNATURE) if payload.model_extra else None
        if sig:
            block["type"] = "thinking"
            block["thinking"] = payload.thought
            block["signature"] = sig

    elif payload.type == "tool_call":
        call_id = payload.model_extra.get(CLAUDE_TOOL_ID) if payload.model_extra else None
        block["type"] = "tool_use"
        block["id"] = call_id or ""
        block["name"] = payload.tool_name
        block["input"] = payload.tool_args

    elif payload.type == "tool_output":
        output_id = payload.model_extra.get(CLAUDE_TOOL_ID) if payload.model_extra else None
        block["type"] = "tool_result"
        if output_id:
            block["tool_use_id"] = output_id
        block["content"] = _format_tool_output_content(payload)

    elif payload.type == "image":
        if payload.data is None:
            return block
        block["type"] = "image"
        if payload.encoding == "base64":
            block["source"] = {
                "type": "base64",
                "data": payload.data,
                **({"media_type": payload.mime_type} if payload.mime_type else {}),
            }
        else:
            block["source"] = {
                "type": "url",
                "url": payload.data,
            }

    elif payload.type == "document":
        block["type"] = "document"
        if payload.data is None:
            block["source"] = {"type": "url", "url": payload.ref}
        elif payload.encoding == "base64":
            block["source"] = {
                "type": "base64",
                "data": payload.data,
                **({"media_type": payload.mime_type} if payload.mime_type else {}),
            }
        else:
            block["source"] = {
                "type": "text",
                "media_type": "text/plain",
                "data": payload.data,
            }

    return block
