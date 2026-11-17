# Repository 自动化测试
# 使用 pytest 临时数据库隔离测试数据
from datetime import datetime, timezone

from storage.repository import find_execution_events
import json

from app.models import ExecutionEvent
from storage.repository import insert_execution_event
import sqlite3
import pytest

from storage import database
# 导入需要测试的 Repository 函数
from storage.repository import (
    find_order,
    insert_ticket,
    create_ticket_record,)

# 测试：可以从临时 SQLite 数据库查询订单
def test_find_order_success(tmp_path, monkeypatch):

    # 第一步：创建临时数据库文件路径
    test_db = tmp_path / "test.db"

    # 第二步：临时替换 database 模块中的数据库路径
    # 测试结束后 monkeypatch 会自动恢复原来的值
    monkeypatch.setattr(database, "DB_PATH", test_db)

    # 第三步：初始化临时数据库表结构
    database.init_db()

    # 第四步：准备虚构订单数据
    conn = database.get_connection()

    try:
        conn.execute(
            """
            INSERT INTO orders (order_id, amount, status)
            VALUES (?, ?, ?)
            """,
            ("ORD-001", 199, "paid")
        )

        # 提交测试数据
        conn.commit()

    finally:
        # 保证数据库连接被关闭
        conn.close()

    # 第五步：调用真正的 Repository 函数
    result = find_order("ORD-001")

    # 第六步：验证查询结果
    assert result is not None
    assert result["order_id"] == "ORD-001"
    assert result["amount"] == 199
    assert result["status"] == "paid"

    # 测试：订单不存在时，Repository 应返回 None
# 使用独立临时数据库，避免依赖正式项目数据
def test_find_order_not_found(tmp_path, monkeypatch):

    # 第一步：创建本次测试专用的数据库路径
    test_db = tmp_path / "test_not_found.db"

    # 第二步：将数据库路径临时指向测试文件
    monkeypatch.setattr(database, "DB_PATH", test_db)

    # 第三步：初始化数据库表结构
    database.init_db()

    # 第四步：查询不存在的订单
    result = find_order("ORD-999")

    # 第五步：验证不存在的订单返回 None
    assert result is None

#测试创建工单
def test_insert_ticket_success(tmp_path,monkeypatch):
        test_db = tmp_path/"test_ticket.db"
        monkeypatch.setattr(database,"DB_PATH",test_db)

        database.init_db()
        #调用repository创建工单
        result = insert_ticket(
            ticket_id="TICKET-001",
            title="订单异常",
            description="物流未更新"
        )
        assert result["ticket_id"]=="TICKET-001"
        assert result["status"] =="open"

        conn = database.get_connection()

        try:
        #查询刚创建的工具
            cursor = conn.execute(
                """
                SELECT ticket_id,title,description,status
                FROM tickets
                WHERE ticket_id = ?
                """,
            ("TICKET-001",)
            )
            row = cursor.fetchone()
            assert row is not None

            assert row["ticket_id"] == "TICKET-001"
            assert row["title"] == "订单异常"
            assert row["description"] == "物流未更新"
            assert row["status"] == "open"

        finally:
            conn.close()


#测试 SQLite 主键唯一性约束
#重复使用相同工单编号时，数据库必须拒绝第二次插入
def test_insert_ticket_duplicate_id(tmp_path, monkeypatch):

    # 第一步：使用独立临时数据库
    test_db = tmp_path / "test_duplicate.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)

    # 第二步：初始化表结构
    database.init_db()

    # 第三步：第一次插入
    insert_ticket(
        ticket_id="TICKET-001",
        title="订单异常",
        description="物流未更新"
    )

    # 第四步：重复插入相同编号，应该抛出 IntegrityError
    with pytest.raises(sqlite3.IntegrityError):
        insert_ticket(
            ticket_id="TICKET-001",
            title="重复工单",
            description="第二次插入"
        )

    # 第五步：验证数据库中只有一条对应记录
    conn = database.get_connection()

    try:
        cursor = conn.execute(
            """
            SELECT COUNT(*)
            FROM tickets
            WHERE ticket_id = ?
            """,
            ("TICKET-001",)
        )

        count = cursor.fetchone()[0]

        # 重复插入不能产生第二条记录
        assert count == 1

    finally:
        # 无论断言成功或失败，都关闭连接
        conn.close()

        # 验证非标准编号不会干扰编号生成，并检查真实持久化结果
def test_create_ticket_record_generates_next_id(tmp_path, monkeypatch):

    # 第一步：准备独立的临时数据库
    test_db = tmp_path / "test_auto_ticket.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)

    # 第二步：初始化数据库表结构
    database.init_db()

    # 第三步：准备两条已有工单
    insert_ticket("TICKET-001", "已有工单", "标准编号")
    insert_ticket("TICKET-TEST-001", "测试工单", "非标准编号")

    # 第四步：使用新函数自动生成编号并创建工单
    result = create_ticket_record(
        title="订单异常",
        description="物流未更新"
    )

    # 第五步：验证自动生成的编号
    assert result["ticket_id"] == "TICKET-002"
    assert result["status"] == "open"

    # 第六步：重新连接数据库，验证工单确实保存
    conn = database.get_connection()

    try:
        row = conn.execute(
            """
            SELECT ticket_id, title, description, status
            FROM tickets
            WHERE ticket_id = ?
            """,
            ("TICKET-002",)
        ).fetchone()

        # 数据库必须存在这条工单
        assert row is not None
        assert row["ticket_id"] == "TICKET-002"
        assert row["title"] == "订单异常"
        assert row["description"] == "物流未更新"
        assert row["status"] == "open"

    finally:
        # 无论测试成功或失败，都关闭数据库连接
        conn.close()

# 使用独立的临时 SQLite 数据库，不污染正式数据
def test_insert_execution_event(test_database):

    # 第一步：构造一条工具执行成功事件
    event = ExecutionEvent(
        event_id="evt-001",
        task_id="task-001",
        event_type="tool_result",
        tool_name="get_order",
        status="success",
        latency_ms=12.5,
        details={"result": "success"}
    )

    # 第二步：通过 Repository 保存事件
    insert_execution_event(event)

    # 第三步：重新建立连接，查询 SQLite 中的事件
    conn = database.get_connection()

    try:
        row = conn.execute(
            """
            SELECT *
            FROM execution_events
            WHERE event_id = ?
            """,
            ("evt-001",)
        ).fetchone()

        # 第四步：验证事件确实存在
        assert row is not None

        # 第五步：验证核心执行指标
        assert row["task_id"] == "task-001"
        assert row["event_type"] == "tool_result"
        assert row["tool_name"] == "get_order"
        assert row["status"] == "success"
        assert row["latency_ms"] == 12.5
        assert row["error_type"] is None

        # 第六步：验证 JSON 数据能够正确还原
        details = json.loads(row["details"])
        assert details == {"result": "success"}

        # 第七步：验证数据库保存了时间戳
        assert row["timestamp"] == event.timestamp.isoformat()

    finally:
        # 无论测试是否成功，都关闭连接
        conn.close()


#验证执行事件的查询顺序与任务隔离
def test_find_execution_events(test_database):

    # 第一步：准备三条事件
    # 故意让插入顺序和时间顺序不一致
    event_late = ExecutionEvent(
        event_id="evt-002",
        task_id="task-001",
        event_type="tool_result",
        timestamp=datetime(
            2026, 11, 17, 10, 0, 2,
            tzinfo=timezone.utc
        ),
        tool_name="get_order",
        status="success",
        latency_ms=12.5,
        details={"result": "success"}
    )

    event_early = ExecutionEvent(
        event_id="evt-001",
        task_id="task-001",
        event_type="task_started",
        timestamp=datetime(
            2026, 11, 17, 10, 0, 0,
            tzinfo=timezone.utc
        )
    )

    event_other_task = ExecutionEvent(
        event_id="evt-003",
        task_id="task-002",
        event_type="error",
        timestamp=datetime(
            2026, 11, 17, 10, 0, 1,
            tzinfo=timezone.utc
        ),
        status="failed",
        error_type="UNKNOWN_TOOL"
    )

    # 第二步：故意打乱插入顺序
    insert_execution_event(event_late)
    insert_execution_event(event_other_task)
    insert_execution_event(event_early)

    # 第三步：只查询 task-001
    events = find_execution_events("task-001")

    # 第四步：验证只返回该任务的两条事件
    assert len(events) == 2

    # 第五步：验证按照时间排序，而不是插入顺序
    assert [e.event_id for e in events] == [
        "evt-001",
        "evt-002"
    ]

    # 第六步：验证查询结果重新还原为 Pydantic 模型
    assert all(isinstance(e, ExecutionEvent) for e in events)

    # 第七步：验证重要字段及 JSON 数据正确还原
    assert events[1].tool_name == "get_order"
    assert events[1].status == "success"
    assert events[1].latency_ms == 12.5
    assert events[1].details == {"result": "success"}

    # 第八步：不存在的任务应该返回空列表
    assert find_execution_events("task-999") == []


