import uuid
from datetime import datetime
from service.package.hospital_info_sys import get_history_data
from service.repository.mongo_task_manager import TaskStatus
from service.repository.mongo_treatment_info import treatment_info_manager
from service.repository.mongo_medical_record_manager import medical_record_manager
from agents.medical_summary import medical_summary
from util.logger import service_logger

def summarize_history_data(task_id, task_params):
    treatment_id = task_params.get("treatment_id")
    with_diagnosis_info = task_params.get("with_diagnosis_info", False)

    # 参数检查
    if not treatment_id:
        service_logger.error(f"treatment_id is required")
        return TaskStatus.FAIL
    
    # 调用医院 HIS 系统，获取患者历史就诊记录
    treatment_info = treatment_info_manager.get_by_treatment_id(treatment_id)
    if not treatment_info:
        service_logger.error(f"can not get treatment info from database, treatment_id: {treatment_id}")
        return TaskStatus.FAIL
    
    patient_info = treatment_info["patient_info"]
    if not patient_info:
        service_logger.error(f"can not get patient info from database, treatment_id: {treatment_id}")
        return TaskStatus.FAIL
    
    # 调用医院 HIS 系统，获取患者历史就诊记录
    history_treatment_list = get_history_data(treatment_id)
    if history_treatment_list is None:
        service_logger.error(f"can not get history treatment list from hospital, treatment_id: {treatment_id}")
        history_treatment_list = []
    elif len(history_treatment_list) == 0:
        service_logger.warning(f"get empty history treatment list from hospital, treatment_id: {treatment_id}")
    
    # 保存历史就诊记录到数据库
    treatment_info_manager.update_by_treatment_id(treatment_id, {"history_data": history_treatment_list})
    
    # 已经完成预问诊的阶段，已经有诊断信息
    medical_diagnosis = ""
    if with_diagnosis_info:
        # 需要获取最新的诊断
        medical_diagnosis = treatment_info_manager.get_latest_medical_diagnosis(treatment_id)
        if not medical_diagnosis:
            service_logger.error(f"can not get latest medical diagnosis from database, treatment_id: {treatment_id}")
            return TaskStatus.FAIL
        # 调用大模型生成总结，注意字段对齐
        diagnosis_info = medical_diagnosis["初步诊断"]["主要诊断"]["名称"]
        history_summary = medical_summary(patient_info=patient_info, diagnosis_info=diagnosis_info, treatment_list=history_treatment_list, report_info=None)
        #print(f"history_summary: {history_summary}")
        if not history_summary:
            service_logger.error(f"failed to get history summary, task_id: {task_id}, treatment_id: {treatment_id}")
            return TaskStatus.FAIL
        
        # 保存总结到数据库
        treatment_info_manager.update_by_treatment_id(treatment_id, {"history_summary": history_summary})

    else:
        # 还没有完成预问诊，没有诊断信息
        # 需要调用大模型对历史就诊记录进行总结，作为和患者多轮问诊的上下文
        # TODO：调用初次总结 Agent
        history_context = ""
        treatment_info_manager.update_by_treatment_id(treatment_id, {"history_context": history_context})
        pass
    
    return TaskStatus.COMPLETED

if __name__ == "__main__":
    result = summarize_history_data(task_id="68106ca196128e91f4343a72", task_params={"treatment_id": "10_874944831", "with_diagnosis_info": True})
    print(result)