import asyncio
import logging
from typing import Callable, Dict, List, Type, TypeVar, Awaitable, Generic, Any
from pydantic import BaseModel

logger = logging.getLogger("EventBus")
T = TypeVar('T')

class BaseEventBus(Generic[T]):
    """1:N 단방향 이벤트를 발송(Publish)하고 구독(Subscribe)하는 버스"""
    def __init__(self, bus_name: str = "EventBus"):
        self.bus_name = bus_name
        self._listeners: Dict[Type[T], List[Callable[[T], Awaitable[None]]]] = {}
        self._background_tasks = set()

    def subscribe(self, msg_type: Type[T], callback: Callable[[T], Awaitable[None]]):
        if msg_type not in self._listeners:
            self._listeners[msg_type] = []
        if callback not in self._listeners[msg_type]:
            self._listeners[msg_type].append(callback)

    def unsubscribe(self, msg_type: Type[T], callback: Callable[[T], Awaitable[None]]):
        if msg_type in self._listeners and callback in self._listeners[msg_type]:
            self._listeners[msg_type].remove(callback)

    def publish(self, message: T):
        msg_type = type(message)
        if msg_type in self._listeners:
            for callback in self._listeners[msg_type]:
                coro = callback(message)
                task = asyncio.create_task(coro)
                self._background_tasks.add(task)
                task.add_done_callback(self._on_task_done)

    def _on_task_done(self, task: asyncio.Task):
        self._background_tasks.discard(task)
        if task.exception():
            logger.error(f"[{self.bus_name}] 예외 발생: {task.exception()}", exc_info=task.exception())

    def on(self, msg_type: Type[T]):
        """데코레이터 형태로 구독을 지원합니다."""
        def decorator(callback: Callable[[T], Awaitable[None]]):
            self.subscribe(msg_type, callback)
            return callback
        return decorator

class BaseEvent(BaseModel):
    pass

class EventBus(BaseEventBus[BaseEvent]):
    """내부 비즈니스 로직용 전역 이벤트 버스입니다."""
    def __init__(self):
        super().__init__("InternalEventBus")
