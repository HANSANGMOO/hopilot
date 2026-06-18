from typing import Any, Optional, Dict, List

from api.provider.base_provider import BaseProvider
from core.models import HOChunk, HopilotPayload
from utils import get_logger

logger = get_logger("OpenAIProvider")


class OpenAIProvider(BaseProvider, provider="openai"):
    """
    OpenAI GPT REST API 공급자 구현체입니다.
    """

    base_url = "https://api.openai.com/v1/chat/completions"

    def __init__(
        self, api_key: str, model: str = "gpt-4o", base_url: Optional[str] = None, **kwargs: Any
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url, **kwargs)
        # TODO: HTTP 클라이언트 초기화

    def format_payload(self, payload: HopilotPayload) -> Any:
        # TODO: HopilotPayload -> OpenAI messages REST API 페이로드 변환
        raise NotImplementedError

    def _format_chunk(self, chunk: HOChunk) -> Any:
        # TODO: 단일 HOChunk를 OpenAI 특화 포맷으로 변환
        raise NotImplementedError

    def parse_sse_event(self, event_line: str) -> List[HOChunk]:
        # TODO: OpenAI SSE 이벤트 라인 파싱
        raise NotImplementedError

    def _parse_chunk(self, data: Dict[str, Any]) -> List[HOChunk]:
        # TODO: OpenAI JSON 딕셔너리 -> List[HOChunk] 변환
        raise NotImplementedError
