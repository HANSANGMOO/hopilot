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

from .types import OPENAI_CALL_ID, OPENAI_REASONING_SIGNATURE, OPENAI_RESPONSE_ID

logger = get_logger("OpenAIParser")


class OpenAIParser:
    """
    OpenAI Responses API SSE 스트림 파서.

    [계층 구조]
      Response  — HOMessage 1개에 대응하는 단위 (Claude: message_start ~ message_stop)
        Item    — Response 안의 content 조각 단위 (Claude: content_block_start ~ content_block_stop)
                  type=reasoning    → ThoughtPayload
                  type=function_call → ToolCallPayload
                  type=message      → TextPayload (output_text.delta로 즉시 emit)
          Payload — Item 안의 실제 데이터 조각 (Claude: content_block_delta)
                    reasoning_summary_text.delta → ThoughtPayload 누적
                    function_call_arguments.delta → arguments 누적
                    output_text.delta            → TextPayload 즉시 emit

    [이벤트 흐름]
        response.created         ← Response 시작 (무시)
        response.in_progress     ← Response 처리 중 (무시)

          ┌─ output_item.added   (type=reasoning)   ← Item 시작: reasoning 버퍼 생성
          │    reasoning_summary_text.delta × N      ← Payload: thought 누적
          │    reasoning_summary_text.done
          └─ output_item.done                        → ThoughtPayload emit

          ┌─ output_item.added   (type=function_call) ← Item 시작: FC 버퍼 생성
          │    function_call_arguments.delta × N       ← Payload: arguments 누적
          │    function_call_arguments.done
          └─ output_item.done                          → ToolCallPayload emit

          ┌─ output_item.added   (type=message)      ← Item 시작 (버퍼 불필요)
          │    content_part.added
          │      output_text.delta × N               ← Payload: TextPayload 즉시 emit
          │    output_text.done
          │    content_part.done
          └─ output_item.done                        (무시 — 이미 delta로 emit)

        response.completed       ← Response 종료 → UsagePayload + StreamPayload emit
        response.failed          ← Response 오류 → StreamPayload(error) emit
    """

    def __init__(self) -> None:
        self._items: Dict[str, Dict[str, Any]] = {}  # item_id → 버퍼

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def parse_sse_event(self, event_line: str) -> List[HOChunk]:
        line = event_line.strip()
        if not line.startswith("data:"):
            return []

        data_str = line[len("data:"):].strip()
        if not data_str or data_str == "[DONE]":
            return []

        try:
            data = json.loads(data_str)
            return self._dispatch(data)
        except Exception as e:
            logger.warning(f"[parse_sse_event] JSON 파싱 실패: {e} | line: {repr(event_line[:200])}")
            return []

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, data: Dict[str, Any]) -> List[HOChunk]:
        match data.get("type", ""):
            case "response.created":
                return [HOChunk(payload=StreamPayload(event=EType.MESSAGE_START))]
            case "response.in_progress":
                return []
            case "response.completed":
                return self._on_response_completed(data)
            case "response.failed":
                return self._on_response_failed(data)
            case "response.output_item.added":
                return self._on_output_item_added(data)
            case "response.output_item.done":
                return self._on_output_item_done(data)
            case "response.reasoning_summary_text.delta":
                return self._on_reasoning_summary_text_delta(data)
            case "response.function_call_arguments.delta":
                return self._on_function_call_arguments_delta(data)
            case "response.output_text.delta":
                return self._on_output_text_delta(data)
            case _:
                return []

    # ------------------------------------------------------------------
    # Response 단위 (HOMessage 1개 = 1 Response)
    # ------------------------------------------------------------------

    def _on_response_created(self, data: Dict[str, Any]) -> List[HOChunk]:
        return []

    def _on_response_in_progress(self, data: Dict[str, Any]) -> List[HOChunk]:
        return []

    def _on_response_completed(self, data: Dict[str, Any]) -> List[HOChunk]:
        # Response 종료 — usage 확정 시점
        # response.id 는 response.completed 에 항상 포함 → OPENAI_RESPONSE_ID로 저장
        response_obj = data.get("response", {})
        usage = response_obj.get("usage") or {}
        chunks: List[HOChunk] = []

        if usage:
            output_details = usage.get("output_tokens_details") or {}
            input_details  = usage.get("input_tokens_details") or {}
            reasoning_tokens = output_details.get("reasoning_tokens")
            cached_tokens    = input_details.get("cached_tokens")
            raw_output       = usage.get("output_tokens", 0)
            chunks.append(HOChunk(payload=UsagePayload(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=raw_output - (reasoning_tokens or 0),
                thinking_tokens=reasoning_tokens,
                cached_tokens=cached_tokens,
                total_tokens=usage.get("total_tokens"),
                raw=usage,
            )))

        status = response_obj.get("status", "completed")
        finish_reason = response_obj.get("incomplete_details", {}).get("reason", "length") \
            if status == "incomplete" else "stop"
        response_id = response_obj.get("id") or None
        extra = {OPENAI_RESPONSE_ID: response_id} if response_id else {}
        chunks.append(HOChunk(payload=StreamPayload(event=EType.MESSAGE_END, finish_reason=finish_reason, **extra)))

        return chunks

    def _on_response_failed(self, data: Dict[str, Any]) -> List[HOChunk]:
        return [HOChunk(payload=StreamPayload(finish_reason="error"))]

    # ------------------------------------------------------------------
    # Item 단위 (Response 안의 content 조각 — reasoning / FC / message)
    # ------------------------------------------------------------------

    def _on_output_item_added(self, data: Dict[str, Any]) -> List[HOChunk]:
        # Item 시작 — item.type 에 따라 _items 버퍼 초기화
        item    = data.get("item", {})
        item_id = item.get("id", "")

        match item.get("type"):
            case "reasoning":
                self._items[item_id] = {"type": "reasoning", "thought": ""}
            case "function_call":
                self._items[item_id] = {
                    "type": "function_call",
                    "id": item_id,                       # fc_...  → 프론트엔드 raw_id 매칭용
                    "call_id": item.get("call_id", ""),  # call_... → formatter call_id 매칭용
                    "name": item.get("name", ""),
                    "arguments": "",
                }
            # type=message 는 output_text.delta 로 즉시 emit — 버퍼 불필요

        return []

    def _on_output_item_done(self, data: Dict[str, Any]) -> List[HOChunk]:
        # Item 완료 — 버퍼에서 꺼내 Payload emit
        item    = data.get("item", {})
        item_id = item.get("id", "")
        buf     = self._items.pop(item_id, None)
        if buf is None:
            return []

        match buf["type"]:
            case "reasoning":
                return [HOChunk(payload=ThoughtPayload(
                    thought="",
                    **{OPENAI_REASONING_SIGNATURE: item_id},
                ))]
            case "function_call":
                try:
                    args = json.loads(buf["arguments"]) if buf["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}
                extra = {OPENAI_CALL_ID: buf["call_id"]} if buf["call_id"] else {}
                return [HOChunk(payload=ToolCallPayload(
                    tool_name=buf["name"],
                    tool_args=args,
                    id=buf["id"],   # model_extra["id"] → 프론트엔드 payload.id (raw_id 매칭)
                    **extra,        # model_extra["call_id"] → formatter
                ))]
            case _:
                return []

    # ------------------------------------------------------------------
    # Payload 단위 — reasoning item 내부 텍스트 조각
    # ------------------------------------------------------------------

    def _on_reasoning_summary_text_delta(self, data: Dict[str, Any]) -> List[HOChunk]:
        # _items[item_id]["thought"] 에 누적
        delta = data.get("delta", "")
        if delta:
            return [HOChunk(payload=ThoughtPayload(thought=delta))]
        return []

    def _on_reasoning_summary_text_done(self, data: Dict[str, Any]) -> List[HOChunk]:
        return []

    # ------------------------------------------------------------------
    # Payload 단위 — function_call item 내부 arguments 조각
    # ------------------------------------------------------------------

    def _on_function_call_arguments_delta(self, data: Dict[str, Any]) -> List[HOChunk]:
        # _items[item_id]["arguments"] 에 누적
        item_id = data.get("item_id", "")
        buf = self._items.get(item_id)
        if buf and buf["type"] == "function_call":
            buf["arguments"] += data.get("delta", "")
        return []

    def _on_function_call_arguments_done(self, data: Dict[str, Any]) -> List[HOChunk]:
        return []

    # ------------------------------------------------------------------
    # Payload 단위 — message item 내부 텍스트 조각 (즉시 emit)
    # ------------------------------------------------------------------

    def _on_content_part_added(self, data: Dict[str, Any]) -> List[HOChunk]:
        return []

    def _on_content_part_done(self, data: Dict[str, Any]) -> List[HOChunk]:
        return []

    def _on_output_text_delta(self, data: Dict[str, Any]) -> List[HOChunk]:
        # 버퍼 없이 TextPayload 즉시 emit
        delta = data.get("delta", "")
        if delta:
            return [HOChunk(payload=TextPayload(text=delta))]
        return []

    def _on_output_text_done(self, data: Dict[str, Any]) -> List[HOChunk]:
        return []


