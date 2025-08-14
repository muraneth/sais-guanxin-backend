import datetime
import jwt
import asyncio
import traceback
from fastapi import APIRouter, Depends
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse

from service.api.stream_search import overwrite_ans
from service.config.config import service_config, DIRECT_TO_DOCTOR_WORKSTATION, DOCTOR_WORKSTATION_URL, IS_DEMO_MODE, PROLOGUE
from service.repository.mongo_dialog_manager import dialog_manager, get_ai_doctor_chat_history
from service.repository.mongo_task_manager import task_manager, TaskStatus
from service.repository.mongo_treatment_info import treatment_info_manager
from service.repository.mongo_medical_record_manager import medical_record_manager

from service.package.auth import authenticate, check_user_dialog_id
from service.package.hospital_info_sys import get_patient_base_info

from util.stream.response_queue import ResponseQueue
from util.stream.stream_search_model import StreamSearchData
from util.tracker.stream_search_tracker import StreamingSearchTracker
from util.oss import oss_client
from util.minio_client import minio_client
from util.spark_slm_iat_origin import wsParam
from util.model_types import AppResponse, StatusCode,User
from util.mode import DOMAIN_AI_DOCTOR
from util.logger import service_logger

from agents.medical_dialogue import medical_dialogue
router = APIRouter(
    prefix="/api/doctor"
)

# 判断就诊号是否存在
@router.get("/is_treatment_id_exists")
async def is_treatment_id_exists(request: Request):
    treatment_id = request.query_params.get("treatment_id", None)
    if not treatment_id:
        raise HTTPException(status_code=400, detail="treatment_id is required")
    patient_info = get_patient_base_info(treatment_id)
    if patient_info:
        return JSONResponse({
            "code": 0,
            "msg": "ok",
            "data": {
                "exists": True
            }
        })
    else:
        return JSONResponse({
            "code": 0,
            "msg": "ok",
            "data": {
                "exists": False
            }
        })
    
# 创建新的对话
@router.post("/new_treatment_chat")
async def new_treatment_chat(request: Request):
    # 如果第一次调用，只有 treatment_id， 没有 dialog_id，后端生成一个新的 dialog_id
    # 如果不是第一次调用，有 dialog_id， 取回历史对话记录
    # 无论如何都会生成新的 token

    # 参数合法性检查， 是否包含 treatment_id
    data = await request.json()
    treatment_id = data.get("treatment_id", None)
    if not treatment_id:
        raise HTTPException(status_code=400, detail="treatment_id is required")
    

    # 检查 treatment_id 是否存在
    treatment_info = treatment_info_manager.get_by_treatment_id(treatment_id)
    if treatment_info:
        # 不是第一次调用，有 dialog_id， 取回历史对话记录
        dialog_id = str(treatment_info["dialog_id"])
    else:
        # 对接医院 HIS 系统，取回患者信息，并将信息保存下来
        patient_info = get_patient_base_info(treatment_id)
        if not patient_info:
            # 后续步骤都依赖于 patient_info，所以如果获取不到 patient_info，则直接返回错误
            service_logger.error(f"can not get patient info from hospital, treatment_id: {treatment_id}")
            raise HTTPException(status_code=500, detail="can not get patient info from hospital")
        
        # 生成开场白
        prologue = PROLOGUE
            
        # 检查是否存在 dialog_id
        dialog = dialog_manager.get_dialog_by_treatment_id(treatment_id)
        if dialog:
            dialog_id = str(dialog["_id"])
        else:
            # 创建新的对话，并产生新的 dialog_id
            new_dialog = dialog_manager.new_ai_doctor_dialog(treatment_id)
            dialog_id = str(new_dialog.inserted_id)
            # 固定开场白文案
            dialog_manager.upsert_message(
                content={
                    "answer": prologue
                },
                dialog_id=dialog_id, 
                message_id=None,
                sources={},
                cost=0.0,
                domain=DOMAIN_AI_DOCTOR,
                enable_think=None)
    
        # 检查 header 中是否存在 mock 参数
        demo_mode = False
        mock = request.headers.get("mock", None)
        if mock and mock == "true":
            demo_mode = True

        # 保存病人信息，合并 dialog_id 和 patient_info
        treatment_info_manager.insert_treatment_info({
            "dialog_id": dialog_id,
            "treatment_id": treatment_id,
            "patient_info": patient_info,
            "demo_mode": demo_mode
        })

        # 创建异步任务：对接医院 HIS 系统，获取患者历史就诊记录，并生成总结，二者都保存到数据库中
        # 用于AI问诊时上下文的参考
        task_manager.add_task(
            task_type="summarize_history_data",
            params={
                "treatment_id": treatment_id,
                "with_diagnosis_info": False
            }
        )

    # 获取对话历史
    chat_history, diagnose_finished = get_ai_doctor_chat_history(dialog_id, show_appendix=True)

    # 生成新的 token
    # 将有效时间，user_id 嵌入 jwt-token，并返回 token
    token = jwt.encode(
        {
            'dialog_id': dialog_id,
            'treatment_id': treatment_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=12)
        },
        service_config.jwt.secret_key,
        algorithm='HS256'
    )

    return JSONResponse({
        "code": 0,
        "msg": "ok",
        "data": {
            "token": token,
            "dialog_id": dialog_id,
            "chat_history": chat_history,
        }
    })


@router.get("/get_xunfei_asr_url")
async def get_xunfei_asr_url(request: Request, requester: User = Depends(authenticate)):
    # 参数合法性检查
    dialog_id = request.query_params.get("dialog_id", None)
    if not dialog_id:
        raise HTTPException(status_code=400, detail="dialog_id is required")
    
    # 检查 dialog_id 与 Token 是否合法
    check_user_dialog_id(requester, dialog_id)
    
    return JSONResponse({
        "code": 0,
        "msg": "ok",
        "data": {
            "url": wsParam.create_url(),
        }
    })

@router.get("/get_xunfei_avatar_url")
async def get_xunfei_avatar_url(request: Request, requester: User = Depends(authenticate)):
    # 参数合法性检查
    dialog_id = request.query_params.get("dialog_id", None)
    if not dialog_id:
        raise HTTPException(status_code=400, detail="dialog_id is required")
    
    # 检查 dialog_id 与 Token 是否合法
    check_user_dialog_id(requester, dialog_id)
    
    return JSONResponse({
        "code": 0,
        "msg": "ok",
        "data": {
            "url": wsParam.create_url(),
        }
    })

@router.post("/stream")
async def stream(request: Request, requester: User = Depends(authenticate)):
    # 参数合法性检查
    data = await request.json()
    dialog_id = data.get("dialog_id", None)
    if not dialog_id:
        raise HTTPException(status_code=400, detail="dialog_id is required")
    
    raw_query = data.get("query", None)
    if not raw_query:
        raise HTTPException(status_code=400, detail="query is required")
    
    # 检查 dialog_id 与 Token 是否合法
    check_user_dialog_id(requester, dialog_id)

    # 检查 header 中是否存在 mock 参数
    mock_mode = False
    mock = request.headers.get("mock", None)
    if mock and mock == "true":
        mock_mode = True

    # 是否开启调试模式
    is_debugging = data.get('is_debugging', False)

    # 初始化元数据 carrier 和 DB 记录 tracker
    metadata = {}
    tracker = StreamingSearchTracker(dialog_manager) # 存入db
    finished_event = asyncio.Event()
    domain = DOMAIN_AI_DOCTOR
        
    service_logger.info(f"ai doctor patient chat got request: {data}")
    def _next_callback(item: StreamSearchData):
        if item is None:
            return None
        # 过滤
        if not is_debugging and item.event == StreamSearchData.SearchEvent.Debug:
            filter_result = None
        elif item.event == StreamSearchData.SearchEvent.Recalled:
            # 召回和溯源信息都在 trace，所以暂时不需要 event: recalled，
            filter_result = None
        else:
            item.meta = metadata
            filter_result = item
        # 保存
        tracker.track(item)
        return filter_result

    def _error_callback(error: Exception):
        service_logger.error(f"error during stream search: {str(error)}, stack: {traceback.format_exc()}")
        return StreamSearchData.build_from_error(dialog_id, metadata)

    def _completed_callback():
        service_logger.info(f"response complete request, dialog_id: {dialog_id}, request data: {data}")
        tracker.untrack()
        finished_event.set()

    response_queue = ResponseQueue(next_action=_next_callback, error_action=_error_callback, complete_action=_completed_callback, tracker=tracker)
    try:        
        # 初始化 message
        message_id = asyncio.run(overwrite_ans(dialog_id, data.get("message_id"), metadata, domain, data.get("enable_think")))
        query_data = asyncio.run(build_dialogue_query(dialog_id=dialog_id,
                                                raw_query=raw_query,
                                                enable_think=data.get("enable_think")))
        if mock_mode:
            # 如果 mock 模式开启，则将 mock 信息添加到 query_data 中
            query_data["mock_info"] = {
                "enable_mock": True,
                "mock_turns": int(len(query_data["chat_history"])/2),
            }
            service_logger.info(f"mock mode is enabled, dialog_id: {dialog_id}")

        # There are some sync calls in algo modules, thus put it in an executor to avoid blocking the elp
        response_queue.put(StreamSearchData.Builder()
                            .event(StreamSearchData.SearchEvent.Received)
                            .query(raw_query)
                            .dialog_id(dialog_id)
                            .message_id(message_id)
                            .meta(metadata)
                            .build())
        
        if query_data.get("diagnose_finished", False):
            # 如果诊断已经完成，则直接返回
            response_queue.put(StreamSearchData.Builder().event(StreamSearchData.SearchEvent.Finished).build())
            # None 通知 ResponseQueue 结束
            response_queue.put(None) 
        else:
            service_logger.info(f"dialog_id: {dialog_id}, medical_dialogue by query: {query_data}")
            # 请求病史采集 Agent
            asyncio.get_event_loop().run_in_executor(None, medical_dialogue, response_queue, query_data, metadata, tracker)

    except Exception as search_ex:
        service_logger.error(f"failed to do search: {str(search_ex)}, stack: {traceback.format_exc()}")
        metadata.update({"message": str(search_ex)})
        response_queue.put(StreamSearchData.build_from_error(dialog_id, metadata))
        response_queue.put(None)

    finally:
        async def flush():
            try:
                await finished_event.wait()
                tracker.store_message(dialog_id, message_id, data.get("sources"), domain=domain)
            except asyncio.CancelledError:
                service_logger.warning("asyncio.CancelledError in flush")
            except Exception as flush_ex:
                service_logger.error(f"flush failed: {flush_ex}")

        asyncio.create_task(flush())
        return StreamingResponse(response_queue.subscribe(), media_type="text/event-stream", status_code=200)


async def build_dialogue_query(dialog_id, raw_query, enable_think):
    # 组装历史对话
    chat_history, diagnose_finished = get_ai_doctor_chat_history(dialog_id)
    chat_history.append({
            "role": "user",
            "content": raw_query
        })
    
    # 构建 model_query
    dialogue_query_data = {
        "chat_history": chat_history,
        "diagnose_finished": diagnose_finished,
    }

    # 获取病人信息
    patient_info = treatment_info_manager.get_by_dialog_id(dialog_id)
    if patient_info:
        # 基本信息和历史病例总结（异步生成），如果有的话就传，没有就不传
        if "patient_info" in patient_info and len(patient_info["patient_info"]) > 0:
            dialogue_query_data["patient_base_info"] = patient_info["patient_info"]
        if "history_context" in patient_info and len(patient_info["history_context"]) > 0:
            dialogue_query_data["patient_context_info"] = patient_info["history_context"]

    if enable_think:
        dialogue_query_data["enable_think"] = enable_think

    return dialogue_query_data


# 获取 OSS 信息
@router.get("/oss_policy")
async def oss_policy(request: Request, requester: User = Depends(authenticate)):
    # 参数合法性检查
    dialog_id = request.query_params.get("dialog_id", None)
    if not dialog_id:
        raise HTTPException(status_code=400, detail="dialog_id is required")
    
    # 检查 dialog_id 与 Token 是否合法
    check_user_dialog_id(requester, dialog_id)

    try:
        if service_config.image_fs_type == "oss":
            policy = oss_client.get_oss_policy()
        elif service_config.image_fs_type == "minio":
            policy = minio_client.get_policy()
        else:
            raise HTTPException(status_code=400, detail="invalid image_fs_type")
        return JSONResponse({
            AppResponse.status_code: StatusCode.Success,
            AppResponse.message: "get oss policy ok",
            "data": policy
        })
    except:
        return JSONResponse({
            AppResponse.status_code: StatusCode.InternalError,
            AppResponse.message: "get oss policy fail",
            "data": {}
        })


# 上传报告
@router.post("/submit_report")
async def submit_report(request: Request, requester: User = Depends(authenticate)):
    # 参数合法性检查
    request_json = await request.json()
    # 从request_json 中获取 dialog_id / file_name / file_type / file_oss_key
    dialog_id = request_json.get("dialog_id")
    file_name = request_json.get("file_name")
    file_type = request_json.get("file_type")
    file_oss_key = request_json.get("file_oss_key")
    storage_type = request_json.get("storage_type", service_config.image_fs_type)
    
    # 检查参数是否齐全
    if not dialog_id or not file_name or not file_type or not file_oss_key:
        return JSONResponse({
            AppResponse.status_code: StatusCode.BadRequest,
            AppResponse.message: "missing required fields",
            "data": {}
        })

    # 检查 dialog_id 与 Token 是否合法
    check_user_dialog_id(requester, dialog_id)

    # 将上传报告的任务写入任务队列中
    task_id = task_manager.add_task(
        task_type="upload_report", 
        params={
            "dialog_id": dialog_id, 
            "file_name": file_name, 
            "file_type": file_type, 
            "file_oss_key": file_oss_key,
            "storage_type": storage_type,
            "treatment_id": requester.treatment_id,
        }
    )

    # 如果任务写入失败，返回错误
    if not task_id:
        return JSONResponse({
            AppResponse.status_code: StatusCode.InternalError,
            AppResponse.message: "submit report fail",
            "data": {}
        })

    # 将上传报告的事件写入对话历史中，以便重新加载对话时显示这里上传了报告
    dialog_manager.upsert_message(
        content={
            "type": "report",
            "task_id": task_id, 
            "file_name": file_name, 
            "file_type": file_type, 
            "file_oss_key": file_oss_key,
            "storage_type": storage_type
        },
        dialog_id=dialog_id,
        message_id=task_id,
        sources={},
        cost=0.0,
        domain=DOMAIN_AI_DOCTOR,
        enable_think=None
    )

    return JSONResponse({
        AppResponse.status_code: StatusCode.Success,
        AppResponse.message: "submit report ok",
        "data": {
            "report_id": task_id,
            "file_name": file_name, 
            "file_type": file_type, 
            "file_oss_key": file_oss_key,
            "storage_type": storage_type
        }
    })


# 删除上传的图片报告，
@router.post("/delete_report")
async def delete_report(request: Request, requester: User = Depends(authenticate)):
    # 参数合法性检查
    data = await request.json()
    dialog_id = data.get("dialog_id", None)
    if not dialog_id:
        raise HTTPException(status_code=400, detail="dialog_id is required")
    
    report_id = data.get("report_id", None)
    if not report_id:
        raise HTTPException(status_code=400, detail="report_id is required")
    
    # 检查 dialog_id 与 Token 是否合法
    check_user_dialog_id(requester, dialog_id)

    # 更新任务队列中的 task 状态为 Cancel
    task_manager.update_task_status(task_id=report_id, task_status=TaskStatus.CANCEL)

    # 删除对话中的报告
    dialog_manager.delete_message(message_id=report_id)

    return JSONResponse({
        "code": 0,
        "msg": "ok"
    })


# 提交候诊
@router.post("/submit_to_wait")
async def submit_to_wait(request: Request, requester: User = Depends(authenticate)):
    # 参数合法性检查
    data = await request.json()
    dialog_id = data.get("dialog_id", None)
    if not dialog_id:
        raise HTTPException(status_code=400, detail="dialog_id is required")

    # 检查 dialog_id 与 Token 是否合法
    check_user_dialog_id(requester, dialog_id)

    # 构建异步任务，生成并保存电子病历
    # 生成电子病历 -> 生成诊断结论 -> 生成历史总结+处置方案
    task_id = task_manager.add_task(
        task_type="generate_first_electronic_report",
        params={
            "dialog_id": dialog_id,
            "treatment_id": requester.treatment_id,
        }
    )

    redirect = False
    if DIRECT_TO_DOCTOR_WORKSTATION and (DIRECT_TO_DOCTOR_WORKSTATION is True or DIRECT_TO_DOCTOR_WORKSTATION == "true"):
        redirect = True

    if task_id is None:
        return JSONResponse({
            "code": 500,
            "msg": "failed to generate electronic report",
            "data": {
                "redirect": redirect,
                "redirect_url": DOCTOR_WORKSTATION_URL,
            }
        })

    return JSONResponse({
        "code": 0,
        "msg": "ok",
        "data": {
            "task_id": task_id,
            "redirect": redirect,
            "redirect_url": DOCTOR_WORKSTATION_URL,
        }
    })


# 请求获取初版的电子病历（由患者第一次提交候诊产生）以及初步诊断结论，诊断结论为数字虚拟人说话内容。
@router.get("/get_electronic_report")
async def get_electronic_report(request: Request, requester: User = Depends(authenticate)):
    # 参数合法性检查
    dialog_id = request.query_params.get("dialog_id", None)
    if not dialog_id:
        raise HTTPException(status_code=400, detail="dialog_id is required")

    # 检查 dialog_id 与 Token 是否合法
    check_user_dialog_id(requester, dialog_id)

    treatment_id = requester.treatment_id

    # 获取所有电子病历
    electronic_reports = medical_record_manager.get_by_treatment_id(treatment_id)
    if electronic_reports is None or len(electronic_reports) == 0:
        return JSONResponse({
            "code": 0,
            "msg": "ok",
            "data": {
            }
        })
    
    data = {}

    # 获取第一版电子病历
    first_electronic_report = electronic_reports[-1]
    if "electronic_report" in first_electronic_report:
        data["electronic_report"] = first_electronic_report["electronic_report"]

    # 获取初步诊断结论
    treatment_info = treatment_info_manager.get_by_treatment_id(treatment_id)
    if "diagnosis_text" in treatment_info and len(treatment_info["diagnosis_text"]) > 0:
        data["diagnosis_text"] = treatment_info["diagnosis_text"]

    # 获取最早一版的诊断信息
    if "medical_diagnosis" in treatment_info and len(treatment_info["medical_diagnosis"]) > 0:
        all_medical_diagnosis = treatment_info["medical_diagnosis"]
        # 根据 created_at 排序，获取最早的诊断信息
        medical_diagnosis = sorted(all_medical_diagnosis.values(), key=lambda x: x["created_at"], reverse=False)[0]
        data["medical_diagnosis"] = medical_diagnosis

    service_logger.info(f"get_electronic_report: {data}")
    return JSONResponse({
        "code": 0,
        "msg": "ok",
        "data": data
    })


if __name__ == "__main__":
    query_data = asyncio.run(build_dialogue_query(dialog_id="6810c9925053c5a2c4fbe241", raw_query="没有了", enable_think=True))
    print(query_data)