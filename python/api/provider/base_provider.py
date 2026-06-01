from abc import ABC, abstractmethod
from typing import List, Any, Dict, AsyncGenerator, Optional

from core.models import HOMessage, HOChunk


class BaseProvider(ABC):
    """
    모든 LLM 공급자(Provider)가 상속해야 하는 추상 기반 클래스입니다.

    각 공급자(Gemini, Claude, OpenAI)의 SDK별 차이를 이 계층에서 흡수하고,
    상위 계층(ApiManager, Engine)에는 통일된 인터페이스(HOMessage 입력 -> HOChunk 스트림 출력)만 노출합니다.
    """

    provider_name: str

    def __init__(self, api_key: str, model: str, **kwargs: Any) -> None:
        # 공급자 인증 및 기본 모델 설정을 주입받습니다.
        self.api_key = api_key
        self.model = model
        self.options: Dict[str, Any] = kwargs
        # TODO: 각 공급자별 SDK 클라이언트 초기화
        self._client: Optional[Any] = None

    @abstractmethod
    async def stream_generate(
        self,
        messages: List[HOMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[HOChunk, None]:
        """
        대화 메시지를 받아 LLM 응답을 스트리밍으로 생성합니다.

        공급자별 raw 스트림을 표준 HOChunk 단위로 변환하여 배출(yield)해야 합니다.
        """
        raise NotImplementedError
        yield  # pragma: no cover  (AsyncGenerator 타입 명시용)

    @abstractmethod
    def _to_provider_messages(self, messages: List[HOMessage]) -> Any:
        """
        내부 표준 DTO(HOMessage)를 해당 공급자 SDK가 요구하는 메시지 포맷으로 변환합니다.
        """
        raise NotImplementedError

    @abstractmethod
    def _to_ho_chunk(self, raw_chunk: Any) -> HOChunk:
        """
        공급자 SDK가 배출한 raw 청크를 내부 표준 DTO(HOChunk)로 변환합니다.
        """
        raise NotImplementedError
