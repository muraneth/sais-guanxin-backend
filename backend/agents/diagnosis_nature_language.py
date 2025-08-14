import traceback
import asyncio

from service.config.config import algo_config
from util.logger import service_logger
from util.aiohttp_sse_client import aiosseclient

diagnosis_nature_language_url = algo_config.medical_algo_service_http_url + "/assistant/diagnosis_nature_language_stream"



"""
diagnosis_info: 诊断结果, dict
"""
async def diagnosis_nature_language_stream(diagnosis_info: dict, first_diagnosis: bool, demo_mode: bool = False):

    # 过滤不需要的诊断信息
    filter_diagnosis_info = {}
    if "初步诊断" in diagnosis_info:
        filter_diagnosis_info["初步诊断"] = diagnosis_info["初步诊断"]
    if "鉴别诊断" in diagnosis_info:
        filter_diagnosis_info["鉴别诊断"] = diagnosis_info["鉴别诊断"]

    # 构造请求参数
    data = {
        "diagnosis_info": filter_diagnosis_info,
        "first_diagnosis": first_diagnosis,
    }
    if demo_mode is not None:
        data["demo_mode"] = demo_mode
    service_logger.info(f"diagnosis_nature_language_stream request data: {data}")
    async for raw_event in aiosseclient(url=diagnosis_nature_language_url, data=data, timeout_total=10*60):
        try:
            event = raw_event.data_json
            yield event
        except Exception as e:
            # 输出 Exception 信息
            service_logger.warning(f"can not get event data in {event}, error: {e}")
            continue


def diagnosis_nature_language(diagnosis_info: dict, first_diagnosis: bool, demo_mode: bool = False):
    async def collect_last_event():
        final_event = None
        async for event in diagnosis_nature_language_stream(diagnosis_info, first_diagnosis, demo_mode):
            final_event = event
        service_logger.info(f"diagnosis_nature_language final_event: {final_event}")
        return final_event["answer"] if final_event else None
    
    return asyncio.run(collect_last_event())


if __name__ == "__main__":
    final_event = diagnosis_nature_language(
        diagnosis_info={
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
    )
    print(f"final_event: {final_event}")