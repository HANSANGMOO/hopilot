import json
from typing import Any, Dict, List, Literal, Optional, TypedDict

from api.provider.base_provider import BaseProvider
from core.models import (
    HOChunk,
    HopilotPayload,
    StreamPayload,
    TextPayload,
    ThoughtPayload,
    ToolCallPayload,
)
from utils import get_logger

logger = get_logger("ClaudeProvider")

# Anthropic Messages API wire 상수
ANTHROPIC_VERSION = "2023-06-01"
# 멀티턴에서 thinking 블록을 재전송하려면 서명(signature)이 필요합니다.
# Gemini의 thoughtSignature와 동일한 역할로, payload.model_extra에 보관합니다.
CLAUDE_SIGNATURE = "signature"


# --- Anthropic Request TypedDicts ---
class ClaudeContentBlock(TypedDict, total=False):
    type: str
    text: str
    thinking: str
    signature: str
    id: str
    name: str
    input: Dict[str, Any]
    tool_use_id: str
    content: Any


class ClaudeMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: List[ClaudeContentBlock]


class ClaudeThinkingConfig(TypedDict):
    type: Literal["adaptive"]


class ClaudePayload(TypedDict, total=False):
    model: str
    max_tokens: int
    stream: bool
    system: str
    messages: List[ClaudeMessage]
    thinking: ClaudeThinkingConfig
    tools: List[Dict[str, Any]]


# ---------------------------------


class ClaudeProvider(BaseProvider, provider="claude"):
    """
    Anthropic Claude (Messages API) REST 공급자 구현체입니다.
    """

    base_url = "https://api.anthropic.com/v1/messages"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-4-8",
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url, **kwargs)
        self.max_tokens: int = int(self.options.get("max_tokens", 16000))
        # 어댑티브 사고(Opus 4.8 권장). 비활성화하려면 enable_thinking=False 전달.
        self.enable_thinking: bool = bool(self.options.get("enable_thinking", True))

        # [스트리밍 상태] Anthropic은 tool_use 인자(input)를 여러 SSE 이벤트에 걸쳐
        # 조각(input_json_delta)으로 보냅니다. provider 인스턴스 수명 = 스트림 하나이므로
        # content_block index 별 누적 버퍼를 인스턴스 속성으로 안전하게 보관합니다.
        self._tool_buffers: Dict[int, Dict[str, Any]] = {}

    def build_url(self) -> str:
        """Anthropic Messages 엔드포인트 (모델은 body에 담기므로 URL은 고정)."""
        return self.base_url

    def build_headers(self) -> Dict[str, str]:
        """Anthropic 인증 및 버전 헤더 생성."""
        return {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

    def format_payload(self, payload: HopilotPayload) -> ClaudePayload:
        """HopilotPayload를 Anthropic Messages 요청(body)으로 변환합니다."""
        request: ClaudePayload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "stream": True,
        }

        # 1. System Instruction (top-level system)
        if payload.system_instructions:
            request["system"] = payload.system_instructions

        # 2. Messages 구성
        messages: List[ClaudeMessage] = []
        for msg in payload.messages:
            if msg.role == "system":
                continue  # system은 위에서 별도 처리

            role: Literal["user", "assistant"] = "assistant" if msg.role == "ai" else "user"
            blocks: List[ClaudeContentBlock] = []

            for chunk in msg.chunks:
                block = self._format_chunk(chunk)
                if block:
                    blocks.append(block)

            if blocks:
                messages.append({"role": role, "content": blocks})

        request["messages"] = messages

        # 3. 어댑티브 사고 (Opus 4.8/4.7은 adaptive만 허용; budget_tokens/온도는 400)
        if self.enable_thinking:
            request["thinking"] = {"type": "adaptive"}

        # 4. Tools (context에 도구 명세가 있으면 추가)
        if payload.context and "tools" in payload.context:
            request["tools"] = payload.context["tools"]

        return request

    def _format_chunk(self, chunk: HOChunk) -> ClaudeContentBlock:
        """단일 HOChunk를 Anthropic content 블록으로 변환합니다."""
        block: ClaudeContentBlock = {}
        payload = chunk.payload

        if payload.type == "text":
            block["type"] = "text"
            block["text"] = payload.text

        elif payload.type == "thought":
            # thinking 블록 재전송엔 signature가 필수입니다. 서명이 없으면(스트리밍 표시용
            # 사고였던 경우) 재전송 시 거부되므로, 서명이 있을 때만 블록으로 복원합니다.
            sig = payload.model_extra.get(CLAUDE_SIGNATURE) if payload.model_extra else None
            if sig:
                block["type"] = "thinking"
                block["thinking"] = payload.thought
                block["signature"] = sig

        elif payload.type == "tool_call":
            call_id = payload.model_extra.get("id") if payload.model_extra else None
            block["type"] = "tool_use"
            block["id"] = call_id or ""
            block["name"] = payload.tool_name
            block["input"] = payload.tool_args

        elif payload.type == "tool_output":
            output_id = payload.model_extra.get("id") if payload.model_extra else None
            block["type"] = "tool_result"
            if output_id:
                block["tool_use_id"] = output_id
            block["content"] = payload.output

        return block

    def parse_sse_event(self, event_line: str) -> List[HOChunk]:
        """Anthropic SSE 문자열 라인 파싱 및 변환.

        Anthropic은 'event:'와 'data:' 라인을 쌍으로 보냅니다. data 페이로드 자체에
        'type' 필드가 있으므로 data 라인만 보고 분기합니다.
        """
        line = event_line.strip()
        if not line.startswith("data:"):
            return []

        data_str = line[len("data:") :].strip()
        if not data_str:
            return []

        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            return []

        return self._parse_chunk(data)

    def _parse_chunk(self, data: Dict[str, Any]) -> List[HOChunk]:
        """Anthropic SSE 이벤트(dict)를 HOChunk 리스트로 변환합니다."""
        etype = data.get("type")
        chunks: List[HOChunk] = []

        if etype == "content_block_start":
            block = data.get("content_block", {})
            if block.get("type") == "tool_use":
                index = data.get("index", 0)
                self._tool_buffers[index] = {
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "json": "",
                }

        elif etype == "content_block_delta":
            index = data.get("index", 0)
            delta = data.get("delta", {})
            dtype = delta.get("type")

            if dtype == "text_delta":
                text = delta.get("text", "")
                if text:
                    chunks.append(HOChunk(payload=TextPayload(text=text)))

            elif dtype == "thinking_delta":
                # 기본(display=omitted)에선 thinking 텍스트가 비어있을 수 있으므로 가드.
                thought = delta.get("thinking", "")
                if thought:
                    chunks.append(HOChunk(payload=ThoughtPayload(thought=thought)))

            elif dtype == "input_json_delta":
                if index in self._tool_buffers:
                    self._tool_buffers[index]["json"] += delta.get("partial_json", "")

            # TODO: signature_delta — 멀티턴 thinking 재전송용 서명 보존(추후).

        elif etype == "content_block_stop":
            index = data.get("index", 0)
            buf = self._tool_buffers.pop(index, None)
            if buf is not None:
                try:
                    args = json.loads(buf["json"]) if buf["json"] else {}
                except json.JSONDecodeError:
                    args = {}
                extra = {"id": buf["id"]} if buf["id"] else {}
                chunks.append(
                    HOChunk(
                        payload=ToolCallPayload(
                            tool_name=buf["name"], tool_args=args, **extra
                        )
                    )
                )

        elif etype == "message_delta":
            stop_reason = data.get("delta", {}).get("stop_reason")
            if stop_reason:
                chunks.append(HOChunk(payload=StreamPayload(finish_reason=stop_reason)))

        elif etype == "error":
            logger.error(f"[ClaudeProvider] 스트림 에러 이벤트: {data.get('error', {})}")

        # message_start / message_stop / ping 등은 무시(빈 리스트)
        return chunks
