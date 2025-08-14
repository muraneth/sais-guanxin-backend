from fastapi import APIRouter, Depends

from starlette.requests import Request
from starlette.responses import JSONResponse

from service.repository.mongo_dialog_manager import dialog_manager
from service.repository.mongo_task_manager import task_manager
from service.package.auth import authenticate, check_user

from util.timer import Timer
from util.model_types import User, AppResponse, StatusCode
from util.oss import oss_client
from util.mode import DOMAIN_SEARCH, get_domain_from_mode

router = APIRouter(
    prefix="/api"
)


@router.get("/oss_policy")
async def oss_policy(request: Request, requester: User = Depends(authenticate)):
    timer = Timer()
    check_user(requester)
    try:
        oss_policy = oss_client.get_oss_policy()
        return JSONResponse({
            AppResponse.status_code: StatusCode.Success,
            AppResponse.message: "get oss policy ok",
            AppResponse.latency: timer.duration(),
            "data": oss_policy
        })
    except:
        return JSONResponse({
            AppResponse.status_code: StatusCode.InternalError,
            AppResponse.message: "get oss policy fail",
            AppResponse.latency: timer.duration(),
            "data": {}
        })


@router.post("/submit_report")
async def submit_report(request: Request, requester: User = Depends(authenticate)):
    timer = Timer()

    request_json = await request.json()
    # 从request_json 中获取 dialog_id / file_name / file_type / file_oss_key
    dialog_id = request_json.get("dialog_id")
    file_name = request_json.get("file_name")
    file_type = request_json.get("file_type")
    file_oss_key = request_json.get("file_oss_key")

    # 检查参数是否齐全
    if not dialog_id or not file_name or not file_type or not file_oss_key:
        return JSONResponse({
            AppResponse.status_code: StatusCode.BadRequest,
            AppResponse.message: "missing required fields",
            AppResponse.latency: timer.duration(),
            "data": {}
        })
    
    domain = DOMAIN_SEARCH
    if "mode" in request_json:
        domain = get_domain_from_mode(request_json.get("mode"))

    # 将上传报告的任务写入任务队列中
    task_id = task_manager.add_task(
        task_type="upload_report", 
        params={
            "dialog_id": dialog_id, 
            "file_name": file_name, 
            "file_type": file_type, 
            "file_oss_key": file_oss_key
        }
    )
    
    if not task_id:
        return JSONResponse({
            AppResponse.status_code: StatusCode.InternalError,
            AppResponse.message: "submit report fail",
            AppResponse.latency: timer.duration(),
            "data": {}
        })
    
    # 将上传报告的事件写入对话历史中，以便重新加载对话时显示这里上传了报告
    dialog_manager.upsert_message(
        content={
            "task_id": task_id, 
            "file_name": file_name, 
            "file_type": file_type, 
            "file_oss_key": file_oss_key
        },
        dialog_id=dialog_id,
        message_id=task_id,
        sources={},
        cost=0.0,
        domain=domain,
        enable_think=None
    )
    
    return JSONResponse({
        AppResponse.status_code: StatusCode.Success,
        AppResponse.latency: timer.duration(),
        AppResponse.message: "submit report ok",
        "report_id": task_id,
        "file_name": file_name, 
        "file_type": file_type, 
        "file_oss_key": file_oss_key
    })


@router.get("/check_report_process")
async def check_report_process(request: Request, requester: User = Depends(authenticate)):
    timer = Timer()
    # 参数处理
    query_params = request.query_params
    task_id = query_params.get("report_id")

    # 检查参数是否齐全
    if not task_id:
        return JSONResponse({
            AppResponse.status_code: StatusCode.BadRequest,
            AppResponse.message: "missing required fields",
            AppResponse.latency: timer.duration(),
            "data": {}
        })
    
    # 将 task_id 转换为列表
    task_ids = task_id.split(",") if task_id else []
    
    # 从任务队列中获取任务状态
    result = []
    for task_id in task_ids:
        task = task_manager.get_by_task_id(task_id)
        if not task:
            return JSONResponse({
                AppResponse.status_code: StatusCode.InternalError,
                AppResponse.message: "task not found",
                AppResponse.latency: timer.duration(),
                "data": {}
            })
        result.append({
            "report_id": task_id,
            "status": task.get("status")
        })

    return JSONResponse({
        AppResponse.status_code: StatusCode.Success,
        AppResponse.message: "check report process ok",
        AppResponse.latency: timer.duration(),
        "data": {
            "result": result
        }
    })
