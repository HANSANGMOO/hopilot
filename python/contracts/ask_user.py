from typing import List, Optional
from typing_extensions import TypedDict

from core.bus.signal import BaseOutboundRequestSignal


class AskUserParams(TypedDict):
    question: str
    choices: Optional[List[str]]   # 다지선다 선택지. None이면 주관식 전용
    placeholder: Optional[str]     # 주관식 입력창 placeholder


class AskUserSignal(BaseOutboundRequestSignal):
    """백엔드 → 프론트엔드: LLM 도구 실행 중 사용자 입력을 요청하는 시그널입니다."""
    method: str = "tool/ask_user"
    params: AskUserParams
