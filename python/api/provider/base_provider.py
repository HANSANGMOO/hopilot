from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

from core.models import CopilotRequest, HOChunk


class BaseProvider(ABC):
    """
    모든 LLM 공급자(Provider)가 상속해야 하는 추상 기반 클래스입니다.

    각 공급자(Gemini, Claude, OpenAI)의 REST API 차이를 이 계층에서 어댑터로 흡수하고,
    상위 계층(ApiManager, Engine)에는 통일된 인터페이스(CopilotRequest 입력 -> HOChunk 스트림 출력)만 노출합니다.
    """

    provider_name: str
    base_url: str

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None, **kwargs: Any) -> None:
        # 공급자 인증 및 기본 모델 설정을 주입받습니다.
        self.api_key = api_key
        self.model = model
        # 커스텀 base_url이 전달되면 우선 적용하고, 없으면 클래스의 기본 base_url을 사용합니다.
        self.base_url = base_url or self.__class__.base_url
        self.options: Dict[str, Any] = kwargs
        # TODO: HTTP 클라이언트 세션(aiohttp, httpx 등) 초기화 고려
        self._client: Optional[Any] = None

    @abstractmethod
    async def stream_generate(
        self,
        request: CopilotRequest,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[HOChunk, None]:
        """
        CopilotRequest를 받아 직접 REST API를 호출하여 LLM 응답을 스트리밍으로 생성합니다.

        공급자별 SSE raw 스트림을 표준 HOChunk 단위로 변환하여 배출(yield)해야 합니다.
        """
        raise NotImplementedError
        yield  # pragma: no cover  (AsyncGenerator 타입 명시용)

    @abstractmethod
    def _to_provider_payload(self, request: CopilotRequest) -> Any:
        """
        내부 표준 도메인 모델(CopilotRequest)을 해당 공급자의 REST API가 요구하는 페이로드(JSON) 포맷으로 변환합니다.
        """
        raise NotImplementedError

    @abstractmethod
    def _to_ho_chunk(self, raw_chunk: Any) -> HOChunk:
        """
        공급자 REST API 스트림에서 발생한 raw 청크를 내부 표준 DTO(HOChunk)로 변환합니다.
        """
        raise NotImplementedError
