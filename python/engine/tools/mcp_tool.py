"""
McpClient를 BaseTool 인터페이스로 감싸는 어댑터입니다.
McpService가 MCP 서버에서 조회한 각 도구마다 인스턴스를 동적으로 생성합니다.
"""
from typing import Any, List, Tuple

from core.models import BaseTool, ToolMediaItem, ToolSchema
from mcp_infra.client import McpClient


class McpTool(BaseTool):
    """
    MCP 서버의 단일 도구를 BaseTool로 노출합니다.
    name / description / input_schema 는 서버에서 조회한 ToolSchema로 동적으로 설정됩니다.
    """

    def __init__(self, meta: ToolSchema, client: McpClient, source: str) -> None:
        self.id = f"{source}.{meta.name}"
        self.name = meta.name
        self.description = meta.description
        self._parameters = meta.parameters
        self._client = client

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self._parameters,
        )

    async def execute(self, **kwargs: Any) -> Tuple[str, List[ToolMediaItem]]:
        return await self._client.call_tool(self.name, kwargs)
