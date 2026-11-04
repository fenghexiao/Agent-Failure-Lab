# 根据订单编号查询订单
# call_id：本次工具调用的唯一标识
# args：经过 Pydantic 校验的订单查询参数
# 返回：统一的 ToolResult，包含成功状态、订单数据或错误码
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

 # 如果订单不存在，返回固定的业务错误码
    if order is None:
        return ToolResult(
            call_id=call_id,
            tool_name="get_order",
            success=False,
            error="ORDER_NOT_FOUND"
        )

 # 返回订单副本，避免外部修改原始订单数据
    return ToolResult(
        call_id=call_id,
        tool_name="get_order",
        success=True,
        data=order.copy(),
    )
