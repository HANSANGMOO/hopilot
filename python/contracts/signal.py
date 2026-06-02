from pydantic import BaseModel, Field, model_validator
from typing import Any

class BaseSignal(BaseModel):
    """
    프론트엔드(Electron)와 백엔드(Python) 간의 통신(웹소켓 등)에서 
    가장 기본이 되는 최상위 시그널(이벤트) 객체입니다.
    
    모든 하위 시그널은 이 객체를 상속받으며, 
    자식 클래스의 이름이 자동으로 `type` 필드에 주입됩니다.
    """
    type: str = Field(default="", description="시그널의 고유 이름 (라우팅 식별자)")

    @model_validator(mode='before')
    @classmethod
    def inject_type(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("type"):
            data["type"] = cls.__name__
        return data
