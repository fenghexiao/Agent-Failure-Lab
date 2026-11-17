#统一执行器自动化测试
from storage.repository import find_execution_events
from agent.executor import execute_tool
from app.models import ToolResult

#测试正常查询工单
#使用临时数据库，不依赖本地 agent.db 中是否恰好存在这条订单
def test_execute_get_order_success(test_database):
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
#使用临时数据库，执行器写入的事件不落到正式库
def test_execute_unknown_tool(test_database):
    result = execute_tool(
        name = "delete_order",
        args={},
        call_id="test-003"
    )
    assert result.success is False
    assert result.error == "UNKNOWN_TOOL"

#测试错误参数被拒绝
#使用临时数据库，执行器写入的事件不落到正式库
def test_execute_invalid_arguments(test_database):
    result = execute_tool(
        name ="get_order",
        args={},
        call_id="test-004"
    )

    assert result.success is False
    assert result.error == "INVALID_ARGUMENTS"

#测试工具内部异常被执行器捕获
#使用临时数据库，执行器写入的事件不落到正式库
def test_execute_tool_exception(monkeypatch, test_database):
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


# Day 16 - 验证未知工具失败时自动记录执行事件
# 失败结果和错误类型都必须写入临时 SQLite 数据库
def test_execute_tool_records_failed_event(test_database):

    # 第一步：调用一个没有注册的工具
    result = execute_tool(
        name="delete_order",
        args={},
        call_id="call-failed-001"
    )

    # 第二步：验证工具执行结果
    assert result.success is False
    assert result.error == "UNKNOWN_TOOL"

    # 第三步：查询自动生成的执行事件
    # 当前阶段暂时使用 call_id 作为 task_id
    events = find_execution_events("call-failed-001")

    # 失败的调用也必须产生一条事件
    assert len(events) == 1

    event = events[0]

    # 第四步：验证失败事件的核心字段
    assert event.event_type == "tool_result"
    assert event.task_id == "call-failed-001"
    assert event.tool_name == "delete_order"
    assert event.status == "failed"
    assert event.error_type == "UNKNOWN_TOOL"

    # 第五步：即使失败，也应该记录耗时
    assert event.latency_ms is not None
    assert event.latency_ms >= 0

    # 第六步：验证安全摘要
    assert event.details == {
        "call_id": "call-failed-001",
        "success": False
    }


# Day 16 - 验证参数校验失败时自动记录执行事件
# 即使工具没有真正执行，也应该保存失败原因
def test_execute_tool_records_invalid_arguments_event(test_database):

    # 第一步：调用已注册工具，但故意遗漏必需参数
    result = execute_tool(
        name="get_order",
        args={},
        call_id="call-invalid-001"
    )

    # 第二步：验证执行器返回参数错误
    assert result.success is False
    assert result.error == "INVALID_ARGUMENTS"

    # 第三步：查询执行器自动保存的事件
    events = find_execution_events("call-invalid-001")

    # 参数校验失败也必须产生一条事件
    assert len(events) == 1

    event = events[0]

    # 第四步：验证事件类型及失败状态
    assert event.event_type == "tool_result"
    assert event.tool_name == "get_order"
    assert event.status == "failed"
    assert event.error_type == "INVALID_ARGUMENTS"

    # 第五步：验证失败调用同样记录耗时
    assert event.latency_ms is not None
    assert event.latency_ms >= 0

    # 第六步：只记录安全摘要，不记录原始参数
    assert event.details == {
        "call_id": "call-invalid-001",
        "success": False
    }


# Day 16 - 验证工具执行异常也会自动生成失败事件
# 使用 monkeypatch 模拟工具故障，不需要真的破坏数据库
def test_execute_tool_records_exception_event(test_database, monkeypatch):

    # 第一步：定义一个始终抛出异常的模拟工具
    def broken_tool(call_id, args):
        raise RuntimeError("模拟工具内部故障")

    # 第二步：临时替换注册表中的工具查找函数
    # 只有本次测试受到影响，结束后 pytest 会自动恢复
    monkeypatch.setattr(
        "agent.executor.get_tool",
        lambda name: broken_tool
    )

    # 第三步：调用执行器，触发模拟故障
    result = execute_tool(
        name="get_order",
        args={"order_id": "ORD-001"},
        call_id="call-exception-001"
    )

    # 第四步：验证异常被统一转换为工具失败结果
    assert result.success is False
    assert result.error == "TOOL_EXECUTION_ERROR"

    # 第五步：查询执行器自动保存的事件
    events = find_execution_events("call-exception-001")

    # 工具发生异常，也必须产生一条事件
    assert len(events) == 1

    event = events[0]

    # 第六步：验证事件的失败类型
    assert event.event_type == "tool_result"
    assert event.tool_name == "get_order"
    assert event.status == "failed"
    assert event.error_type == "TOOL_EXECUTION_ERROR"

    # 第七步：验证异常发生前的耗时也被记录
    assert event.latency_ms is not None
    assert event.latency_ms >= 0

    # 第八步：事件中不保存内部异常文本或原始业务参数
    assert event.details == {
        "call_id": "call-exception-001",
        "success": False
    }


# Day 16 - 验证事件写入失败不会影响工具执行结果
# 使用 monkeypatch 模拟事件数据库故障
def test_event_write_failure_does_not_override_tool_result(
    test_database,
    monkeypatch
):

    # 第一步：定义一个模拟的事件写入故障
    def broken_event_writer(event):
        raise RuntimeError("模拟事件数据库不可用")

    # 第二步：临时替换执行器中的事件写入函数
    monkeypatch.setattr(
        "agent.executor.insert_execution_event",
        broken_event_writer
    )

    # 第三步：执行正常的订单查询
    result = execute_tool(
        name="get_order",
        args={"order_id": "ORD-001"},
        call_id="call-write-failure-001"
    )

    # 第四步：事件写入失败，但业务结果必须保持成功
    assert result.success is True
    assert result.error is None
    assert result.data["order_id"] == "ORD-001"

    # 第五步：确认失败的事件没有被保存
    events = find_execution_events("call-write-failure-001")
    assert events == []
