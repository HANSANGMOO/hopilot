import logging
import uvicorn
from fastapi import FastAPI

# 의존성 모듈들 임포트
from core.event_bus import EventBus
from server.fastapi_server import FastAPIServer
from controller.app_controller import AppController
from utils import setup_logger

def bootstrap_app() -> FastAPI:
    """
    DI Container 역할: 앱의 모든 객체를 생성하고 최상위에서 조립(Wiring)합니다.
    """
    # 0. 전역 로거 초기화
    logger = setup_logger(level=logging.INFO)
    logger.info("Hopilot Backend Bootstrapping Started...")
    
    # 1. 코어 인프라 객체 생성 (Singleton)
    event_bus = EventBus()
    
    # 2. 비즈니스 코어(Controller) 생성 및 의존성 주입
    app_controller = AppController(event_bus=event_bus)
    
    # 3. FastAPI 서버 객체 생성 및 의존성 주입
    # FastAPIServer 내부에 FastAPI app 객체가 포함되어 있습니다.
    fastapi_server = FastAPIServer(event_bus=event_bus)
    
    return fastapi_server.app

# 앱 초기화
app = bootstrap_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
