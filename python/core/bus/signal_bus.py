import asyncio
import logging
import uuid
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Type, TypeVar

from contracts.signal import BaseSignal

from .event_bus import BaseEventBus
from .request_bus import BaseRequestBus
from .stream_bus import BaseStreamBus

logger = logging.getLogger("SignalBus")

T_Signal = TypeVar("T_Signal", bound=BaseSignal)


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

        # GC 방어 로직: 완료되지 않은 백그라운드 태스크의 강한 참조 유지 (invoke_id 기준)
        self._background_tasks: Dict[str, asyncio.Task] = {}

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

    def invoke_background(
        self, signal: BaseSignal, send_callback: Callable[[dict], Awaitable[None]]
    ):  # noqa: E501
        """
        [FastAPI 전용] 메인 루프를 블로킹하지 않고 RequestBus를 호출한 뒤,
        결과가 나오면 콜백(웹소켓 send)을 실행합니다.
        """

        async def _run_unary():
            try:
                result = await self.requests.invoke(signal)
                result_data = result.model_dump() if hasattr(result, "model_dump") else result

                # 단일 요청 정상 완료 -> JSON-RPC Result 응답
                response = {
                    "jsonrpc": "2.0",
                    "id": getattr(signal, "id", None),
                    "result": result_data,
                }
                await send_callback(response)

            except asyncio.CancelledError:
                # 작업 취소 시 -> JSON-RPC Error 응답 (-32800: Request Cancelled)
                signal_id = getattr(signal, "id", None)
                if signal_id:
                    response = {
                        "jsonrpc": "2.0",
                        "id": signal_id,
                        "error": {"code": -32800, "message": "Request cancelled"},
                    }
                    await send_callback(response)
                raise
            except Exception as e:
                logger.error(f"[SignalBus] invoke_background 예외 발생: {e}", exc_info=True)
                # 처리 중 예외 발생 시 -> JSON-RPC Error 응답 (-32000: Server Error)
                signal_id = getattr(signal, "id", None)
                if signal_id:
                    response = {
                        "jsonrpc": "2.0",
                        "id": signal_id,
                        "error": {"code": -32000, "message": str(e)},
                    }
                    await send_callback(response)
            finally:
                pass  # 단일 요청이므로 별도의 자원 닫기 불필요

        task = asyncio.create_task(_run_unary())
        task_id = getattr(signal, "id", None) or str(uuid.uuid4())
        self._background_tasks[task_id] = task
        task.add_done_callback(lambda t: self._on_task_done(task_id, t))

    # ==========================
    # Stream (1:1, 양방향 스트리밍 응답 대기)
    # ==========================
    def stream_handle(
        self, signal_type: Type[T_Signal], handler: Callable[[T_Signal], AsyncGenerator]
    ):  # noqa: E501
        self.streams.handle(signal_type, handler)  # type: ignore

    def stream_background(
        self, signal: BaseSignal, send_callback: Callable[[dict], Awaitable[None]]
    ):  # noqa: E501
        """
        [FastAPI 전용] 메인 루프를 블로킹하지 않고 StreamBus의 청크를 실시간으로
        가져와 콜백(웹소켓 send)으로 전송합니다.
        """

        async def _run_stream():
            gen = None
            signal_id = getattr(signal, "id", None)
            try:
                # stream()은 await 없이 즉시 제너레이터를 반환
                gen = self.streams.stream(signal)
                async for chunk in gen:
                    chunk_data = chunk.model_dump() if hasattr(chunk, "model_dump") else chunk
                    # 스트리밍 청크 -> Progress Notification
                    progress_notification = {
                        "jsonrpc": "2.0",
                        "method": "$/progress",
                        "params": {"token": signal_id, "chunk": chunk_data},
                    }
                    await send_callback(progress_notification)

                # 정상 완료 시 -> JSON-RPC 최종 Result 응답
                if signal_id:
                    response = {
                        "jsonrpc": "2.0",
                        "id": signal_id,
                        "result": {"status": "completed"},
                    }
                    await send_callback(response)

            except asyncio.CancelledError:
                # 작업 취소 시 -> JSON-RPC Error 응답 (-32800)
                if signal_id:
                    response = {
                        "jsonrpc": "2.0",
                        "id": signal_id,
                        "error": {"code": -32800, "message": "Stream cancelled"},
                    }
                    await send_callback(response)
                raise
            except Exception as e:
                logger.error(f"[SignalBus] stream_background 예외 발생: {e}", exc_info=True)
                # 에러 발생 시 -> JSON-RPC Error 응답 (-32000)
                if signal_id:
                    response = {
                        "jsonrpc": "2.0",
                        "id": signal_id,
                        "error": {"code": -32000, "message": str(e)},
                    }
                    await send_callback(response)
            finally:
                if gen is not None:
                    await gen.aclose()

        task = asyncio.create_task(_run_stream())
        task_id = getattr(signal, "id", None) or str(uuid.uuid4())
        self._background_tasks[task_id] = task
        task.add_done_callback(lambda t: self._on_task_done(task_id, t))
