#瀵煎叆HTTP璇锋眰妯″瀷鍜屽凡鏈夊伐鍏锋墽琛屽櫒
from app.models import ToolExecuteRequest,ToolResult
from agent.executor import execute_tool
from fastapi import FastAPI

app = FastAPI(title="Agent Failure Lab", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok","message":"Agent Failure Lab is running"}

#HTTP宸ュ叿鎵ц鍏ュ彛
@app.post("/tools/execute",response_model=ToolResult)
def execute_tool_api(request:ToolExecuteRequest)->ToolResult:
    #璺敱鍙礋璐ｈ皟鐢ㄦ墽琛屽櫒
    result = execute_tool(
        name=request.name,
        args=request.args,
        call_id=request.call_id
    )

    #FastAPI 灏員oolResult杞崲涓篔SON鍝嶅簲
    return result
