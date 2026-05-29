import uvicorn
from fastapi import FastAPI

# 의존성 모듈들 임포트
from api.copilot_handler import CopilotHandler
from controller.app_controller import AppController

def bootstrap_app() -> FastAPI:
    """
    DI Container 역할: 앱의 모든 객체를 생성하고 최상위에서 조립(Wiring)합니다.
    """
    app = FastAPI(title="Hopilot Backend")
    
    # 1. 의존성 객체 생성 (하위 계층부터 조립)
    # (추후 EventBus, CopilotService 등도 모두 여기서 생성하여 주입합니다)
    copilot_handler = CopilotHandler()
    
    # 2. AppController 생성 및 의존성 주입 (Constructor Injection)
    app_controller = AppController(copilot_handler=copilot_handler)
    
    # 3. 라우터(웹소켓) 바인딩
    app_controller.register_routes(app)
    
    return app

# 앱 초기화
app = bootstrap_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
