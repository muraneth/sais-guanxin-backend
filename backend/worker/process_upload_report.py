import traceback
import json
from service.repository.mongo_task_manager import task_manager, TaskStatus
from util.oss import oss_client
from util.minio_client import minio_client
from util.ocr_client import ocr_client
from util.logger import service_logger

# 支持 oss 和 minio
def process_upload_report(task_id, task_params):
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
    
    # 调用OCR接口
    result = ocr_client.process_image(image_url=file_url)
    service_logger.info(f"task_id: {task_id}, result: {result}")

    # 更新任务结果
    update_result = task_manager.update_task(task_id, result)
    if not update_result:
        return TaskStatus.FAIL

    return TaskStatus.COMPLETED if result.get("status") == 0 else TaskStatus.FAIL


def get_report_info_by_id(task_id: str):
    task = task_manager.get_by_task_id(task_id)
    if not task:
        service_logger.error(f"report not found, report_id: {task_id}")
        return None
    # task result 是 json string，当中嵌套 result
    task_result = task.get("result")
    if task_result is None:
        return None
    # 这一层是 OCR client 返回的结果
    task_result = task_result.get("result")
    if task_result is None:
        return None
    # 如果 task_result 是 str，则直接添加到 additional_info_list
    if isinstance(task_result, str):
        return task_result
    # 如果 task_result 是 dict，则需要确定算法侧需要 result 中的 doc_str 字段
    elif isinstance(task_result, dict):
            # 确定算法侧需要 result 中的 doc_str 字段
        doc_str = task_result.get("Doc_Str")
        if doc_str and doc_str != "":
            return doc_str
        else:
            result_str = json.dumps(task_result, ensure_ascii=False)
            return result_str
    else:
        service_logger.error(f"unknown task_result: {task_result}")
        return None
    
if __name__ == "__main__":
    print(process_upload_report(task_id="123", task_params={
        "file_oss_key": "home/health/app/user_reports/knowledge_assistant/054d4e72-b782-4272-adab-351d2ed76919.png",
        "storage_type": "oss"
    }))