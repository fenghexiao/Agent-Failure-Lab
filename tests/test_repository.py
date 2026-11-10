# Repository 自动化测试
# 使用 pytest 临时数据库隔离测试数据

import sqlite3

from storage import database
from storage.repository import find_order


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