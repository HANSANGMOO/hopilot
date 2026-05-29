from __future__ import annotations
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import typing
from utils import get_logger

logger = get_logger("AppController")

# 타입 힌팅 전용 임포트 (런타임 순환 참조 및 의존성 방지)
if typing.TYPE_CHECKING:
    from controller.handlers.copilot_handler import CopilotHandler

class AppController:
    # 밖(main.py)에서 조립된 핸들러를 주입받습니다.
    # 문자열 타입 힌팅('CopilotHandler')을 사용하여 런타임 에러를 방지합니다.
    def __init__(self, copilot_handler: CopilotHandler):
        self.copilot_handler = copilot_handler

    def register_routes(self, app: FastAPI):
        @app.websocket("/ws/copilot")
        async def copilot_websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            logger.info("WebSocket client connected.")
            
            try:
                while True:
                    raw_text = await websocket.receive_text()
                    logger.debug(f"Received raw data: {raw_text}")
                    
                    response_dict = await self.copilot_handler.handle_message(raw_text)
                    
                    await websocket.send_json(response_dict)
                    
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected.")
