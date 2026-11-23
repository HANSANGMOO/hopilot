from typing import Any, Dict, List, Optional

from api.provider.base_provider import BaseProvider
from core.models import HOChunk, HopilotPayload

from .formatter import format_payload
from .parser import LocalParser
from .types import LocalConfig, LocalPayload


class LocalProvider(BaseProvider, provider="local"):
    """
    사내 local LLM 게이트웨이(OpenAI Chat Completions 호환) 공급자 구현체입니다.
    qwen/qwen3.6, google/gemma4-26B 모델을 model 필드로만 구분하여 공유합니다.
    """

    base_url = "https://h-llm-gw.auto-hmg.io/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str = "qwen/qwen3.6",
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url, **kwargs)
        # 파서는 스트림 상태(_tool_calls)를 가지므로 요청마다 새 인스턴스 생성
        self._parser = LocalParser()

    def build_url(self) -> str:
        return self.base_url

    def build_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_config(self) -> LocalConfig:
        return LocalConfig(max_tokens=int(self.options.get("max_tokens", 16000)))

    def format_payload(self, payload: HopilotPayload) -> LocalPayload:
        return format_payload(payload, self.model, self._build_config())

    def parse_sse_event(self, event_line: str) -> List[HOChunk]:
        return self._parser.parse_sse_event(event_line)
