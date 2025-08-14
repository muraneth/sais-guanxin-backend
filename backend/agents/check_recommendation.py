# -根据患者的病历信息，推荐患者应该做哪些检查，并结合指南返回推荐依据（溯源）
# 文档：https://inflytech.feishu.cn/wiki/IrgpwWRuKi1qxVkOVcBcK7C8nCb

import traceback

from service.config.config import algo_config
from util.sync_http_request import send_request
from util.logger import service_logger
from util.transfer import get_chinese_patient_info
medical_treatment_url = algo_config.medical_algo_service_http_url + "/assistant/check_recommendation"

"""
config: dict, 配置信息
patient_info: dict, 病人基本信息
medical_record: dict, 病人电子病历
diagnosis_info: dict, 病人诊断信息
"""
def generate_check_recommendation(patient_info: dict, medical_record: dict, diagnosis_info: dict, first_diagnosis: bool, demo_mode: bool = False):
    patient_info = get_chinese_patient_info(patient_info)
    data = {
        "config": {},
        "patient_info": patient_info,
        "patient_history": medical_record,
        "diagnosis_info": diagnosis_info,
        "first_diagnosis": first_diagnosis
    }
    if demo_mode is not None:
        data["demo_mode"] = demo_mode
    try:
        service_logger.info(f"generate_check_recommendation request data: {data}")
        result = send_request(url=medical_treatment_url, body=data)
        status_code = result["status_code"] 
        if status_code == 200:
            body = result["body"]
            body_code = body["code"]
            if body_code == 0:
                check_recommendation = body["data"]
                if "event" in check_recommendation:
                    del check_recommendation["event"]
                return check_recommendation

        service_logger.error(f"failed to get check recommendation, status_code: {status_code}, body: {result['body']}")
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
    medical_record = {
        "主诉": "发作性胸骨后疼痛2小时（2019-09-11 04:52）",
        "现病史": "患者2小时前于哺乳时出现持续性胸骨后闷痛，伴胸闷、气短、心悸、乏力、咽部哽咽感，两次发作各持续10分钟。外院心电图示Ⅱ、Ⅲ、aVF、V3R～V5R导联ST段抬高，心肌酶升高，诊断为急性心肌梗死，予双抗血小板及抗凝治疗后转入我院。现精神尚可，睡眠差。",
        "既往史": "既往体健，无慢性病史、传染病史、手术史及过敏史",
        "个人史": "无烟酒嗜好",
        "家族史": "母亲患高血压，否认家族遗传病史",
    }   
    diagnosis_info = {"初步诊断": {"主要诊断": {"名称": "动脉性肺动脉高压（PAH）", "疾病分型": "毛细血管前性肺动脉高压（WHO第1类）", "诊断依据": ["症状：反复劳力性气促1年余，进行性加重，伴胸闷痛、咳嗽、咳白黏痰；鼻衄病史", "查体：心界向左扩大，P2亢进分裂，胸骨左缘2-3肋间3/6级收缩期杂音", "辅助检查：心超示右房室增大，PASP 59mmHg；心导管检查PAP 73/50(57)mmHg，PVR 7.9WU，PAWP 11mmHg；右心功能测定示右室收缩及舒张功能降低"], "trace": {"cite_key": [["chief_complaint", "past_medical_history"], ["physical_examination"], ["auxiliary_examinations"]], "cite_block": [[[0, 10], [15, 40]], [20, 30], [32, 33]]}}, "次要诊断": [{"名称": "三尖瓣重度关闭不全（继发性）", "诊断依据": ["症状：劳力性气促", "查体：胸骨左缘收缩期杂音", "辅助检查：心超示三尖瓣关闭缝隙宽6mm，反流量110ml；右心导管示RAP升高至26mmHg"], "trace": {"cite_key": [["chief_complaint", "past_medical_history"], ["physical_examination"], ["auxiliary_examinations"]], "cite_block": [[[0, 10], [15, 40]], [20, 30], [32, 33]]}}, {"名称": "高尿酸血症", "诊断依据": ["辅助检查：尿酸581μmol/L（正常参考值通常<357μmol/L）"], "trace": {"cite_key": [["chief_complaint", "past_medical_history"]], "cite_block": [[[0, 10], [15, 40]]]}}]}, "鉴别诊断": [{"名称": "慢性血栓栓塞性肺动脉高压（CTEPH，WHO第4类）", "选取依据": "考虑可能导致继发肺动脉高压的常见疾病", "支持依据": ["辅助检查：D-二聚体222μg/L（轻度升高）", "辅助检查：肺动脉高压的血流动力学特征（PVR升高）"], "不支持依据": ["辅助检查：心超未发现肺动脉内血栓征象", "症状：无深静脉血栓相关症状（如肢体肿胀）"], "trace_postive": {"cite_key": [["chief_complaint", "past_medical_history"], ["chief_complaint"]], "cite_block": [[[0, 10], [15, 40]], [[0, 40]]]}, "trace_negative": {"cite_key": [["chief_complaint", "past_medical_history"], ["chief_complaint"]], "cite_block": [[[0, 10], [15, 40]], [[0, 40]]]}, "是否可排除": "否", "对应检查推荐": ["肺通气/灌注显像", "CT肺动脉造影（CTPA）"]}, {"名称": "遗传性出血性毛细血管扩张症（HHT）相关PAH", "选取依据": "结合鼻衄史考虑遗传性疾病", "支持依据": ["症状：反复鼻衄病史", "辅助检查：PAH的血流动力学证据"], "不支持依据": ["查体：未描述皮肤黏膜毛细血管扩张", "家族史：无相关家族史"], "trace_postive": {"cite_key": [["chief_complaint", "past_medical_history"], ["chief_complaint"]], "cite_block": [[[0, 10], [15, 40]], [[0, 40]]]}, "trace_negative": {"cite_key": [["chief_complaint", "past_medical_history"], ["chief_complaint"]], "cite_block": [[[0, 10], [15, 40]], [[0, 40]]]}, "是否可排除": "否", "对应检查推荐": ["ACVRL1/ENG基因检测", "皮肤毛细血管扩张检查"]}, {"名称": "结缔组织病相关PAH", "选取依据": "考虑继发性PAH常见病因", "支持依据": ["辅助检查：女性患者（PAH高危人群）"], "不支持依据": ["症状：无关节痛、皮疹等结缔组织病典型表现", "辅助检查：血常规、尿常规未见自身免疫性异常"], "trace_postive": {"cite_key": [["chief_complaint", "past_medical_history"]], "cite_block": [[[0, 10], [15, 40]]]}, "trace_negative": {"cite_key": [["chief_complaint", "past_medical_history"], ["chief_complaint"]], "cite_block": [[[0, 10], [15, 40]], [[0, 40]]]}, "是否可排除": "否", "对应检查推荐": ["ANA/ENA抗体谱检测", "抗核抗体检测"]}]}
    check_recommendation = generate_check_recommendation(patient_info, medical_record, diagnosis_info)
    print(check_recommendation)
