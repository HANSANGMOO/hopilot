from utils import get_logger
from core.bus import EventBus, SignalBus
from contracts.copilot import SendUserRequestSignal
from controller.handlers.copilot_handler import CopilotHandler
from services.copilot_service import CopilotService
from services.session_service import SessionService

logger = get_logger("AppController")

class AppController:
    """
    앱의 라이프사이클과 핵심 비즈니스 로직을 오케스트레이션하는 메인 컨트롤러입니다.
    네트워크 로직(FastAPI)과 완전히 분리되어 있으며, EventBus를 통해 시스템과 통신합니다.
    """
    def __init__(self, event_bus: EventBus, signal_bus: SignalBus, copilot_service: CopilotService, session_service: SessionService):
        self.event_bus = event_bus
        self.signal_bus = signal_bus
        self.copilot_handler = CopilotHandler(copilot_service=copilot_service, session_service=session_service)
        logger.info("AppController initialized with EventBus, SignalBus, and Handlers.")
        
        self.connect_signals()

    def connect_signals(self):
        """SignalBus를 통해 들어오는 외부 시그널을 각 핸들러의 슬롯에 연결합니다."""
        self.signal_bus.stream_handle(SendUserRequestSignal, self.copilot_handler.handle_user_request)
