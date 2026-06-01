from typing import List, Any, Dict, AsyncGenerator, Optional

from core.models import HOMessage, HOChunk
from utils import get_logger

from api.provider.base_provider import BaseProvider

logger = get_logger("ApiManager")


class ApiManager:
    """
    여러 LLM 공급자(Provider)를 등록/관리하고, 요청을 적절한 공급자에게 라우팅하는 파사드(Facade)입니다.

    상위 계층(Engine)은 공급자별 SDK 차이를 알 필요 없이 ApiManager를 통해서만 LLM 생성을 요청합니다.
    """

    def __init__(self) -> None:
        # provider_name -> BaseProvider 인스턴스 레지스트리
        self._providers: Dict[str, BaseProvider] = {}
        self._default_provider: Optional[str] = None

    def register_provider(self, provider: BaseProvider, is_default: bool = False) -> None:
        """공급자 인스턴스를 이름 기준으로 레지스트리에 등록합니다."""
        if provider.provider_name in self._providers:
            raise ValueError(f"'{provider.provider_name}' 공급자가 이미 등록되어 있습니다.")

        self._providers[provider.provider_name] = provider
        if is_default or self._default_provider is None:
            self._default_provider = provider.provider_name

        logger.info(f"공급자 등록 완료: {provider.provider_name} (default={is_default})")

    def get_provider(self, name: Optional[str] = None) -> BaseProvider:
        """
        이름에 해당하는 공급자를 반환합니다. 이름이 없으면 기본 공급자를 반환합니다.
        """
        target = name or self._default_provider
        if target is None:
            raise ValueError("등록된 공급자가 없습니다.")
        if target not in self._providers:
            raise ValueError(f"'{target}' 공급자가 등록되지 않았습니다.")

        return self._providers[target]

    async def stream_generate(
        self,
        messages: List[HOMessage],
        provider_name: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[HOChunk, None]:
        """
        선택된 공급자에게 생성을 위임하고, 표준 HOChunk 스트림을 그대로 중계(proxy yield)합니다.
        """
        provider = self.get_provider(provider_name)
        # TODO: 재시도/타임아웃/에러 표준화 등 공통 정책을 이 계층에 추가
        async for chunk in provider.stream_generate(messages, tools=tools):
            yield chunk
