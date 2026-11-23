import asyncio
import logging
import uuid
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Optional, Type, TypeVar

from .signal import BaseInboundRequestSignal, BaseOutboundRequestSignal, BaseSignal

from .event_bus import BaseEventBus
from .request_bus import BaseRequestBus
from .stream_bus import BaseStreamBus

logger = logging.getLogger("SignalBus")

T_Signal = TypeVar("T_Signal", bound=BaseSignal)


class SignalBus:
    """
    프론트엔드(Electron)와 통신하는 네트워크 전용 파사드(Facade) 버스입니다.
    내부적으로 단방향 Event, 양방향 Request, 스트리밍 Stream을 나누어 라우팅합니다.
    Channel을 attach/detach하여 웹소켓 생명주기와 분리됩니다.
    """

    def __init__(self):
        self.events = BaseEventBus[BaseSignal]("SignalEventBus")
        self.requests = BaseRequestBus[BaseSignal]("SignalRequestBus")
        self.streams = BaseStreamBus[BaseSignal]("SignalStreamBus")

        self._channel: Optional[Any] = None  # Channel; attach() 호출 전까지 None

        # 백엔드 → 프론트엔드 invoke 대기 중인 Future (id → Future)
        self._pending: Dict[str, asyncio.Future] = {}

        # GC 방어 로직: 완료되지 않은 백그라운드 태스크의 강한 참조 유지 (invoke_id 기준)
        self._background_tasks: Dict[str, asyncio.Task] = {}

    # ==========================
    # Channel 생명주기
    # ==========================

    def attach(self, channel: Any) -> None:
        """WebSocket 연결 시 Channel 주입."""
        self._channel = channel

    def detach(self) -> None:
        """WebSocket 연결 종료 시 Channel 제거 및 대기 중인 invoke Future 취소."""
        self._channel = None
        for fut in self._pending.values():
            if not fut.done():
                fut.cancel()
        self._pending.clear()

    def _on_task_done(self, task_id: str, task: asyncio.Task):
        """백그라운드 태스크가 완료되면 GC 방어 딕셔너리에서 깔끔하게 삭제"""
        self._background_tasks.pop(task_id, None)
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            logger.error(f"[SignalBus] 태스크({task_id}) 처리 중 예외: {exc}", exc_info=exc)

    def cancel_task(self, invoke_id: str):
        """진행 중인 태스크에 CancelledError를 주입하여 우아하게 종료합니다."""
        if invoke_id in self._background_tasks:
            logger.info(f"[SignalBus] 백그라운드 태스크({invoke_id}) 취소 요청 수신 - 취소 시작")
            self._background_tasks[invoke_id].cancel()
        else:
            logger.warning(f"[SignalBus] 취소하려는 태스크({invoke_id})를 찾을 수 없습니다.")

    def cancel_all_tasks(self):
        """현재 진행 중인 모든 백그라운드 태스크를 강제 취소합니다."""
        if not self._background_tasks:
            return
        logger.info(
            f"[SignalBus] 연결 종료 - "
            f"모든 백그라운드 태스크({len(self._background_tasks)}개) 강제 취소"
        )
        for task in list(self._background_tasks.values()):
            task.cancel()

    async def shutdown(self):
        """진행 중인 모든 태스크를 취소하고 완료를 기다립니다."""
        tasks = list(self._background_tasks.values())
        if tasks:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"[SignalBus] {len(tasks)}개 백그라운드 태스크 취소 완료")
        await self.events.shutdown()

    # ==========================
    # Event (1:N, 단방향 발신/수신)
    # ==========================
    def connect(self, signal_type: Type[T_Signal], callback: Callable[[T_Signal], Awaitable[None]]):
        self.events.subscribe(signal_type, callback)  # type: ignore

    def disconnect(
        self, signal_type: Type[T_Signal], callback: Callable[[T_Signal], Awaitable[None]]
    ):  # noqa: E501
        self.events.unsubscribe(signal_type, callback)  # type: ignore

    def emit(self, signal: BaseSignal):
        self.events.publish(signal)

    def slot(self, signal_type: Type[BaseSignal]):
        return self.events.on(signal_type)

    # ==========================
    # Request (1:1, 양방향 단일 응답 대기)
    # ==========================
    def handle(self, signal_type: Type[T_Signal], handler: Callable[[T_Signal], Awaitable[Any]]):
        self.requests.handle(signal_type, handler)  # type: ignore

    def invoke_background(self, signal: BaseSignal):
        """
        [FastAPI 전용] 메인 루프를 블로킹하지 않고 RequestBus를 호출한 뒤,
        결과가 나오면 attach된 Channel을 통해 프론트엔드로 전송합니다.
        """

        async def _run_unary():
            try:
                result = await self.requests.invoke(signal)
                result_data = result.model_dump() if hasattr(result, "model_dump") else result
                response = {
                    "jsonrpc": "2.0",
                    "id": getattr(signal, "id", None),
                    "result": result_data,
                }
                if self._channel:
                    await self._channel.send(response)

            except asyncio.CancelledError:
                signal_id = getattr(signal, "id", None)
                if signal_id is not None and self._channel:
                    response = {
                        "jsonrpc": "2.0",
                        "id": signal_id,
                        "error": {"code": -32800, "message": "Request cancelled"},
                    }
                    await self._channel.send(response)
                raise
            except Exception as e:
                logger.error(f"[SignalBus] invoke_background 예외 발생: {e}", exc_info=True)
                signal_id = getattr(signal, "id", None)
                if signal_id is not None and self._channel:
                    response = {
                        "jsonrpc": "2.0",
                        "id": signal_id,
                        "error": {"code": -32000, "message": str(e)},
                    }
                    await self._channel.send(response)

        task = asyncio.create_task(_run_unary())
        raw_id = getattr(signal, "id", None)
        task_id = str(raw_id) if raw_id is not None else str(uuid.uuid4())
        self._background_tasks[task_id] = task
        task.add_done_callback(lambda t: self._on_task_done(task_id, t))

    # ==========================
    # Stream (1:1, 양방향 스트리밍 응답 대기)
    # ==========================
    def stream_handle(
        self, signal_type: Type[T_Signal], handler: Callable[[T_Signal], AsyncGenerator]
    ):  # noqa: E501
        self.streams.handle(signal_type, handler)  # type: ignore

    def stream_background(self, signal: BaseSignal):
        """
        [FastAPI 전용] 메인 루프를 블로킹하지 않고 StreamBus의 청크를 실시간으로
        가져와 attach된 Channel을 통해 프론트엔드로 전송합니다.
        """

        async def _run_stream():
            gen = None
            signal_id = getattr(signal, "id", None)
            try:
                gen = self.streams.stream(signal)
                async for chunk in gen:
                    chunk_data = chunk.model_dump() if hasattr(chunk, "model_dump") else chunk
                    progress_notification = {
                        "jsonrpc": "2.0",
                        "method": "$/progress",
                        "params": {"token": signal_id, "chunk": chunk_data},
                    }
                    if self._channel:
                        await self._channel.send(progress_notification)

                if signal_id is not None and self._channel:
                    response = {
                        "jsonrpc": "2.0",
                        "id": signal_id,
                        "result": {"status": "completed"},
                    }
                    await self._channel.send(response)

            except asyncio.CancelledError:
                if signal_id is not None and self._channel:
                    response = {
                        "jsonrpc": "2.0",
                        "id": signal_id,
                        "error": {"code": -32800, "message": "Stream cancelled"},
                    }
                    await self._channel.send(response)
                raise
            except Exception as e:
                logger.error(f"[SignalBus] stream_background 예외 발생: {e}", exc_info=True)
                if signal_id is not None and self._channel:
                    response = {
                        "jsonrpc": "2.0",
                        "id": signal_id,
                        "error": {"code": -32000, "message": str(e)},
                    }
                    await self._channel.send(response)
            finally:
                if gen is not None:
                    await gen.aclose()

        task = asyncio.create_task(_run_stream())
        raw_id = getattr(signal, "id", None)
        task_id = str(raw_id) if raw_id is not None else str(uuid.uuid4())
        self._background_tasks[task_id] = task
        task.add_done_callback(lambda t: self._on_task_done(task_id, t))

    # ==========================
    # Invoke (백엔드 → 프론트엔드 요청, JS RequestBus.handle 대응)
    # ==========================

    async def invoke(self, signal: BaseOutboundRequestSignal) -> Any:
        """
        백엔드에서 프론트엔드로 요청을 보내고 응답을 기다립니다.
        JS signalBus.requests.handle(method, handler)에 등록된 핸들러가 응답합니다.
        """
        if self._channel is None:
            raise RuntimeError("[SignalBus] Channel이 연결되지 않았습니다.")

        request_id = str(uuid.uuid4())
        signal.id = request_id  # id는 송신 시점에 자동 부여
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending[request_id] = fut

        request = signal.model_dump()
        await self._channel.send(request)

        try:
            return await fut
        finally:
            self._pending.pop(request_id, None)

    def resolve(self, signal: BaseOutboundRequestSignal) -> None:
        """
        invoke()의 짝. 프론트엔드에서 도착한 응답을 대기 중인 Future에 전달합니다.
        """
        response_id = str(signal.id)
        fut = self._pending.get(response_id)
        if fut is None or fut.done():
            logger.warning(f"[SignalBus] 응답 ID '{response_id}'에 대한 대기 요청 없음")
            return
        if signal.error is not None:
            fut.set_exception(RuntimeError(signal.error.get("message", "RPC error from frontend")))
        else:
            fut.set_result(signal.result)
