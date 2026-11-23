from typing import Any, Dict, List, Optional

from api.provider.base_provider import BaseProvider
from core.models import HOChunk, HopilotPayload

from .formatter import format_payload
from .parser import ExaoneParser
from .types import ExaoneConfig, ExaonePayload


class ExaoneProvider(BaseProvider, provider="exaone"):
    """
    LG AI연구원 EXAONE API Platform 공급자 구현체입니다.
    OpenAI Chat Completions 호환 인터페이스(/v1/chat/completions)로 통신합니다.
    """

    base_url = "https://api.exaone.ai/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str = "k-exaone_v2.5",
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url, **kwargs)
        self._parser = ExaoneParser()

    def build_url(self) -> str:
        return self.base_url

    def build_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_config(self) -> ExaoneConfig:
        config: ExaoneConfig = {
            "max_tokens": int(self.options.get("max_tokens", 16384)),
        }
        if (temperature := self.options.get("temperature")) is not None:
            config["temperature"] = float(temperature)
        if (top_p := self.options.get("top_p")) is not None:
            config["top_p"] = float(top_p)
        if (reasoning_effort := self.options.get("reasoning_effort")) is not None:
            config["reasoning_effort"] = str(reasoning_effort)  # type: ignore[typeddict-item]
        return config

    def format_payload(self, payload: HopilotPayload) -> ExaonePayload:
        return format_payload(payload, self.model, self._build_config())

    def parse_sse_event(self, event_line: str) -> List[HOChunk]:
        return self._parser.parse_sse_event(event_line)
