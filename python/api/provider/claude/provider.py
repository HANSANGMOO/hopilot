from typing import Any, Dict, List, Optional

from api.provider.base_provider import BaseProvider
from core.models import HOChunk, HopilotPayload

from .formatter import format_payload
from .optimizer import add_cache_breakpoints
from .parser import ClaudeParser
from .types import ANTHROPIC_VERSION, ClaudeConfig, ClaudePayload


class ClaudeProvider(BaseProvider, provider="claude"):
    """
    Anthropic Claude (Messages API) REST 공급자 구현체입니다.
    """

    base_url = "https://dev-internal-apigw-kr.hmg-corp.io/hchat-in/api/v3/claude/messages"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url, **kwargs)
        self.enable_cache: bool = bool(self.options.get("enable_cache", True))
        # 파서는 스트림 상태(_tool_buffers)를 가지므로 요청마다 새 인스턴스 생성
        self._parser = ClaudeParser()

    def build_url(self) -> str:
        return self.base_url

    def build_headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

    def _build_config(self) -> ClaudeConfig:
        config: ClaudeConfig = {
            "max_tokens": int(self.options.get("max_tokens", 16000)),
            "thinking_mode": self.options.get("thinking_mode", "adaptive"),
        }
        if effort := self.options.get("effort"):
            config["effort"] = effort
        if display := self.options.get("thinking_display"):
            config["thinking_display"] = display
        if budget := self.options.get("budget_tokens"):
            config["budget_tokens"] = int(budget)
        return config

    def format_payload(self, payload: HopilotPayload) -> ClaudePayload:
        return format_payload(payload, self.model, self._build_config())

    def optimize_payload(self, payload: ClaudePayload) -> ClaudePayload:
        if self.enable_cache:
            return add_cache_breakpoints(payload)
        return payload

    def parse_sse_event(self, event_line: str) -> List[HOChunk]:
        return self._parser.parse_sse_event(event_line)
