from service.config.config import algo_config
from util.sync_http_request import send_request
from util.logger import service_logger
from util.transfer import get_chinese_patient_info
import traceback

medical_summary_url = algo_config.medical_algo_service_http_url + "/assistant/medical_summary"

"""
patient_info: 病人基本信息,dict
    - gender: 病人性别
    - age: 病人 年龄
    - marital_status: 婚姻状态
diagnosis_info: 本次就诊主要诊断,str
treatment_list: 病人既往就诊信息
    - doccontent: 包含患者一诉五史和就诊时间,list<dict>
    - Auxiliary_examination: 包含查体、检测、影像检查,dict
    - maindiagnosis: 包含主要诊断,str
    - treatments: 手术和药品等处置方案,list
report_info: 如果做报告摘要，请保证该字段不为空,str
"""
def medical_summary(patient_info: dict, diagnosis_info: str, treatment_list: list, report_info: str = None):
    #patient_info = get_chinese_patient_info(patient_info)
    # 构造请求参数
    data = {
        "config": {},
        "patient_info": patient_info,
        "treatment_list": treatment_list,
    }
    if len(diagnosis_info) > 0:
        data["diagnosis_info"] = diagnosis_info
        
    if report_info: 
        data["report_info"] = report_info

    try:
        service_logger.info(f"medical_summary data: {data}")
        result = send_request(url=medical_summary_url, body=data)
        status_code = result["status_code"] 
        if status_code == 200:
            body = result["body"]
            body_code = body["code"]
            if body_code == 0:
                summary = body["data"]
                if "event" in summary:
                    del summary["event"]
                return summary

        service_logger.error(f"failed to get medical summary, status_code: {status_code}, body: {result['body']}")
        return None

    except Exception as e:
        service_logger.error(f"failed to request: {str(e)}, stack: {traceback.format_exc()}")
        return None


import asyncio
from service.package.hospital_info_sys import get_patient_base_info, get_history_data
from util.transfer import get_chinese_patient_info
async def test_medical_summary():
    patient_info = get_patient_base_info("just for test")
    treatment_list = get_history_data("just for test")
    diagnosis_info = "冠状动脉支架植入后复查"
    print(f"patient_info: {patient_info}")
    print(f"diagnosis_info: {diagnosis_info}")
    print(f"treatment_list: {treatment_list}")
    summary = medical_summary(patient_info=patient_info, diagnosis_info=diagnosis_info, treatment_list=treatment_list, report_info=None)
    print(f"总结:\n{summary}")

if __name__ == "__main__":
    asyncio.run(test_medical_summary())