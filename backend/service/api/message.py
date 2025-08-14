from fastapi import APIRouter, Depends
import traceback

from fastapi import APIRouter, Depends
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from service.repository.mongo_dialog_manager import dialog_manager
from service.exceptions import BackendServiceExceptionReasonCode
from service.exceptions.dialog_exceptions import NewDialogException, UpdateDialogException, DeleteDialogException
from util.execution_context import ExecutionContext
from util.logger import service_logger
from service.package.auth import authenticate, check_user, AUTH_FAILED_RESPONSE
from util.timer import Timer
from util.model_types import AppResponse, StatusCode, MessageCollectionModel, DialogCollectionModel, User
from util.mode import get_domain_from_mode

router = APIRouter(
    prefix="/api"
)

@router.post("/new_message")
async def new_message(request: Request, requester: User = Depends(authenticate)):
    check_user(requester)
    timer = Timer()
    # 获取请求参数
    data = await request.json()
    if "mode" not in data:
        raise Exception("mode is required")
    domain=get_domain_from_mode(data["mode"])
    dialog_id = data.get("dialog_id", None)
    if not dialog_id:
        raise Exception("dialog_id is required")
    # 获取助手消息
    assistant_content = data.get("assistant_content", "")
    # 获取用户消息
    user_content = data.get("user_content", "")

    # 插入消息
    message_id = dialog_manager.upsert_message(
        content={
            "answer": assistant_content,
            "query": user_content
        },
        dialog_id=dialog_id,
        message_id=None,
        sources={},
        cost=0.0,
        domain=domain,
        enable_think=None
    )
    if not message_id:
        raise Exception("insert message error")
    
    # 返回响应
    resp = {
        AppResponse.status_code: StatusCode.Success,
        AppResponse.latency: timer.duration(),
        "message_id": message_id,
    }
    return JSONResponse(resp)
    