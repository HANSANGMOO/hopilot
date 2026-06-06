import logging

import uvicorn
from fastapi import FastAPI

from api.api_manager import ApiManager
from controller.app_controller import AppController
from core.bus import EventBus, SignalBus
from db.db_manager import DBManager
from engine.agent_worker import AgentWorker
from engine.request_engine import RequestEngine
from server.fastapi_server import FastAPIServer
from services.copilot_service import CopilotService
from services.session_service import SessionService
from utils import setup_logger


def bootstrap_app() -> FastAPI:
    """
    DI Container 역할: 앱의 모든 객체를 생성하고 최상위에서 조립(Wiring)합니다.
    """
    # 0. 전역 로거 초기화
    logger = setup_logger(level=logging.INFO)
    logger.info("Hopilot Backend Bootstrapping Started...")

    # 1. 코어 인프라 객체 생성 (Singleton)
    event_bus: EventBus = EventBus()
    signal_bus: SignalBus = SignalBus()

    # 2. 비즈니스 서비스 생성 및 하위 컴포넌트 주입
    db_manager: DBManager = DBManager()
    session_service: SessionService = SessionService(db_manager)
    api_manager: ApiManager = ApiManager()
    request_engine: RequestEngine = RequestEngine()
    agent_worker: AgentWorker = AgentWorker(event_bus=event_bus)

    copilot_service: CopilotService = CopilotService(
        event_bus=event_bus,
        api_manager=api_manager,
        request_engine=request_engine,
        agent_worker=agent_worker
    )

    # 3. 비즈니스 코어(Controller) 생성 및 의존성 주입 (내부에서 핸들러 생성)
    app_controller: AppController = AppController(
        event_bus=event_bus,
        signal_bus=signal_bus,
        copilot_service=copilot_service,
        session_service=session_service
    )

    # 4. FastAPI 서버 객체 생성 및 의존성 주입
    # FastAPIServer 내부에 FastAPI app 객체가 포함되어 있습니다.
    fastapi_server: FastAPIServer = FastAPIServer(event_bus=event_bus, signal_bus=signal_bus)

    return fastapi_server.app

# 앱 초기화
app = bootstrap_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
