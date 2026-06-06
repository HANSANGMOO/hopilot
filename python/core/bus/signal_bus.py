import asyncio
import logging
from typing import Any, AsyncGenerator, Callable, Type, Awaitable
from contracts.signal import BaseSignal
from .event_bus import BaseEventBus
from .request_bus import BaseRequestBus
from .stream_bus import BaseStreamBus

logger = logging.getLogger("SignalBus")

class SignalBus:
    """
    프론트엔드(Electron)와 통신하는 네트워크 전용 파사드(Facade) 버스입니다.
    내부적으로 단방향 Event, 양방향 Request, 스트리밍 Stream을 나누어 라우팅합니다.
    웹소켓의 병목을 막기 위해 invoke_background와 stream_background 메서드를 제공합니다.
    """
    def __init__(self):
        self.events = BaseEventBus[BaseSignal]("SignalEventBus")
        self.requests = BaseRequestBus[BaseSignal]("SignalRequestBus")
        self.streams = BaseStreamBus[BaseSignal]("SignalStreamBus")
        
        # GC 방어 로직: 완료되지 않은 백그라운드 태스크의 강한 참조 유지
        self._background_tasks = set()

    def _on_task_done(self, task: asyncio.Task):
        """백그라운드 태스크가 완료되면 GC 방어 셋에서 깔끔하게 삭제(is_callback_done)"""
        self._background_tasks.discard(task)
        if task.exception():
            logger.error(f"[SignalBus] 태스크 처리 중 예외 발생: {task.exception()}", exc_info=task.exception())

    # ==========================
    # Event (1:N, 단방향 발신/수신)
    # ==========================
    def connect(self, signal_type: Type[BaseSignal], callback: Callable[[BaseSignal], Awaitable[None]]):
        self.events.subscribe(signal_type, callback)

    def disconnect(self, signal_type: Type[BaseSignal], callback: Callable[[BaseSignal], Awaitable[None]]):
        self.events.unsubscribe(signal_type, callback)

    def emit(self, signal: BaseSignal):
        self.events.publish(signal)

    def slot(self, signal_type: Type[BaseSignal]):
        return self.events.on(signal_type)

    # ==========================
    # Request (1:1, 양방향 단일 응답 대기)
    # ==========================
    def handle(self, signal_type: Type[BaseSignal], handler: Callable[[BaseSignal], Awaitable[Any]]):
        self.requests.handle(signal_type, handler)

    def invoke_background(self, signal: BaseSignal, send_callback: Callable[[dict], Awaitable[None]]):
        """
        [FastAPI 전용] 메인 루프를 블로킹하지 않고 RequestBus를 호출한 뒤,
        결과가 나오면 콜백(웹소켓 send)을 실행합니다.
        """
        async def _run_unary():
            try:
                result = await self.requests.invoke(signal)
                # 만약 result가 Pydantic 모델이라면 dict로 변환 (필요시)
                data = result.model_dump() if hasattr(result, "model_dump") else result
                
                # 원본 시그널의 invoke_id 보존
                if hasattr(signal, "invoke_id") and isinstance(data, dict):
                    data["invoke_id"] = signal.invoke_id
                    
                await send_callback(data)
            except Exception as e:
                logger.error(f"[SignalBus] invoke_background 실행 실패: {e}", exc_info=True)

        task = asyncio.create_task(_run_unary())
        self._background_tasks.add(task)
        task.add_done_callback(self._on_task_done)

    # ==========================
    # Stream (1:1, 양방향 스트리밍 응답 대기)
    # ==========================
    def stream_handle(self, signal_type: Type[BaseSignal], handler: Callable[[BaseSignal], AsyncGenerator]):
        self.streams.handle(signal_type, handler)

    def stream_background(self, signal: BaseSignal, send_callback: Callable[[dict], Awaitable[None]]):
        """
        [FastAPI 전용] 메인 루프를 블로킹하지 않고 StreamBus의 청크를 실시간으로 
        가져와 콜백(웹소켓 send)으로 전송합니다.
        """
        async def _run_stream():
            try:
                # stream()은 await 없이 즉시 제너레이터를 반환
                gen = self.streams.stream(signal)
                async for chunk in gen:
                    data = chunk.model_dump() if hasattr(chunk, "model_dump") else chunk
                    if hasattr(signal, "invoke_id") and isinstance(data, dict):
                        data["invoke_id"] = signal.invoke_id
                    await send_callback(data)
            except Exception as e:
                logger.error(f"[SignalBus] stream_background 실행 실패: {e}", exc_info=True)

        task = asyncio.create_task(_run_stream())
        self._background_tasks.add(task)
        task.add_done_callback(self._on_task_done)
