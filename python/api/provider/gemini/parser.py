import json
import uuid
from typing import Any, Dict, List

from core.models import (
    EType,
    HOChunk,
    StreamPayload,
    TextPayload,
    ThoughtPayload,
    ToolCallPayload,
    UsagePayload,
)
from utils import get_logger

from .types import GEMINI_THOUGHT_SIGNATURE, GEMINI_TOOL_ID

logger = get_logger("GeminiParser")


def parse_sse_event(event_line: str) -> List[HOChunk]:
    """NDJSON(줄 단위 JSON) 및 SSE 형식 모두 처리합니다."""
    line = event_line.strip()
    if not line:
        return []

    if line.startswith("data: "):
        data_str = line[len("data: "):].strip()
    elif line.startswith("{"):
        data_str = line
    else:
        return []

    if not data_str or data_str == "[DONE]":
        return []

    try:
        data = json.loads(data_str)
        return _parse_chunk(data)
    except Exception as e:
        logger.warning(f"[parse_sse_event] JSON 파싱 실패: {e} | line: {repr(event_line[:200])}")
        return []


def _parse_chunk(data: Dict[str, Any]) -> List[HOChunk]:
    """Gemini JSON 딕셔너리를 HOChunk 리스트로 변환합니다."""
    chunks: List[HOChunk] = []

    # 1. candidates → 텍스트 / 사고 / 도구 청크
    candidate = None
    if data.get("candidates"):
        candidate = data["candidates"][0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])

        for part in parts:
            payload = None
            extra = {}

            if "thoughtSignature" in part:
                extra[GEMINI_THOUGHT_SIGNATURE] = part["thoughtSignature"]

            if "text" in part:
                if part.get("thought") is True:
                    payload = ThoughtPayload(thought=part["text"], **extra)
                else:
                    payload = TextPayload(text=part["text"], **extra)
            elif "functionCall" in part:
                call = part["functionCall"]
                extra[GEMINI_TOOL_ID] = call.get(GEMINI_TOOL_ID) or f"call_{uuid.uuid4().hex[:8]}"
                payload = ToolCallPayload(
                    tool_name=call.get("name", ""),
                    tool_args=call.get("args", {}),
                    **extra,
                )

            if payload:
                chunks.append(HOChunk(payload=payload))

    # 2. usageMetadata → UsagePayload
    usage_meta = data.get("usageMetadata", {})
    if "promptTokenCount" in usage_meta:
        chunks.append(HOChunk(payload=UsagePayload(
            input_tokens=usage_meta["promptTokenCount"],
            output_tokens=usage_meta.get("candidatesTokenCount", 0),
            thinking_tokens=usage_meta.get("thoughtsTokenCount"),
            cached_tokens=usage_meta.get("cachedContentTokenCount"),
            total_tokens=usage_meta.get("totalTokenCount"),
            raw=usage_meta,
        )))

    # 3. finishReason → StreamPayload
    if candidate is not None:
        finish_reason = candidate.get("finishReason")
        if finish_reason:
            chunks.append(HOChunk(payload=StreamPayload(event=EType.MESSAGE_END, finish_reason=finish_reason)))

    return chunks
