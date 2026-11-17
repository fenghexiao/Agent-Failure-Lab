#统一工具执行器，负责工具查找、参数验证和异常处理
from uuid import uuid4

from app.models import ExecutionEvent
from storage.repository import insert_execution_event
import time
from typing import Any

from pydantic import ValidationError

from app.models import ToolCall,ToolResult
from agent.registry import get_tool

# 统一工具执行器
# 将所有执行分支汇合到一个返回位置
# 为后续耗时统计和事件记录做准备
def execute_tool(
    name: str,
    args: dict[str, Any],
    call_id: str
) -> ToolResult:
    #从进入执行器开始计时
    start_time = time.perf_counter()

    # 第一步：从注册表查找工具
    tool_func = get_tool(name)

    # 第二步：检查工具是否存在
    if tool_func is None:
        result = ToolResult(
            call_id=call_id,
            tool_name=name,
            success=False,
            error="UNKNOWN_TOOL"
        )

    else:
        # 第三步：使用 Pydantic 验证工具参数
        try:
            call = ToolCall(
                call_id=call_id,
                tool_name=name,
                arguments=args
            )

        except ValidationError:
            result = ToolResult(
                call_id=call_id,
                tool_name=name,
                success=False,
                error="INVALID_ARGUMENTS"
            )

        else:
            # 第四步：执行工具并统一处理运行异常
            try:
                result = tool_func(
                    call_id=call.call_id,
                    args=call.arguments
                )

            except Exception:
                result = ToolResult(
                    call_id=call_id,
                    tool_name=name,
                    success=False,
                    error="TOOL_EXECUTION_ERROR"
                )

   
    # 计算工具调用耗时
    latency_ms = (time.perf_counter() - start_time) * 1000

    # 为本次执行生成唯一事件编号
    event_id = f"evt-{uuid4().hex}"

    # 根据 ToolResult 判断真实执行状态
    status = "success" if result.success else "failed"

    # 构造执行事件
    # 当前还没有独立的任务上下文，暂时使用 call_id 关联事件
    event = ExecutionEvent(
        event_id=event_id,
        task_id=call_id,
        event_type="tool_result",
        tool_name=name,
        status=status,
        latency_ms=latency_ms,
        error_type=result.error if not result.success else None,

        # 只记录非敏感的执行摘要
        # 不保存原始 args、工单描述或完整 ToolResult.data
        details={
            "call_id": call_id,
            "success": result.success
        }
    )

    # 尝试将事件写入 SQLite
    try:
        insert_execution_event(event)

    except Exception as exc:
        # 事件记录失败不能覆盖已完成的业务执行结果
        print(
            f"[Event Warning] 事件记录失败: "
            f"{type(exc).__name__}"
        )

    # 保留原始工具执行结果
    return result