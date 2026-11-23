from typing import Optional


# ==========================================
# Base
# ==========================================

class HopilotError(Exception):
    """Hopilot 백엔드 전체의 에러 베이스."""
    pass


# ==========================================
# LLM API 에러 (ApiManager 레이어에서 발생)
# ==========================================

class LlmError(HopilotError):
    """모든 LLM 요청 에러의 베이스."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class LlmAuthError(LlmError):
    """401 — API 키가 없거나 올바르지 않습니다."""


class LlmRateLimitError(LlmError):
    """429 — 요청 한도를 초과했습니다."""


class LlmServerError(LlmError):
    """5xx — LLM 공급자 서버 오류."""


class LlmTimeoutError(LlmError):
    """LLM 응답 대기 시간이 초과됐습니다."""


class LlmConnectionError(LlmError):
    """LLM 공급자에 대한 네트워크 연결에 실패했습니다."""


class LlmBadRequestError(LlmError):
    """400 — 요청 형식이 잘못됐습니다 (payload 구성 오류 등)."""


# ==========================================
# Payload 에러 (PayloadEngine 레이어에서 발생)
# ==========================================

class PayloadError(HopilotError):
    """payload 빌드 중 발생하는 에러의 베이스."""
    pass


class AttachmentLoadError(PayloadError):
    """첨부 파일을 불러오지 못했습니다 (파일 없음, 권한 없음 등)."""


class AttachmentNotFoundError(PayloadError):
    """요청한 attachment ID가 스토어에 존재하지 않습니다."""


class ImageLoadError(AttachmentLoadError):
    """이미지 파일을 불러오지 못했습니다."""


class DocumentLoadError(AttachmentLoadError):
    """문서 파일을 불러오지 못했습니다."""


# ==========================================
# 설정 에러 (서비스 레이어에서 발생)
# ==========================================

class ConfigError(HopilotError):
    """설정 또는 초기화 관련 에러의 베이스."""
    pass


class ModelNotFoundError(ConfigError):
    """요청한 모델 ID가 llm_config.yaml에 존재하지 않습니다."""


class ApiKeyMissingError(ConfigError):
    """모델에 필요한 API 키가 설정되지 않았습니다."""


class McpConfigError(ConfigError):
    """mcp.json 파싱 또는 플레이스홀더 치환 중 오류가 발생했습니다."""


# ==========================================
# 세션 / 데이터 에러 (DB 레이어에서 발생)
# ==========================================

class SessionError(HopilotError):
    """세션 관련 에러의 베이스."""
    pass


class SessionNotFoundError(SessionError):
    """요청한 session_id가 DB에 존재하지 않습니다."""


class MessageNotFoundError(SessionError):
    """요청한 message_id가 세션에 존재하지 않습니다."""
