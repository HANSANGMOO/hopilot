import asyncio
import logging
from pydantic import BaseModel
from typing import Callable, Dict, List, Type, TypeVar, Awaitable

logger = logging.getLogger("EventBus")

class BaseEvent(BaseModel):
    pass

T = TypeVar('T', bound=BaseEvent)

class EventBus:
    def __init__(self) -> None:
        self._callbacks: Dict[Type[BaseEvent], List[Callable[[T], Awaitable[None]]]] = {}
        self._background_tasks = set()

    def subscribe(self, event_type: Type[T], callback: Callable[[T], Awaitable[None]]) -> None:
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        if callback not in self._callbacks[event_type]:
            self._callbacks[event_type].append(callback)

    def unsubscribe(self, event_type: Type[T], callback: Callable[[T], Awaitable[None]]) -> None:
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)

    def _on_task_done(self, task: asyncio.Task) -> None:
        """태스크 종료 시 GC 방지용 셋에서 제거하고, 발생한 예외를 안전하게 로깅합니다."""
        self._background_tasks.discard(task)
        try:
            exc = task.exception()
            if exc:
                logger.error(f"EventBus 콜백 실행 중 예외 발생: {exc}", exc_info=exc)
        except asyncio.CancelledError:
            pass

    def publish(self, event: T) -> None:
        event_type = type(event)
        if event_type in self._callbacks:
            for callback in self._callbacks[event_type]:
                coro = callback(event)
                task = asyncio.create_task(coro)
                self._background_tasks.add(task)
                task.add_done_callback(self._on_task_done)

    def on(self, event_type: Type[T]) -> Callable[[Callable[[T], Awaitable[None]]], Callable[[T], Awaitable[None]]]:
        def decorator(callback: Callable[[T], Awaitable[None]]) -> Callable[[T], Awaitable[None]]:
            self.subscribe(event_type, callback)
            return callback
        return decorator
