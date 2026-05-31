import asyncio
import json
import logging
from typing import Any, Dict, Callable, Awaitable, Optional, AsyncGenerator

logger = logging.getLogger("Channel")

class ChannelDisconnected(Exception):
    """Raised when the channel connection is closed normally."""
    pass

class Channel:
    """
    웹소켓(또는 기타 문자열 기반 스트림)의 물리적 연결(프레임워크)과
    메시지 처리 논리를 완벽히 분리하기 위한 순수 파이썬 채널 인프라입니다.
    비동기 제너레이터(Async Generator) 패턴을 사용하여 이벤트를 배출(yield)합니다.
    """
    
    def __init__(
        self, 
        send_msg_func: Callable[[str], Awaitable[None]], 
        receive_msg_func: Callable[[], Awaitable[str]]
    ):
        # 네트워크 송수신 기능을 외부(Controller)로부터 주입받습니다.
        self._send_msg_func = send_msg_func
        self._receive_msg_func = receive_msg_func
        
        # 송신 대기열 큐 (백그라운드에서 순차 전송)
        self._send_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._send_task: Optional[asyncio.Task] = None
        
        # 백그라운드 태스크 GC 방지용 Set
        self._background_tasks = set()

    def _on_task_done(self, task: asyncio.Task) -> None:
        """태스크 종료 시 GC 방지용 셋에서 제거하고, 발생한 예외를 안전하게 로깅합니다."""
        self._background_tasks.discard(task)
        try:
            exc = task.exception()
            if exc:
                logger.error(f"Background task exception in Channel: {exc}", exc_info=exc)
        except asyncio.CancelledError:
            pass

    async def send(self, data: Dict[str, Any]) -> None:
        """
        EventBus 등 파이썬 내부 로직이 프론트엔드로 메시지를 보낼 때 호출합니다.
        큐에 넣기만 하므로 절대 블로킹되지 않습니다.
        """
        await self._send_queue.put(data)

    async def _send_loop(self) -> None:
        """큐에 쌓인 데이터를 순차적으로 직렬화하여 쏘아주는 백그라운드 워커"""
        try:
            while True:
                data_dict = await self._send_queue.get()
                try:
                    json_str = json.dumps(data_dict)
                    await self._send_msg_func(json_str)
                except Exception as e:
                    logger.error(f"Failed to send message: {e}", exc_info=True)
                finally:
                    self._send_queue.task_done()
        except asyncio.CancelledError:
            logger.debug("Send loop cancelled gracefully.")

    async def _receive_loop(self) -> AsyncGenerator[Dict[str, Any], None]:
        """외부로부터 텍스트를 수신하고 파싱하여 배출(yield)하는 메인 수신 워커"""
        try:
            while True:
                raw_text = await self._receive_msg_func()

                try:
                    payload = json.loads(raw_text)
                    yield payload
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON format: {raw_text}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}", exc_info=True)
                    
        except ChannelDisconnected:
            logger.info("Channel disconnected normally.")
        except Exception as e:
            logger.error(f"Unexpected error during channel receive: {e}", exc_info=True)

    async def listen(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Controller에서 최종적으로 호출하는 진입점입니다.
        송수신 생명주기를 관리하고 수신된 데이터를 외부로 배출합니다.
        """
        # 1. 송신 루프를 백그라운드 태스크로 시작
        self._send_task = asyncio.create_task(self._send_loop())
        self._background_tasks.add(self._send_task)
        self._send_task.add_done_callback(self._on_task_done)
        
        try:
            # 2. 수신 루프 실행 및 데이터 중계(Proxy yield)
            async for payload in self._receive_loop():
                yield payload
        finally:
            # 3. 수신이 종료(에러/연결끊김)되면 송신 태스크도 안전하게 취소(Cleanup)
            if self._send_task:
                self._send_task.cancel()
