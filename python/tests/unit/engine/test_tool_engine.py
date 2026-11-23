import asyncio
import time
import pytest
from pathlib import Path
from pydantic import BaseModel

from core.models import BaseTool, HOChunk, ToolCallPayload, ToolOutputPayload, ToolParameters, ToolSchema
from engine.tool_engine import ToolEngine


# ── Fakes ─────────────────────────────────────────────────────────────────────

class _ArgsSchema(BaseModel):
    x: int


class _FakeTool(BaseTool):
    id = "fake_tool"
    name = "fake_tool"
    description = "fake"
    input_schema = _ArgsSchema

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(name=self.name, description=self.description, parameters=self.input_schema.model_json_schema())

    async def execute(self, **kwargs) -> str:
        return "tool_result"


class _FakeToolWithKwargs(BaseTool):
    id = "fake_tool_with_kwargs"
    name = "fake_tool_with_kwargs"
    description = "fake"
    input_schema = _ArgsSchema
    required_kwargs = ["kg_jsonl_path"]

    def __init__(self):
        self.received_kwargs = {}

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(name=self.name, description=self.description, parameters=self.input_schema.model_json_schema())

    async def execute(self, **kwargs) -> str:
        self.received_kwargs = kwargs
        return "tool_result"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    return ToolEngine()


# ── Tests ─────────────────────────────────────────────────────────────────────

class DescribeToolEngine:
    class DescribeExecuteTools:
        @pytest.mark.anyio(backend="asyncio")
        async def it_executes_a_single_tool_call(self, engine):
            tool = _FakeTool()
            call = ToolCallPayload(tool_name="fake_tool", tool_args={"x": 1})

            chunks = [c async for c in engine.execute_tools([call], {tool.name: tool})]

            assert len(chunks) == 1
            assert isinstance(chunks[0].payload, ToolOutputPayload)
            assert chunks[0].payload.tool_name == "fake_tool"
            assert chunks[0].payload.output == "tool_result"

        @pytest.mark.anyio(backend="asyncio")
        async def it_executes_a_single_tool_call_with_kwargs(self, engine):
            tool = _FakeToolWithKwargs()
            call = ToolCallPayload(tool_name="fake_tool_with_kwargs", tool_args={"x": 1})
            params = ToolParameters(kg_jsonl_path=Path("/some/path.jsonl"))

            chunks = [c async for c in engine.execute_tools([call], {tool.name: tool}, params)]

            assert len(chunks) == 1
            assert tool.received_kwargs["kg_jsonl_path"] == Path("/some/path.jsonl")

        @pytest.mark.anyio(backend="asyncio")
        async def it_executes_multiple_tool_calls(self, engine):
            tools = [_FakeTool() for _ in range(3)]
            tool_map = {t.name: t for t in tools}
            calls = [ToolCallPayload(tool_name="fake_tool", tool_args={"x": i}) for i in range(3)]

            chunks = [c async for c in engine.execute_tools(calls, tool_map)]

            assert len(chunks) == 3
            assert all(isinstance(c.payload, ToolOutputPayload) for c in chunks)
            assert all(c.payload.output == "tool_result" for c in chunks)

        @pytest.mark.anyio(backend="asyncio")
        async def it_executes_parallel_tool_calls_concurrently(self, engine):
            class _SlowTool(BaseTool):
                id = "slow_tool"
                name = "slow_tool"
                description = "slow"
                input_schema = _ArgsSchema

                def get_tool_schema(self) -> ToolSchema:
                    return ToolSchema(name=self.name, description=self.description, parameters=self.input_schema.model_json_schema())

                async def execute(self, **kwargs) -> str:
                    await asyncio.sleep(0.1)
                    return "done"

            tool = _SlowTool()
            calls = [ToolCallPayload(tool_name="slow_tool", tool_args={"x": i}) for i in range(3)]

            start = time.monotonic()
            chunks = [c async for c in engine.execute_tools(calls, {tool.name: tool})]
            elapsed = time.monotonic() - start

            assert len(chunks) == 3
            assert elapsed < 0.25

        @pytest.mark.anyio(backend="asyncio")
        async def it_returns_error_output_when_tool_raises(self, engine):
            class _ErrorTool(BaseTool):
                id = "error_tool"
                name = "error_tool"
                description = "error"
                input_schema = _ArgsSchema

                def get_tool_schema(self) -> ToolSchema:
                    return ToolSchema(name=self.name, description=self.description, parameters=self.input_schema.model_json_schema())

                async def execute(self, **kwargs) -> str:
                    raise ValueError("something went wrong")

            tool = _ErrorTool()
            call = ToolCallPayload(tool_name="error_tool", tool_args={"x": 1})

            chunks = [c async for c in engine.execute_tools([call], {tool.name: tool})]

            assert len(chunks) == 1
            assert isinstance(chunks[0].payload, ToolOutputPayload)
            assert "something went wrong" in chunks[0].payload.output

        @pytest.mark.anyio(backend="asyncio")
        async def it_returns_error_output_when_tool_not_found(self, engine):
            call = ToolCallPayload(tool_name="nonexistent_tool", tool_args={})

            chunks = [c async for c in engine.execute_tools([call], {})]

            assert len(chunks) == 1
            assert isinstance(chunks[0].payload, ToolOutputPayload)
            assert "nonexistent_tool" in chunks[0].payload.output

        @pytest.mark.anyio(backend="asyncio")
        async def it_executes_tool_that_uses_injected_dependency(self, engine):
            class _FakeService:
                def __init__(self):
                    self.called = False

                def fetch(self) -> str:
                    self.called = True
                    return "service_result"

            class _DependentTool(BaseTool):
                id = "dependent_tool"
                name = "dependent_tool"
                description = "uses injected service"
                input_schema = _ArgsSchema
                dependencies = [_FakeService]

                def __init__(self, service: _FakeService):
                    self._service = service

                def get_tool_schema(self) -> ToolSchema:
                    return ToolSchema(name=self.name, description=self.description, parameters=self.input_schema.model_json_schema())

                async def execute(self, **kwargs) -> str:
                    return self._service.fetch()

            service = _FakeService()
            tool = _DependentTool(service=service)
            call = ToolCallPayload(tool_name="dependent_tool", tool_args={"x": 1})

            chunks = [c async for c in engine.execute_tools([call], {tool.name: tool})]

            assert len(chunks) == 1
            assert chunks[0].payload.output == "service_result"
            assert service.called
