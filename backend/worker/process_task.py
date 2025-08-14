import socket
import uuid
import time

from util.logger import service_logger
from service.repository.mongo_task_manager import task_manager, TaskStatus

from worker.process_upload_report import process_upload_report
from worker.summarize_history_data import summarize_history_data
from worker.generate_first_electronic_report import generate_first_electronic_report
from worker.generate_diagnosis_and_treatment_plan import generate_diagnosis_and_treatment_plan
from worker.generate_treatment import generate_treatment
from worker.check_examine_result import check_examine_result
from worker.process_examine_result import process_examine_result
# 获取当前host的name作为worker的id
worker_id = socket.gethostname()+"_"+str(uuid.uuid4())[:8]

job_map = {
    "upload_report": process_upload_report,
    "summarize_history_data": summarize_history_data,
    "generate_first_electronic_report": generate_first_electronic_report,
    "generate_diagnosis_and_treatment_plan": generate_diagnosis_and_treatment_plan,
    "generate_treatment": generate_treatment,
    "check_examine_result": check_examine_result,
    "process_examine_result": process_examine_result,
}

def process_pending_tasks():
    # 从任务队列中获取任务
    tasks = task_manager.find_pending_tasks()
    for task in tasks:
        # 获取任务状态
        task_status = task.get("status")
        if task_status != TaskStatus.PENDING.value:
            continue

        # 获取任务id
        task_id = task.get("task_id")
        
        success = task_manager.acquire_lock(task_id, worker_id)
        if not success:
            continue

        service_logger.info(f"acquire task lock, task_id: {task_id}, worker_id: {worker_id}")

        # 获取任务类型
        task_type = task.get("task_type")
        
        # 任务计时开始
        start_time = time.time()
        
        # 执行任务
        task_result_status = None
        if task_type in job_map:
            # 获取任务参数
            task_params = task.get("params")
            service_logger.info(f"start task: {task_type}, id: {task_id}, params: {task_params}")
            # TODO：临时取消重试，后续需要优化
            for i in range(1):
                task_result_status = job_map[task_type](task_id, task_params)
                if task_result_status == TaskStatus.FAIL:
                    service_logger.error(f"task failed, task_id: {task_id}, worker_id: {worker_id}, task_type: {task_type}, retry: {i}")
                    time.sleep(1)
                else:
                    break
        else:
            # 未知任务类型
            service_logger.error(f"unknown task type: {task_type}, task_id: {task_id}, worker_id: {worker_id}")
            task_result_status = TaskStatus.FAIL

        # 任务计时结束
        end_time = time.time()

        # 释放任务锁
        service_logger.info(f"release task lock, task_id: {task_id}, worker_id: {worker_id}, task_result_status: {task_result_status}, cost: {end_time - start_time} seconds")
        task_manager.release_lock(
            task_id=task_id, 
            worker_id=worker_id, 
            task_status=task_result_status, 
            time_cost=end_time - start_time
        )


