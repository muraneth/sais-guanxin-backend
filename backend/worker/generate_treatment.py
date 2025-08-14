from service.repository.mongo_task_manager import TaskStatus
from service.repository.mongo_treatment_info import treatment_info_manager
from service.repository.mongo_medical_record_manager import medical_record_manager
from util.logger import service_logger
from agents.medical_treatment import generate_medical_treatment
from agents.check_recommendation import generate_check_recommendation


def generate_treatment(task_id, task_params):
    service_logger.info(f"task_id={task_id}, task_params={task_params}")
    treatment_id = task_params.get("treatment_id")
    diagnose_id = task_params.get("diagnose_id")
    treatment_plan_id = task_params.get("treatment_plan_id")
    check_recommendation_id = task_params.get("treatment_plan_id")
    source = task_params.get("source", "")

    treatment_info = treatment_info_manager.get_by_treatment_id(treatment_id)
    if not treatment_info:
        service_logger.error(f"can not get treatment info from database, treatment_id: {treatment_id}")
        return TaskStatus.FAIL
    
    # 判断是否是演示模式
    demo_mode = treatment_info.get("demo_mode", False)
    
    # 获取病人信息
    if "patient_info" in treatment_info:
        patient_info = treatment_info["patient_info"]
    else:
        service_logger.error(f"can not get patient info from database, treatment_id: {treatment_id}")
        return TaskStatus.FAIL
    
    # 获取诊断信息
    if "medical_diagnosis" in treatment_info and diagnose_id in treatment_info["medical_diagnosis"]:
        medical_diagnosis = treatment_info["medical_diagnosis"][diagnose_id]
        # 不需要传 trace_info 给大模型
        if "trace_info" in medical_diagnosis:
            del medical_diagnosis["trace_info"]
        if "thinking" in medical_diagnosis:
            del medical_diagnosis["thinking"]
        if "diagnose_id" in medical_diagnosis:
            del medical_diagnosis["diagnose_id"]
    else:
        service_logger.error(f"can not get medical diagnosis from database, diagnose_id: {diagnose_id}")
        return TaskStatus.FAIL
    
    # 获取病人电子病历信息
    medical_records = medical_record_manager.get_by_treatment_id(treatment_id)
    if not medical_records:
        service_logger.error(f"can not get medical records from database, treatment_id: {treatment_id}")
        return TaskStatus.FAIL
    
    # 最新电子病历
    latest_medical_record = medical_records[0]["electronic_report"]
    
    # 调用 agent 生成治疗方案
    medical_treatment = generate_medical_treatment(
        patient_info=patient_info, 
        medical_record=latest_medical_record, 
        diagnosis_info=medical_diagnosis, 
        first_diagnosis=(source == "generate_first_electronic_report"),
        demo_mode=demo_mode)
    if not medical_treatment:
        service_logger.error(f"can not generate medical treatment, treatment_id: {treatment_id}, diagnose_id: {diagnose_id}")
        return TaskStatus.FAIL
    
    service_logger.info(f"medical_treatment: {medical_treatment}")
    # 保存治疗方案
    treatment_info_manager.insert_treatment_plan(treatment_id, treatment_plan_id, medical_treatment)

    # 调用 agent 生成检查推荐
    check_recommendation = generate_check_recommendation(
        patient_info=patient_info,
        medical_record=latest_medical_record,
        diagnosis_info=medical_diagnosis,
        first_diagnosis=(source == "generate_first_electronic_report"),
        demo_mode=demo_mode
    )
    if not check_recommendation:
        service_logger.error(f"can not generate check recommendation, treatment_id: {treatment_id}, diagnose_id: {diagnose_id}")
        return TaskStatus.FAIL
    
    service_logger.info(f"check_recommendation result: {check_recommendation}")
    # 保存检查推荐
    treatment_info_manager.insert_check_recommendation(treatment_id, check_recommendation_id, check_recommendation)

    # 更新电子病历
    treatments = []
    if "return_info" in medical_treatment:
        treatments.append(medical_treatment["return_info"])

    if "return_info" in check_recommendation:
        treatments.append(check_recommendation["return_info"])
    
    if len(treatments) > 0:
        medical_record_manager.update_last_record(treatment_id, "处置", "；".join(treatments))

    return TaskStatus.COMPLETED


if __name__ == "__main__":
    import uuid
    result = generate_treatment(task_id=str(uuid.uuid4()), task_params={
        "treatment_id": "10_874944831",
        "diagnose_id": "4d2a4f7b-f43a-4a84-bb07-040d979805a1",
        "treatment_plan_id": str(uuid.uuid4())
    })
    print(f"result={result}")