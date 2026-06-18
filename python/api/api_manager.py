from typing import Any, AsyncGenerator, Dict, List, Type, Optional
import httpx

from api.provider.base_provider import BaseProvider
from api.provider.gemini_provider import GeminiProvider
from api.provider.claude_provider import ClaudeProvider
from api.provider.openai_provider import OpenAIProvider
from contracts.api import HttpRequestSpec
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

    def create_provider(self, provider: str, api_key: str, model_id: str) -> BaseProvider:
        """
        이름에 해당하는 공급자 클래스를 찾아, api_key와 model_id로 인스턴스화하여 반환합니다.
        """
        provider_cls = BaseProvider.registry.get(provider)
        if not provider_cls:
            raise ValueError(f"'{provider}' 공급자 클래스가 지원되지 않습니다.")

        return provider_cls(api_key=api_key, model=model_id)

    async def generate_stream(
        self,
        payload: HopilotPayload,
        model_info: ModelInfo,
    ) -> AsyncGenerator[HOChunk, None]:
        """
        넘겨받은 model 정보를 이용해 공급자를 런타임에 인스턴스화하고, 
        Provider로부터 명세(Spec)를 받아 실제 HTTP 통신(SSE 스트리밍)을 수행합니다.
        """
        # 1. API 키 검증 및 Provider 인스턴스 생성
        if not model_info.provider or not model_info.api_key:
            raise ValueError("Provider 및 API Key가 ModelInfo에 필요합니다.")
            
        provider = self.create_provider(model_info.provider, model_info.api_key, model_info.id)

        # 2. Provider에게 "이 Payload를 보낼 건데 URL, Header, Body 좀 만들어줘" (순수 매핑)
        req_spec: HttpRequestSpec = provider.build_http_spec(payload)

        # 3. 내부 래핑 함수 호출 (Tenacity 등을 사용해 Timeout, 429 Retry 정책 적용 가능)
        async for line in self._safe_stream_request(req_spec):
            # 4. SSE 한 줄(line)을 읽을 때마다 다시 Provider에게 파싱 위임
            chunks = provider.parse_sse_event(line)
            
            # 5. 완성된 HOChunk 배출
            for chunk in chunks:
                yield chunk

    # [내부 재시도 래퍼 함수]
    # @tenacity.retry(stop=..., wait=...)
    async def _safe_stream_request(self, req_spec: HttpRequestSpec) -> AsyncGenerator[str, None]:
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
                    logger.error(f"HTTP Error {response.status_code}: {response.text}")
                    response.raise_for_status()
                async for line in response.aiter_lines():
                    yield line
        except httpx.HTTPStatusError as e:
            error_body = await e.response.aread()
            logger.error(f"HTTP Error {e.response.status_code}: {error_body.decode('utf-8', errors='ignore')}")
            raise
        except Exception as e:
            logger.error(f"Stream Request Failed: {str(e)}")
            raise
