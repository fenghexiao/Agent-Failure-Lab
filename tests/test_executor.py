#统一执行器自动化测试
from storage.repository import find_execution_events
from agent.executor import execute_tool
from app.models import ToolResult

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
# 使用临时数据库，避免影响正式项目数据
def test_execute_creat_ticket_success(test_database):

    # 第一步：通过统一执行器调用创建工单工具
    result = execute_tool(
        name="create_ticket",
        args={
            "title": "订单异常",
            "description": "物流未更新"
        },
        call_id="call-001"
    )

    # 第二步：验证执行器正确返回工具结果
    assert result.success is True
    assert result.call_id == "call-001"
    assert result.tool_name == "create_ticket"
    assert result.data["ticket_id"] == "TICKET-001"
    assert result.data["title"] == "订单异常"
    assert result.data["status"] == "open"

    # 第三步：验证执行器调用后的数据库持久化结果
    from storage.database import get_connection

    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT ticket_id, title, status
            FROM tickets
            WHERE ticket_id = ?
            """,
            (result.data["ticket_id"],)
        ).fetchone()

        assert row is not None
        assert row["title"] == "订单异常"
        assert row["status"] == "open"

    finally:
        # 无论测试是否成功，都关闭数据库连接
        conn.close()


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


# Day 16 - 验证执行器自动记录成功事件
# 使用临时 SQLite 数据库，不影响正式数据
def test_execute_tool_records_success_event(test_database):

    # 第一步：通过执行器查询已有订单
    result = execute_tool(
        name="get_order",
        args={"order_id": "ORD-001"},
        call_id="call-event-001"
    )

    # 第二步：确认工具本身执行成功
    assert result.success is True

    # 第三步：查询执行器自动写入的事件
    # 当前阶段暂时使用 call_id 作为 task_id
    events = find_execution_events("call-event-001")

    # 一次工具执行应该产生一条结果事件
    assert len(events) == 1

    event = events[0]

    # 第四步：验证事件的核心字段
    assert event.event_type == "tool_result"
    assert event.task_id == "call-event-001"
    assert event.tool_name == "get_order"
    assert event.status == "success"
    assert event.error_type is None

    # 第五步：验证耗时是实际计算的非负数
    assert event.latency_ms is not None
    assert event.latency_ms >= 0

    # 第六步：验证事件只保存安全摘要
    assert event.details == {
        "call_id": "call-event-001",
        "success": True
    }

    # 不允许原始工具参数或业务结果进入事件详情
    assert "order_id" not in event.details
    assert "amount" not in event.details


