from typing import Any, Dict, List, Optional

from api.provider.base_provider import BaseProvider
from core.models import HOChunk, HopilotPayload

from .formatter import format_payload
from .parser import OpenAIParser
from .types import OpenAIConfiguration, OpenAIPayload


class OpenAIProvider(BaseProvider, provider="openai"):
    """
    OpenAI Responses API 공급자 구현체입니다.
    사내 Enterprise Gateway의 /openai/responses 엔드포인트로 통신합니다.

    [ChatCompletions API와의 주요 차이]
    - 요청 body: messages → input (flat 배열, tool_call/tool_output이 content 밖 최상위 item)
    - 응답 body: choices → output
    - Reasoning: thinking 블록 대신 reasoning summary (response.reasoning_summary_text.delta)
    """

    base_url = "https://dev-internal-apigw-kr.hmg-corp.io/hchat-in/api/v3/openai/responses"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5.4",
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url, **kwargs)
        self.max_output_tokens: int = int(self.options.get("max_output_tokens", 128000))
        self.reasoning_effort: str = str(self.options.get("reasoning_effort", "high"))
        self.truncation: Optional[str] = self.options.get("truncation")
        self._parser = OpenAIParser()

    def build_url(self) -> str:
        return self.base_url

    def build_headers(self) -> Dict[str, str]:
        return {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def format_payload(self, payload: HopilotPayload) -> OpenAIPayload:
        config = OpenAIConfiguration(
            model=self.model,
            max_output_tokens=self.max_output_tokens,
            reasoning={"effort": self.reasoning_effort, "summary": "auto"},
        )
        if self.truncation:
            config["truncation"] = self.truncation
        if text := self.options.get("text"):
            config["text"] = text
        return format_payload(payload, config)

    def parse_sse_event(self, event_line: str) -> List[HOChunk]:
        return self._parser.parse_sse_event(event_line)
