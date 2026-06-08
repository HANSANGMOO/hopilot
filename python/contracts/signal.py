from typing_extensions import TypedDict

from pydantic import BaseModel, Field


class BaseSignal(BaseModel):
    """
    프론트엔드와 백엔드 간의 통신에서 가장 기본이 되는 최상위 시그널(이벤트) 객체입니다.
    JSON-RPC 2.0 규격을 따르며, params 속성을 자식 클래스에서 재정의(TypedDict 등)하여 사용합니다.
    """
    jsonrpc: str = "2.0"
    method: str = Field(default="", description="JSON-RPC 2.0 규격의 식별자(기존 type)")

    @classmethod
    def resolve_signal(cls, payload: dict) -> 'BaseSignal':
        """
        프론트엔드에서 수신된 원시 JSON 딕셔너리를
        자신을 상속받은 자식 클래스 명단을 뒤져 알맞은 객체로 역직렬화합니다.
        """
        signal_method = payload.get("method")
        if not signal_method:
            raise ValueError("페이로드에 'method' 필드가 없습니다.")

        # 모든 자식 클래스를 순회하며 이름 또는 method 기본값이 일치하는 클래스를 찾습니다.
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


from typing import Union

class BaseRequestSignal(BaseSignal):
    """프론트엔드에서 단일 응답을 기다리는 양방향 1:1 통신용 시그널입니다."""
    id: Union[str, int] = Field(..., description="JSON-RPC 요청을 매칭하기 위한 고유 식별자")


class BaseEventSignal(BaseSignal):
    """단방향으로 발송만 하고 끝나는 1:N 알림용 시그널 (Notification) 입니다. id 없음."""
    pass


class BaseStreamSignal(BaseSignal):
    """프론트엔드에서 스트리밍 응답(Progress Notification)을 기다리는 양방향 통신용 시그널입니다."""
    id: Union[str, int] = Field(..., description="스트림 응답을 매칭하기 위한 고유 식별자")


# ==========================================
# 기본 제공 시그널 정의 (TypedDict 사용)
# ==========================================

class CancelRequestParams(TypedDict):
    id: Union[str, int]

class CancelRequestSignal(BaseEventSignal):
    """
    프론트엔드에서 백엔드의 특정 태스크(id) 취소를 요청하는 시그널입니다.
    LSP의 `$/cancelRequest` 규격을 모방합니다.
    """
    method: str = "$/cancelRequest"
    params: CancelRequestParams
