import pytest
from pydantic import ValidationError

from app.models import(
    TaskRequest,
    ToolCall,
    ToolResult,
    ExecutionEvent,
    GetOrderArgs,
    CreateTicketArgs,
)

def test_task_request_valid():
    request = TaskRequest(task="查询订单 ORD-001")
    assert request.task == "查询订单 ORD-001"

def test_task_request_rejects_empty_task():
    with pytest.raises(ValidationError):
        TaskRequest(task="")

def test_get_order_tool_call_valid():
    call = ToolCall(
        call_id="call-001",
        tool_name="get_order",
        arguments=GetOrderArgs(order_id="ORD-001"))
    assert call.tool_name == "get_order"
    assert isinstance(call.arguments, GetOrderArgs)

def test_create_ticket_tool_call_valid():
    call = ToolCall(
        call_id="call-002",
        tool_name="create_ticket",
        arguments=CreateTicketArgs(title="订单异常", description="订单状态未更新"))
    assert call.tool_name == "create_ticket"
    assert isinstance(call.arguments, CreateTicketArgs)

def test_tool_call_invalid_arguments():
    with pytest.raises(ValidationError):
        ToolCall(
            call_id="call-003",
            tool_name="get_order",
            arguments=CreateTicketArgs(title="订单异常", description="订单状态未更新"))

def test_tool_call_rejects_unknown_tool():
    with pytest.raises(ValidationError):
        ToolCall(
            call_id="call-004",
            tool_name="unknown_tool",
            arguments=GetOrderArgs(order_id="ORD-001"))

def test_tool_result_valid():
    result = ToolResult(
        call_id="call-001",
        tool_name="get_order",
        success=True,
        data={"order_id": "ORD-001", "status": "paid"})
    assert result.success is True
    assert result.data["status"] == "paid"

def test_execution_event_valid():
    event = ExecutionEvent(
        event_id="event-001",
        task_id="task-001",
        event_type="task_started",
        details={"task": "查询订单 ORD-001"})
    assert event.event_id == "event-001"
    assert event.event_type == "task_started"
    assert event.timestamp.tzinfo is not None

def test_execution_event_details_are_independent():
    event1 = ExecutionEvent(
        event_id="event-001",
        task_id="task-001",
        event_type="task_started",
    )
    event2 = ExecutionEvent(
        event_id="event-002",
        task_id="task-001",
        event_type="tool_call",
    )

    event1.details["tool"] = "get_order"

    assert event2.details == {}
  
