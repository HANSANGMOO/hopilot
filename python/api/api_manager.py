from typing import Any, AsyncGenerator, Dict, List, Type, Optional
import httpx

from api.provider.base_provider import BaseProvider
from api.provider.gemini import GeminiProvider
from api.provider.claude import ClaudeProvider
from api.provider.openai import OpenAIProvider
from api.provider.local import LocalProvider
from api.provider.exaone import ExaoneProvider
from contracts.api import HttpRequestSpec
from core.errors import (
    LlmError,
    LlmAuthError,
    LlmRateLimitError,
    LlmServerError,
    LlmBadRequestError,
    LlmTimeoutError,
    LlmConnectionError,
)
from core.models import HopilotPayload, HOChunk, ModelInfo
from utils import get_logger

logger = get_logger("ApiManager")


class ApiManager:
    """
    여러 LLM 공급자(Provider) 클래스를 관리하고,
    요청 시점에 ModelInfo(API 키 포함)를 받아 인스턴스를 동적으로 생성하여 라우팅하는 팩토리 겸 퍼사드(Facade)입니다.
    """

    def __init__(self) -> None:
        # 전역 HTTP 커넥션 풀 (앱 기동 시 초기화)
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """
        앱 구동 시 호출되어 고성능 비동기 HTTP 커넥션 풀(httpx.AsyncClient)과
        글로벌 Timeout, Limits 설정을 초기화합니다.
        """
        if self._client is None:
            limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
            timeout = httpx.Timeout(60.0, connect=10.0, read=300.0) # 긴 SSE 스트림을 위해 read timeout을 길게
            self._client = httpx.AsyncClient(limits=limits, timeout=timeout)
            logger.info("ApiManager HTTP Client initialized.")

    async def shutdown(self) -> None:
        """
        앱 종료 시 호출되어 열려있는 HTTP 커넥션 풀을 안전하게 닫습니다(Graceful Shutdown).
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("ApiManager HTTP Client shutdown.")

    def get_supported_providers(self) -> List[str]:
        """퍼사드 패턴: 현재 레지스트리에 자동 등록된 모든 Provider 이름(ID) 목록을 반환합니다."""
        return list(BaseProvider.registry.keys())

    def create_provider(self, provider: str, api_key: str, model_id: str, options: Dict = None) -> BaseProvider:
        """
        이름에 해당하는 공급자 클래스를 찾아, api_key와 model_id로 인스턴스화하여 반환합니다.
        options는 llm_config.yaml에서 로드된 provider 전용 설정값을 **kwargs로 전달합니다.
        """
        provider_cls = BaseProvider.registry.get(provider)
        if not provider_cls:
            raise ValueError(f"'{provider}' 공급자 클래스가 지원되지 않습니다.")

        return provider_cls(api_key=api_key, model=model_id, **(options or {}))

    async def generate_stream(
        self,
        payload: HopilotPayload,
        model_info: ModelInfo,
    ) -> AsyncGenerator[HOChunk, None]:
        """
        넘겨받은 model 정보를 이용해 공급자를 런타임에 인스턴스화하고, 
        Provider로부터 명세(Spec)를 받아 실제 HTTP 통신(SSE 스트리밍)을 수행합니다.
        """
        # 1. Provider 인스턴스 생성
        provider = self.create_provider(model_info.provider, model_info.api_key, model_info.id, model_info.options)

        # 2. Provider에게 "이 Payload를 보낼 건데 URL, Header, Body 좀 만들어줘" (순수 매핑)
        req_spec: HttpRequestSpec = provider.build_http_spec(payload)

        # 3. 내부 래핑 함수 호출 (Tenacity 등을 사용해 Timeout, 429 Retry 정책 적용 가능)
        async for line in self._request_stream(req_spec):
            # 4. SSE 한 줄(line)을 읽을 때마다 다시 Provider에게 파싱 위임
            chunks = provider.parse_sse_event(line)
            
            # 5. 완성된 HOChunk 배출
            for chunk in chunks:
                yield chunk

    async def _request_stream(self, req_spec: HttpRequestSpec) -> AsyncGenerator[str, None]:
        """httpx.AsyncClient.stream을 통해 스트림으로 연결하고 SSE 라인을 반복적으로 yield합니다."""
        if self._client is None:
            raise RuntimeError("ApiManager가 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")

        try:
            async with self._client.stream(
                method=req_spec.method,
                url=req_spec.url,
                headers=req_spec.headers,
                json=req_spec.json_body,
            ) as response:
                if response.status_code >= 400:
                    await response.aread()
                    self._raise_for_status(response.status_code, response.text)
                async for line in response.aiter_lines():
                    yield line

        except LlmError:
            raise

        except httpx.TimeoutException as e:
            logger.error(f"LLM 응답 시간 초과: {e}")
            raise LlmTimeoutError("LLM 응답 대기 시간이 초과됐습니다.") from e

        except httpx.RequestError as e:
            logger.error(f"네트워크 연결 실패: {e}")
            raise LlmConnectionError("LLM 공급자에 대한 네트워크 연결에 실패했습니다.") from e

    def _raise_for_status(self, code: int, body: str) -> None:
        """HTTP 상태 코드를 LlmError 계열로 변환하여 던집니다."""
        logger.error(f"HTTP {code}: {body}")
        match code:
            case 401:
                raise LlmAuthError("API 키가 올바르지 않습니다.", status_code=code)
            case 429:
                raise LlmRateLimitError("요청 한도를 초과했습니다.", status_code=code)
            case c if c >= 500:
                raise LlmServerError("LLM 서버 오류가 발생했습니다.", status_code=code)
            case _:
                raise LlmBadRequestError("잘못된 요청입니다.", status_code=code)
