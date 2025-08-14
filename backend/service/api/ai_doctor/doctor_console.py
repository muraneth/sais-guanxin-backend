import uuid
from datetime import datetime
from fastapi import APIRouter, Depends
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from service.config.config import IS_DEMO_MODE
from service.repository.mongo_dialog_manager import dialog_manager
from service.repository.mongo_treatment_info import treatment_info_manager
from service.repository.mongo_dialog_manager import get_ai_doctor_chat_history
from service.repository.mongo_medical_record_manager import medical_record_manager
from service.repository.mongo_feedback import mongo_feedback_manager
from service.repository.mongo_task_manager import task_manager, TaskStatus
from service.package.hospital_info_sys import upload_ai_emr
from worker.process_upload_report import get_report_info_by_id
from util.oss import oss_client
from util.logger import service_logger

router = APIRouter(
    prefix="/api/doctor"
)

"""
医生后台管理
接口设计文档：https://inflytech.feishu.cn/wiki/XsfhwkPBri7Pbjkv8E1czAJnngh
"""

def get_dialog_by_treatment_id(treatment_id: str = None, show_appendix: bool = False):
    # treatment_id 转换为 dialog_id
    dialog = dialog_manager.get_dialog_by_treatment_id(treatment_id)
    # 获取对话历史
    chat_history, diagnose_finished = get_ai_doctor_chat_history(str(dialog["_id"]), show_appendix)
    return chat_history


# 重新运行任务
@router.post("/rerun_task")
async def rerun_task(request: Request):
    data = await request.json()
    task_id = data.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id is required")
    
    task = task_manager.get_by_task_id(task_id)
    if not task:
        raise HTTPException(status_code=400, detail="task not found")
    
    task_manager.update_task_status(task_id, TaskStatus.PENDING)
    return JSONResponse({
        "code": 0,
        "msg": "ok",
    })
    

@router.get("/get_execution_progress")
async def get_execution_progress(request: Request):
    treatment_id = request.query_params.get("treatment_id")
    if not treatment_id:
        raise HTTPException(status_code=400, detail="treatment_id is required")
    
    tasks = task_manager.find_task_by_treatment_id(treatment_id)

    # 判断任务是否成功完成
    def task_not_completed(task_status):
        return task_status == TaskStatus.PENDING.value or task_status == TaskStatus.PROCESSING.value
    # 判断当前处于哪个阶段
    def get_current_stage(tasks):
        for task in tasks:
            task_type, task_status = task["task_type"], task["status"]
            if task_type == "upload_report" and task_not_completed(task_status):
                # 第一阶段
                return "report_text_extract", "识别报告内容"
            elif (task_type == "generate_first_electronic_report" or task_type == "summarize_history_data") and task_not_completed(task_status):
                # 第二阶段
                return "emr_generation", "生成电子病历"
            elif (task_type == "generate_diagnosis_and_treatment_plan" or task_type == "generate_treatment") and task_not_completed(task_status):
                source = task.get("params", {}).get("source", "")
                if source == "generate_first_electronic_report":
                    # 第三阶段
                    return "diagnose_generation", "生成初步诊断"
        
        return "completed", "完成"
    
    stage, stage_text = get_current_stage(tasks)

    # 将 tasks 中的 task_id 转换为 _id
    return JSONResponse({
        "code": 0,
        "msg": "ok",
        "data": {
            "tasks": tasks,
            "stage": stage,
            "stage_text": stage_text
        }
    })

@router.get("/get_all_treatments")
async def get_all_treatments(request: Request):
    raw_treatments = treatment_info_manager.get_all_treatments()
    treatments = []
    # 保留部分信息
    for treatment in raw_treatments:
        treatments.append({
            "treatment_id": treatment["treatment_id"],
            "patient_info": treatment["patient_info"],
            "created_at": treatment["created_at"]
        })
    # 返回
    return JSONResponse({
        "code": 0,
        "msg": "ok",
        "data": {
            "treatments": treatments
        }
    })


# 获取患者信息
@router.get("/get_patient_info")
async def get_patient_info(request: Request):
    treatment_id = request.query_params.get("treatment_id")
    if not treatment_id:
        raise HTTPException(status_code=400, detail="treatment_id is required")
    
    # 从数据库中获取患者信息
    treatment_info = treatment_info_manager.get_by_treatment_id(treatment_id)
    if not treatment_info:
        # 400 和 文案不要改，前端依赖这个判断是否存在患者信息
        raise HTTPException(status_code=404, detail="can not get patient info from database")
    
    # 从数据库中获取患者历史对话
    chat_history = get_dialog_by_treatment_id(treatment_id, show_appendix=True)

    # 获取患者基本信息
    base_info = {}
    if "patient_info" in treatment_info:
        base_info = treatment_info["patient_info"]

    # 获取患者历史报告
    history_reports = []
    if "history_data" in treatment_info:
        history_reports = treatment_info["history_data"]

    # 获取患者历史总结
    history_summary = ""
    if "history_summary" in treatment_info:
        history_summary = treatment_info["history_summary"]

    return JSONResponse({
        "code": 0,
        "msg": "ok",
        "data": {
            "base_info": base_info,
            "chat_history": chat_history,
            "history_reports": history_reports,
            "history_summary": history_summary
        }
    })   

# 获取患者病历
@router.get("/get_patient_report")
async def get_patient_report(request: Request):
    treatment_id = request.query_params.get("treatment_id")
    if not treatment_id:
        raise HTTPException(status_code=400, detail="treatment_id is required")
    
    # 获取患者病历
    medical_records = medical_record_manager.get_by_treatment_id(treatment_id)
    if not medical_records:
        raise HTTPException(status_code=400, detail="can not get medical records from database")
    if len(medical_records) == 0:
        raise HTTPException(status_code=400, detail="can not get medical records from database")
    
    # 获取最新的一条电子病历
    latest_medical_record = medical_records[0]

    # 添加附加信息
    latest_medical_record["medical_diagnosis"] = treatment_info_manager.get_latest_medical_diagnosis(treatment_id)
    latest_medical_record["treatment_plan"] = treatment_info_manager.get_latest_treatment_plan(treatment_id)
    latest_medical_record["check_recommendation"] = treatment_info_manager.get_latest_check_recommendation(treatment_id)

    return JSONResponse({
        "code": 0,
        "msg": "ok",
        "data": latest_medical_record
    })

# 获取患者历史所有病例
@router.get("/get_history_report")
async def get_history_report(request: Request):
    treatment_id = request.query_params.get("treatment_id")
    if not treatment_id:
        raise HTTPException(status_code=400, detail="treatment_id is required")
    
    medical_records = medical_record_manager.get_by_treatment_id(treatment_id)
    if not medical_records:
        raise HTTPException(status_code=400, detail="can not get medical records from database")
    return JSONResponse({
        "code": 0,
        "msg": "ok",
        "data": {
            "history_report": medical_records
        }
    })
    

# get_patient_appendix
@router.get("/get_patient_appendix")
async def get_patient_appendix(request: Request):
    treatment_id = request.query_params.get("treatment_id")
    if not treatment_id:
        raise HTTPException(status_code=400, detail="treatment_id is required")
    
    # 从历史对话中获取附件
    dialog = get_dialog_by_treatment_id(treatment_id, show_appendix=True)
    result = []
    for message in dialog:
        #print(f"message: {message}")
        content = message.get("content")
        if content and "type" in content and content["type"] == "report":
            if "task_id" in content:
                # 将图片报告的解析内容加入进去
                report_content = get_report_info_by_id(content["task_id"])
                if report_content:
                    content["content"] = report_content
                else:
                    content["content"] = "报告解析失败，请查看报告原图"
            result.append(content)
    return JSONResponse({
        "code": 0,
        "msg": "ok",
        "data": {
            "appendix_list": result
        }
    })


# report_feedback
@router.post("/report_feedback")
async def report_feedback(request: Request):
    data = await request.json()
    treatment_id = data.get("treatment_id")
    if not treatment_id:
        raise HTTPException(status_code=400, detail="treatment_id is required")
    feedback_type = data.get("feedback_type")
    if not feedback_type:
        raise HTTPException(status_code=400, detail="feedback_type is required")
    origin_content = data.get("origin_content")
    if not origin_content:
        raise HTTPException(status_code=400, detail="origin_content is required")
    mongo_feedback_manager.insert_feedback(treatment_id, feedback_type, origin_content)
    return JSONResponse({
        "code": 0,
        "msg": "ok",
    })


# 更新电子病历的某一个字段
@router.post("/update_electronic_report_field")
async def update_electronic_report_field(request: Request):
    # 处理参数
    data = await request.json()
    # 就诊ID
    treatment_id = data.get("treatment_id")
    if not treatment_id or treatment_id == "":
        raise HTTPException(status_code=400, detail="treatment_id is required")
    # 电子病历ID
    medical_record_id = data.get("medical_record_id")
    if not medical_record_id or medical_record_id == "":
        raise HTTPException(status_code=400, detail="medical_record_id is required")
    # 字段
    field = data.get("field")
    if not field or field == "":
        raise HTTPException(status_code=400, detail="field is required")
    # 字段值
    value = data.get("value", "")
    
    # 更新电子病历
    medical_record_manager.update_medical_record(medical_record_id, field, value)
    return JSONResponse({
        "code": 0,
        "msg": "ok",
    })

# get_diagnose
@router.get("/get_diagnose")
async def get_diagnose(request: Request):
    treatment_id = request.query_params.get("treatment_id")
    if not treatment_id:
        raise HTTPException(status_code=400, detail="treatment_id is required") 
    diagnose_id = request.query_params.get("diagnose_id")
    if not diagnose_id:
        raise HTTPException(status_code=400, detail="diagnose_id is required")
    
    treatment_info = treatment_info_manager.get_by_treatment_id(treatment_id)
    if not treatment_info:
        raise HTTPException(status_code=400, detail="can not get treatment info from database")
    
    if "medical_diagnosis" in treatment_info and diagnose_id in treatment_info["medical_diagnosis"]:
        return JSONResponse({
            "code": 0,
            "msg": "ok",
            "data": treatment_info["medical_diagnosis"][diagnose_id]
        }) 
    else:
        return JSONResponse({
            "code": 0,
            "msg": "ok",
            "data": {}
        })
    

# generate_diagnose
# 既生成诊断，也生成治疗方案
@router.post("/generate_diagnose")
async def generate_diagnose(request: Request):
    data = await request.json()
    treatment_id = data.get("treatment_id")
    if not treatment_id:
        raise HTTPException(status_code=400, detail="treatment_id is required")
    
    # 随机生成 diagnose_id 和 treatment_plan_id
    diagnose_id = str(uuid.uuid4())
    treatment_plan_id = str(uuid.uuid4())

    # 异步生成诊断和治疗方案
    task_manager.add_task(
        task_type="generate_diagnosis_and_treatment_plan",
        params={
            "treatment_id": treatment_id,
            "diagnose_id": diagnose_id,
            "treatment_plan_id": treatment_plan_id,
            "source": "doctor_console"
        }
    )
    # 返回 task_id 给前端
    return JSONResponse({
        "code": 0,
        "msg": "ok",
        "data": {
            "diagnose_id": diagnose_id,
            "treatment_plan_id": treatment_plan_id
        }
    })


# get_treatment_plan
@router.get("/get_treatment_plan")
async def get_treatment_plan(request: Request):
    treatment_id = request.query_params.get("treatment_id")
    if not treatment_id:
        raise HTTPException(status_code=400, detail="treatment_id is required")
    treatment_plan_id = request.query_params.get("treatment_plan_id")
    if not treatment_plan_id:
        raise HTTPException(status_code=400, detail="treatment_plan_id is required")    
        
    treatment_info = treatment_info_manager.get_by_treatment_id(treatment_id)
    if not treatment_info:
        raise HTTPException(status_code=400, detail="can not get treatment info from database")
    
    if "treatment_plan" in treatment_info and treatment_plan_id in treatment_info["treatment_plan"] and "check_recommendation" in treatment_info and treatment_plan_id in treatment_info["check_recommendation"]:
        return JSONResponse({
            "code": 0,
            "msg": "ok",
            "data": {
                "treatment_plan": treatment_info["treatment_plan"][treatment_plan_id],
                "check_recommendation": treatment_info["check_recommendation"][treatment_plan_id]
            }
        })
    else:
        return JSONResponse({
            "code": 0,
            "msg": "ok",
            "data": {}
        })  
    

# generate_treatment_plan
@router.post("/generate_treatment_plan")
async def generate_treatment_plan(request: Request):
    data = await request.json()
    treatment_id = data.get("treatment_id")
    if not treatment_id:
        raise HTTPException(status_code=400, detail="treatment_id is required")
    diagnose_id = data.get("diagnose_id")
    if not diagnose_id:
        raise HTTPException(status_code=400, detail="diagnose_id is required")
    
    # 随机生成 treatment_plan_id
    treatment_plan_id = str(uuid.uuid4())

    task_manager.add_task(
        task_type="generate_treatment",
        params={
            "treatment_id": treatment_id,
            "diagnose_id": diagnose_id,
            "treatment_plan_id": treatment_plan_id
        }
    )
    # 返回 task_id 给前端
    return JSONResponse({
        "code": 0,
        "msg": "ok",
        "data": {
            "treatment_plan_id": treatment_plan_id
        }
    })


# 获取 OSS 信息
@router.get("/pc_oss_policy")
async def pc_oss_policy(request: Request):
    try:
        oss_policy = oss_client.get_oss_policy()
        return JSONResponse({
            "code": 0,
            "msg": "ok",
            "data": oss_policy
        })
    except:
        return JSONResponse({
            "code": 500,
            "msg": "get oss policy fail",
            "data": {}
        })
    

@router.post("/upload_examine_result")
async def upload_examine_result(request: Request):
    data = await request.json()
    treatment_id = data.get("treatment_id")
    if not treatment_id:
        raise HTTPException(status_code=400, detail="treatment_id is required")
    
    file_name = data.get("file_name")
    file_type = data.get("file_type")
    file_oss_key = data.get("file_oss_key")
    storage_type = "oss"
    if "storage_type" in data:
        storage_type = data.get("storage_type")
    
    # 检查参数是否齐全
    if not file_name or not file_type or not file_oss_key:
        raise HTTPException(status_code=400, detail="file_name, file_type, file_oss_key is required")

    # 将上传报告的任务写入任务队列中
    task_id = task_manager.add_task(
        task_type="process_examine_result", 
        params={
            "treatment_id": treatment_id, 
            "file_name": file_name, 
            "file_type": file_type, 
            "file_oss_key": file_oss_key,
            "storage_type": storage_type,
            "source": "upload_examine_result",
        }
    )

    # 如果任务写入失败，返回错误
    if not task_id:
        raise HTTPException(status_code=500, detail="submit examine result fail")
    
    # 写入检查结果
    treatment_info_manager.insert_examine_result(treatment_id, task_id, {
        "file_name": file_name,
        "file_type": file_type,
        "file_oss_key": file_oss_key,
        "storage_type": storage_type
    })

    return JSONResponse({
        "code": 0,
        "msg": "ok",
        "data": {
            "examine_result_id": task_id,
            "file_name": file_name, 
            "file_type": file_type, 
            "file_oss_key": file_oss_key,
            "storage_type": storage_type
        }
    })
    

# 获取检验检查报告
@router.get("/get_examine_result")
async def get_examine_result(request: Request):
    treatment_id = request.query_params.get("treatment_id")
    if not treatment_id:
        raise HTTPException(status_code=400, detail="treatment_id is required")
    
    treatment_info = treatment_info_manager.get_by_treatment_id(treatment_id)
    if not treatment_info:
        raise HTTPException(status_code=400, detail="can not get treatment info from database")
    
    if "examine_result" in treatment_info:
        examine_result = treatment_info["examine_result"]
    else:
        examine_result = {}

    examine_result_list = []
    for examine_result_id, examine_result_data in examine_result.items():
        examine_result_data["id"] = examine_result_id
        examine_result_list.append(examine_result_data)

    all_tasks = task_manager.find_task_by_treatment_id(treatment_id)
    #print(f"all_tasks: {all_tasks}")
    tasks = [task for task in all_tasks if "source" in task["params"] and task["params"]["source"] == "upload_examine_result"]
        
    return JSONResponse({
        "code": 0,
        "msg": "ok",
        "data": {
            "examine_result": examine_result_list,
            "tasks": tasks # 相关的更新诊断和处置的任务，用于前端判断是否需要更新病历中的诊断和处置，前端检查到所有任务的状态都是 completed ，就去刷新一下病历
        }
    })


# submit_final_report
@router.post("/submit_final_report")
async def submit_final_report(request: Request):
    data = await request.json()
    service_logger.info(f"submit_final_report request data: {data}")
    treatment_id = data.get("treatment_id")
    if not treatment_id:
        raise HTTPException(status_code=400, detail="treatment_id is required")
    dialog_id = data.get("dialog_id")
    if not dialog_id:
        raise HTTPException(status_code=400, detail="dialog_id is required")
    section_name = data.get("sectionname")
    if not section_name:
        raise HTTPException(status_code=400, detail="sectionname is required")
    doctor_code = data.get("doctorcode")
    if not doctor_code:
        raise HTTPException(status_code=400, detail="doctorcode is required")
    emr_id = data.get("emr_id", "")
    
    # 获取最后一次电子病历
    # 只有电子病历能改，需要传回，其它都不需要传回
    final_electronic_report = data.get("electronic_report")
    if not final_electronic_report:
        raise HTTPException(status_code=400, detail="electronic_report is required")
    
    # trace_info 有可能没有，不需要检查
    electronic_report_trace_info = data.get("trace_info", {})
    
    # 保存最后一次电子病历
    medical_record_manager.insert_medical_record({
        "treatment_id": treatment_id,
        "dialog_id": dialog_id,
        "electronic_report": final_electronic_report,
        "trace_info": electronic_report_trace_info,
        "source": "doctor_console"
    })

    # 检查是否存在 emr_id
    if len(emr_id) == 0:
        treatment_info = treatment_info_manager.get_by_treatment_id(treatment_id)
        if "emr_id" in treatment_info:
            emr_id = treatment_info["emr_id"]
        else:
            emr_id = ""
    
    # 回写 HIS 系统
    response_data = upload_ai_emr(treatment_id=treatment_id, ai_emr=final_electronic_report, doctor_code=doctor_code, section_name=section_name, emr_id=emr_id)
    status = response_data.get("status", "fail")
    if status != "success":
        raise HTTPException(status_code=500, detail="upload ai emr to his failed")

    emr_id = response_data.get("spare", "")
    if emr_id and emr_id != "":
        treatment_info_manager.update_by_treatment_id(treatment_id=treatment_id, update_data={"emr_id": emr_id})
    
    # 启动定时任务，定时查询检验检查报告
    # if not IS_DEMO_MODE:
    #     task_manager.add_task(
    #         task_type="check_examine_result",
    #         params={
    #             "treatment_id": treatment_id,
    #             "date": datetime.now().strftime("%Y-%m-%d")
    #         },
    #         delay=60*10
    #     )
    
    return JSONResponse({
        "code": 0,
        "msg": "ok",
    })