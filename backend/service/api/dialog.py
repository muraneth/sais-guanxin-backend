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

# 开启新的多轮问诊对话
@router.post('/new_medical_inquiry')
async def new_medical_inquiry(request: Request, requester: User = Depends(authenticate)):
    check_user(requester)
    timer = Timer()
    data = await request.json()
    domain=get_domain_from_mode(data["mode"])
    name = "多轮问诊"
    if "name" in data:
        name = data["name"]
    # 创建新会话
    new_dialog = dialog_manager.add_dialog(
        user_id=requester.id,
        user_name=requester.username,
        company=requester.company,
        name=name,
        sources=[],
        domain=domain)
    if new_dialog:
        resp = {
            AppResponse.status_code: StatusCode.Success,
            AppResponse.latency: timer.duration(),
            DialogCollectionModel.dialog_id: str(new_dialog.inserted_id)
        }
    else:
        raise NewDialogException(BackendServiceExceptionReasonCode.Match_Dialog_Count_Error.value, ExecutionContext.current())
    
    # 保存第一次对话
    content = {
        "answer": data["query"]
    }
    new_message_id = dialog_manager.upsert_message(content=content,
                                                      dialog_id=str(new_dialog.inserted_id),
                                                      message_id=None,
                                                      sources={},
                                                      cost=0.0,
                                                      domain=domain,
                                                      enable_think=None)
    if not new_message_id:
        raise Exception("insert message error")
    
    return JSONResponse(resp)

@router.post('/get_dialogs')
async def get_dialogs(request: Request, requester: User = Depends(authenticate)):
    check_user(requester)
    timer = Timer()
    data = await request.json()
    result = dialog_manager.get_dialog(
        keyword=data.get(DialogCollectionModel.keyword, ""),
        user_id=requester.id
    )
    resp = {
        AppResponse.status_code: StatusCode.Success,
        AppResponse.latency: timer.duration(),
        "data": result
    }
    return JSONResponse(resp)


@router.post('/update_dialog')
async def update_dialog(request: Request, requester: User = Depends(authenticate)):
    check_user(requester)
    timer = Timer()
    data = await request.json()
    dialog_id = data.get(DialogCollectionModel.dialog_id)
    result = dialog_manager.update_dialog(dialog_id, data.get(DialogCollectionModel.sources))
    if result.matched_count == 1:
        resp = {
            AppResponse.status_code: StatusCode.Success,
            AppResponse.latency: timer.duration()
        }
    else:
        raise UpdateDialogException(dialog_id,
                                    BackendServiceExceptionReasonCode.Match_Dialog_Count_Error.value,
                                    ExecutionContext.current())
    return JSONResponse(resp)


@router.post('/delete_dialog')
async def delete_dialog(request: Request, requester: User = Depends(authenticate)):
    check_user(requester)
    timer = Timer()
    data = await request.json()
    dialog_id = data.get(DialogCollectionModel.id)
    result = dialog_manager.delete_dialog(dialog_id)
    if result.matched_count == 1:
        resp = {
            AppResponse.status_code: StatusCode.Success,
            AppResponse.latency: timer.duration()
        }
    else:
        raise DeleteDialogException(dialog_id,
                                    BackendServiceExceptionReasonCode.Match_Dialog_Count_Error.value,
                                    ExecutionContext.current())
    return JSONResponse(resp)


@router.post('/get_dialog_messages')
async def get_dialog_messages(request: Request, requester: User = Depends(authenticate)):
    check_user(requester)
    timer = Timer()
    data = await request.json()
    result = dialog_manager.get_dialog_messages(
        domain=data[MessageCollectionModel.domain],
        dialog_id=data[MessageCollectionModel.dialog_id]
    )
    resp = {
        AppResponse.status_code: StatusCode.Success,
        AppResponse.latency: timer.duration(),
        "data": result
    }
    return JSONResponse(resp)


@router.post('/get_dialog_message')
async def get_dialog_message(request: Request, requester: User = Depends(authenticate)):
    check_user(requester)
    timer = Timer()
    data = await request.json()
    result = dialog_manager.get_dialog_message(
        message_id=data[MessageCollectionModel.message_id]
    )
    resp = {
        AppResponse.status_code: StatusCode.Success,
        AppResponse.latency: timer.duration(),
        "data": result
    }
    return JSONResponse(resp)


@router.post('/get_dialog_message_debug')
async def get_dialog_message_debug(request: Request, requester: User = Depends(authenticate)):
    check_user(requester)
    timer = Timer()
    data = await request.json()
    result = dialog_manager.get_dialog_message(
        message_id=data[MessageCollectionModel.message_id]
    )
    resp = {
        AppResponse.status_code: StatusCode.Success,
        AppResponse.latency: timer.duration(),
        "data": result["content"]["debug"]
    }
    return JSONResponse(resp)


@router.post('/update_conversation')
async def update_conversation(request: Request, requester: User = Depends(authenticate)):
    try:
        check_user(requester)
        timer = Timer()
        data = await request.json()
        dialog_manager.update_conversation(data=data)
        resp = {
            AppResponse.status_code: StatusCode.Success,
            AppResponse.message: "提交成功",
            AppResponse.latency: timer.duration()
        }
        return JSONResponse(resp)
    except HTTPException:
        return AUTH_FAILED_RESPONSE
    except Exception as ex:
        return get_error_response(ex)


@router.post('/edit')
async def edit_dialog_name(request: Request, requester: User = Depends(authenticate)):
    try:
        check_user(requester)
        timer = Timer()
        data = await request.json()
        dialog_manager.edit_dialog_name(
            dialog_name=data[DialogCollectionModel.name],
            dialog_id=data[DialogCollectionModel.dialog_id]
        )
        resp = {
            AppResponse.status_code: StatusCode.Success,
            AppResponse.message: "编辑成功",
            AppResponse.latency: timer.duration()
        }
        return JSONResponse(resp)
    except HTTPException:
        return AUTH_FAILED_RESPONSE
    except Exception as ex:
        return get_error_response(ex)


def get_error_response(ex: Exception) -> JSONResponse:
    service_logger.warning(traceback.format_exc())
    return JSONResponse(
        {
            AppResponse.status_code: StatusCode.InternalError,
            AppResponse.message: str(ex),
            AppResponse.latency: 0.0,
            AppResponse.trace_id: ExecutionContext.current().trace_id
        },
        status_code=500)
