import json
from app.models import ExecutionEvent
#Repository 数据访问层
from storage.database import get_connection

#根据订单编号查询订单
def find_order(order_id:str)->dict |None:

    #建立数据库连接
    conn = get_connection()

    try:
        #使用参数化SQL查询订单
        cursor = conn.execute(
            """
            SELECT order_id,amount,status
            FROM orders
            WHERE order_id = ?
            """,
            (order_id,)
        )

        #读取一条查询结果
        row = cursor.fetchone()
        if row is None:
            return None

        #将sqlite3.Row转换为普通字典
        return dict(row)
    finally:
        #关闭连接
        conn.close()

 #创建工单并保存到 SQLite
def insert_ticket(
        ticket_id: str,
        title: str,
        description: str)-> dict:

    #建立数据库连接
    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO tickets
            (ticket_id, title,description,status)
            VALUES(?,?,?,?)
            """,
            (ticket_id,title,description,"open")
        )
        conn.commit()

        return{
            "ticket_id":ticket_id,
            "title":title,
            "description":description,
            "status":"open"
        }

    finally:
        conn.close()

        #自动生成编号并创建工单
# 使用 SQLite 写事务保护编号分配和数据插入
def create_ticket_record(title: str, description: str) -> dict:
    conn = get_connection()

    try:
        #事务锁提前获取写
        conn.execute("BEGIN IMMEDIATE")

        #读取现有工单编号
        cursor = conn.execute(
            """
            SELECT ticket_id
            FROM tickets
            """
        )

        #找出标准格式工单中的最大编号
        max_number = 0

        for row in cursor.fetchall():
            ticket_id = row["ticket_id"]

            # 仅处理 TICKET-数字 这种标准格式
            # 排除 TICKET-TEST-001 等其他编号
            if not ticket_id.startswith("TICKET-"):
                continue

            number_text = ticket_id[len("TICKET-"):]

            if not number_text.isdigit():
                continue

            number = int(number_text)

            if number > max_number:
                max_number = number

        # 生成下一个工单编号
        next_number = max_number + 1
        ticket_id = f"TICKET-{next_number:03d}"

        # 在同一事务中插入工单
        conn.execute(
            """
            INSERT INTO tickets
            (ticket_id, title, description, status)
            VALUES (?, ?, ?, ?)
            """,
            (ticket_id, title, description, "open")
        )

        # 提交事务
        conn.commit()

        # 返回创建的工单信息
        return {
            "ticket_id": ticket_id,
            "title": title,
            "description": description,
            "status": "open"
        }

    except Exception:
        # 发生异常时撤销本次事务
        conn.rollback()
        raise

    finally:
        conn.close()

#将执行事件持久到SQLite
def insert_execution_event(event:ExecutionEvent)->None:
    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO execution_events (
            event_id,
            task_id,
            event_type,
            timestamp,
            tool_name,
            status,
            latency_ms,
            error_type,
            details
            )
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
        (
            event.event_id,
            event.task_id,
            event.event_type,
            event.timestamp.isoformat(),
            event.tool_name,
            event.status,
            event.latency_ms,
            event.error_type,
            json.dumps(event.details,ensure_ascii=False),
        )
        )

        conn.commit()

    except Exception:
        #异常时回滚
        conn.rollback()
        raise

    finally:
        conn.close()

# 返回按时间顺序排列的 ExecutionEvent 对象列表
def find_execution_events(task_id: str) -> list[ExecutionEvent]:

    # 建立数据库连接
    conn = get_connection()

    try:
        # 使用参数化 SQL 查询指定任务的所有事件
        cursor = conn.execute(
            """
            SELECT *
            FROM execution_events
            WHERE task_id = ?
            ORDER BY timestamp ASC, rowid ASC
            """,
            (task_id,)
        )

        # 获取全部匹配记录
        rows = cursor.fetchall()

        # 将 SQLite 数据转换回 Pydantic 模型
        events = []

        for row in rows:
            event = ExecutionEvent(
                event_id=row["event_id"],
                task_id=row["task_id"],
                event_type=row["event_type"],
                timestamp=row["timestamp"],
                tool_name=row["tool_name"],
                status=row["status"],
                latency_ms=row["latency_ms"],
                error_type=row["error_type"],
                details=json.loads(row["details"])
            )

            events.append(event)

        return events

    finally:
        # 无论查询是否成功，都关闭数据库连接
        conn.close()