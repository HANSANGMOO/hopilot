import inspect
import logging
from typing import AsyncGenerator, Callable, Dict, Generic, Type, TypeVar

from pydantic import BaseModel

logger = logging.getLogger("StreamBus")
T = TypeVar('T')

class BaseStreamBus(Generic[T]):
    """1:1 스트리밍 응답(AsyncGenerator)을 처리하는 버스"""
    def __init__(self, bus_name: str = "StreamBus"):
        self.bus_name = bus_name
        self._handlers: Dict[Type[T], Callable[[T], AsyncGenerator]] = {}

    def handle(self, msg_type: Type[T], handler: Callable[[T], AsyncGenerator]):
        """특정 스트림 요청 타입에 대해 비동기 제너레이터를 반환하는 핸들러를 등록합니다."""
        if msg_type in self._handlers:
            raise ValueError(f"'{msg_type.__name__}'에 대한 핸들러가 이미 존재합니다. StreamBus는 1:1 매칭만 지원합니다.")
        self._handlers[msg_type] = handler

    def stream(self, message: T) -> AsyncGenerator:
        """요청을 발생시키고 등록된 제너레이터 핸들러 객체를 즉시 반환합니다. (await 사용 안 함)"""
        msg_type = type(message)
        if msg_type not in self._handlers:
            raise ValueError(f"'{msg_type.__name__}'을(를) 처리할 핸들러가 등록되지 않았습니다.")

        handler = self._handlers[msg_type]

        if not inspect.isasyncgenfunction(handler):
            raise ValueError(f"'{msg_type.__name__}'의 핸들러는 반드시 비동기 제너레이터 함수(async def + yield)여야 합니다.")

        return handler(message)

    def on_handle(self, msg_type: Type[T]):
        """데코레이터 형태로 핸들러 등록을 지원합니다."""
        def decorator(handler: Callable[[T], AsyncGenerator]):
            self.handle(msg_type, handler)
            return handler
        return decorator

class BaseStream(BaseModel):
    """내부 비즈니스 로직용 스트림 객체의 부모 클래스입니다."""
    pass

class StreamBus(BaseStreamBus[BaseStream]):
    """내부 비즈니스 로직용 전역 스트림 버스입니다."""
    def __init__(self):
        super().__init__("InternalStreamBus")
