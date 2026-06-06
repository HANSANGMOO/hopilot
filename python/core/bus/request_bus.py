import logging
import inspect
from typing import Callable, Dict, Type, TypeVar, Awaitable, Generic, Any

logger = logging.getLogger("RequestBus")
T = TypeVar('T')

class BaseRequestBus(Generic[T]):
    """1:1 양방향 요청(Invoke)과 응답(Handle)을 처리하는 버스"""
    def __init__(self, bus_name: str = "RequestBus"):
        self.bus_name = bus_name
        self._handlers: Dict[Type[T], Callable[[T], Awaitable[Any]]] = {}

    def handle(self, msg_type: Type[T], handler: Callable[[T], Awaitable[Any]]):
        """특정 요청 타입에 대해 결과값을 반환하는 1:1 비동기 핸들러를 등록합니다."""
        if msg_type in self._handlers:
            raise ValueError(f"'{msg_type.__name__}'에 대한 핸들러가 이미 존재합니다. RequestBus는 1:1 매칭만 지원합니다.")
        self._handlers[msg_type] = handler

    async def invoke(self, message: T) -> Any:
        """요청을 발생시키고 등록된 핸들러의 결과를 기다려 반환합니다."""
        msg_type = type(message)
        if msg_type not in self._handlers:
            raise ValueError(f"'{msg_type.__name__}'을(를) 처리할 핸들러가 등록되지 않았습니다.")
        
        handler = self._handlers[msg_type]
        
        if not inspect.iscoroutinefunction(handler):
            raise ValueError(f"'{msg_type.__name__}'의 핸들러는 반드시 비동기 함수(async def)여야 합니다.")
            
        return await handler(message)

    def on_handle(self, msg_type: Type[T]):
        """데코레이터 형태로 핸들러 등록을 지원합니다."""
        def decorator(handler: Callable[[T], Awaitable[Any]]):
            self.handle(msg_type, handler)
            return handler
        return decorator

class BaseRequest:
    """내부 비즈니스 로직용 요청 객체의 부모 클래스입니다."""
    pass

class RequestBus(BaseRequestBus[BaseRequest]):
    """내부 비즈니스 로직용 전역 요청 버스입니다."""
    def __init__(self):
        super().__init__("InternalRequestBus")
