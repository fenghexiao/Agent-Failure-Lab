#统一执行器自动化测试
from agent.executor import execute_tool
from app.models import ToolResult
from tools import tickets

#测试正常查询工单
def test_execute_get_order_success():
    result = execute_tool(
        name="get_order",
        args={"order_id":"ORD-001"},
        call_id="test-001"
    )

    assert result.success is True
    assert result.data["order_id"]=="ORD-001"

#测试正常创建工单
def test_execute_creat_ticket_success(monkeypatch):
    #使用独立列表
    monkeypatch.setattr(tickets,"TICKETS",[])

    result = execute_tool(
        name="create_ticket",
        args={
            "title":"测试工单",
            "description":"这是一个自动化测试"
        },
        call_id="test-002"
    )
    assert result.success is True
    assert result.data["title"]=="测试工单"

#测试未知工具必须被拒绝
def test_execute_unknown_tool():
    result = execute_tool(
        name = "delete_order",
        args={},
        call_id="test-003"
    )
    assert result.success is False
    assert result.error == "UNKNOWN_TOOL"

#测试错误参数被拒绝
def test_execute_invalid_arguments():
    result = execute_tool(
        name ="get_order",
        args={},
        call_id="test-004"
    )

    assert result.success is False
    assert result.error == "INVALID_ARGUMENTS"

#测试工具内部异常被执行器捕获
def test_execute_tool_exception(monkeypatch):
    #创建一个故意失败的工具
    def broken_tool(call_id,args):
        raise RuntimeError("模拟工具运行异常")
    #临时替换注册表
    monkeypatch.setattr(
        "agent.executor.get_tool",
        lambda name:broken_tool
    )

    result = execute_tool(
        name="get_order",
        args={"order_id":"ORD-001"},
        call_id="test-005"
    )
    assert isinstance(result,ToolResult)
    assert result.success is False
    assert result.error == "TOOL_EXECUTION_ERROR"

    

