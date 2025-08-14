import datetime
import uuid
from service.package.hospital_info_sys import get_report
from service.repository.mongo_task_manager import TaskStatus, task_manager
from service.repository.mongo_treatment_info import treatment_info_manager
from service.repository.mongo_medical_record_manager import medical_record_manager
from agents.report_summary import report_summary
from util.logger import service_logger
from service.config.config import service_config, IS_DEMO_MODE

def check_examine_result(task_id, task_params):
    treatment_id = task_params.get("treatment_id")
    if not treatment_id:
        service_logger.error(f"treatment_id is required, task_id: {task_id}, task_params: {task_params}")
        return TaskStatus.FAIL
    
    date = task_params.get("date")
    if not date:
        service_logger.error(f"date is required, task_id: {task_id}, task_params: {task_params}")
        return TaskStatus.FAIL
    
    # 通过医院 HIS 系统获取检查报告
    report_result = get_report(treatment_id)
    if not report_result:
        # 检查报告获取失败
        return TaskStatus.FAIL
    
    # 检查报告为空，继续等待
    if isinstance(report_result, list) and len(report_result) == 0:
        # 判断 date 是否为今天，如果是今天则继续等待，否则返回成功
        if date == datetime.now().strftime("%Y-%m-%d"):
            # 添加延迟任务，继续等待
            task_manager.add_task(
                task_type="check_examine_result",
                params={
                    "treatment_id": treatment_id,
                    "date": date
                },
                delay=service_config.check_examine_result_delay
            )
        else:
            service_logger.info(f"no examine result, treatment_id: {treatment_id}")
        return TaskStatus.COMPLETED
    
    # 保存检查报告
    service_logger.info(f"save examine result, treatment_id: {treatment_id}, examine_result: {report_result}")
    if isinstance(report_result, list): 
        for examine_result in report_result:
            examine_result_id = str(uuid.uuid4())
            if not treatment_info_manager.insert_examine_result(treatment_id, examine_result_id, examine_result):
                service_logger.error(f"failed to insert examine result")
                return TaskStatus.FAIL
    else:
        examine_result_id = str(uuid.uuid4())
        if not treatment_info_manager.insert_examine_result(treatment_id, examine_result_id, report_result):
            service_logger.error(f"failed to insert examine result")
            return TaskStatus.FAIL

    # 调用 Agent 总结检查结果
    summary_result = report_summary(report_result)

    # 触发电子病历更新 - 将总结后的检查结果写入电子病历（辅助检查）
    medical_record_manager.update_last_record(treatment_id, "辅助检查", summary_result)

    if IS_DEMO_MODE:
        # 随机生成 diagnose_id 和 treatment_plan_id
        diagnose_id = str(uuid.uuid4())
        treatment_plan_id = str(uuid.uuid4())

        # 异步重新生成诊断和处置（加入了辅助检查）
        task_manager.add_task(
            task_type="generate_diagnosis_and_treatment_plan",
            params={
                "treatment_id": treatment_id,
                "diagnose_id": diagnose_id,
                "treatment_plan_id": treatment_plan_id,
                "source": "check_examine_result"
            }
        )
    return TaskStatus.COMPLETED


if __name__ == "__main__":
    print(check_examine_result("123", {"treatment_id": "10_877621196"}))
    print(check_examine_result("123", {"treatment_id": "10_880653606"}))
