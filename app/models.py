"""Agent Failure Lab 的数据模型层（Day 12 产物）。

这个文件只做一件事：定义项目里所有「数据的形状」，不做业务逻辑、
不读数据库、不调工具。

──────────────────────────────────────────────────────────────
为什么要把模型单独放一层？
──────────────────────────────────────────────────────────────
工具函数（tools/orders.py）和 API 接口（app/app.py）都要收发数据。
如果每处都自己拼 dict，字段名写错、类型写错只有跑到那一行才会暴露。
用 Pydantic 定义一次，所有地方复用，数据在进入业务逻辑之前就被校验过了。

反过来说：本文件不负责「查订单」「建工单」这些动作，那是 tools/ 的事。
模型只管**数据长得对不对**，不管**业务做没做对**。

──────────────────────────────────────────────────────────────
六个模型按用途分三组
──────────────────────────────────────────────────────────────
1. 工具入参    GetOrderArgs、CreateTicketArgs
2. 调用输入输出 TaskRequest、ToolCall、ToolResult
3. 执行过程记录 ExecutionEvent
"""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


# ══════════════════════════════════════════════════════════════
# 第一组：工具入参
#
# 这两个模型回答同一个问题：「调用这个工具，需要提供哪些参数？」
# 它们将来由模型（LLM）提出、由代码校验，所以这里必须严格。
# ══════════════════════════════════════════════════════════════


class GetOrderArgs(BaseModel):
    """查询订单所需的参数。

    只有一个字段：订单编号。

    Field(min_length=1) 的作用是拒绝空字符串。
    如果只写 order_id: str，那么 order_id="" 也能构造成功，
    直到查库时才发现「查了个空编号」，错误发现得太晚。
    """

    order_id: str = Field(min_length=1)


class CreateTicketArgs(BaseModel):
    """创建工单所需的参数。

    title 和 description 都要求至少 1 个字符：
    一张没有标题的工单，人工处理时根本不知道该干嘛。
    """

    title: str = Field(min_length=1)
    description: str = Field(min_length=1)


# ══════════════════════════════════════════════════════════════
# 第二组：一次调用的输入与输出
#
# 这三个模型描述「用户提一个任务 → Agent 决定调哪个工具 →
# 工具返回什么」这条链路上的数据结构。
# ══════════════════════════════════════════════════════════════


class TaskRequest(BaseModel):
    """用户提交给系统的一个任务（自然语言）。

    max_length=2000 是成本与安全护栏：
    超长输入会消耗大量 token，也是提示注入的常见载体。
    """

    task: str = Field(min_length=1, max_length=2000)


class ToolCall(BaseModel):
    """Agent 提出的一次工具调用：调哪个工具、带什么参数。

    ┌─ call_id ─────────────────────────────────────────────┐
    │ 本次调用的唯一标识。工具返回 ToolResult 时会原样带回， │
    │ 靠它把「请求」和「响应」配对。一次任务可能连着调好几   │
    │ 次工具，没有 call_id 就分不清哪个结果对应哪次调用。    │
    └───────────────────────────────────────────────────────┘

    ┌─ tool_name: Literal[...] ──────────────────────────────┐
    │ 为什么不写 tool_name: str？                             │
    │ 因为 str 允许 "delete_order"、"get_orders"（多个 s）    │
    │ 这类拼写错误或危险工具名通过校验。                      │
    │ Literal 把取值范围写死在类型里，只能是这两个字符串，    │
    │ 传别的直接 ValidationError。                            │
    └───────────────────────────────────────────────────────┘

    ┌─ arguments: GetOrderArgs | CreateTicketArgs ───────────┐
    │ 竖线表示「联合类型」：可以是两种模型中的任意一种。      │
    │ 查订单时传 GetOrderArgs，建工单时传 CreateTicketArgs。 │
    └───────────────────────────────────────────────────────┘
    """

    call_id: str = Field(min_length=1)
    tool_name: Literal["get_order", "create_ticket"]
    arguments: GetOrderArgs | CreateTicketArgs

    @model_validator(mode="after")
    def validate_arguments_match_tool(self):
        """确保 tool_name 和 arguments 的类型是配套的。

        ── 为什么光有 Union 类型还不够？────────────────────────
        Pydantic 处理 Union 的策略是「按顺序试，能装进哪个就是哪个」。
        它只关心「这个字典能不能塞进某个模型」，
        **完全不关心 tool_name 和参数类型是否匹配**。

        于是会出现这种荒谬但合法的情况：
            ToolCall(tool_name="get_order",
                     arguments={"title": "x", "description": "y"})
        GetOrderArgs 装不下（没有 order_id），于是轮到 CreateTicketArgs，
        它装得下 —— 于是一个「查询订单」的调用带着「创建工单」的参数，
        被静默接受了。这个对象一旦流到执行器，
        执行器可能真去建一张工单。

        这就是「模型提议 vs 代码决定」的分界线：
        模型可能给出自相矛盾的调用，而这一层必须拦住它。

        ── mode="after" 是什么意思？───────────────────────────
        "after" 表示「字段都按类型转换完成后，再调用这个函数」。
        所以这里拿到的 self.arguments 已经是 GetOrderArgs 或
        CreateTicketArgs 的实例，可以直接用 isinstance 判断。

        ── 为什么 raise ValueError 会变成 ValidationError？──────
        这是 Pydantic 的约定：validator 里抛 ValueError，
        它会被包装成 ValidationError 抛给调用方。
        好处是调用方只需要处理一种异常，
        而且错误信息里会带上输入数据，便于排查。
        """

        if self.tool_name == "get_order":
            if not isinstance(self.arguments, GetOrderArgs):
                raise ValueError("get_order 必须使用 GetOrderArgs")

        elif self.tool_name == "create_ticket":
            if not isinstance(self.arguments, CreateTicketArgs):
                raise ValueError("create_ticket 必须使用 CreateTicketArgs")

        # validator 必须 return self，否则 Pydantic 拿不到模型实例
        return self


class ToolResult(BaseModel):
    """一次工具调用的结果。

    ┌─ success 是唯一的判断依据 ────────────────────────────┐
    │ 调用方只看 success，不看 data 或 error 是不是空的。    │
    │   success=True  → 读 data                             │
    │   success=False → 读 error                            │
    │ 这样将来新增工具、新增错误类型，调用方的代码都不用改。 │
    └───────────────────────────────────────────────────────┘

    ┌─ error 里为什么是 "ORDER_NOT_FOUND" 这种常量 ─────────┐
    │ 而不是「订单不存在」这句中文？                          │
    │ 因为 Day 31 你要写 30 个评估案例、Day 33 要做基线对比，│
    │ 需要按错误类型统计次数。中文措辞随时会改              │
    │ （「订单不存在」/「未找到订单」），错误码不会。        │
    │ 错误码稳定，统计才可靠。                              │
    └───────────────────────────────────────────────────────┘

    call_id 和 tool_name 与发起它的 ToolCall 保持一致，
    这样从结果可以反查是哪次调用、哪个工具产生的。
    """

    call_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


# ══════════════════════════════════════════════════════════════
# 第三组：执行过程记录
#
# Day 16 叫「执行事件可观测性」，Day 30 叫「日志与成本记录」。
# 这个模型就是那两天的地基：Agent 每做一步，留一条结构化记录。
# 事后复盘「这次任务为什么失败」时，靠的就是这一串事件。
# ══════════════════════════════════════════════════════════════


class ExecutionEvent(BaseModel):
    """执行过程中的一条事件记录。

    event_type 用 Literal 限定为四种：
        task_started → 任务开始
        tool_call    → 发起了一次工具调用
        tool_result  → 拿到了工具返回值
        error        → 出了错

    这四个值构成了任务生命周期的骨架。
    将来想加「重试」「预算超限」等事件，就在这里加一个值，
    其他地方如果用了 Literal 校验，会立刻提示你需要同步处理。
    """

    event_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    event_type: Literal[
        "task_started",
        "tool_call",
        "tool_result",
        "error",
    ]

    # ┌─ 为什么写 default_factory=lambda: ... 而不是直接赋值？──┐
    # │ 直接写 timestamp: datetime = datetime.now(timezone.utc)│
    # │ 会有两个问题：                                          │
    # │   1. 时间在「模块导入时」就算好了，所有事件共用同一个   │
    # │      时间戳，全错。                                     │
    # │   2. datetime.now() 是 naive（不带时区）的，            │
    # │      日志跨时区或跨机器对比时会产生歧义。               │
    # │ default_factory 表示「每次创建实例时才调用这个函数」，  │
    # │ timezone.utc 则保证时间戳永远带 UTC 时区信息。          │
    # └─────────────────────────────────────────────────────────┘
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # ┌─ 这里是本文件最容易被忽略的一个坑 ─────────────────────┐
    # │ 如果写成 details: dict[str, Any] = {}，                  │
    # │ Python 的默认参数只在函数定义时求值一次，                │
    # │ 于是**所有 ExecutionEvent 实例共享同一个字典**：        │
    # │                                                        │
    # │     a = ExecutionEvent(...)                            │
    # │     b = ExecutionEvent(...)                            │
    # │     a.details["tool"] = "get_order"                    │
    # │     print(b.details)   # {'tool': 'get_order'}  ← 污染 │
    # │                                                        │
    # │ 用 default_factory=dict 才能让每个实例拿到独立的新字典。│
    # │ tests/test_models.py 里的                                │
    # │ test_execution_event_details_are_independent 就在测这个。│
    # └─────────────────────────────────────────────────────────┘
    details: dict[str, Any] = Field(default_factory=dict)
