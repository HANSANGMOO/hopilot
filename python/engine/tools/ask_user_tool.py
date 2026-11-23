from typing import Optional

from pydantic import BaseModel, Field

from contracts.ask_user import AskUserSignal
from core.bus.signal_bus import SignalBus
from core.models import BaseTool, ToolSchema


class AskUserArgs(BaseModel):
    question: str = Field(
        ...,
        description="The question to present to the user."
    )
    choices: Optional[str] = Field(
        None,
        description=(
            "Optional multiple-choice options, one option per line (separated by newlines). "
            "Provide this when the answer should be one of a fixed set of options. "
            "Example: 'Chocolate\\nVanilla\\nStrawberry'. Omit for open-ended questions."
        )
    )
    placeholder: Optional[str] = Field(
        None,
        description="Optional placeholder text shown in the free-text input field."
    )


class AskUserTool(BaseTool):
    id = "ask_user"
    name = "ask_user"
    description = (
        "Ask the user a question and wait for their response. "
        "Supports two modes:\n"
        "- Multiple choice: provide 'choices' with one option per line — the user picks one.\n"
        "- Open-ended: omit 'choices' — the user types a free-form answer.\n"
        "Use this when you need clarification, a decision, or information that only the user can provide. "
        "Always prefer this over making assumptions."
    )
    input_schema = AskUserArgs
    dependencies = [SignalBus]

    def __init__(self, signal_bus: SignalBus) -> None:
        self._signal_bus = signal_bus

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.input_schema.model_json_schema(),
        )

    async def execute(
        self,
        question: str,
        choices: Optional[str] = None,
        placeholder: Optional[str] = None,
    ) -> str:
        choices_list = [c.strip() for c in choices.splitlines() if c.strip()] if choices else None
        signal = AskUserSignal(params={
            "question": question,
            "choices": choices_list,
            "placeholder": placeholder,
        })
        result = await self._signal_bus.invoke(signal)
        return result.get("answer", "") if isinstance(result, dict) else str(result)
