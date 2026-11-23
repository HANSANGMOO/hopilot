import json
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

from .types import EXAONE_TOOL_ID

logger = get_logger("ExaoneParser")


class ExaoneParser:
    """
    EXAONE Chat Completions 호환 SSE 스트림 파서.

    delta.reasoning_content는 ThoughtPayload로, delta.content는 TextPayload로 즉시 emit하며,
    delta.tool_calls는 index별 버퍼에 누적한 뒤 finish_reason 또는 [DONE] 시점에
    ToolCallPayload로 flush합니다.
    """

    def __init__(self) -> None:
        self._tool_calls: Dict[int, Dict[str, Any]] = {}
        self._started: bool = False
        self._ended: bool = False

    def parse_sse_event(self, event_line: str) -> List[HOChunk]:
        line = event_line.strip()
        if not line.startswith("data:"):
            return []

        data_str = line[len("data:"):].strip()
        if not data_str:
            return []

        if data_str == "[DONE]":
            chunks: List[HOChunk] = []
            if self._tool_calls:
                chunks.extend(self._flush_tool_calls())
            if self._started and not self._ended:
                self._ended = True
                chunks.append(
                    HOChunk(payload=StreamPayload(event=EType.MESSAGE_END, finish_reason="stop"))
                )
            return chunks

        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            logger.warning(f"[ExaoneParser] JSON 파싱 실패: {data_str[:200]!r}")
            return []

        return self._dispatch(data)

    def _dispatch(self, data: Dict[str, Any]) -> List[HOChunk]:
        if data.get("result_code") is not None or data.get("error") is not None:
            err = data.get("error")
            if isinstance(err, dict):
                msg = err.get("message") or str(err)
            elif err is not None:
                msg = str(err)
            else:
                msg = data.get("description") or str(data)
            logger.error(f"[ExaoneParser] 스트림 에러: {msg}")
            return [HOChunk(payload=StreamPayload(event=EType.ERROR, error_message=str(msg)))]

        chunks: List[HOChunk] = []

        if not self._started:
            self._started = True
            chunks.append(HOChunk(payload=StreamPayload(event=EType.MESSAGE_START)))

        choices = data.get("choices") or []
        if choices:
            choice = choices[0]
            delta = choice.get("delta") or {}

            if reasoning := delta.get("reasoning_content"):
                chunks.append(HOChunk(payload=ThoughtPayload(thought=reasoning)))

            if content := delta.get("content"):
                chunks.append(HOChunk(payload=TextPayload(text=content)))

            for tc_delta in delta.get("tool_calls") or []:
                self._accumulate_tool_call(tc_delta)

            if finish_reason := choice.get("finish_reason"):
                chunks.extend(self._flush_tool_calls())
                self._ended = True
                chunks.append(
                    HOChunk(
                        payload=StreamPayload(event=EType.MESSAGE_END, finish_reason=finish_reason)
                    )
                )

        usage = data.get("usage")
        if usage:
            raw_completion = usage.get("completion_tokens", 0)
            reasoning_tokens = usage.get("reasoning_tokens")
            if reasoning_tokens is None:
                reasoning_tokens = (usage.get("completion_tokens_details") or {}).get(
                    "reasoning_tokens"
                )
            output_tokens = max(0, raw_completion - (reasoning_tokens or 0))
            cached_tokens = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
            chunks.append(
                HOChunk(
                    payload=UsagePayload(
                        input_tokens=usage.get("prompt_tokens", 0),
                        output_tokens=output_tokens,
                        thinking_tokens=reasoning_tokens if reasoning_tokens else None,
                        cached_tokens=cached_tokens,
                        total_tokens=usage.get("total_tokens"),
                        raw=usage,
                    )
                )
            )

        return chunks

    def _accumulate_tool_call(self, tc_delta: Dict[str, Any]) -> None:
        index = tc_delta.get("index", 0)
        buf = self._tool_calls.setdefault(index, {"id": "", "name": "", "arguments": ""})

        if tc_delta.get("id"):
            buf["id"] = tc_delta["id"]

        function = tc_delta.get("function") or {}
        if function.get("name"):
            buf["name"] = function["name"]
        if function.get("arguments"):
            buf["arguments"] += function["arguments"]

    def _flush_tool_calls(self) -> List[HOChunk]:
        chunks: List[HOChunk] = []
        for index in sorted(self._tool_calls):
            buf = self._tool_calls[index]
            try:
                args = json.loads(buf["arguments"]) if buf["arguments"] else {}
            except json.JSONDecodeError:
                args = {}
            extra = {EXAONE_TOOL_ID: buf["id"]} if buf["id"] else {}
            chunks.append(
                HOChunk(
                    payload=ToolCallPayload(
                        tool_name=buf["name"],
                        tool_args=args,
                        **extra,
                    )
                )
            )
        self._tool_calls.clear()
        return chunks
