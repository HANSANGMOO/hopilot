import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Optional
from utils import get_logger

from core.channel import Channel
from core.bus import EventBus, SignalBus
from contracts.copilot import SendUserRequestSignal

logger = get_logger("FastAPIServer")

class FastAPIServer:
    """
    네트워크와 프레임워크(FastAPI)의 생명주기를 전담하는 인프라/API 계층 클래스입니다.
    순수 비즈니스 로직(Engine, Service)을 알지 못하며, 오직 웹소켓 연결과 Channel 생성을 담당합니다.
    """
    
    def __init__(self, event_bus: EventBus, signal_bus: SignalBus):
        self.app = FastAPI(title="Hopilot Backend")
        self.event_bus = event_bus
        self.signal_bus = signal_bus
        self.channel: Optional[Channel] = None
        
        self._register_routes()

    def _register_routes(self):
        @self.app.websocket("/ws/hopilot")
        async def hopilot_websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            logger.info("프론트엔드 웹소켓 연결 수락됨.")
            
            # 1. 클라이언트 접속 순간 Channel 객체 즉시 생성 (의존성 주입)
            self.channel = Channel(
                send_msg_func=websocket.send_text,
                receive_msg_func=websocket.receive_text
            )
            
            try:
                # 2. Channel의 수신 루프 가동
                # 클라이언트가 보낸 메시지(JSON 파싱된 Dict)가 지속적으로 배출(yield)됩니다.
                async for payload in self.channel.listen():
                    logger.debug(f"웹소켓 수신 -> Channel 배출: {payload}")
                    
                    # 3. 수신된 데이터를 Pydantic 시그널 객체로 파싱하여 SignalBus에 Publish
                    signal_type = payload.get("type")
                    if signal_type == "SendUserRequestSignal":
                        signal = SendUserRequestSignal(**payload)
                        self.signal_bus.emit(signal)
                    else:
                        logger.warning(f"알 수 없는 시그널 타입 수신: {signal_type}")
                    
            except WebSocketDisconnect:
                logger.info("프론트엔드 웹소켓 연결 종료됨.")
            except Exception as e:
                logger.error(f"웹소켓 통신 중 예외 발생: {e}", exc_info=True)
            finally:
                # 4. 연결 종료 시 Channel 객체 소멸
                self.channel = None
