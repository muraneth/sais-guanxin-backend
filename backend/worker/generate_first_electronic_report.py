import asyncio
import time
import uuid
import nest_asyncio

from service.repository.mongo_dialog_manager import get_ai_doctor_chat_history
from service.repository.mongo_task_manager import task_manager, TaskStatus
from service.repository.mongo_medical_record_manager import medical_record_manager
from util.logger import service_logger
from agents.electronic_report import electronic_report
from agents.electronic_report_fix import fix_electronic_report
from service.config.config import IS_DEMO_MODE

# 应用 nest_asyncio 补丁
nest_asyncio.apply()

def generate_first_electronic_report(task_id, task_params):
    dialog_id = task_params.get("dialog_id")
    treatment_id = task_params.get("treatment_id")
    
    # 获取历史对话
    chat_history_with_appendix, _ = get_ai_doctor_chat_history(dialog_id=dialog_id, show_appendix=True)
    service_logger.info(f"chat_history_with_appendix: {chat_history_with_appendix}")

    # 检查图片报告是否完成解析
    previous_auxiliary_report = []
    chat_history = []
    for item in chat_history_with_appendix:
        content = item.get("content")
        if content is None:
            continue
        if isinstance(content, dict) and item.get("appendix"):
            # 目前只处理图片报告类型
            if content.get("type") == "report" and content.get("file_oss_key") is not None:
                # 检查图片报告是否完成解析
                report_task_id = content.get("task_id")
                report_task = task_manager.get_by_task_id(report_task_id)
                service_logger.info(f"report_task: {report_task}")
                report_task_status = report_task.get("status")
                if report_task_status == TaskStatus.COMPLETED.value:
                    # 图片报告解析完成
                    previous_auxiliary_report.append({
                        "report_id": report_task_id,
                        "content": report_task.get("result").get("result")
                    })
                elif report_task_status == TaskStatus.FAIL.value or report_task_status == TaskStatus.CANCEL.value:
                    # 图片报告解析失败，或者被取消
                    continue
                elif report_task_status == TaskStatus.PROCESSING.value:
                    # 图片报告解析未完成，等待
                    while True:
                        report_task = task_manager.get_by_task_id(report_task_id)
                        report_task_status = report_task.get("status")
                        if report_task_status == TaskStatus.COMPLETED.value:
                            previous_auxiliary_report.append({
                                "report_id": report_task_id,
                                "content": report_task.get("result").get("result")
                            })
                            break
                        time.sleep(5)
                elif report_task_status == TaskStatus.PENDING.value:
                    # 图片报告解析未开始，把该产生电子病历的任务重新加入队列
                    task_manager.add_task(task_id, task_params)
                    return TaskStatus.PENDING
        else:
            chat_history.append(item)
    
    service_logger.info(f"task_id: {task_id}, treatment_id: {treatment_id}, dialog_id: {dialog_id}, chat_history: {chat_history}, previous_auxiliary_report: {previous_auxiliary_report}")
    # 生成电子病历
    electronic_report_result = electronic_report(chat_history, previous_auxiliary_report, [], True)
    if electronic_report_result is None:
        service_logger.error(f"failed to generate electronic report, chat_history: {chat_history}, previous_auxiliary_report: {previous_auxiliary_report}")
        return TaskStatus.FAIL
    
    electronic_report_result["treatment_id"] = treatment_id
    electronic_report_result["dialog_id"] = dialog_id
    service_logger.info(f"electronic_report_result old: {electronic_report_result}")
   
    original_report = electronic_report_result["electronic_report"]
    electronic_report_result["electronic_report_old"] = original_report

    # Get fixed report with extended timeout (120 seconds)
    try:
        service_logger.info(f"Starting electronic report fix for treatment_id: {treatment_id}")
        fixed_report = fix_electronic_report(original_report, timeout_seconds=120)
        
        if fixed_report and isinstance(fixed_report, dict):
            electronic_report_result["electronic_report"] = fixed_report
            service_logger.info(f"Successfully fixed electronic report for treatment_id: {treatment_id}")
        else:
            service_logger.warning(f"Invalid response from fix_electronic_report for treatment_id: {treatment_id}, keeping original")
            
    except Exception as e:
        service_logger.error(f"Failed to fix electronic report for treatment_id: {treatment_id}, error: {str(e)}")
        service_logger.error(f"Keeping original electronic report due to fix failure")
        # Keep the original report if fix fails
        
    service_logger.info(f"electronic_report_result final: {electronic_report_result}")
    # 保存电子病历
    medical_record_manager.insert_medical_record(electronic_report_result)

    # 随机生成 diagnose_id 和 treatment_plan_id
    diagnose_id = str(uuid.uuid4())
    treatment_plan_id = str(uuid.uuid4())

    # 异步生成最初版本的诊断和治疗方案
    task_manager.add_task(
        task_type="generate_diagnosis_and_treatment_plan",
        params={
            "treatment_id": treatment_id,
            "diagnose_id": diagnose_id,
            "treatment_plan_id": treatment_plan_id,
            "source": "generate_first_electronic_report"
        }
    )

    return TaskStatus.COMPLETED


if __name__ == "__main__":
    print(generate_first_electronic_report(task_id="67ff5a330ca23fcaa5e7097g", task_params={"dialog_id": "6809b66a1dbca758f6329359", "treatment_id": "af76907b-09b3-4af5-8d62-a71a085c9e86"}))
    #chat_history_with_appendix, _ = asyncio.run(get_ai_doctor_chat_history(dialog_id="6809b66a1dbca758f6329359", show_appendix=True))
    #service_logger.info(f"chat_history_with_appendix: {chat_history_with_appendix}")