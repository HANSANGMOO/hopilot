from pydantic import BaseModel, Field, model_validator
from typing import Any, Optional

class BaseSignal(BaseModel):
    """
    프론트엔드(Electron)와 백엔드(Python) 간의 통신(웹소켓 등)에서 
    가장 기본이 되는 최상위 시그널(이벤트) 객체입니다.
    """
    type: str = Field(default="", description="시그널의 고유 이름 (라우팅 식별자)")

    @model_validator(mode='before')
    @classmethod
    def inject_type(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("type"):
            data["type"] = cls.__name__
        return data

    @classmethod
    def resolve_signal(cls, payload: dict) -> 'BaseSignal':
        """
        프론트엔드에서 수신된 원시 JSON 딕셔너리를 
        자신을 상속받은 자식 클래스 명단을 뒤져 알맞은 객체로 역직렬화합니다.
        """
        signal_type = payload.get("type")
        if not signal_type:
            raise ValueError("페이로드에 'type' 필드가 없습니다.")

        # 모든 자식 클래스(손자 포함)를 순회하며 이름이 일치하는 클래스를 찾습니다.
        def _find_subclass(parent_cls, target_name):
            for subclass in parent_cls.__subclasses__():
                if subclass.__name__ == target_name:
                    return subclass
                result = _find_subclass(subclass, target_name)
                if result:
                    return result
            return None

        target_cls = _find_subclass(cls, signal_type)
        if not target_cls:
            raise ValueError(f"'{signal_type}'을(를) 파싱할 수 있는 자식 클래스가 정의되지 않았습니다.")
            
        return target_cls(**payload)

class BaseRequestSignal(BaseSignal):
    """프론트엔드에서 응답을 기다리는 양방향 1:1 통신용 시그널입니다."""
    invoke_id: str = Field(default="", description="RequestBus 응답을 매칭하기 위한 고유 식별자")

class BaseEventSignal(BaseSignal):
    """단방향으로 발송만 하고 끝나는 1:N 알림용 시그널입니다. (invoke_id 없음)"""
    pass

class BaseStreamSignal(BaseSignal):
    """프론트엔드에서 스트리밍 응답(비동기 제너레이터)을 기다리는 양방향 통신용 시그널입니다."""
    invoke_id: str = Field(default="", description="StreamBus 응답을 매칭하기 위한 고유 식별자")


