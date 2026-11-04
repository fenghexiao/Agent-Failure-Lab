import pytest
from pydantic import ValidationError

from app.models import GetOrderArgs
from tools.orders import get_order

def test_get_order_success():
    args = GetOrderArgs(order_id="ORD-001")

    result = get_order("call-001",args)

    assert result.success is True
    assert result.tool_name == "get_order"
    assert result.data["order_id"] == "ORD-001"
    assert result.data["status"] == "paid"
    assert result.error is None

def test_get_order_not_found():
    args = GetOrderArgs(order_id="ORD-999")

    result = get_order("call-002",args)

    assert result.success is False
    assert result.data is None
    assert result.error == "ORDER_NOT_FOUND"

def test_get_order_rejects_empty_order_id():
    with pytest.raises(ValidationError):
        GetOrderArgs(order_id="")

def test_get_order_does_not_modify_original_data():
    args = GetOrderArgs(order_id="ORD-001")

    result = get_order("call-003",args)
    result.data["status"] = "cancelled"

    second_result = get_order("call-004",args)

    assert second_result.data["status"] == "paid"

  
