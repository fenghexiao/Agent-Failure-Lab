#FastAPI集成测试
from storage.database import get_connection
from storage.repository import find_execution_events
#使用TestClient模拟HTTP请求
from fastapi.testclient import TestClient

from app.app import app

#创建测试客户端
client = TestClient(app)

#验证合法订单查询HTTP请求
def test_execute_tool_api_success(test_database):
    #向FastAPI发送POST请求
    response = client.post(
        "/tools/execute",
        json = {
            "name":"get_order",
            "args":{"order_id":"ORD-001"},
            "call_id":"call-api-001"
        }
    )

    #验证HTTP状态码
    assert response.status_code ==200

    #将JSON响应转换为Python字典
    data = response.json()

    #验证ToolResult的核心字段
    assert data["call_id"] == "call-api-001"
    assert data["tool_name"] == "get_order"
    assert data["success"] is True
    assert data["error"] is None

    #验证返回的订单信息
    assert data["data"]["order_id"] == "ORD-001"
    assert data["data"]["amount"] == 199
    assert data["data"]["status"] == "paid"


# Day 17 - 测试订单不存在时的 HTTP 响应
# 请求结构合法，但工具业务执行失败
def test_execute_tool_api_order_not_found(test_database):

    # 第一步：请求查询一个不存在的订单
    response = client.post(
        "/tools/execute",
        json={
            "name": "get_order",
            "args": {"order_id": "ORD-999"},
            "call_id": "call-api-002"
        }
    )

    # 第二步：当前路由正常返回 HTTP 200
    assert response.status_code == 200

    # 第三步：读取 JSON 响应
    data = response.json()

    # 第四步：验证真正的业务执行结果
    assert data["success"] is False
    assert data["error"] == "ORDER_NOT_FOUND"
    assert data["tool_name"] == "get_order"
    assert data["call_id"] == "call-api-002"


# Day 17 - 测试 HTTP 请求缺少必填字段
# 缺少 call_id 时，FastAPI 应直接返回 422
def test_execute_tool_api_missing_call_id(test_database):

    # 第一步：发送缺少 call_id 的 JSON
    response = client.post(
        "/tools/execute",
        json={
            "name": "get_order",
            "args": {"order_id": "ORD-001"}
        }
    )

    # 第二步：验证 HTTP 请求校验失败
    assert response.status_code == 422

    # 第三步：读取 FastAPI 的校验错误信息
    data = response.json()

    # FastAPI 默认使用 detail 描述请求验证错误
    assert "detail" in data

    # 第四步：确认错误涉及缺失的 call_id
    assert any(
        "call_id" in error["loc"]
        for error in data["detail"]
    )


# Day 17 - 测试工具参数错误的 HTTP 响应
# HTTP 请求结构合法，但 get_order 缺少 order_id
def test_execute_tool_api_invalid_arguments(test_database):

    # 第一步：发送合法的 HTTP 请求结构
    # 但故意让工具参数为空
    response = client.post(
        "/tools/execute",
        json={
            "name": "get_order",
            "args": {},
            "call_id": "call-api-invalid-001"
        }
    )

    # 第二步：HTTP 请求被正常接收和处理
    assert response.status_code == 200

    # 第三步：读取工具执行结果
    data = response.json()

    # 第四步：验证 Executor 拦截了不合法的工具参数
    assert data["success"] is False
    assert data["error"] == "INVALID_ARGUMENTS"
    assert data["tool_name"] == "get_order"
    assert data["call_id"] == "call-api-invalid-001"


# Day 17 - 验证 API 拒绝调用未注册工具
# HTTP 请求结构合法，但工具不在注册表中
def test_execute_tool_api_unknown_tool(test_database):

    # 第一步：向 API 提交未知工具请求
    response = client.post(
        "/tools/execute",
        json={
            "name": "delete_order",
            "args": {},
            "call_id": "call-api-004"
        }
    )

    # 第二步：当前 API 使用 HTTP 200 返回工具执行结果
    assert response.status_code == 200

    # 第三步：读取响应 JSON
    data = response.json()

    # 第四步：验证工具被注册表检查拦截
    assert data["success"] is False
    assert data["error"] == "UNKNOWN_TOOL"
    assert data["tool_name"] == "delete_order"
    assert data["call_id"] == "call-api-004"


# Day 17 - 测试通过 HTTP API 创建工单
# 验证 HTTP 响应、业务持久化和执行事件
def test_execute_tool_api_create_ticket(test_database):

    # 第一步：发送创建工单的 HTTP 请求
    response = client.post(
        "/tools/execute",
        json={
            "name": "create_ticket",
            "args": {
                "title": "退款问题",
                "description": "退款未到账"
            },
            "call_id": "call-api-ticket-001"
        }
    )

    # 第二步：检查 HTTP 状态码及工具执行结果
    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["tool_name"] == "create_ticket"
    assert data["call_id"] == "call-api-ticket-001"

    # 第三步：获取实际生成的工单编号
    ticket_id = data["data"]["ticket_id"]

    assert ticket_id == "TICKET-001"

    # 第四步：通过新的数据库连接验证工单持久化
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT ticket_id, title, description, status
            FROM tickets
            WHERE ticket_id = ?
            """,
            (ticket_id,)
        ).fetchone()

        assert row is not None
        assert row["title"] == "退款问题"
        assert row["description"] == "退款未到账"
        assert row["status"] == "open"

    finally:
        conn.close()

    # 第五步：检查 Day 16 的执行事件是否仍然记录
    events = find_execution_events("call-api-ticket-001")

    assert len(events) == 1
    assert events[0].tool_name == "create_ticket"
    assert events[0].status == "success"

    # 执行事件不能泄露工单描述
    assert "description" not in events[0].details
