from typing import TypedDict

from contracts.signal import BaseStreamSignal


class SendUserRequestParams(TypedDict):
    session_id: str
    query: str

class SendUserRequestSignal(BaseStreamSignal):
    """사용자가 프론트엔드에서 입력한 요구사항(Prompt)을 백엔드 에이전트로 전송하는 외부 스트림 시작 시그널입니다."""
    method: str = "copilot/send"
    params: SendUserRequestParams

