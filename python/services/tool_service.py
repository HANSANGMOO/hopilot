import inspect
from functools import partial
from typing import Dict, List, Optional, Type

from core.di import ToolDependency
from core.models import BaseTool, ToolDTO, ToolGroup, ToolParameters
from engine.tool_engine import ToolEngine
from engine.tools.ask_user_tool import AskUserTool
from engine.tools.context_tool import (
    AddObservationsTool,
    CreateEntitiesTool,
    CreateRelationsTool,
    DeleteEntitiesTool,
    DeleteObservationsTool,
    DeleteRelationsTool,
    OpenNodesTool,
    ReadGraphTool,
    SearchNodesTool,
)
from engine.tools.python_execution_tool import PythonExecutionTool
from engine.tools.text_vm_tool import TextVMTool
from utils import get_logger

logger = get_logger("ToolService")

_BUILTIN_BASIC = "basic"
_BUILTIN_CONTEXT = "context"


class ToolService:
    """
    사용 가능한 도구 목록을 관리하고, 활성화된 도구의 BaseTool 리스트를 제공합니다.
    """

    def __init__(self, tool_engine: ToolEngine):
        self.tool_engine = tool_engine
        self._groups: Dict[str, ToolGroup] = {}
        self._deps: Optional[ToolDependency] = None

    def initialize(self, deps: ToolDependency, groups: List[ToolGroup]) -> None:
        """의존성 컨테이너와 추가 도구 그룹(MCP 등)을 등록합니다."""
        self._deps = deps
        self._register_defaults()
        self._register_mcp(groups)

    def list_tools(self) -> List[dict]:
        """등록된 모든 도구 그룹의 DTO 목록을 반환합니다."""
        from contracts.tool import ToolGroupDTO, ToolItemDTO
        return [
            ToolGroupDTO(
                source=group.source,
                tools=[ToolItemDTO(id=t.id, name=t.name, description=t.description) for t in group.tools],
                error=group.error,
            ).model_dump()
            for group in self._groups.values()
        ]

    def resolve(self, tool_ids: List[str], params: Optional[ToolParameters] = None) -> Optional[ToolDTO]:
        """활성화할 tool_id 목록을 받아 ToolDTO를 반환합니다. 빈 목록이면 None을 반환합니다."""
        registry = self._flat_registry()
        tools = [registry[tool_id] for tool_id in tool_ids if tool_id in registry]
        if not tools:
            return None
        partial_execute = partial(self.tool_engine.execute_tools, params=params)
        return ToolDTO(tools=tools, execute_tools=partial_execute)

    def _register_defaults(self) -> None:
        self._groups[_BUILTIN_BASIC] = ToolGroup(
            source=_BUILTIN_BASIC,
            tools=[
                self._instantiate(PythonExecutionTool),
                self._instantiate(AskUserTool),
                self._instantiate(TextVMTool),
            ],
        )
        self._groups[_BUILTIN_CONTEXT] = ToolGroup(
            source=_BUILTIN_CONTEXT,
            tools=[
                self._instantiate(ReadGraphTool),
                self._instantiate(CreateEntitiesTool),
                self._instantiate(DeleteEntitiesTool),
                self._instantiate(AddObservationsTool),
                self._instantiate(DeleteObservationsTool),
                self._instantiate(SearchNodesTool),
                self._instantiate(OpenNodesTool),
                self._instantiate(CreateRelationsTool),
                self._instantiate(DeleteRelationsTool),
            ],
        )

    def _register_mcp(self, groups: List[ToolGroup]) -> None:
        for group in groups:
            if group.source in self._groups:
                logger.error(
                    f"Tool group source collision: '{group.source}' is already registered. Skipping."
                )
                continue
            self._groups[group.source] = group
        total = sum(len(g.tools) for g in groups)
        logger.info(f"ToolService initialized: {len(groups)} external group(s), {total} external tool(s).")

    def _flat_registry(self) -> Dict[str, BaseTool]:
        """모든 그룹을 flatten한 tool_id → BaseTool 맵을 반환합니다."""
        registry: Dict[str, BaseTool] = {}
        for group in self._groups.values():
            for tool in group.tools:
                if tool.id in registry:
                    logger.error(
                        f"Tool ID collision: '{tool.id}' is already registered "
                        f"(existing: {type(registry[tool.id]).__name__}, "
                        f"incoming: {type(tool).__name__}). Keeping existing."
                    )
                    continue
                registry[tool.id] = tool
        return registry

    def _instantiate(self, tool_cls: Type[BaseTool]) -> BaseTool:
        """dependencies 선언을 보고 컨테이너에서 resolve해 인스턴스를 생성합니다."""
        dep_types = getattr(tool_cls, "dependencies", [])
        if not dep_types:
            return tool_cls()
        sig = inspect.signature(tool_cls.__init__)
        kwargs = {}
        for dep_type in dep_types:
            instance = self._deps.get(dep_type) if self._deps else None
            if instance is None:
                raise RuntimeError(
                    f"Cannot instantiate {tool_cls.__name__}: "
                    f"dependency '{dep_type.__name__}' is not registered."
                )
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                if param.annotation is dep_type:
                    kwargs[param_name] = instance
                    break
        return tool_cls(**kwargs)
