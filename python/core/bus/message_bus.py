import asyncio
import logging
from typing import Callable, Dict, List, Type, TypeVar, Awaitable, Generic
from pydantic import BaseModel
from contracts.signal import BaseSignal

logger = logging.getLogger("Bus")
T = TypeVar('T')

class BaseMessageBus(Generic[T]):
    """EventBus와 SignalBus의 공통 핵심 로직을 담당하는 부모 클래스"""
    def __init__(self, bus_name: str):
        self.bus_name = bus_name
        self._listeners: Dict[Type[T], List[Callable[[T], Awaitable[None]]]] = {}
        self._background_tasks = set()

    def add_listener(self, msg_type: Type[T], callback: Callable[[T], Awaitable[None]]):
        if msg_type not in self._listeners:
            self._listeners[msg_type] = []
        if callback not in self._listeners[msg_type]:
            self._listeners[msg_type].append(callback)

    def remove_listener(self, msg_type: Type[T], callback: Callable[[T], Awaitable[None]]):
        if msg_type in self._listeners and callback in self._listeners[msg_type]:
            self._listeners[msg_type].remove(callback)

    def dispatch(self, message: T):
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


class BaseEvent(BaseModel):
    pass

class EventBus(BaseMessageBus[BaseEvent]):
    """
    내부 비즈니스 로직 및 생명주기를 다루는 Event 전용 버스입니다.
    네트워크 통신용 SignalBus와 독립적으로 동작합니다.
    """
    def __init__(self):
        super().__init__("EventBus")

    def subscribe(self, event_type: Type[BaseEvent], callback: Callable[[BaseEvent], Awaitable[None]]):
        self.add_listener(event_type, callback)
        
    def unsubscribe(self, event_type: Type[BaseEvent], callback: Callable[[BaseEvent], Awaitable[None]]):
        self.remove_listener(event_type, callback)

    def publish(self, event: BaseEvent):
        self.dispatch(event)

    def on(self, event_type: Type[BaseEvent]):
        def decorator(callback: Callable[[BaseEvent], Awaitable[None]]):
            self.subscribe(event_type, callback)
            return callback
        return decorator


class SignalBus(BaseMessageBus[BaseSignal]):
    """
    React 프론트엔드와 웹소켓으로 통신하는 BaseSignal 전용 버스입니다.
    내부 비즈니스 로직용 EventBus와 독립적으로 동작합니다.
    """
    def __init__(self):
        super().__init__("SignalBus")

    def connect(self, signal_type: Type[BaseSignal], slot_func: Callable[[BaseSignal], Awaitable[None]]):
        self.add_listener(signal_type, slot_func)
        
    def disconnect(self, signal_type: Type[BaseSignal], slot_func: Callable[[BaseSignal], Awaitable[None]]):
        self.remove_listener(signal_type, slot_func)

    def emit(self, signal: BaseSignal):
        self.dispatch(signal)

    def slot(self, signal_type: Type[BaseSignal]):
        def decorator(slot_func: Callable[[BaseSignal], Awaitable[None]]):
            self.connect(signal_type, slot_func)
            return slot_func
        return decorator
