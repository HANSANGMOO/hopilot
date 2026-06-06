from typing import List, Any, Dict, AsyncGenerator, Optional

from core.models import CopilotRequest, HOChunk
from utils import get_logger

from api.provider.base_provider import BaseProvider

logger = get_logger("GeminiProvider")


class GeminiProvider(BaseProvider):
    """
    Google Gemini REST API 공급자 구현체입니다.
    """

    provider_name = "gemini"
    base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro", base_url: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url, **kwargs)
        # TODO: HTTP 클라이언트 초기화

    async def stream_generate(
        self,
        request: CopilotRequest,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[HOChunk, None]:
        # TODO: HTTP Client를 통한 Gemini REST API (SSE) 호출 및 청크 변환 구현
        raise NotImplementedError
        yield  # pragma: no cover

    def _to_provider_payload(self, request: CopilotRequest) -> Any:
        # TODO: CopilotRequest -> Gemini REST API contents 페이로드 변환
        raise NotImplementedError

    def _to_ho_chunk(self, raw_chunk: Any) -> HOChunk:
        # TODO: Gemini SSE raw chunk -> HOChunk 변환
        raise NotImplementedError
