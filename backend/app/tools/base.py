from abc import ABC, abstractmethod
from typing import Dict, Any, Type, Optional
from pydantic import BaseModel, Field

class ToolExecutionResult(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_category: Optional[str] = None
    duration_ms: float = 0.0

class BaseTool(ABC):
    name: str
    description: str
    schema_model: Type[BaseModel]
    requires_approval: bool = False
    permission_level: str = "read" # "read" | "write" | "admin"

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> ToolExecutionResult:
        """Execute the tool with validated arguments."""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "requires_approval": self.requires_approval,
            "permission_level": self.permission_level,
            "input_schema": self.schema_model.model_json_schema()
        }

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, BaseTool]:
        return dict(self._tools)

    def get_tool_metadata_list(self):
        return [tool.get_metadata() for tool in self._tools.values()]

# Global registry
registry = ToolRegistry()
