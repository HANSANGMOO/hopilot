import json
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from api.provider.base_provider import BaseProvider
from core.models import (
    CopilotPrompt,
    HOChunk,
    HOMessage,
    StreamPayload,
    TextPayload,
    ThoughtPayload,
    ToolCallPayload,
)
from utils import get_logger

logger = get_logger("ClaudeProvider")

# Anthropic Messages API wire 상수
ANTHROPIC_VERSION = "2023-06-01"


class ClaudeProvider(BaseProvider):
    """
    Anthropic Claude REST API 공급자 구현체입니다.

    Messages API(SSE) 스트림을 표준 HOChunk 단위로 변환하여 배출합니다.
    """

    provider_name = "claude"
    base_url = "https://api.anthropic.com/v1/messages"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-4-8",
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url, **kwargs)
        # 스트리밍 기본값. 필요 시 register 시점에 kwargs로 덮어쓸 수 있습니다.
        self.max_tokens: int = int(self.options.get("max_tokens", 16000))
        # 어댑티브 사고(Opus 4.8 권장 기본값). 비활성화하려면 enable_thinking=False 전달.
        self.enable_thinking: bool = bool(self.options.get("enable_thinking", True))
        self.timeout: float = float(self.options.get("timeout", 600.0))

    async def stream_generate(
        self,
        request: CopilotPrompt,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[HOChunk, None]:
        """
        Claude Messages REST API(SSE)를 호출하고 raw 이벤트를 HOChunk로 변환해 배출합니다.
        """
        payload = self._to_provider_payload(request)
        if tools:
            payload["tools"] = tools

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        # content_block index -> tool_use 누적 버퍼 (스트리밍 중 partial_json 조립용)
        tool_buffers: Dict[int, Dict[str, Any]] = {}

        logger.info(f"[ClaudeProvider] 스트림 요청 시작 - model={self.model}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", self.base_url, headers=headers, json=payload
            ) as response:
                if response.status_code != 200:
                    body = (await response.aread()).decode("utf-8", errors="replace")
                    logger.error(f"[ClaudeProvider] HTTP {response.status_code} 오류: {body}")
                    raise httpx.HTTPStatusError(
                        f"Claude API {response.status_code}: {body}",
                        request=response.request,
                        response=response,
                    )

                async for line in response.aiter_lines():
                    # SSE는 'event:'와 'data:' 라인으로 구성됩니다.
                    # data 페이로드 자체에 'type' 필드가 있어 event 라인 없이도 분기 가능합니다.
                    if not line or not line.startswith("data:"):
                        continue

                    data_str = line[len("data:") :].strip()
                    if not data_str:
                        continue

                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        logger.warning(f"[ClaudeProvider] JSON 파싱 실패: {data_str!r}")
                        continue

                    for chunk in self._handle_event(event, tool_buffers):
                        yield chunk

        logger.info("[ClaudeProvider] 스트림 종료")

    def _handle_event(
        self, event: Dict[str, Any], tool_buffers: Dict[int, Dict[str, Any]]
    ) -> List[HOChunk]:
        """
        단일 SSE 이벤트를 0개 이상의 HOChunk로 변환합니다.
        (이벤트:청크가 1:1이 아니므로 리스트를 반환합니다.)
        """
        etype = event.get("type")
        chunks: List[HOChunk] = []

        if etype == "content_block_start":
            block = event.get("content_block", {})
            if block.get("type") == "tool_use":
                index = event.get("index", 0)
                tool_buffers[index] = {"name": block.get("name", ""), "json": ""}

        elif etype == "content_block_delta":
            delta = event.get("delta", {})
            dtype = delta.get("type")

            if dtype == "text_delta":
                text = delta.get("text", "")
                if text:
                    chunks.append(HOChunk(payload=TextPayload(text=text)))

            elif dtype == "thinking_delta":
                # Opus 4.8은 기본(display=omitted)으로 thinking 텍스트가 비어있습니다.
                # 내용이 있을 때(display=summarized 설정 시)만 ThoughtPayload로 배출합니다.
                thought = delta.get("thinking", "")
                if thought:
                    chunks.append(HOChunk(payload=ThoughtPayload(thought=thought)))

            elif dtype == "input_json_delta":
                index = event.get("index", 0)
                if index in tool_buffers:
                    tool_buffers[index]["json"] += delta.get("partial_json", "")

        elif etype == "content_block_stop":
            index = event.get("index", 0)
            buf = tool_buffers.pop(index, None)
            if buf is not None:
                try:
                    args = json.loads(buf["json"]) if buf["json"] else {}
                except json.JSONDecodeError:
                    args = {}
                chunks.append(
                    HOChunk(payload=ToolCallPayload(tool_name=buf["name"], tool_args=args))
                )

        elif etype == "message_delta":
            stop_reason = event.get("delta", {}).get("stop_reason")
            if stop_reason:
                chunks.append(HOChunk(payload=StreamPayload(finish_reason=stop_reason)))

        elif etype == "error":
            err = event.get("error", {})
            logger.error(f"[ClaudeProvider] 스트림 에러 이벤트: {err}")

        # message_start, content_block_start(text/thinking), ping, message_stop은 무시
        return chunks

    def _to_provider_payload(self, request: CopilotPrompt) -> Dict[str, Any]:
        """
        내부 CopilotRequest를 Anthropic Messages API 페이로드로 변환합니다.
        """
        messages = self._build_messages(request)

        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "stream": True,
            "messages": messages,
        }

        if request.system_instructions:
            payload["system"] = request.system_instructions

        if self.enable_thinking:
            # Opus 4.8/4.7은 adaptive만 허용됩니다(budget_tokens/온도 파라미터 사용 시 400).
            payload["thinking"] = {"type": "adaptive"}

        return payload

    def _build_messages(self, request: CopilotPrompt) -> List[Dict[str, Any]]:
        """history(HOMessage들)와 현재 query를 Anthropic messages 배열로 변환합니다."""
        messages: List[Dict[str, Any]] = []

        for msg in request.history:
            role = self._map_role(msg.role)
            if role is None:
                continue  # 'system' 등은 top-level system으로 처리되므로 제외
            text = self._extract_text(msg)
            if text:
                messages.append({"role": role, "content": text})

        # 현재 사용자 입력을 마지막 user 턴으로 추가
        messages.append({"role": "user", "content": request.query})
        return messages

    @staticmethod
    def _map_role(role: str) -> Optional[str]:
        """내부 role('user'/'ai'/'system')을 Anthropic role로 매핑합니다."""
        if role == "user":
            return "user"
        if role == "ai":
            return "assistant"
        return None  # system 등은 메시지 배열에서 제외

    @staticmethod
    def _extract_text(msg: HOMessage) -> str:
        """HOMessage의 chunk들에서 텍스트 payload만 이어붙여 추출합니다."""
        parts: List[str] = []
        for chunk in msg.chunks:
            payload = chunk.payload
            if isinstance(payload, TextPayload):
                parts.append(payload.text)
        return "".join(parts)

    def _to_ho_chunk(self, raw_chunk: Any) -> HOChunk:
        """
        BaseProvider 계약 준수용 단일 변환 진입점.

        SSE 스트림은 이벤트:청크가 1:N이라 실제 변환은 _handle_event에서 수행하며,
        이 메서드는 단일 delta 이벤트를 받아 첫 HOChunk를 반환합니다(없으면 예외).
        """
        chunks = self._handle_event(raw_chunk, {})
        if not chunks:
            raise ValueError("변환 가능한 HOChunk가 없는 이벤트입니다.")
        return chunks[0]
