
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class GetOrderArgs(BaseModel):
    order_id: str = Field(min_length=1)


class CreateTicketArgs(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)


class TaskRequest(BaseModel):
    task: str = Field(min_length=1, max_length=2000)


class ToolCall(BaseModel):
    call_id: str = Field(min_length=1)
    tool_name: Literal["get_order", "create_ticket"]
    arguments: GetOrderArgs | CreateTicketArgs

    @model_validator(mode="after")
    def validate_arguments_match_tool(self):
        if self.tool_name == "get_order":
            if not isinstance(self.arguments, GetOrderArgs):
                raise ValueError("get_order 必须使用 GetOrderArgs")

        elif self.tool_name == "create_ticket":
            if not isinstance(self.arguments, CreateTicketArgs):
                raise ValueError("create_ticket 必须使用 CreateTicketArgs")

        return self


class ToolResult(BaseModel):
    call_id: str = Field(min_length=1)
    tool_name: Literal["get_order", "create_ticket"]
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class ExecutionEvent(BaseModel):
    event_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    event_type: Literal[
        "task_started",
        "tool_call",
        "tool_result",
        "error",
    ]
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    details: dict[str, Any] = Field(default_factory=dict)
