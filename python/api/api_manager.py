from typing import Any, AsyncGenerator, Dict, List, Type

from api.provider.base_provider import BaseProvider
from api.provider.claude_provider import ClaudeProvider
from api.provider.gemini_provider import GeminiProvider
from api.provider.openai_provider import OpenAIProvider
from core.models import CopilotPrompt, HOChunk, ModelInfo
from utils import get_logger

logger = get_logger("ApiManager")


class ApiManager:
    """
    여러 LLM 공급자(Provider) 클래스를 관리하고,
    요청 시점에 ModelInfo(API 키 포함)를 받아 인스턴스를 동적으로 생성하여 라우팅하는 팩토리 겸 파사드입니다.
    """

    def __init__(self) -> None:
        # provider_name -> BaseProvider 구현 클래스(Type) 레지스트리
        self._provider_classes: Dict[str, Type[BaseProvider]] = {
            "claude": ClaudeProvider,
            "gemini": GeminiProvider,
            "openai": OpenAIProvider,
        }

    def register_provider_class(self, provider_name: str, provider_cls: Type[BaseProvider]) -> None:
        """새로운 공급자 클래스를 이름 기준으로 레지스트리에 등록합니다."""
        if provider_name in self._provider_classes:
            logger.warning(f"'{provider_name}' 공급자가 이미 등록되어 있습니다. 덮어씁니다.")

        self._provider_classes[provider_name] = provider_cls
        logger.info(f"공급자 클래스 등록 완료: {provider_name}")

    def create_provider(self, provider_name: str, api_key: str, model_id: str) -> BaseProvider:
        """
        이름에 해당하는 공급자 클래스를 찾아, api_key와 model_id로 인스턴스화하여 반환합니다.
        """
        provider_cls = self._provider_classes.get(provider_name)
        if not provider_cls:
            raise ValueError(f"'{provider_name}' 공급자 클래스가 등록되지 않았습니다.")

        return provider_cls(api_key=api_key, model=model_id)

    async def stream_generate(
        self,
        request: CopilotPrompt,
        model_info: ModelInfo,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[HOChunk, None]:
        """
        넘겨받은 model 정보를 이용해 공급자를 런타임에 인스턴스화하고,
        표준 HOChunk 스트림을 그대로 중계(proxy yield)합니다.
        """
        provider_name = model_info.provider
        api_key = model_info.api_key or ""
        model_id = model_info.id

        if not api_key:
            logger.warning(f"API 키가 없습니다. provider={provider_name}")

        # 1. 동적으로 Provider 인스턴스 생성
        provider_instance = self.create_provider(provider_name, api_key, model_id)

        # 2. 스트림 생성 및 위임
        # TODO: 재시도/타임아웃/에러 표준화 등 공통 정책을 이 계층에 추가
        async for chunk in provider_instance.stream_generate(request, tools=tools):
            yield chunk
