# 创建工单工具
# 通过 Repository 将工单持久化到 SQLite

from app.models import CreateTicketArgs, ToolResult
from storage.repository import create_ticket_record

#创建工单
def create_ticket(call_id: str, args: CreateTicketArgs)->ToolResult:
    # 通过 Repository 创建工单
    # 数据库负责编号生成和持久化
    ticket = create_ticket_record(
        title=args.title,
        description=args.description
    )

      # 将创建结果包装为统一的 ToolResult
    return ToolResult(
        call_id=call_id,
        tool_name="create_ticket",
        success=True,
        data=ticket.copy()
    )
