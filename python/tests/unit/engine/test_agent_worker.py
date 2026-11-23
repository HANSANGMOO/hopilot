"""
Unit tests for AgentWorker.run() — ReAct loop message sequencing.

Test scenario: 3-turn ReAct loop
  Turn 1: AI responds with ToolCall-1  → tool executes → ToolOutput-1
  Turn 2: AI responds with ToolCall-2  → tool executes → ToolOutput-2
  Turn 3: AI responds with ToolCall-3  → tool executes → ToolOutput-3
  (loop continues until a plain-text AI response with no tool calls)

Expected react.messages after the loop:
  [0] user          — initial query
  [1] ai            — ToolCall-1
  [2] user          — ToolOutput-1
  [3] ai            — ToolCall-2
  [4] user          — ToolOutput-2
  [5] ai            — ToolCall-3
  [6] user          — ToolOutput-3
"""
import pytest
import anyio
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncGenerator

from core.models import (
    AgentCallbacks,
    BaseTool,
    CopilotTask,
    HOChunk,
    HOMessage,
    HOreAct,
    HopilotPayload,
    TextPayload,
    ToolCallPayload,
    ToolInfo,
    ToolOutputPayload,
    ToolSchema,
)
from core.bus import EventBus
from engine.agent_worker import AgentWorker
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tool_call_chunk(tool_name: str) -> HOChunk:
    return HOChunk(payload=ToolCallPayload(tool_name=tool_name, tool_args={"x": 1}))


def _text_chunk(text: str = "done") -> HOChunk:
    return HOChunk(payload=TextPayload(text=text))


async def _chunks_gen(*chunks: HOChunk) -> AsyncGenerator[HOChunk, None]:
    for c in chunks:
        yield c


class _FakeArgsSchema(BaseModel):
    x: int


class _FakeTool(BaseTool):
    name = "fake_tool"
    description = "fake"
    input_schema = _FakeArgsSchema

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.input_schema.model_json_schema(),
        )

    async def execute(self, **kwargs) -> str:
        return "tool_result"


def _make_task(tool: BaseTool) -> CopilotTask:
    react = HOreAct()
    user_msg = HOMessage(role="user", chunks=[_text_chunk("hello")], react_id=react.react_id)
    ai_placeholder = HOMessage(role="ai", react_id=react.react_id)
    react.add_message(user_msg)
    react.add_message(ai_placeholder)

    return CopilotTask(
        session_id="sess_test",
        memory=[],
        tools=[tool],
        react=react,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio(backend="asyncio")
async def test_react_loop_three_turns_message_sequence():
    # --- Arrange ---
    tool = _FakeTool()
    task = _make_task(tool)
    react = task.react

    # stream_opener yields tool call chunks for turns 1-3, then plain text on turn 4
    call_count = 0

    async def fake_stream_opener(payload) -> AsyncGenerator[HOChunk, None]:
        nonlocal call_count
        call_count += 1
        if call_count <= 3:
            async for c in _chunks_gen(_tool_call_chunk("fake_tool")):
                yield c
        else:
            async for c in _chunks_gen(_text_chunk("final answer")):
                yield c

    fake_payload = HopilotPayload(
        system_instructions="test",
        memory=[],
        query=react.messages,
    )
    callbacks = AgentCallbacks(
        payload_builder=AsyncMock(return_value=fake_payload),
        stream_opener=fake_stream_opener,
    )

    worker = AgentWorker(event_bus=MagicMock(spec=EventBus))

    # --- Act ---
    async for _ in worker.run(task=task, callbacks=callbacks):
        pass

    # --- Assert ---
    msgs = react.messages
    assert len(msgs) == 8, f"Expected 8 messages, got {len(msgs)}: {[m.role for m in msgs]}"

    # [0] user query
    assert msgs[0].role == "user"

    # [1] ai with ToolCall-1
    assert msgs[1].role == "ai"
    assert any(isinstance(c.payload, ToolCallPayload) for c in msgs[1].chunks)

    # [2] user with ToolOutput-1
    assert msgs[2].role == "user"
    assert any(isinstance(c.payload, ToolOutputPayload) for c in msgs[2].chunks)

    # [3] ai with ToolCall-2
    assert msgs[3].role == "ai"
    assert any(isinstance(c.payload, ToolCallPayload) for c in msgs[3].chunks)

    # [4] user with ToolOutput-2
    assert msgs[4].role == "user"
    assert any(isinstance(c.payload, ToolOutputPayload) for c in msgs[4].chunks)

    # [5] ai with ToolCall-3
    assert msgs[5].role == "ai"
    assert any(isinstance(c.payload, ToolCallPayload) for c in msgs[5].chunks)

    # [6] user with ToolOutput-3
    assert msgs[6].role == "user"
    assert any(isinstance(c.payload, ToolOutputPayload) for c in msgs[6].chunks)

    # [7] final ai — plain text, no tool calls
    assert msgs[7].role == "ai"
    assert not any(isinstance(c.payload, ToolCallPayload) for c in msgs[7].chunks)
    assert any(isinstance(c.payload, TextPayload) for c in msgs[7].chunks)
