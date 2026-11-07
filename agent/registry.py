#注册工具表：集中管理允许调用的工具

from tools.orders import get_order
from tools.tickets import create_ticket

#将工具映射到实际python函数
TOOLS = {
    "get_order":get_order,
    "create_ticket":create_ticket
}

#根据工具名称查找函数，不存在则返回None
def get_tool(name:str):
    return TOOLS.get(name)
    