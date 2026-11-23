from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field


class BaseSignal(BaseModel):
    """
    프론트엔드와 백엔드 간의 통신에서 가장 기본이 되는 최상위 시그널(이벤트) 객체입니다.
    JSON-RPC 2.0 규격을 따르며, params 속성을 자식 클래스에서 재정의(TypedDict 등)하여 사용합니다.
    """
    jsonrpc: str = "2.0"
    method: str = Field(default="", description="JSON-RPC 2.0 규격의 식별자")

    @classmethod
    def resolve_signal(cls, payload: dict) -> 'BaseSignal':
        """
        수신된 원시 JSON 딕셔너리를 알맞은 시그널 객체로 역직렬화합니다.
        method가 없는 경우(JSON-RPC response)는 BaseOutboundRequestSignal로 파싱합니다.
        """
        signal_method = payload.get("method")

        # method 없는 JSON-RPC response → invoke()에 대한 프론트엔드 응답
        if not signal_method:
            return BaseOutboundRequestSignal(**payload)

        def _find_subclass(parent_cls, target_name):
            for subclass in parent_cls.__subclasses__():
                method_field = subclass.model_fields.get("method")
                if method_field and method_field.default == target_name:
                    return subclass
                result = _find_subclass(subclass, target_name)
                if result:
                    return result
            return None

        target_cls = _find_subclass(cls, signal_method)
        if not target_cls:
            raise ValueError(
                f"'{signal_method}'을(를) 파싱할 수 있는 "
                f"자식 클래스가 정의되지 않았습니다."
            )
        return target_cls(**payload)


class BaseInboundRequestSignal(BaseSignal):
    """프론트엔드 → 백엔드: 단일 응답을 기다리는 양방향 1:1 통신용 시그널입니다."""
    id: Union[str, int] = Field(..., description="JSON-RPC 요청을 매칭하기 위한 고유 식별자")


class BaseOutboundRequestSignal(BaseSignal):
    """백엔드 → 프론트엔드: signal_bus.invoke()로 전송하고 응답을 기다리는 시그널입니다.
    프론트엔드 응답 수신 시에도 이 타입으로 파싱됩니다."""
    id: Union[str, int] = Field(default="", description="signal_bus.invoke() 호출 시 자동 부여")
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class BaseEventSignal(BaseSignal):
    """단방향으로 발송만 하고 끝나는 1:N 알림용 시그널 (Notification) 입니다. id 없음."""
    pass


class BaseStreamSignal(BaseSignal):
    """프론트엔드에서 스트리밍 응답(Progress Notification)을 기다리는 양방향 통신용 시그널입니다."""
    id: Union[str, int] = Field(..., description="스트림 응답을 매칭하기 위한 고유 식별자")
