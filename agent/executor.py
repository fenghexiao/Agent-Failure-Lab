#统一工具执行器，负责工具查找、参数验证和异常处理
from typing import Any

from pydantic import ValidationError

from app.models import ToolCall,ToolResult
from agent.registry import get_tool

"""#统一工具调用入口，校验Toolcall，返回ToolResult
def execute_tool(call:ToolCall)->ToolResult:
    #根据工具名称查找函数
    tool_func = get_tool(call.tool_name)
    #执行对应工具
    result = tool_func(call_id=call.call_id,
                       args = call.arguments)
    #返回工具执行结果
    return result"""

def execute_tool(
        name: str,
        args: dict[str, Any],
        call_id: str
)->ToolResult:
    #从注册表查找工具
    tool_func = get_tool(name)

    #1如果工具不存在，返回错误结果
    if tool_func is None:
        return ToolResult(
            call_id=call_id,
            tool_name=name,
            success=False,
            error="UNKNOWN_TOOL"
        )

    #2使用 Pydantic 验证工具名称和参数
    try:
        call = ToolCall(
            call_id=call_id,
            tool_name=name,
            arguments=args
        )
    except ValidationError as e:
        return ToolResult(
            call_id=call_id,
            tool_name=name,
            success=False,
            error="INVALID_ARGUMENTS"
        )

    #3执行工具，并统一处理运行异常
    try:
        result = tool_func(
            call_id=call.call_id,
            args=call.arguments
        )
        return result
    except Exception:
        return ToolResult(
            call_id=call_id,
            tool_name=name,
            success=False,
            error="TOOL_EXECUTION_ERROR"
        )
