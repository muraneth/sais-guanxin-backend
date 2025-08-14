# -*- coding: utf-8 -*-
# 根据患者的病历信息，向医生推荐具体的治疗（处置）措施，并结合指南返回推荐依据（溯源）
# 文档：https://inflytech.feishu.cn/wiki/F56Gwk6EciJtWzkGVaNcndlanbb

import traceback

from service.config.config import algo_config
from util.sync_http_request import send_request
from util.logger import service_logger
from util.transfer import get_chinese_patient_info
medical_treatment_url = algo_config.medical_algo_service_http_url + "/assistant/treatment_recommendation"

"""
patient_info: dict, 病人基本信息
medical_record: dict, 病人电子病历
diagnosis_info: dict, 病人诊断信息
"""
def generate_medical_treatment(patient_info: dict, medical_record: dict, diagnosis_info: dict, first_diagnosis: bool, demo_mode: bool = False):
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
    service_logger.info(f"generate_medical_treatment request data: {data}")
    try:
        result = send_request(url=medical_treatment_url, body=data)
        status_code = result["status_code"] 
        if status_code == 200:
            body = result["body"]
            body_code = body["code"]
            if body_code == 0:
                return body["data"]

        service_logger.error(f"failed to get medical treatment, status_code: {status_code}, body: {result['body']}")
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
        "chief_complaint": "发作性胸骨后疼痛2小时（2019-09-11 04:52）",
        "present_illness_history": "患者2小时前于哺乳时出现持续性胸骨后闷痛，伴胸闷、气短、心悸、乏力、咽部哽咽感，两次发作各持续10分钟。外院心电图示Ⅱ、Ⅲ、aVF、V3R～V5R导联ST段抬高，心肌酶升高，诊断为急性心肌梗死，予双抗血小板及抗凝治疗后转入我院。现精神尚可，睡眠差。",
        "past_medical_history": "既往体健，无慢性病史、传染病史、手术史及过敏史",
        "family_history": "母亲患高血压，否认家族遗传病史",
        "marital_and_reproductive_history": "育1子1女均顺产，现处于产后第4天伴恶露",
        "personal_history": "无烟酒嗜好",
        "physical_examination": "生命体征平稳，心肺腹查体未见明显异常，双下肢无水肿",
        "auxiliary_examinations": "1．实验室检查\n\n血常规：红细胞计数3.40×10<sup>12</sup>/L，血红蛋白98g/L，白细胞计数5×10<sup>9</sup>/L，中性粒细胞百分比80.0%，血小板计数176×10<sup>9</sup>/L。\n\n肝功能：谷草转氨酶57U/L↑，谷丙转氨酶26U/L，碱性磷酸酶127U/L↑，总胆红素12.3μmol/L，白蛋白32.7g/L↓。\n\n肾功能：尿素氮4.2mmol/L，肌酐53μmol/L，尿酸326μmol/L。\n\n电解质：钾3.77mmol/L，钠138mmol/L。\n\nNT-proBNP 479.80pg/mL。\n\n高敏肌钙蛋白T 0.381mg/mL。\n\n血脂：甘油三酯2.00mmol/L↑、高密度脂蛋白1.47mmol/L、低密度脂蛋白2.39mmol/L、脂蛋白a 109mg/L、同型半胱氨酸15.4μmol/L↑。\n\n心肌酶：谷草转氨酶54U/L↑，乳酸脱氢酶311U/L↑，羟丁酸脱氢酶28U/L↑，肌酸激酶452U/L↑，肌酸激酶同工酶52U/L↑。\n\n糖化血红蛋白5.6%；C反应蛋白18.5mg/L↑；血沉38mm/h↑；免疫八项、结缔组织全套、甲状腺功能未见明显异常。\n\n抗环瓜氨酸多肽抗体：阴性。\n\n血清蛋白电泳：α<sub>1</sub>球蛋白7.00↑（参考值：2.9～4.9），α<sub>2</sub>球蛋白12.80↑（参考值：7.1～11.8），β<sub>1</sub>球蛋白9.00↑（参考值：4.7～7.2）。\n\n2．影像学检查\n\n当地医院入院心电图（2019-09-11 05：15）病例33图1。\n\n\n当地医院期间发作复查心电图（2019-09-11 05：31）见病例33图2。\n\n\n我院入院心电图（2019-09-11 06：57）见病例33图3。\n\n\n床旁胸片（2019-09-11 13：58）：两肺淤血，心影增大。\n\n\n床旁超声心动图（2019-09-11）：EF 56%；左室舒张末期/收缩末期前后径54/37mm；左室壁、右室壁节段性运动减低（左室下壁、右室侧壁）；左心稍大伴二尖瓣少量反流；左室整体收缩功能正常偏低；心包积液（少量）。"
    }
    diagnosis_info = {
        "初步诊断": {
            "主要诊断": {
                "名称": "动脉性肺动脉高压（PAH）",
                "疾病分型": "毛细血管前性肺动脉高压（WHO第1类）",
                "诊断依据": [
                    "症状：反复劳力性气促1年余，进行性加重，伴胸闷痛、咳嗽、咳白黏痰；鼻衄病史",
                    "查体：心界向左扩大，P2亢进分裂，胸骨左缘2-3肋间3/6级收缩期杂音",
                    "辅助检查：心超示右房室增大，PASP 59mmHg；心导管检查PAP 73/50(57)mmHg，PVR 7.9WU，PAWP 11mmHg；右心功能测定示右室收缩及舒张功能降低"
                ]
            },
            "次要诊断": [
                {
                    "名称": "三尖瓣重度关闭不全（继发性）",
                    "诊断依据": [
                        "症状：劳力性气促",
                        "查体：胸骨左缘收缩期杂音",
                        "辅助检查：心超示三尖瓣关闭缝隙宽6mm，反流量110ml；右心导管示RAP升高至26mmHg"
                    ]
                },
                {
                    "名称": "高尿酸血症",
                    "诊断依据": [
                        "辅助检查：尿酸581μmol/L（正常参考值通常<357μmol/L）"
                    ]
                }
            ]
        },
        "鉴别诊断": [
            {
                "名称": "慢性血栓栓塞性肺动脉高压（CTEPH，WHO第4类）",
                "选取依据": "考虑可能导致继发肺动脉高压的常见疾病",
                "支持依据": [
                    "辅助检查：D-二聚体222μg/L（轻度升高）",
                    "辅助检查：肺动脉高压的血流动力学特征（PVR升高）"
                ],
                "不支持依据": [
                    "辅助检查：心超未发现肺动脉内血栓征象",
                    "症状：无深静脉血栓相关症状（如肢体肿胀）"
                ],
                "是否可排除": False,
                "对应检查推荐": [
                    "肺通气/灌注显像",
                    "CT肺动脉造影（CTPA）"
                ]
            },
            {
                "名称": "遗传性出血性毛细血管扩张症（HHT）相关PAH",
                "选取依据": "结合鼻衄史考虑遗传性疾病",
                "支持依据": [
                    "症状：反复鼻衄病史",
                    "辅助检查：PAH的血流动力学证据"
                ],
                "不支持依据": [
                    "查体：未描述皮肤黏膜毛细血管扩张",
                    "家族史：无相关家族史"
                ],
                "是否可排除": False,
                "对应检查推荐": [
                    "ACVRL1/ENG基因检测",
                    "皮肤毛细血管扩张检查"
                ]
            },
            {
                "名称": "结缔组织病相关PAH",
                "选取依据": "考虑继发性PAH常见病因",
                "支持依据": [
                    "辅助检查：女性患者（PAH高危人群）"
                ],
                "不支持依据": [
                    "症状：无关节痛、皮疹等结缔组织病典型表现",
                    "辅助检查：血常规、尿常规未见自身免疫性异常"
                ],
                "是否可排除": False,
                "对应检查推荐": [
                    "ANA/ENA抗体谱检测",
                    "抗核抗体检测"
                ]
            }
        ]
    }
    medical_treatment = generate_medical_treatment(patient_info, medical_record, diagnosis_info)
    print(f"medical_treatment: {medical_treatment}")
