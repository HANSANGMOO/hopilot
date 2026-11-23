from typing import Any, Dict, List, Optional

from api.provider.base_provider import BaseProvider
from core.models import HOChunk, HopilotPayload

from .formatter import format_payload
from .parser import parse_sse_event
from .types import GeminiGenerationConfig, GeminiPayload, GeminiThinkingConfig


class GeminiProvider(BaseProvider, provider="gemini"):
    """
    Google Gemini REST API 공급자 구현체입니다.
    """

    base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3-flash-preview",
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url, **kwargs)

    def build_url(self) -> str:
        """Gemini SSE 스트리밍을 위한 엔드포인트 URL 생성 (alt=sse 필수)"""
        base = self.base_url.rstrip("/")
        return f"{base}/{self.model}:streamGenerateContent?key={self.api_key}&alt=sse"

    def build_headers(self) -> Dict[str, str]:
        """Gemini API 인증 및 컨텐츠 타입 헤더 생성"""
        return {"Content-Type": "application/json"}

    def _build_config(self) -> GeminiGenerationConfig:
        return GeminiGenerationConfig(
            temperature=float(self.options.get("temperature", 1.0)),
            maxOutputTokens=int(self.options.get("max_tokens", 8192)),
            thinkingConfig=GeminiThinkingConfig(
                thinkingLevel=str(self.options.get("thinking_level", "high")),
                includeThoughts=bool(self.options.get("include_thoughts", True)),
            ),
        )

    def format_payload(self, payload: HopilotPayload) -> GeminiPayload:
        return format_payload(payload, self._build_config())

    def parse_sse_event(self, event_line: str) -> List[HOChunk]:
        return parse_sse_event(event_line)
