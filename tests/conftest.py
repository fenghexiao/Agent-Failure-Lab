# pytest 共享测试配置
# 提供独立的 SQLite 测试数据库
import pytest

from storage import database

@pytest.fixture
def test_database(tmp_path,monkeypatch):

    test_db =tmp_path/"agent_test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)
    database.init_db()

    conn = database.get_connection()

    try:
        conn.execute(
            """
            INSERT INTO orders (order_id, amount, status)
            VALUES (?, ?, ?)
            """,
            ("ORD-001", 199, "paid")
        )

        conn.execute(
            """
            INSERT INTO orders (order_id, amount, status)
            VALUES (?, ?, ?)
            """,
            ("ORD-002", 299, "pending")
        )

        conn.commit()

    finally:
      #关闭数据库连接
        conn.close()
    #将数据库路径提供给测试函数
    yield test_db
