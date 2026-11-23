import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.api_manager import ApiManager
from config import CONTEXT_DIR, DB_DIR, DB_FILE_PATH, DYNAMIC_CONTEXT_PATH, IMAGE_DIR, LOG_DIR, MCP_CONFIG_FILE_PATH, MCP_TEMPLATE_VARS, STATIC_CONTEXT_PATH, USER_ENV_DIR
from controller.app_controller import AppController
from core.bus import EventBus, SignalBus
from core.models import ContextPaths
from io_.db_manager import DBManager
from io_.knowledge_graph_manager import KnowledgeGraphManager
from engine.agent_worker import AgentWorker
from engine.payload_engine import PayloadEngine
from engine.tool_engine import ToolEngine
from server.fastapi_server import FastAPIServer
from services.attachment_service import AttachmentService
from services.context_service import ContextService
from services.copilot_service import CopilotService
from services.llm_model_service import LlmModelService
from services.mcp_service import McpService
from services.project_service import ProjectService
from services.session_service import SessionService
from services.tool_service import ToolService
from utils import setup_logger


def startup() -> FastAPI:
    for directory in [LOG_DIR, USER_ENV_DIR, IMAGE_DIR, DB_DIR, CONTEXT_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    logger = setup_logger(level=logging.DEBUG)
    logger.info("Hopilot Backend Bootstrapping Started...")

    event_bus: EventBus = EventBus()
    signal_bus: SignalBus = SignalBus()

    db_manager: DBManager = DBManager(db_path=DB_FILE_PATH)
    session_service: SessionService = SessionService(db_manager)
    project_service: ProjectService = ProjectService(db_manager)
    api_manager: ApiManager = ApiManager()
    llm_model_service: LlmModelService = LlmModelService(api_manager=api_manager)
    payload_engine: PayloadEngine = PayloadEngine()
    agent_worker: AgentWorker = AgentWorker(event_bus=event_bus)

    copilot_service: CopilotService = CopilotService(
        event_bus=event_bus,
        api_manager=api_manager,
        payload_engine=payload_engine,
        agent_worker=agent_worker,
    )
    tool_engine: ToolEngine = ToolEngine()
    attachment_service: AttachmentService = AttachmentService()
    kg_manager: KnowledgeGraphManager = KnowledgeGraphManager()
    default_context = ContextPaths(static=STATIC_CONTEXT_PATH, dynamic=DYNAMIC_CONTEXT_PATH)
    context_service: ContextService = ContextService(default=default_context)
    mcp_service: McpService = McpService(config_path=MCP_CONFIG_FILE_PATH, template_vars=MCP_TEMPLATE_VARS)
    tool_service: ToolService = ToolService(tool_engine=tool_engine)

    app_controller = AppController(
        event_bus=event_bus,
        signal_bus=signal_bus,
        copilot_service=copilot_service,
        session_service=session_service,
        project_service=project_service,
        llm_model_service=llm_model_service,
        attachment_service=attachment_service,
        context_service=context_service,
        tool_service=tool_service,
        mcp_service=mcp_service,
        kg_manager=kg_manager,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Lifespan 훅 실행: 초기화 시작")
        await db_manager.initialize()
        await kg_manager.initialize()
        await api_manager.initialize()
        await app_controller.initialize()
        yield
        logger.info("Lifespan 훅 종료: 셧다운 시작")
        await app_controller.shutdown()
        await api_manager.shutdown()
        await signal_bus.shutdown()
        await event_bus.shutdown()
        await kg_manager.shutdown()
        await db_manager.shutdown()

    fastapi_server: FastAPIServer = FastAPIServer(
        event_bus=event_bus, signal_bus=signal_bus, lifespan=lifespan
    )

    return fastapi_server.app
