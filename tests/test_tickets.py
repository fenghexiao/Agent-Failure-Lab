#测试工单创建工具 create_ticket
#覆盖正常创建，连续创建，非法输入和数据隔离

import pytest
from pydantic import ValidationError

from app.models import CreateTicketArgs
from tools.tickets import create_ticket
from storage import database

#测试正常创建工单
def test_create_ticket_success(test_database):

    args = CreateTicketArgs(title="订单异常", 
                            description="物流未更新",)
    result = create_ticket("call-001",args)

    assert result.success is True
    assert result.tool_name == "create_ticket"
    assert result.data["ticket_id"] == "TICKET-001"
    assert result.data["title"] == "订单异常"
    assert result.data["status"] == "open"
    assert result.error is None

    conn = database.get_connection()

    try:
        row = conn.execute(
            """
        SELECT ticket_id,title,description,status
        FROM tickets
        WHERE ticket_id = ?
        """,
        ("TICKET-001",)
        ).fetchone()

        #验证数据库是否保存
        assert row is not None
        assert row["title"] == "订单异常"
        assert row["description"] =="物流未更新"
        assert row["status"] == "open"

    finally:
        conn.close()


# 修改返回字典，不应该改变数据库中的真实工单
def test_create_ticket_does_not_modify_original(test_database):

    # 第一步：构造合法工单参数
    args = CreateTicketArgs(
        title="订单异常",
        description="物流未更新"
    )

    # 第二步：调用工具创建工单
    result = create_ticket("call-001", args)

    # 确认工单创建成功
    assert result.success is True

    # 保存工单编号，供后续数据库查询
    ticket_id = result.data["ticket_id"]

    # 第三步：故意修改工具返回的数据
    result.data["status"] = "closed"

    # 第四步：重新连接 SQLite，查询持久化记录
    conn = database.get_connection()

    try:
        row = conn.execute(
            """
            SELECT status
            FROM tickets
            WHERE ticket_id = ?
            """,
            (ticket_id,)
        ).fetchone()

        # 第五步：检查真实记录没有被返回字典污染
        assert row is not None
        assert row["status"] == "open"

    finally:
        # 无论断言成功或失败，都关闭数据库连接
        conn.close()


# 使用临时 SQLite 数据库，验证两张工单都成功持久化
def test_create_ticket_multiple(test_database):

    # 第一步：构造两次不同的工单请求
    args1 = CreateTicketArgs(
        title="订单异常",
        description="物流未更新"
    )

    args2 = CreateTicketArgs(
        title="退款问题",
        description="退款未到账"
    )

    # 第二步：连续调用创建工单工具
    result1 = create_ticket("call-001", args1)
    result2 = create_ticket("call-002", args2)

    # 第三步：验证工具返回结果
    assert result1.success is True
    assert result2.success is True
    assert result1.data["ticket_id"] == "TICKET-001"
    assert result2.data["ticket_id"] == "TICKET-002"

    # 第四步：查询 SQLite 中实际保存的工单数量
    conn = database.get_connection()

    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM tickets"
        ).fetchone()[0]

        # 两次创建必须产生两条持久化记录
        assert count == 2

    finally:
        # 无论成功或失败，都关闭数据库连接
        conn.close()

        # 参数不合法时，Pydantic 应该拒绝创建模型
def test_create_ticket_empty_title():

    with pytest.raises(ValidationError):
        CreateTicketArgs(
            title="",
            description="物流未更新"
        )


# Day 15 - 验证创建工单时不能使用空描述
# 参数不合法时，Pydantic 应该拒绝创建模型
def test_create_ticket_empty_description():

    with pytest.raises(ValidationError):
        CreateTicketArgs(
            title="订单异常",
            description=""
        )

