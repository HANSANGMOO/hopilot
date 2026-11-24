from contracts.attachment import (
    AttachmentDeleteSignal,
    AttachmentGetSignal,
    AttachmentLoadSignal,
    AttachmentUnloadSignal,
)
from contracts.copilot import CopilotRunStreamSignal
from contracts.model import ModelDTO, ModelListSignal
from contracts.tool import ToolListSignal
from contracts.project import (
    ProjectCreateSignal,
    ProjectDeleteSignal,
    ProjectListSignal,
    ProjectLoadSignal,
    ProjectUpdateSignal,
)
from contracts.session import (
    SessionCreateSignal,
    SessionDeleteSignal,
    SessionForkSignal,
    SessionListSignal,
    SessionLoadSignal,
    SessionTruncateSignal,
    SessionUpdateSignal,
)
from controller.handlers.attachment_handler import AttachmentHandler
from controller.handlers.copilot_handler import CopilotHandler
from controller.handlers.project_handler import ProjectHandler
from controller.handlers.session_handler import SessionHandler
from controller.handlers.tool_handler import ToolHandler
from core.bus import EventBus, SignalBus
from core.di import ToolDependency
from io_.knowledge_graph_manager import KnowledgeGraphManager
from services.attachment_service import AttachmentService
from services.context_service import ContextService
from services.copilot_service import CopilotService
from services.llm_model_service import LlmModelService
from services.mcp_service import McpService
from services.project_service import ProjectService
from services.session_service import SessionService
from services.tool_service import ToolService
from utils import get_logger

logger = get_logger("AppController")

class AppController:
    """
    앱의 라이프사이클과 핵심 비즈니스 로직을 오케스트레이션하는 메인 컨트롤러입니다.
    네트워크 로직(FastAPI)과 완전히 분리되어 있으며, EventBus를 통해 시스템과 통신합니다.
    """
    def __init__(
        self,
        event_bus: EventBus,
        signal_bus: SignalBus,
        copilot_service: CopilotService,
        session_service: SessionService,
        project_service: ProjectService,
        llm_model_service: LlmModelService,
        attachment_service: AttachmentService,
        context_service: ContextService,
        tool_service: ToolService,
        mcp_service: McpService,
        kg_manager: KnowledgeGraphManager,
    ):
        self.event_bus = event_bus
        self.signal_bus = signal_bus
        self.kg_manager = kg_manager
        self.tool_service = tool_service
        self.llm_model_service = llm_model_service
        self.context_service = context_service
        self.copilot_handler = CopilotHandler(
            copilot_service=copilot_service,
            session_service=session_service,
            llm_model_service=llm_model_service,
            attachment_service=attachment_service,
            context_service=context_service,
            tool_service=tool_service,
        )
        self.session_handler = SessionHandler(session_service=session_service)
        self.project_handler = ProjectHandler(project_service=project_service, session_service=session_service, context_service=context_service)
        self.tool_handler = ToolHandler(tool_service=tool_service, mcp_service=mcp_service)
        self.attachment_handler = AttachmentHandler(attachment_service=attachment_service)
        logger.info("AppController initialized with EventBus, SignalBus, and Handlers.")
        self.connect_signals()

    async def initialize(self) -> None:
        """서비스 계층 비동기 초기화. lifespan에서 인프라 초기화 후 호출됩니다."""
        deps = ToolDependency()
        deps.register(SignalBus, self.signal_bus)
        deps.register(KnowledgeGraphManager, self.kg_manager)
        await self.tool_handler.initialize(deps=deps)

    async def shutdown(self) -> None:
        """서비스 계층 종료. lifespan에서 인프라 종료 전 호출됩니다."""
        await self.tool_handler.shutdown()

    def connect_signals(self):
        """SignalBus를 통해 들어오는 외부 시그널을 각 핸들러의 슬롯에 연결합니다."""
        self.signal_bus.stream_handle(CopilotRunStreamSignal, self.copilot_handler.handle_user_request)

        self.signal_bus.handle(ProjectListSignal,   self.project_handler.handle_list)
        self.signal_bus.handle(ProjectLoadSignal,   self.project_handler.handle_load)
        self.signal_bus.handle(ProjectCreateSignal, self.project_handler.handle_create)
        self.signal_bus.handle(ProjectUpdateSignal, self.project_handler.handle_update)
        self.signal_bus.handle(ProjectDeleteSignal, self.project_handler.handle_delete)

        self.signal_bus.handle(SessionListSignal,     self.session_handler.handle_list)
        self.signal_bus.handle(SessionLoadSignal,     self.session_handler.handle_load)
        self.signal_bus.handle(SessionCreateSignal,   self.session_handler.handle_create)
        self.signal_bus.handle(SessionUpdateSignal,   self.session_handler.handle_update)
        self.signal_bus.handle(SessionDeleteSignal,   self.session_handler.handle_delete)
        self.signal_bus.handle(SessionTruncateSignal, self.session_handler.handle_truncate)
        self.signal_bus.handle(SessionForkSignal,     self.session_handler.handle_fork)

        self.signal_bus.handle(ToolListSignal, self.tool_handler.handle_list)
        self.signal_bus.handle(ModelListSignal, self._handle_model_list)

        self.signal_bus.handle(AttachmentLoadSignal,     self.attachment_handler.handle_load)
        self.signal_bus.connect(AttachmentUnloadSignal,  self.attachment_handler.handle_unload)
        self.signal_bus.handle(AttachmentGetSignal,      self.attachment_handler.handle_get)
        self.signal_bus.connect(AttachmentDeleteSignal,  self.attachment_handler.handle_delete)

    async def _handle_model_list(self, signal: ModelListSignal) -> list:
        models = self.llm_model_service.load_models()
        return [
            ModelDTO(
                id=m.get("id", ""),
                display_name=m.get("display_name", ""),
                provider=m.get("provider", ""),
                is_available=m.get("is_available", False),
                is_default=m.get("is_default", False),
            ).model_dump()
            for m in models
        ]
