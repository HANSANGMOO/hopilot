from pydantic import BaseModel, Field

class HOSignal(BaseModel):
    """
    프론트엔드(Electron)와 백엔드(Python) 간의 통신(웹소켓 등)에서 
    가장 기본이 되는 최상위 시그널(이벤트) 객체입니다.
    
    모든 하위 시그널은 이 객체를 상속받아 고유한 `type` 값을 가져야 하며, 
    이 `type` 값이 곧 PyQt의 시그널 이름과 동일한 역할을 합니다.
    """
    type: str = Field(..., description="시그널의 고유 이름 (라우팅 식별자)")
