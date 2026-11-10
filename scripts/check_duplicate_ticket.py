#SQLite 主键冲突验证
#本脚本仅用于验证重复工单编号是否被数据库拒绝

import sqlite3

from storage.repository import insert_ticket


# 尝试插入一个已经存在的工单编号
try:
    insert_ticket(
        ticket_id="TICKET-TEST-001",
        title="重复工单",
        description="测试主键冲突"
    )

    # 如果运行到这里，说明没有发生预期的主键冲突
    print("未触发主键冲突，需要进一步检查")

except sqlite3.IntegrityError as error:
    # 捕获 SQLite 数据完整性约束异常
    print("主键冲突已被数据库拒绝")
    print("异常类型：", type(error).__name__)