import asyncio
from typing import AsyncGenerator, Dict, List

from core.models import BaseTool, HOChunk, ToolCallPayload, ToolMediaItem, ToolOutputPayload, ToolParameters
from utils import get_logger

logger = get_logger("ToolEngine")


class ToolEngine:
    async def _execute_one(
        self,
        call: ToolCallPayload,
        tool_map: Dict[str, BaseTool],
        params: ToolParameters | None = None,
    ) -> HOChunk | None:
        tool = tool_map.get(call.tool_name)
        if tool is None:
            logger.warning(f"Tool '{call.tool_name}' not found.")
            return HOChunk(payload=ToolOutputPayload(
                tool_name=call.tool_name,
                output=f"Error: tool '{call.tool_name}' is not available.",
                **(call.model_extra or {}),
            ))
        try:
            logger.debug(f"[ToolEngine] Executing '{call.tool_name}' args={call.tool_args}")
            runtime_kwargs = params.model_dump(exclude_none=True) if params else {}
            required_kwargs = getattr(tool, "required_kwargs", [])
            filtered_kwargs = {k: v for k, v in runtime_kwargs.items() if k in required_kwargs}
            result = await tool.execute(**call.tool_args, **filtered_kwargs)
            logger.debug(f"[ToolEngine] '{call.tool_name}' completed.")

            output_text = ""
            media_items: List[ToolMediaItem] = []

            if isinstance(result, tuple) and len(result) == 2:
                output_text, media_items = result
            elif isinstance(result, str):
                output_text = result
            else:
                output_text = str(result)

            return HOChunk(payload=ToolOutputPayload(
                tool_name=call.tool_name,
                output=output_text,
                media=media_items,
                **(call.model_extra or {}),
            ))
        except Exception as e:
            logger.error(f"[ToolEngine] '{call.tool_name}' raised an error: {e}", exc_info=True)
            return HOChunk(payload=ToolOutputPayload(
                tool_name=call.tool_name,
                output=f"Error: {e}",
                **(call.model_extra or {}),
            ))

    async def execute_tools(
        self,
        tool_calls: List[ToolCallPayload],
        tool_map: Dict[str, BaseTool],
        params: ToolParameters | None = None,
    ) -> AsyncGenerator[HOChunk, None]:
        queue: asyncio.Queue[HOChunk | None] = asyncio.Queue()

        async def run_and_enqueue(call: ToolCallPayload):
            try:
                chunk = await self._execute_one(call, tool_map, params)
                await queue.put(chunk)
            except Exception as e:
                logger.error(f"[ToolEngine] Unexpected error in run_and_enqueue for '{call.tool_name}': {e}", exc_info=True)
                await queue.put(None)

        tasks = [asyncio.create_task(run_and_enqueue(call)) for call in tool_calls]

        for _ in range(len(tool_calls)):
            chunk = await queue.get()
            if chunk is not None:
                yield chunk

        await asyncio.gather(*tasks)
