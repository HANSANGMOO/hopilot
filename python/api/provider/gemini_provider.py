from typing import List, Any, Dict, AsyncGenerator, Optional

from core.models import HOMessage, HOChunk
from utils import get_logger

from api.provider.base_provider import BaseProvider

logger = get_logger("GeminiProvider")


class GeminiProvider(BaseProvider):
    """
    Google Gemini 계열 모델 공급자 구현체입니다.
    """

    provider_name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro", **kwargs: Any) -> None:
        super().__init__(api_key=api_key, model=model, **kwargs)
        # TODO: google-genai SDK 클라이언트 초기화
        # from google import genai
        # self._client = genai.Client(api_key=api_key)

    async def stream_generate(
        self,
        messages: List[HOMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[HOChunk, None]:
        # TODO: Gemini streaming API 호출 및 청크 변환 구현
        raise NotImplementedError
        yield  # pragma: no cover

    def _to_provider_messages(self, messages: List[HOMessage]) -> Any:
        # TODO: HOMessage -> Gemini contents 포맷 변환
        raise NotImplementedError

    def _to_ho_chunk(self, raw_chunk: Any) -> HOChunk:
        # TODO: Gemini raw chunk -> HOChunk 변환
        raise NotImplementedError
