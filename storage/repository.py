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
