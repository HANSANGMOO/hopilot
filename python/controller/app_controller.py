from utils import get_logger
from core.event_bus import EventBus

logger = get_logger("AppController")

class AppController:
    """
    앱의 라이프사이클과 핵심 비즈니스 로직을 오케스트레이션하는 메인 컨트롤러입니다.
    네트워크 로직(FastAPI)과 완전히 분리되어 있으며, EventBus를 통해 시스템과 통신합니다.
    """
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        logger.info("AppController initialized with EventBus.")
        
        # 추후 이곳에서 시스템 코어 서비스들을 초기화하거나
        # EventBus 구독(Subscribe) 이벤트 매핑을 설정할 수 있습니다.
