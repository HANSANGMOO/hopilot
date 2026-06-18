from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, List

from contracts.api import HttpRequestSpec
from core.models import HOChunk, HopilotPayload


class BaseProvider(ABC):
    """
    모든 LLM 공급자(Provider)가 상속해야 하는 추상 기반 클래스입니다.

    각 공급자(Gemini, Claude, OpenAI)의 REST API 차이를 이 계층에서 어댑터로 흡수하고,
    상위 계층(ApiManager, Engine)에는 통일된 인터페이스(CopilotRequest 입력 -> HOChunk 스트림 출력)만 노출합니다.
    """

    registry: Dict[str, "Type[BaseProvider]"] = {}

    def __init_subclass__(cls, provider: str = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if provider:
            cls.provider = provider
            BaseProvider.registry[provider] = cls

    provider: str
    base_url: str

    def __init__(
        self, api_key: str, model: str, base_url: Optional[str] = None, **kwargs: Any
    ) -> None:
        self.api_key = api_key
        self.model = model
        # 커스텀 base_url이 전달되면 우선 적용하고, 없으면 클래스의 기본 base_url을 사용합니다.
        self.base_url = base_url or self.__class__.base_url
        self.options: Dict[str, Any] = kwargs

    def build_http_spec(self, payload: HopilotPayload) -> HttpRequestSpec:
        """
        템플릿 메서드: URL, Header, Body를 조립하여
        ApiManager가 통신에 즉시 사용할 수 있는 명세(HttpRequestSpec)를 반환합니다.
        """
        return HttpRequestSpec(
            method="POST",
            url=self.build_url(),
            headers=self.build_headers(),
            json_body=self.format_payload(payload),
        )

    @abstractmethod
    def build_url(self) -> str:
        """각 Provider의 API 엔드포인트 URL을 반환합니다."""
        pass

    @abstractmethod
    def build_headers(self) -> Dict[str, str]:
        """인증 키 등 HTTP Header 딕셔너리를 반환합니다."""
        pass

    @abstractmethod
    def format_payload(self, payload: HopilotPayload) -> Any:
        """HopilotPayload를 Provider가 요구하는 JSON Payload(Body) 포맷으로 변환합니다."""
        pass

    @abstractmethod
    def parse_sse_event(self, event_line: str) -> List[HOChunk]:
        """
        단일 SSE 문자열 라인을 파싱하여 표준 HOChunk 리스트로 변환합니다.
        (파싱 결과 의미 있는 데이터가 없는 라인일 경우 빈 리스트 반환)
        """
        pass