import json
from typing import List, Literal, Optional, Union

from core.models import EType, HOChunk, HOMessage, HopilotPayload
from utils import get_logger

from .types import (
    OPENAI_CALL_ID,
    OPENAI_RESPONSE_ID,
    OpenAIConfiguration,
    OpenAIFunctionCallItem,
    OpenAIFunctionDef,
    OpenAIFunctionOutputItem,
    OpenAIItem,
    OpenAIMessageItem,
    OpenAIPart,
    OpenAIPayload,
)

_ChunkItem = Union[OpenAIPart, OpenAIFunctionCallItem, OpenAIFunctionOutputItem]

logger = get_logger("OpenAIFormatter")


def format_payload(payload: HopilotPayload, config: OpenAIConfiguration) -> OpenAIPayload:
    """HopilotPayload를 Responses API의 input 배열 구조로 변환합니다."""
    previous_response_id, query_idx = _find_previous_response_id(payload)

    if previous_response_id:
        # query 안에서 찾은 경우: 그 ai 메시지 이후만 전송 (ReAct 루프)
        # memory 안에서 찾은 경우: query 전체 전송 (일반 멀티턴)
        messages = payload.query[query_idx + 1:] if query_idx is not None else payload.query
    else:
        messages = [*payload.memory, *payload.query]
    input_items: List[OpenAIItem] = _format_messages(messages)

    openai_payload: OpenAIPayload = {
        "model": config["model"],
        "input": input_items,
        "stream": True,
        "store": True,
        "max_output_tokens": config["max_output_tokens"],
        "reasoning": config.get("reasoning", {"effort": "high", "summary": "auto"}),
    }

    if previous_response_id:
        openai_payload["previous_response_id"] = previous_response_id

    if payload.context.system_instructions:
        openai_payload["instructions"] = payload.context.system_instructions

    if "truncation" in config:
        openai_payload["truncation"] = config["truncation"]

    if "include" in config:
        openai_payload["include"] = config["include"]

    if "text" in config:
        openai_payload["text"] = config["text"]

    if payload.tools:
        openai_payload["tools"] = _format_tool_declarations(payload.tools)

    return openai_payload


def _find_previous_response_id(payload: HopilotPayload) -> tuple[Optional[str], Optional[int]]:
    """가장 최근 ai 메시지의 response_id를 반환합니다.

    Returns:
        (response_id, query_idx) —
        query_idx: query 안에서 찾은 경우 해당 인덱스, memory에서 찾은 경우 None
    """
    total_memory = len(payload.memory)
    total_query  = len(payload.query)

    for i, msg in reversed(list(enumerate(payload.query))):
        if msg.role != "ai":
            continue
        for chunk in reversed(msg.chunks):
            p = chunk.payload
            if p.type == "stream" and p.event == EType.MESSAGE_END and p.model_extra and p.model_extra.get(OPENAI_RESPONSE_ID):
                resp_id = p.model_extra[OPENAI_RESPONSE_ID]
                session_idx = total_memory + i  # 전체 세션 기준 인덱스
                logger.info(
                    f"[previous_response_id] 출처=query  "
                    f"query[{i}/{total_query - 1}]  "
                    f"session_idx={session_idx}  "
                    f"resp_id=...{resp_id[-16:] if resp_id else '(none)'}"
                )
                return resp_id, i

    for j, msg in enumerate(reversed(payload.memory)):
        if msg.role != "ai":
            continue
        for chunk in reversed(msg.chunks):
            p = chunk.payload
            if p.type == "stream" and p.event == EType.MESSAGE_END and p.model_extra and p.model_extra.get(OPENAI_RESPONSE_ID):
                resp_id = p.model_extra[OPENAI_RESPONSE_ID]
                memory_idx = total_memory - 1 - j  # 정방향 인덱스
                session_idx = memory_idx
                logger.info(
                    f"[previous_response_id] 출처=memory  "
                    f"memory[{memory_idx}/{total_memory - 1}]  "
                    f"session_idx={session_idx}  "
                    f"resp_id=...{resp_id[-16:] if resp_id else '(none)'}"
                )
                return resp_id, None

    logger.info(
        f"[previous_response_id] 없음 — memory={total_memory}개  query={total_query}개  (cold start)"
    )
    return None, None


def _format_messages(messages: List[HOMessage]) -> List[OpenAIItem]:
    """HOMessage 리스트를 Responses API input 배열로 변환합니다."""
    items: List[OpenAIItem] = []
    for msg in messages:
        if msg.role == "system":
            continue
        items.extend(_format_message(msg))
    return items


def _format_message(msg: HOMessage) -> List[OpenAIItem]:
    """단일 HOMessage를 1개 이상의 OpenAIItem 리스트로 변환합니다.

    텍스트/이미지/파일은 Part로 누적해 MessageItem으로 flush하고,
    FC/FO는 그 전에 flush한 뒤 독립 Item으로 추가합니다.
    """
    role: Literal["user", "assistant"] = "assistant" if msg.role == "ai" else "user"
    items: List[OpenAIItem] = []
    pending_parts: List[OpenAIPart] = []

    for chunk in msg.chunks:
        result = _format_chunk(chunk, role)
        if result is None:
            continue

        if result.get("type") in ("function_call", "function_call_output"):
            if pending_parts:
                items.append(OpenAIMessageItem(type="message", role=role, content=pending_parts))
                pending_parts = []
            items.append(result)
        else:
            pending_parts.append(result)

    if pending_parts:
        items.append(OpenAIMessageItem(type="message", role=role, content=pending_parts))

    return items


def _format_chunk(chunk: HOChunk, role: Literal["user", "assistant"]) -> Optional[_ChunkItem]:
    """단일 HOChunk를 OpenAIPart 또는 FC/FO Item으로 변환합니다."""
    p = chunk.payload

    match p.type:
        case "text":
            content_type = "output_text" if role == "assistant" else "input_text"
            return {"type": content_type, "text": p.text}

        case "thought":
            # Enterprise Gateway: reasoning item 재입력 시 400 반환 → 제외
            return None

        case "image":
            if p.data is None:
                return None
            return {
                "type": "input_image",
                "image_url": f"data:{p.mime_type};base64,{p.data}" if p.encoding == "base64" else p.data,
            }

        case "document":
            if p.data is None:
                return None
            if p.encoding == "base64":
                return {
                    "type": "input_file",
                    "filename": "",
                    "file_data": f"data:{p.mime_type};base64,{p.data}",
                }
            return {"type": "input_text", "text": p.data}

        case "tool_call":
            call_id = p.model_extra.get(OPENAI_CALL_ID) if p.model_extra else None
            return OpenAIFunctionCallItem(
                type="function_call",
                call_id=call_id or "",
                name=p.tool_name,
                arguments=json.dumps(p.tool_args, ensure_ascii=False),
            )

        case "tool_output":
            output_id = p.model_extra.get(OPENAI_CALL_ID) if p.model_extra else None
            output = p.output
            if p.truncated:
                output += "\n[결과가 너무 길어 잘렸습니다. 더 좁은 범위로 재시도하거나 다른 방법을 사용하세요.]"
            return OpenAIFunctionOutputItem(
                type="function_call_output",
                call_id=output_id or "",
                output=output,
            )

        case _:
            return None


def _format_tool_declarations(tools) -> List[OpenAIFunctionDef]:
    return [
        OpenAIFunctionDef(
            type="function",
            name=t.name,
            description=t.description,
            parameters=t.parameters,
            strict=None,
        )
        for t in tools
    ]
