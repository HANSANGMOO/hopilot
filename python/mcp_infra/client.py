"""
개별 MCP 서버와의 연결을 관리하는 클라이언트입니다.
mcp 라이브러리의 ClientSession을 transport 종류(stdio / sse)에 따라 초기화합니다.
"""
import asyncio
from typing import Any, Dict, List, Tuple

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters, stdio_client

from core.models import ToolMediaItem, ToolSchema
from mcp_infra.config import McpServerConfig, SseServerConfig, StdioServerConfig
from utils import get_logger

logger = get_logger("McpClient")


class McpClient:
    """
    MCP 서버 1개에 대응하는 클라이언트입니다.
    McpService가 run()을 Task로 실행하고, ready 이벤트로 연결 완료를 감지합니다.
    """

    def __init__(self, server_name: str, config: McpServerConfig) -> None:
        self.server_name = server_name
        self._config = config
        self._session: ClientSession | None = None
        self.ready = asyncio.Event()

    async def run(self) -> None:
        """transport 연결을 수립하고 Task가 취소될 때까지 세션을 유지합니다."""
        try:
            if isinstance(self._config, StdioServerConfig):
                await self._run_stdio()
            elif isinstance(self._config, SseServerConfig):
                await self._run_sse()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"[{self.server_name}] run() failed: {e}", exc_info=True)
            raise

    async def _run_stdio(self) -> None:
        cfg: StdioServerConfig = self._config
        params = StdioServerParameters(command=cfg.command, args=cfg.args, env=cfg.env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                self._session = session
                await session.initialize()
                logger.info(f"[{self.server_name}] Connected.")
                self.ready.set()
                await asyncio.Future()

    async def _run_sse(self) -> None:
        cfg: SseServerConfig = self._config
        async with sse_client(cfg.url) as (read, write):
            async with ClientSession(read, write) as session:
                self._session = session
                await session.initialize()
                logger.info(f"[{self.server_name}] Connected.")
                self.ready.set()
                await asyncio.Future()

    async def list_tools(self) -> List[ToolSchema]:
        """서버가 노출하는 도구 목록을 ToolSchema 리스트로 반환합니다."""
        result = await self._session.list_tools()
        return [
            ToolSchema(
                name=tool.name,
                description=tool.description or "",
                parameters=tool.inputSchema,
            )
            for tool in result.tools
        ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[str, List[ToolMediaItem]]:
        """도구를 호출하고 (텍스트_결과, 미디어_리스트) 튜플을 반환합니다. 300초 초과 시 TimeoutError를 발생시킵니다."""
        try:
            result = await asyncio.wait_for(
                self._session.call_tool(tool_name, arguments),
                timeout=300.0,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"[{self.server_name}] Tool '{tool_name}' timed out after 300 seconds.")
        if result.isError:
            raise RuntimeError(f"[{self.server_name}] Tool '{tool_name}' returned an error: {result.content}")
        return self._parse_content_blocks(result.content)

    @staticmethod
    def _parse_content_blocks(content: List[Any]) -> Tuple[str, List[ToolMediaItem]]:
        """MCP CallToolResult의 content 블록들을 텍스트와 ToolMediaItem 리스트로 분기 파싱합니다."""
        texts: List[str] = []
        media: List[ToolMediaItem] = []

        for block in content:
            if hasattr(block, "text"):
                texts.append(block.text)
            elif hasattr(block, "data"):
                mime_type = getattr(block, "mimeType", None) or "application/octet-stream"
                media_type = "image" if mime_type.startswith("image/") else "audio"
                media.append(ToolMediaItem(
                    type=media_type,
                    data=block.data,
                    mime_type=mime_type,
                ))
            elif hasattr(block, "resource"):
                res = block.resource
                if hasattr(res, "blob"):
                    mime_type = getattr(res, "mimeType", None)
                    uri = str(getattr(res, "uri", "")) or None
                    media.append(ToolMediaItem(
                        type="resource",
                        data=res.blob,
                        mime_type=mime_type,
                        uri=uri,
                    ))
                elif hasattr(res, "text"):
                    texts.append(res.text)

        
        return "\n".join(texts), media