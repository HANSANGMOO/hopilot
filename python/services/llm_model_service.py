import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import dotenv_values, set_key, unset_key

from api.api_manager import ApiManager
from config import PROJECT_ROOT, USER_API_KEYS_FILE_PATH, USER_ENV_DIR
from core.errors import ApiKeyMissingError, ModelNotFoundError
from core.models import ModelInfo
from utils import get_logger

logger = get_logger("LlmModelService")

class LlmModelService:
    """
    LLM API 설정 및 모델 메타데이터를 관리하고 프론트엔드에 제공하는 비즈니스 서비스 계층입니다.
    """

    def __init__(self, api_manager: ApiManager, config_filename: str = "llm_config.yaml"):
        self.api_manager = api_manager
        self.config_path = PROJECT_ROOT / "python" / config_filename
        if not USER_API_KEYS_FILE_PATH.exists():
            USER_API_KEYS_FILE_PATH.touch(mode=0o600, exist_ok=True)

    def _get_env_key(self, provider: str) -> str:
        """Provider 이름을 바탕으로 환경변수 키 이름(ex: GEMINI_API_KEY)을 생성합니다."""
        return f"{provider.upper()}_API_KEY"

    def _read_api_keys(self) -> Dict[str, str]:
        """로컬 .env 파일에서 API 키를 읽어옵니다."""
        try:
            # dotenv_values returns a dict of env vars
            env_dict = dotenv_values(USER_API_KEYS_FILE_PATH)
            # filter None values and return
            return {k: v for k, v in env_dict.items() if v is not None}
        except Exception as e:
            logger.error(f"Failed to read API keys: {e}")
            return {}

    def load_models(self) -> List[Dict[str, Any]]:
        """
        llm_config.yaml 파일을 파싱하고, 보관된 API 키의 존재 여부를 결합하여
        사용 가능한 LLM 모델 목록을 반환합니다.
        """
        if not self.config_path.exists():
            logger.error(f"Config file not found: {self.config_path}")
            return []

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
            
            models = config_data.get("models", [])
            api_keys = self._read_api_keys()
            supported_providers = self.api_manager.get_supported_providers()

            valid_models = []
            # API 키 유무에 따라 is_available 플래그 추가 및 검증
            for model in models:
                provider = model.get("provider", "")
                if provider not in supported_providers:
                    logger.warning(f"Unsupported provider '{provider}'. Skipping model: {model.get('id')}")
                    continue
                
                env_key = self._get_env_key(provider)
                model["is_available"] = bool(api_keys.get(env_key))
                valid_models.append(model)

            return valid_models
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            return []

    def get_default_model(self) -> Dict[str, Any]:
        """기본(Default)으로 설정된 LLM 모델 정보를 반환합니다."""
        models = self.load_models()
        for model in models:
            if model.get("is_default"):
                return model
        # default가 명시되지 않은 경우 첫 번째 모델 반환
        return models[0] if models else {}

    def resolve(self, model_id: Optional[str] = None) -> ModelInfo:
        """model_id로 모델을 찾고, 없거나 None이면 기본 모델로 대체하여 ModelInfo를 반환합니다."""
        model = None
        if model_id:
            models = self.load_models()
            model = next((m for m in models if m.get("id") == model_id), None)
            if not model:
                logger.warning(f"Model ID '{model_id}' not found. Falling back to default.")

        if not model:
            model = self.get_default_model()

        if not model:
            raise ModelNotFoundError("사용 가능한 모델이 없습니다. llm_config.yaml을 확인해주세요.")

        provider = model.get("provider", "")
        api_key = self.get_api_key(provider)
        if not api_key:
            raise ApiKeyMissingError(f"{provider} API 키가 설정되지 않았습니다.")

        return ModelInfo(
            id=model.get("id", ""),
            provider=provider,
            display_name=model.get("display_name", ""),
            api_key=api_key,
            options=model.get("options") or {},
        )

    def validate_model(self, model_id: str) -> bool:
        """요청받은 모델 ID가 현재 설정에서 지원 가능한지 검증합니다."""
        models = self.load_models()
        return any(model.get("id") == model_id for model in models)

    # ==========================================
    # 커스텀 모델 CRUD 관리
    # ==========================================
    def add_model(self, model_data: Dict[str, Any]) -> None:
        """새로운 (커스텀) 모델을 설정에 추가합니다."""
        raise NotImplementedError("Custom models not fully supported yet.")

    def update_model(self, model_id: str, model_data: Dict[str, Any]) -> None:
        """기존 모델의 정보(이름 등)를 수정합니다."""
        raise NotImplementedError("Custom models not fully supported yet.")

    def delete_model(self, model_id: str) -> None:
        """특정 모델을 목록에서 삭제합니다."""
        raise NotImplementedError("Custom models not fully supported yet.")

    # ==========================================
    # API Key CRUD 관리 및 검증
    # ==========================================
    def add_api_key(self, provider: str, api_key: str) -> None:
        """보안 저장소에 특정 Provider의 API 키를 추가/업데이트합니다."""
        env_key = self._get_env_key(provider)
        try:
            set_key(
                dotenv_path=USER_API_KEYS_FILE_PATH,
                key_to_set=env_key,
                value_to_set=api_key,
                quote_mode="always"
            )
            logger.info(f"API key updated for provider: {provider}")
        except Exception as e:
            logger.error(f"Failed to add API key for {provider}: {e}")

    def get_api_key(self, provider: str) -> str:
        """보안 저장소에서 특정 Provider의 API 키를 조회합니다."""
        keys = self._read_api_keys()
        env_key = self._get_env_key(provider)
        return keys.get(env_key, "")

    def delete_api_key(self, provider: str) -> None:
        """보안 저장소에서 특정 Provider의 API 키를 삭제합니다."""
        env_key = self._get_env_key(provider)
        try:
            unset_key(
                dotenv_path=USER_API_KEYS_FILE_PATH,
                key_to_unset=env_key,
                quote_mode="always"
            )
            logger.info(f"API key deleted for provider: {provider}")
        except Exception as e:
            logger.error(f"Failed to delete API key for {provider}: {e}")

    def validate_api_key(self, provider: str, api_key: str) -> bool:
        """
        ApiManager(또는 Provider)에 위임하여 해당 API 키가 실제 통신 가능한 유효한 키인지 검증합니다.
        """
        raise NotImplementedError("validate_api_key is not implemented yet")
