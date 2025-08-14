import uuid
import traceback

from service.repository.mongo_task_manager import TaskStatus, task_manager
from service.repository.mongo_treatment_info import treatment_info_manager
from service.repository.mongo_medical_record_manager import medical_record_manager
from agents.report_summary import report_summary
from util.logger import service_logger
from util.minio_client import minio_client
from util.ocr_client import ocr_client
from util.oss import oss_client


def process_examine_result(task_id, task_params):
    # 参数合法性检查
    treatment_id = task_params.get("treatment_id")
    if not treatment_id:
        service_logger.error(f"treatment_id is required, task_id: {task_id}, task_params: {task_params}")
        return TaskStatus.FAIL
    
    # 下载检查结果
    try:
        # 默认使用oss
        storage_type = "oss"
        if "storage_type" in task_params:
            storage_type = task_params.get("storage_type")
        # 保存文件的oss_key
        file_oss_key = task_params.get("file_oss_key")
        # 获取文件url
        if storage_type == "oss":
            file_url = oss_client.get_file_url(file_oss_key=file_oss_key)
        elif storage_type == "minio":
            file_url = minio_client.get_file_url(file_oss_key=file_oss_key)
        else:
            service_logger.error(f"unknown storage_type: {storage_type}")
            return TaskStatus.FAIL
        service_logger.info(f"task_id: {task_id}, file_oss_key: {file_oss_key}, storage_type: {storage_type}, file_url: {file_url}")
    except:
        service_logger.error(traceback.format_exc())
        return TaskStatus.FAIL
    
    # 调用OCR接口识别检查结果
    result = ocr_client.process_image(image_url=file_url)
    service_logger.info(f"task_id: {task_id}, ocr result: {result}")

    ocr_content = ""
    if isinstance(result, dict) and "result" in result:
        ocr_content = result.get("result", "")
    
    # 保存检查报告
    service_logger.info(f"update examine result, treatment_id: {treatment_id}, ocr result: {ocr_content}")
    treatment_info_manager.update_examine_result(treatment_id, task_id, "content", ocr_content)

    # 取回所有的检验检查报告
    treatment_info = treatment_info_manager.get_by_treatment_id(treatment_id)
    examine_result = {}
    if "examine_result" in treatment_info:
        examine_result = treatment_info["examine_result"]
        
    # 检查是否存在 content
    content_list = []
    for examine_result_id, examine_result_data in examine_result.items():
        if "content" in examine_result_data:
            content_list.append(examine_result_data["content"])

    if len(content_list) == len(examine_result):
        # 每一个检查结果都有内容，则调用 Agent 总结所有的检验检查检查结果
        summary_result = report_summary("\n".join(content_list))

        if summary_result is None or summary_result == "":
            service_logger.error(f"summary_result is empty, task_id: {task_id}, treatment_id: {treatment_id}, content_list: {content_list}")
            return TaskStatus.FAIL

        # 触发电子病历更新 - 将总结后的检查结果写入电子病历（辅助检查）
        success, msg = medical_record_manager.update_last_record(treatment_id, "辅助检查", summary_result)
        if success:
            service_logger.info(f"success to update last medical record, summary_result: {summary_result}, task_id: {task_id}, treatment_id: {treatment_id}, msg: {msg}")
        else:
            service_logger.error(f"failed to update last medical record, summary_result: {summary_result}, task_id: {task_id}, treatment_id: {treatment_id}, msg: {msg}")
            return TaskStatus.FAIL

        # 随机生成 diagnose_id 和 treatment_plan_id
        diagnose_id = str(uuid.uuid4())
        treatment_plan_id = str(uuid.uuid4())

        # 因为加入了辅助检查，所以需要重新生成诊断和处置
        task_manager.add_task(
            task_type="generate_diagnosis_and_treatment_plan",
            params={
                "treatment_id": treatment_id,
                "diagnose_id": diagnose_id,
                "treatment_plan_id": treatment_plan_id,
                "source": "upload_examine_result"
            }
        )
    return TaskStatus.COMPLETED


if __name__ == "__main__":
    print(process_examine_result("123", {"treatment_id": "10_880345832", "file_oss_key": "home/health/app/user_reports/knowledge_assistant/6a2760a1-ee8d-4c82-a15c-5d1c7f56b8d3.png"}))
