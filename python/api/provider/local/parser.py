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

from .types import LOCAL_TOOL_ID

logger = get_logger("LocalParser")


class LocalParser:
    """
    OpenAI Chat Completions 호환 로컬 LLM 게이트웨이 SSE 스트림 파서.

    choices[0].delta.tool_calls[]는 index 기준으로 여러 청크에 걸쳐 조각(arguments)이
    스트리밍될 수 있으므로(OpenAI 표준 동작) index별 버퍼에 누적한 뒤 finish_reason 시점에
    ToolCallPayload로 emit합니다. text(content)는 델타 즉시 emit합니다.

    delta.reasoning_content(qwen 계열에서 항상 노출됨, gemma는 이 게이트웨이에서 미노출)는
    별도 필드로 스트리밍되며 content보다 먼저 등장하므로 ThoughtPayload로 즉시 emit합니다.
    """

    def __init__(self) -> None:
        self._tool_calls: Dict[int, Dict[str, Any]] = {}  # index → {id, name, arguments}
        self._started = False

    def parse_sse_event(self, event_line: str) -> List[HOChunk]:
        line = event_line.strip()
        if not line.startswith("data:"):
            return []

        data_str = line[len("data:"):].strip()
        if not data_str or data_str == "[DONE]":
            return []

        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            return []

        return self._dispatch(data)

    def _dispatch(self, data: Dict[str, Any]) -> List[HOChunk]:
        chunks: List[HOChunk] = []

        if not self._started:
            self._started = True
            chunks.append(HOChunk(payload=StreamPayload(event=EType.MESSAGE_START)))

        choices = data.get("choices") or []
        if choices:
            choice = choices[0]
            delta = choice.get("delta") or {}

            reasoning = delta.get("reasoning_content")
            if reasoning:
                chunks.append(HOChunk(payload=ThoughtPayload(thought=reasoning)))

            content = delta.get("content")
            if content:
                chunks.append(HOChunk(payload=TextPayload(text=content)))

            for tc_delta in delta.get("tool_calls") or []:
                self._accumulate_tool_call(tc_delta)

            finish_reason = choice.get("finish_reason")
            if finish_reason:
                chunks.extend(self._flush_tool_calls())
                chunks.append(HOChunk(payload=StreamPayload(event=EType.MESSAGE_END, finish_reason=finish_reason)))

        usage = data.get("usage")
        if usage:
            chunks.append(HOChunk(payload=UsagePayload(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens"),
                raw=usage,
            )))

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
            extra = {LOCAL_TOOL_ID: buf["id"]} if buf["id"] else {}
            chunks.append(HOChunk(payload=ToolCallPayload(
                tool_name=buf["name"], tool_args=args, **extra
            )))
        self._tool_calls.clear()
        return chunks
