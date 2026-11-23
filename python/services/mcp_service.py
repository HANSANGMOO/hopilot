"""
MCP 서버 풀을 관리하는 서비스입니다.
startup.py의 lifespan 훅에서 initialize() / shutdown()을 호출합니다.
"""
import asyncio
from pathlib import Path
from typing import Dict, List, Optional

from core.errors import McpConfigError
from core.models import McpTemplateVars, ToolGroup
from engine.tools.mcp_tool import McpTool
from mcp_infra.client import McpClient
from mcp_infra.config import load_mcp_config
from utils import get_logger

logger = get_logger("McpService")


class McpService:
    """
    mcp.json에 정의된 서버들의 McpClient 인스턴스를 생성·보관하고
    생명주기를 관리합니다.
    initialize() 후 tool_groups 프로퍼티로 ToolGroup 목록을 노출합니다.
    """

    def __init__(self, config_path: Path, template_vars: Optional[McpTemplateVars] = None) -> None:
        self._config_path = config_path
        self._template_vars = template_vars
        self._clients: Dict[str, McpClient] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._groups: Dict[str, ToolGroup] = {}

    @property
    def tool_groups(self) -> List[ToolGroup]:
        """initialize() 이후 사용 가능한 MCP 도구 그룹 목록입니다."""
        return list(self._groups.values())

    async def initialize(self) -> None:
        """mcp.json을 읽어 서버에 연결하고 도구 목록을 메모리에 올립니다."""
        try:
            config = load_mcp_config(self._config_path, self._template_vars)
        except McpConfigError as e:
            logger.warning(f"MCP 설정 오류로 MCP 기능을 비활성화합니다: {e}")
            return

        for name, error in config.errors.items():
            logger.warning(f"[{name}] Config error: {error}")
            self._groups[name] = ToolGroup(source=f"mcp-{name}", tools=[], error=error)

        if not config.servers:
            logger.info("No MCP servers configured.")
            return

        for name, cfg in config.servers.items():
            client = McpClient(server_name=name, config=cfg)
            self._clients[name] = client
            self._tasks[name] = asyncio.create_task(client.run())

        await asyncio.gather(
            *[self._initialize_client(name) for name in self._clients],
            return_exceptions=True,
        )

        total = sum(len(g.tools) for g in self._groups.values())
        logger.info(f"McpService initialized: {len(self._clients)} server(s), {total} tool(s).")

    async def _initialize_client(self, server_name: str) -> None:
        """단일 서버의 연결 완료를 기다리고 ToolGroup을 등록합니다. 실패 시 error 그룹으로 등록합니다."""
        client = self._clients[server_name]
        task = self._tasks[server_name]
        try:
            ready_task = asyncio.create_task(client.ready.wait())
            done, _ = await asyncio.wait(
                [ready_task, task],
                timeout=60.0,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                ready_task.cancel()
                raise TimeoutError(f"Connection timed out after 60 seconds.")
            if task in done and not client.ready.is_set():
                ready_task.cancel()
                raise task.exception() or RuntimeError("run() exited unexpectedly.")
            schemas = await client.list_tools()
            group_name = f"mcp-{server_name}"
            self._groups[server_name] = ToolGroup(
                source=group_name,
                tools=[McpTool(meta=schema, client=client, source=group_name) for schema in schemas],
            )
            logger.info(f"[{server_name}] Registered {len(schemas)} tool(s).")
        except Exception as e:
            logger.warning(f"[{server_name}] Failed to connect: {e}", exc_info=True)
            self._tasks[server_name].cancel()
            group_name = f"mcp-{server_name}"
            self._groups[server_name] = ToolGroup(source=group_name, tools=[], error=str(e))

    async def shutdown(self) -> None:
        """연결된 모든 MCP 서버 Task를 취소하고 정리합니다."""
        for task in self._tasks.values():
            task.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._clients.clear()
        self._tasks.clear()
        self._groups.clear()
        logger.info("McpService shutdown complete.")
