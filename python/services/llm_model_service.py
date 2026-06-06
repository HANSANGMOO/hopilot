from typing import Any, Dict, List

from utils import get_logger

logger = get_logger("LlmModelService")

class LlmModelService:
    """
    LLM API 설정 및 모델 메타데이터를 관리하고 프론트엔드에 제공하는 비즈니스 서비스 계층입니다.
    """

    def __init__(self, config_path: str = "llm_config.yaml"):
        self.config_path = config_path

    def load_models(self) -> List[Dict[str, Any]]:
        """
        llm_config.yaml 파일을 파싱하고, 보관된 API 키의 존재 여부를 결합하여
        사용 가능한 LLM 모델 목록을 반환합니다.
        """
        raise NotImplementedError("load_models is not implemented yet")

    def get_default_model(self) -> Dict[str, Any]:
        """기본(Default)으로 설정된 LLM 모델 정보를 반환합니다."""
        raise NotImplementedError("get_default_model is not implemented yet")

    def validate_model(self, model_id: str) -> bool:
        """요청받은 모델 ID가 현재 설정에서 지원 가능한지 검증합니다."""
        raise NotImplementedError("validate_model is not implemented yet")

    # ==========================================
    # 커스텀 모델 CRUD 관리
    # ==========================================
    def add_model(self, model_data: Dict[str, Any]) -> None:
        """새로운 (커스텀) 모델을 설정에 추가합니다."""
        raise NotImplementedError("add_model is not implemented yet")

    def update_model(self, model_id: str, model_data: Dict[str, Any]) -> None:
        """기존 모델의 정보(이름 등)를 수정합니다."""
        raise NotImplementedError("update_model is not implemented yet")

    def delete_model(self, model_id: str) -> None:
        """특정 모델을 목록에서 삭제합니다."""
        raise NotImplementedError("delete_model is not implemented yet")

    # ==========================================
    # API Key CRUD 관리 및 검증
    # ==========================================
    def add_api_key(self, provider: str, api_key: str) -> None:
        """보안 저장소에 특정 Provider의 API 키를 암호화하여 추가/업데이트합니다."""
        raise NotImplementedError("add_api_key is not implemented yet")

    def get_api_key(self, provider: str) -> str:
        """보안 저장소에서 특정 Provider의 API 키를 조회합니다."""
        raise NotImplementedError("get_api_key is not implemented yet")

    def delete_api_key(self, provider: str) -> None:
        """보안 저장소에서 특정 Provider의 API 키를 삭제합니다."""
        raise NotImplementedError("delete_api_key is not implemented yet")

    def validate_api_key(self, provider: str, api_key: str) -> bool:
        """
        ApiManager(또는 Provider)에 위임하여 해당 API 키가 실제 통신 가능한 유효한 키인지 검증합니다.
        """
        raise NotImplementedError("validate_api_key is not implemented yet")
