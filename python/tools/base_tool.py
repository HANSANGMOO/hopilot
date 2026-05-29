from pydantic import BaseModel
from typing import Type, Any, Dict
from abc import ABC, abstractmethod

class BaseTool(ABC):
    """
    Abstract base class for all tools that the Copilot can use.
    Provides automatic JSON schema generation from Pydantic models.
    """
    name: str
    description: str
    args_schema: Type[BaseModel]

    def get_tool_schema(self) -> Dict[str, Any]:
        """
        Automatically generates the tool schema for LLM function calling
        using Pydantic's JSON schema serialization (v2).
        """
        schema = self.args_schema.model_json_schema()
        return {
            "name": self.name,
            "description": self.description,
            "parameters": schema
        }

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Executes the tool logic with the provided arguments.
        """
        pass
