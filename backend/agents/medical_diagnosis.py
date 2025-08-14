# 根据患者病历（门诊/住院），生成诊断和鉴别诊断，并对相关证据进行溯源。
# 文档：https://inflytech.feishu.cn/wiki/QgLbwpm6Cium4kk6JMncGU7onjq
import traceback

from service.config.config import algo_config
from util.sync_http_request import send_request
from util.logger import service_logger

medical_diagnosis_url = algo_config.medical_algo_service_http_url + "/assistant/medical_diagnosis"

def generate_medical_diagnosis(patient_info: dict, patient_history: dict, first_diagnosis: bool, demo_mode: bool = False):
    # 构造请求参数
    data = {
        "config": {},
        "patient_info": patient_info,
        "patient_history": patient_history,
        "first_diagnosis": first_diagnosis,
    }
    if demo_mode is not None:
        data["demo_mode"] = demo_mode
    try:
        service_logger.info(f"generate_medical_diagnosis request data: {data}")
        result = send_request(url=medical_diagnosis_url, body=data)
        status_code = result["status_code"] 
        if status_code == 200:
            body = result["body"]
            body_code = body["code"]
            if body_code == 0:
                raw = body["data"]["answer"]
                medical_diagnosis = raw["answer"]
                medical_diagnosis["thinking"] = raw["thinking"]
                medical_diagnosis["trace_info"] = raw["trace_info"]
                medical_diagnosis["doc_list"] = raw["doc_list"]
                return medical_diagnosis

        service_logger.error(f"failed to get medical diagnosis, status_code: {status_code}, body: {result['body']}")
        return None

    except Exception as e:
        service_logger.error(f"failed to request: {str(e)}, stack: {traceback.format_exc()}")
        return None

if __name__ == "__main__":
    patient_info = {
          "gender": "女性",
          "age": 30,
          "occupation": "无",
          "marital_status": "已婚",
    }
    patient_history = {
        "主诉": "发作性胸骨后疼痛2小时（2019-09-11 04:52）",
        "现病史": "患者2小时前于哺乳时出现持续性胸骨后闷痛，伴胸闷、气短、心悸、乏力、咽部哽咽感，两次发作各持续10分钟。外院心电图示Ⅱ、Ⅲ、aVF、V3R～V5R导联ST段抬高，心肌酶升高，诊断为急性心肌梗死，予双抗血小板及抗凝治疗后转入我院。现精神尚可，睡眠差。",
        "既往史": "既往体健，无慢性病史、传染病史、手术史及过敏史",
        "个人史": "无烟酒嗜好",
        "家族史": "母亲患高血压，否认家族遗传病史",
        "婚育史": "育1子1女均顺产，现处于产后第4天伴恶露",
        "体格检查": "生命体征平稳，心肺腹查体未见明显异常，双下肢无水肿",
        "辅助检查": "未提及。",
        "初步诊断": "未提及。",
        "诊疗计划": "未提及。"
    }
    medical_diagnosis = generate_medical_diagnosis(patient_info, patient_history)
    print("medical_diagnosis: ", medical_diagnosis)
