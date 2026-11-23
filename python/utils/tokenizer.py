"""
tokenizer.py — Payload별 토큰 수 추정 유틸리티

정밀한 토크나이저(tiktoken 등) 없이 휴리스틱으로 대략적인 컨텍스트 길이를 추정한다.
LLM API 호출 전 히스토리 트리밍, 컨텍스트 윈도우 초과 여부 판단 용도.

[추정 근거]
  텍스트  : 문자 수 / CHARS_PER_TOKEN (영문 ~4자, 한글 ~2자 → 혼합 평균 3.5자)
  이미지  : base64라면 디코딩 바이트 수 기반, URL이라면 고정 기본값 사용
  도구 호출: tool_name + JSON(args)를 텍스트로 직렬화 후 동일 규칙 적용
  도구 출력: output 문자열에 동일 규칙 적용
  신호류  : StreamPayload, UsagePayload는 0 (LLM에게 전달되지 않음)
"""

import json
from typing import List

from core.models import (
    HOChunk,
    HOMessage,
    ImagePayload,
    StreamPayload,
    TextPayload,
    ThoughtPayload,
    ToolCallPayload,
    ToolOutputPayload,
    UsagePayload,
)
from utils.logger import get_logger

logger = get_logger("Tokenizer")

# ── 추정 상수 ──────────────────────────────────────────────────────────────────

# 텍스트
_CHARS_PER_TOKEN: float = 3.5       # 영문/한글 혼합 기준 (영문 ~4자, 한글 ~2자)

# 이미지 — base64
_IMG_BYTES_PER_TOKEN: int = 750     # 디코딩 후 바이트 기준 (Gemini ~258tok/img, Claude ~800tok/img 중간값)
_IMG_MIN_TOKENS: int = 85           # OpenAI vision 최소 단위 참고

# 이미지 — URL (크기 불명)
_IMG_URL_DEFAULT: int = 800

# 메시지 역할 오버헤드 (role 토큰 + 구분자 등)
_MSG_ROLE_OVERHEAD: int = 4


class Tokenizer:
    """
    Payload 타입별 추정 토큰 수를 반환하는 유틸리티 클래스.

    인스턴스로 사용하거나, 상수를 오버라이드해 커스텀 휴리스틱을 적용할 수 있다.

    Example:
        tok = Tokenizer()
        tokens = tok.estimate(text_payload)
        total  = tok.estimate_message(ho_message)
    """

    chars_per_token: float = _CHARS_PER_TOKEN
    img_bytes_per_token: int = _IMG_BYTES_PER_TOKEN
    img_min_tokens: int = _IMG_MIN_TOKENS
    img_url_default: int = _IMG_URL_DEFAULT
    msg_role_overhead: int = _MSG_ROLE_OVERHEAD

    # ── 공개 API ───────────────────────────────────────────────────────────────

    def estimate(self, payload) -> int:
        """단일 Payload의 추정 토큰 수를 반환한다."""
        if isinstance(payload, TextPayload):
            return self._from_text(payload.text)

        if isinstance(payload, ThoughtPayload):
            # thinking/reasoning 블록도 컨텍스트를 소비함
            return self._from_text(payload.thought)

        if isinstance(payload, ImagePayload):
            return self._from_image(payload.image_url)

        if isinstance(payload, ToolCallPayload):
            return self._from_tool_call(payload)

        if isinstance(payload, ToolOutputPayload):
            return self._from_text(payload.output)

        # StreamPayload, UsagePayload — LLM에게 전달되지 않는 신호/메타데이터
        if isinstance(payload, (StreamPayload, UsagePayload)):
            return 0

        # 알 수 없는 Payload 타입: 보수적으로 0 반환
        logger.warning(f"[Tokenizer] 알 수 없는 payload 타입: {type(payload).__name__}")
        return 0

    def estimate_chunk(self, chunk: HOChunk) -> int:
        """단일 HOChunk의 추정 토큰 수를 반환한다."""
        return self.estimate(chunk.payload)

    def estimate_chunks(self, chunks: List[HOChunk]) -> int:
        """HOChunk 리스트 전체의 추정 토큰 합계를 반환한다."""
        return sum(self.estimate_chunk(c) for c in chunks)

    def estimate_message(self, message: HOMessage) -> int:
        """
        HOMessage 한 턴의 추정 토큰 수를 반환한다.
        role 오버헤드(~4 토큰)를 포함한다.
        """
        return self.msg_role_overhead + self.estimate_chunks(message.chunks)

    def estimate_messages(self, messages: List[HOMessage]) -> int:
        """HOMessage 리스트 전체의 추정 토큰 합계를 반환한다."""
        return sum(self.estimate_message(m) for m in messages)

    # ── 내부 추정 로직 ─────────────────────────────────────────────────────────

    def _from_text(self, text: str) -> int:
        """텍스트 문자 수 기반 토큰 추정."""
        if not text:
            return 0
        return max(1, round(len(text) / self.chars_per_token))

    def _from_image(self, image_url: str) -> int:
        """
        이미지 토큰 추정.

        - data URI (base64): 인코딩된 문자 수로 실제 바이트를 역산한 뒤 bytes/token 적용
        - 일반 URL: 크기를 알 수 없으므로 고정 기본값 사용
        """
        if image_url.startswith("data:"):
            try:
                # "data:image/jpeg;base64,<b64data>"
                b64_part = image_url.split(",", 1)[1]
                # base64 인코딩 오버헤드(4/3배)를 역산하여 바이트 수 근사
                approx_bytes = len(b64_part) * 3 // 4
                tokens = approx_bytes // self.img_bytes_per_token
                return max(self.img_min_tokens, tokens)
            except Exception:
                logger.warning("[Tokenizer] base64 이미지 파싱 실패, 기본값 사용")
                return self.img_url_default

        return self.img_url_default

    def _from_tool_call(self, payload: ToolCallPayload) -> int:
        """
        도구 호출 토큰 추정.
        tool_name + JSON 직렬화된 args를 하나의 텍스트로 취급한다.
        """
        try:
            serialized = payload.tool_name + json.dumps(
                payload.tool_args, ensure_ascii=False, separators=(",", ":")
            )
        except Exception:
            serialized = payload.tool_name
        return self._from_text(serialized)
