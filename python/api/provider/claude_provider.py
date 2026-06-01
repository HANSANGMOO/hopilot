from typing import List, Any, Dict, AsyncGenerator, Optional

from core.models import HOMessage, HOChunk
from utils import get_logger

from api.provider.base_provider import BaseProvider

logger = get_logger("ClaudeProvider")


class ClaudeProvider(BaseProvider):
    """
    Anthropic Claude 계열 모델 공급자 구현체입니다.
    """

    provider_name = "claude"

    def __init__(self, api_key: str, model: str = "claude-opus-4-8", **kwargs: Any) -> None:
        super().__init__(api_key=api_key, model=model, **kwargs)
        # TODO: anthropic SDK 클라이언트 초기화
        # from anthropic import AsyncAnthropic
        # self._client = AsyncAnthropic(api_key=api_key)

    async def stream_generate(
        self,
        messages: List[HOMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[HOChunk, None]:
        # TODO: Claude Messages streaming API 호출 및 청크 변환 구현
        raise NotImplementedError
        yield  # pragma: no cover

    def _to_provider_messages(self, messages: List[HOMessage]) -> Any:
        # TODO: HOMessage -> Anthropic messages 포맷 변환
        raise NotImplementedError

    def _to_ho_chunk(self, raw_chunk: Any) -> HOChunk:
        # TODO: Claude raw event -> HOChunk 변환
        raise NotImplementedError
