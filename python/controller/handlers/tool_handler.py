from contracts.tool import ToolListSignal
from core.di import ToolDependency
from services.mcp_service import McpService
from services.tool_service import ToolService
from utils import get_logger

logger = get_logger("ToolHandler")


class ToolHandler:
    def __init__(self, tool_service: ToolService, mcp_service: McpService):
        self.tool_service = tool_service
        self.mcp_service = mcp_service

    async def initialize(self, deps: ToolDependency) -> None:
        """MCP 서버에 연결하고 도구 목록을 ToolService에 등록합니다."""
        await self.mcp_service.initialize()
        self.tool_service.initialize(deps=deps, groups=self.mcp_service.tool_groups)

    async def shutdown(self) -> None:
        """MCP 서버 연결을 정리합니다."""
        await self.mcp_service.shutdown()

    async def handle_list(self, signal: ToolListSignal) -> list:
        return self.tool_service.list_tools()
