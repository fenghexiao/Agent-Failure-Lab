#工单创建工具
#本文件使用内存列表模拟工单存储

from app.models import CreateTicketArgs,ToolResult

#工单存储列表
TICKETS = []

#创建工单
def create_ticket(call_id: str, args: CreateTicketArgs)->ToolResult:
    #生成工单编号
    ticket_id = f"TICKET-{len(TICKETS)+1:03d}"

    #构建工单数据
    ticket = {
        "ticket_id": ticket_id,
        "title": args.title,
        "description": args.description,
        "status": "open",
    }

    #将工单添加到存储列表
    TICKETS.append(ticket)

    #返回工单副本，避免调用者修改原始数据
    return ToolResult (
      call_id=call_id,
      tool_name="create_ticket",
      success=True,
      data=ticket.copy(),
   )