from app.models import ToolResult,GetOrderArgs

#虚构订单数据
ORDERS = {
    "ORD-001": {"order_id": "ORD-001",
                 "amount": 199,
                 "status":"paid"},
    "ORD-002": {"order_id": "ORD-002",
                "amount": 299,
                "status":"pending"},
}

def get_order(call_id: str,args:GetOrderArgs)->ToolResult:
    order = ORDERS.get(args.order_id)

    if order is None:
        return ToolResult(
            call_id=call_id,
            tool_name="get_order",
            success=False,
            error="ORDER_NOT_FOUND"
        )

    return ToolResult(
        call_id=call_id,
        tool_name="get_order",
        success=True,
        data=order.copy(),
    )
