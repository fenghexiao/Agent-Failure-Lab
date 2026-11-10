#SQLite 数据库基础模块
#负责数据库连接与表结构初始化
#不负责具体的订单查询或工单创建业务
import sqlite3
from pathlib import Path
#获取项目根目录
# __file__ 是当前 database.py 文件的位置
# parents[1] 表示向上两级定位到项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "agent.db"
#创建并返回数据库连接
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    #设置查询结果通过列名访问
    conn.row_factory = sqlite3.Row

    return conn

#初始化数据库表结构
def init_db():
    #创建数据库连接
    conn = get_connection()

    try:
        #创建订单表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            order_id TEXT PRIMARY KEY,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL
        )
        """)

        #创建工单表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets(
        ticket_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL
        )
        """)

        #提交数据库初始化操作
        conn.commit()

    finally:
        #关闭数据库
        conn.close()
