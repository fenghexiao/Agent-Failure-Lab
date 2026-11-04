#测试工单创建工具 create_ticket
#覆盖正常创建，连续创建，非法输入和数据隔离

import pytest
from pydantic import ValidationError

from app.models import CreateTicketArgs
from tools.tickets import create_ticket,TICKETS

#每个测试前清空虚构工单列表
#避免不同测试之间互相影响
@pytest.fixture(autouse=True)
def clear_tickets():
    TICKETS.clear()
    yield
    TICKETS.clear()

#测试正常创建工单
def test_create_ticket_success():
    args = CreateTicketArgs(title="订单异常", 
                            description="物流未更新",)
    result = create_ticket("call-001",args)

    assert result.success is True
    assert result.tool_name == "create_ticket"
    assert result.data["ticket_id"] == "TICKET-001"
    assert result.data["title"] == "订单异常"
    assert result.data["status"] == "open"
    assert result.error is None
    assert len(TICKETS) == 1

#测试连续创建两个工单
def test_create_ticket_multiple():
    args1 = CreateTicketArgs(title="订单异常", 
                            description="物流未更新",)

    args2 = CreateTicketArgs(title="退款问题",
                             description="退款未到账",)

    result1 = create_ticket("call-001",args1)
    result2 = create_ticket("call-002",args2)

    assert result1.data["ticket_id"] == "TICKET-001"
    assert result2.data["ticket_id"] == "TICKET-002"
    assert len(TICKETS) == 2

#测试空标题被pydantic拒绝
def test_create_ticket_rejects_empty_title():
    with pytest.raises(ValidationError):
        CreateTicketArgs(title="", 
                         description="物流未更新")

#测试空描述被pydantic拒绝
def test_create_ticket_rejects_empty_description():
    with pytest.raises(ValidationError):
        CreateTicketArgs(title="订单异常", 
                         description="")

#测试返回数据是副本，修改不会影响原始数据
def test_create_ticket_does_not_modify_original():
    args = CreateTicketArgs(title="订单异常", 
                            description="物流未更新",)
    result = create_ticket("call-001",args)

    #故意修改返回的数据
    result.data["status"] = "closed"

    #内存中保存的工单状态不应该改变
    assert TICKETS[0]["status"] == "open"
    