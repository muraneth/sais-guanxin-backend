from datetime import datetime
from service.repository.mongo_task_manager import TaskStatus, task_manager
from service.repository.mongo_treatment_info import treatment_info_manager
from service.repository.mongo_medical_record_manager import medical_record_manager
from agents.medical_diagnosis import generate_medical_diagnosis
from agents.diagnosis_nature_language import diagnosis_nature_language
from util.logger import service_logger
from service.config.config import IS_DEMO_MODE


def generate_diagnosis_and_treatment_plan(task_id, task_params):
    # 获取任务参数
    treatment_id = task_params.get("treatment_id")
    diagnose_id = task_params.get("diagnose_id")
    treatment_plan_id = task_params.get("treatment_plan_id")
    source = task_params.get("source", "generate_first_electronic_report")
    service_logger.info(f"task_id={task_id}, treatment_id={treatment_id}, diagnose_id={diagnose_id}, treatment_plan_id={treatment_plan_id}, source={source}")

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
    
    # 获取病人历史就诊记录
    medical_records = medical_record_manager.get_by_treatment_id(treatment_id)
    if not medical_records or len(medical_records) == 0:
        service_logger.error(f"can not get medical records from database, treatment_id: {treatment_id}")
        return TaskStatus.FAIL
    
    # 最新电子病历
    medical_record = medical_records[0]
    
    # 最新电子病历
    if "electronic_report" not in medical_record:
        service_logger.error(f"can not get latest medical record from database, treatment_id: {treatment_id}")
        return TaskStatus.FAIL
    latest_medical_record = medical_record["electronic_report"]
    
    # 调用大模型生成诊断信息
    medical_diagnosis = generate_medical_diagnosis(
        patient_info=patient_info, 
        patient_history=latest_medical_record, 
        first_diagnosis=(source == "generate_first_electronic_report"),
        demo_mode=demo_mode
    )
    if not medical_diagnosis:
        service_logger.error(f"can not generate medical diagnosis, treatment_id: {treatment_id}")
        return TaskStatus.FAIL
    
    service_logger.info(f"task_id={task_id}, medical_diagnosis={medical_diagnosis}")
    
    # 保存诊断信息
    treatment_info_manager.insert_medical_diagnosis(treatment_id=treatment_id, diagnose_id=diagnose_id, diagnose_data=medical_diagnosis)
    
    # 更新电子病历
    try:
        medical_record_manager.update_last_record(treatment_id, "诊断", medical_diagnosis["初步诊断"]["主要诊断"]["名称"])
    except Exception as e:
        service_logger.error(f"failed to update medical record, treatment_id: {treatment_id}, medical_diagnosis: {medical_diagnosis}, error: {e}")
        return TaskStatus.FAIL

    # 生产完成电子病历，触发一个异步任务，用于生成总结，并保存到数据库
    if not IS_DEMO_MODE and source == "generate_first_electronic_report":
        # 总结历史病历
        task_manager.add_task(
            task_type="summarize_history_data",
            params={
                "treatment_id": treatment_id,
                "with_diagnosis_info": True
            }   
        )

    # 演示模式下，生成数字虚拟人台词，自然语言的诊断信息
    if IS_DEMO_MODE and source == "generate_first_electronic_report":
        service_logger.info(f"generate diagnosis text in demo mode, treatment_id: {treatment_id}")
        diagnosis_text = diagnosis_nature_language(
            diagnosis_info=medical_diagnosis, 
            first_diagnosis=(source == "generate_first_electronic_report"),
            demo_mode=demo_mode
        )
        treatment_info_manager.update_by_treatment_id(treatment_id, {"diagnosis_text": diagnosis_text})
    else:
        service_logger.info(f"skip generating diagnosis text in real mode, treatment_id: {treatment_id}")

    # 异步生成治疗方案
    task_manager.add_task(
        task_type="generate_treatment",
        params={
            "treatment_id": treatment_id,
            "diagnose_id": diagnose_id,
            "treatment_plan_id": treatment_plan_id,
            "source": source
        }
    )

    return TaskStatus.COMPLETED


if __name__ == "__main__":
    import uuid
    result = generate_diagnosis_and_treatment_plan(task_id=str(uuid.uuid4()), task_params={
        "treatment_id": "10_874944831",
        "diagnose_id": str(uuid.uuid4()),
        "treatment_plan_id": str(uuid.uuid4())
    })
    print(f"result={result}")
