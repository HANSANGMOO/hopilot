import json
from typing import Any, Dict, List, Optional

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
from .types import CLAUDE_SIGNATURE, CLAUDE_TOOL_ID

logger = get_logger("ClaudeParser")


class ClaudeParser:
    """
    Anthropic SSE 스트림 파서.

    이벤트 수신 순서:
        message_start
          content_block_start  (index=N)
            content_block_delta × M
          content_block_stop   (index=N)
          ...
        message_delta
        message_stop
    """

    def __init__(self) -> None:
        self._input_usage: Dict[str, Any] = {}         # message_start.message.usage
        self._blocks: Dict[int, Dict[str, Any]] = {}   # index → block 버퍼

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def parse_sse_event(self, event_line: str) -> List[HOChunk]:
        """Anthropic SSE 문자열 라인을 파싱하여 HOChunk 리스트로 변환합니다."""
        line = event_line.strip()
        if not line.startswith("data:"):
            return []

        data_str = line[len("data:"):].strip()
        if not data_str:
            return []

        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            return []

        return self._dispatch(data)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, data: Dict[str, Any]) -> List[HOChunk]:
        etype = data.get("type")

        if etype == "message_start":
            return self._on_message_start(data)
        elif etype == "message_delta":
            return self._on_message_delta(data)
        elif etype == "message_stop":
            return self._on_message_stop(data)
        elif etype == "content_block_start":
            return self._on_content_block_start(data)
        elif etype == "content_block_delta":
            return self._on_content_block_delta(data)
        elif etype == "content_block_stop":
            return self._on_content_block_stop(data)
        elif etype == "error":
            logger.error(f"[ClaudeParser] 스트림 에러: {data.get('error', {})}")

        return []

    # ------------------------------------------------------------------
    # Message lifecycle
    # ------------------------------------------------------------------

    def _on_message_start(self, data: Dict[str, Any]) -> List[HOChunk]:
        self._input_usage = data.get("message", {}).get("usage", {})
        return [HOChunk(payload=StreamPayload(event=EType.MESSAGE_START))]

    def _on_message_delta(self, data: Dict[str, Any]) -> List[HOChunk]:
        # output_tokens는 스트림 종료 시 확정되므로 message_start usage와 병합
        delta_usage = data.get("usage", {})
        merged = {**self._input_usage, **delta_usage}

        chunks: List[HOChunk] = []

        if "output_tokens" in merged:
            thinking_tokens = (merged.get("output_tokens_details") or {}).get("thinking_tokens")
            raw_output = merged.get("output_tokens", 0)
            chunks.append(HOChunk(payload=UsagePayload(
                input_tokens=merged.get("input_tokens", 0),
                output_tokens=raw_output - (thinking_tokens or 0),
                thinking_tokens=thinking_tokens if thinking_tokens else None,
                cached_tokens=merged.get("cache_read_input_tokens"),
                cache_creation_tokens=merged.get("cache_creation_input_tokens"),
                raw=merged,
            )))

        stop_reason = data.get("delta", {}).get("stop_reason")
        if stop_reason:
            chunks.append(HOChunk(payload=StreamPayload(event=EType.MESSAGE_END, finish_reason=stop_reason)))

        return chunks

    def _on_message_stop(self, data: Dict[str, Any]) -> List[HOChunk]:
        return []

    # ------------------------------------------------------------------
    # Content block lifecycle
    # ------------------------------------------------------------------

    def _on_content_block_start(self, data: Dict[str, Any]) -> List[HOChunk]:
        index = data.get("index", 0)
        block = data.get("content_block", {})
        btype = block.get("type")

        if btype == "thinking":
            self._blocks[index] = {"type": "thinking"}
        elif btype == "tool_use":
            self._blocks[index] = {
                "type": "tool_use",
                CLAUDE_TOOL_ID: block.get(CLAUDE_TOOL_ID, ""),
                "name": block.get("name", ""),
                "json": "",
            }

        return []

    def _on_content_block_delta(self, data: Dict[str, Any]) -> List[HOChunk]:
        index = data.get("index", 0)
        delta = data.get("delta", {})
        dtype = delta.get("type")
        block: Optional[Dict[str, Any]] = self._blocks.get(index)

        if dtype == "text_delta":
            text = delta.get("text", "")
            if text:
                return [HOChunk(payload=TextPayload(text=text))]

        elif dtype == "thinking_delta":
            thought = delta.get("thinking", "")
            if thought:
                return [HOChunk(payload=ThoughtPayload(thought=thought))]

        elif dtype == "signature_delta":
            sig = delta.get("signature", "")
            if sig and block and block["type"] == "thinking":
                return [HOChunk(payload=ThoughtPayload(
                    thought="",
                    **{CLAUDE_SIGNATURE: sig},
                ))]

        elif dtype == "input_json_delta":
            if block and block["type"] == "tool_use":
                fragment = delta.get("partial_json", "")
                logger.debug(f"[ClaudeParser] tool_use partial_json fragment: {fragment!r}")
                block["json"] += fragment

        return []

    def _on_content_block_stop(self, data: Dict[str, Any]) -> List[HOChunk]:
        index = data.get("index", 0)
        block = self._blocks.pop(index, None)
        if block is None:
            return []

        btype = block["type"]

        if btype == "tool_use":
            logger.debug(f"[ClaudeParser] tool_use raw json ({block['name']}): {block['json']!r}")
            try:
                args = json.loads(block["json"]) if block["json"] else {}
            except json.JSONDecodeError:
                args = {}
            logger.debug(f"[ClaudeParser] tool_use parsed args ({block['name']}): {args!r}")
            extra = {CLAUDE_TOOL_ID: block[CLAUDE_TOOL_ID]} if block[CLAUDE_TOOL_ID] else {}
            return [HOChunk(payload=ToolCallPayload(
                tool_name=block["name"], tool_args=args, **extra
            ))]

        return []
