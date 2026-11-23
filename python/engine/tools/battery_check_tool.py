from pydantic import BaseModel, Field

from core.models import BaseTool, ToolSchema


class BatteryCheckArgs(BaseModel):
    battery: str = Field(..., description="The battery identifier or serial number to evaluate.")


class BatteryCheckTool(BaseTool):
    id = "battery_check"
    name = "battery_check"
    description = "Evaluates the condition of a battery and returns a diagnostic result."
    input_schema = BatteryCheckArgs

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.input_schema.model_json_schema(),
        )

    async def execute(self, battery: str) -> str:
        return f"배터리 '{battery}' 진단 결과: 정상입니다."
