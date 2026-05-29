from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import typing

# 타입 힌팅 전용 임포트 (런타임 순환 참조 및 의존성 방지)
if typing.TYPE_CHECKING:
    from api.copilot_handler import CopilotHandler

class AppController:
    # 밖(main.py)에서 조립된 핸들러를 주입받습니다.
    # 문자열 타입 힌팅('CopilotHandler')을 사용하여 런타임 에러를 방지합니다.
    def __init__(self, copilot_handler: 'CopilotHandler'):
        self.copilot_handler = copilot_handler

    def register_routes(self, app: FastAPI):
        @app.websocket("/ws/copilot")
        async def copilot_websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            print("[AppController] 클라이언트가 연결되었습니다.")
            
            try:
                while True:
                    # 수신 (AppController 전담)
                    raw_text = await websocket.receive_text()
                    print(f"[AppController] 수신됨: {raw_text}")
                    
                    # 위임 (주입받은 핸들러 사용)
                    response_dict = await self.copilot_handler.handle_message(raw_text)
                    
                    # 송신
                    await websocket.send_json(response_dict)
                    
            except WebSocketDisconnect:
                print("[AppController] 연결이 끊어졌습니다.")
