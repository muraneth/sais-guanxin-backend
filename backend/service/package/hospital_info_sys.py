# -*- coding: utf-8 -*-
# TODO：对接医院真实 HIS 接口
# 当前使用 mock 数据
# 接口说明文档：https://diqj2vyywfa.feishu.cn/wiki/DWOLw67PLi72rdk9uaoclPgynqb

from util.logger import service_logger
from service.config.config import service_config
from util.sync_http_request import send_request
from service.config.config import IS_DEMO_MODE

his_service_url = service_config.his_service_http_url

# 获取病人信息
def get_patient_base_info(treatment_id: str):
    url = f"{his_service_url}/ai-doctor/get_patient_info"
    body = {
        "treatmentid": treatment_id
    }
    response_body = send_request(url, body=body)
    if response_body.get("status_code") != 200:
        service_logger.error(f"get patient base info failed, treatment_id: {treatment_id}, response_body: {response_body}")
        return None

    if "body" not in response_body or "data" not in response_body["body"]:
        service_logger.error(f"get patient base info failed, treatment_id: {treatment_id}, response_body: {response_body}")
        return None
    
    info = response_body["body"]["data"]
    if not info:
        service_logger.error(f"get patient base info failed, treatment_id: {treatment_id}, response_body: {response_body}")
        return None
    # 90 表示已婚 (⊙o⊙)…
    """
    {
        "name": "张三",
        "gender": "男",
        "age": 50,
        "occupation": "程序员",
        "marital_status": "已婚"
    }
    """
    if info["marital_status"] == "90":
        info["marital_status"] = "已婚"
    return info


# 获取历史就诊接口1
"""
接口用途:从 HIS 中获取当前患者历史就诊记录（病史、诊断、治疗）。
触发时机:患者在病史采集生成电子病历之后，基于初版电子病历生成初步诊断，在初步诊断生成之后依据初步诊断相关疾病类型，从历史就诊中摘要相关信息，辅助本次诊断
病例格式，从 HIS 系统中查到，格式参考：https://diqj2vyywfa.feishu.cn/wiki/DWOLw67PLi72rdk9uaoclPgynqb#share-AfAdd9QLJoa8X9xFU1VcQBZQnzg
"""
def get_history_data(treatment_id: str, depname: list = [], record_period: int = 3, record_num: int = 30):
    url = f"{his_service_url}/ai-doctor/get_history_data"
    default_dep_name = getattr(service_config, 'his_default_dep_name', [])
    if not depname or len(depname) == 0:
        depname = default_dep_name
    body = {
        "treatmentid": treatment_id,
        "depname": depname,
        "recordperiod": record_period,
        "recordnum": record_num
    }
    response_body = send_request(url, body=body)
    if response_body.get("status_code") != 200:
        service_logger.error(f"get history data failed, treatment_id: {treatment_id}, response_body: {response_body}")
        return None
    """
    [{
        "doccontent": [{
                "treatmenttime": "2024-09-30",
                "treatmenttype": "门急诊",
                "medhistorytype": "既往史",
                "content": "否认其它慢病，否认药物过敏"
            },
            {
                "treatmenttime": "2024-09-30",
                "treatmenttype": "门急诊",
                "medhistorytype": "现病史",
                "content": "\n近期病情稳定，药物治疗有效，否认其他特殊不适。\n"
            },
            {
                "treatmenttime": "2024-09-30",
                "treatmenttype": "门急诊",
                "medhistorytype": "诊断",
                "content": "胸闷、慢性肾功能不全、冠状动脉粥样硬化性心脏病、贫血\n完善检查，注意监测血压/心率，继续目前治疗方案，复查相关指标，门诊随访。血液科、肾内科就诊。"
            },
            {
                "treatmenttime": "2024-09-30",
                "treatmenttype": "门急诊",
                "medhistorytype": "辅助检查",
                "content": "见报告"
            },
            {
                "treatmenttime": "2024-09-30",
                "treatmenttype": "门急诊",
                "medhistorytype": "主诉",
                "content": "胸闷、慢性肾功能不全、冠状动脉粥样硬化性心脏病、贫血复诊。\n"
            },
            {
                "treatmenttime": "2024-09-30",
                "treatmenttype": "门急诊",
                "medhistorytype": "体格检查",
                "content": "神情，一般可，肺部未闻及明显干湿罗音，HR70次/分，律齐，未闻及明显杂音。血压120/70\n"
            }
        ],
        "Auxiliary_examination": {
            "检测": "### 糖代谢+酶类+肾功能+离子浓度+血脂+电解质+肝功能\n| subitemchinesename | testresult | referencevaluelowerlimit | referencevaluehighlimit | unit | sampletype |\n| --- | --- | --- | --- | --- | --- |\n| 肌酐 | 154 | 44 | 115 | μmol/L | 血清 |\n| 总胆红素 | 8.7 | 3.4 | 20.4 | μmol/L | 血清 |\n| 丙氨酸氨基转移酶 | 16 | 9 | 50 | U/L | 血清 |\n| 总胆固醇 | 2.80 |  |  | mmol/L | 血清 |\n| 估算肾小球滤过率  (根据CKD-EPI方程) | 51 |  |  | ml/min/1.73m2 | 血清 |\n| 乳酸脱氢酶 | 177 | 109 | 245 | U/L | 血清 |\n| 直接胆红素 | 2.8 | 0.0 | 6.8 | μmol/L | 血清 |\n| 镁 | 0.83 | 0.67 | 1.04 | mmol/L | 血清 |\n| 前白蛋白 | 314 | 200 | 430 | mg/L | 血清 |\n| 高密度脂蛋白胆固醇 | 0.95 | 1.04 |  | mmol/L | 血清 |\n| 钾 | 4.6 | 3.5 | 5.3 | mmol/L | 血清 |\n| 非高密度脂蛋白胆固醇 | 1.85 |  |  | mmol/L | 血清 |\n| 氯 | 105 | 99 | 110 | mmol/L | 血清 |\n| 低密度脂蛋白胆固醇 | 0.74 |  |  | mmol/L | 血清 |\n| γ-谷氨酰转移酶 | 45 | 10 | 60 | U/L | 血清 |\n| 碱性磷酸酶 | 57 | 45 | 125 | U/L | 血清 |\n| 白蛋白 | 46 | 35 | 55 | g/L | 血清 |\n| 白球比值 | 2.1 | 1.2 | 2.4 |  | 血清 |\n| 门冬氨酸氨基转移酶 | 13 | 15 | 40 | U/L | 血清 |\n| 钙 | 2.34 | 2.15 | 2.55 | mmol/L | 血清 |\n| 葡萄糖 | 4.7 | 3.9 | 5.6 | mmol/L | 血清 |\n| 尿素 | 6.3 | 2.9 | 8.2 | mmol/L | 血清 |\n| 无机磷 | 1.25 | 0.90 | 1.34 | mmol/L | 血清 |\n| 肌酸激酶 | 125 | 34 | 174 | U/L | 血清 |\n| 尿酸 | 523 | 208 | 428 | μmol/L | 血清 |\n| 甘油三酯 | 2.45 |  |  | mmol/L | 血清 |\n| 总蛋白 | 68 | 65 | 85 | g/L | 血清 |\n| 球蛋白 | 22 | 20 | 40 | g/L | 血清 |\n| 钠 | 140 | 137 | 147 | mmol/L | 血清 |\n\n### 血常规\n| subitemchinesename | testresult | referencevaluelowerlimit | referencevaluehighlimit | unit | sampletype |\n| --- | --- | --- | --- | --- | --- |\n| 平均血红蛋白浓度 | 333 | 316 | 354 | g/L | EDTA-K2抗凝血 |\n| 大血小板比率 | 26.3 | 14.0 | 46.0 | % | EDTA-K2抗凝血 |\n| 中性粒细胞数 | 6.3 | 1.8 | 6.3 | X10^9/L | EDTA-K2抗凝血 |\n| 红细胞计数 | 4.81 | 4.30 | 5.80 | X10^12/L | EDTA-K2抗凝血 |\n| 淋巴细胞百分比 | 20.8 | 20.0 | 50.0 | % | EDTA-K2抗凝血 |\n| 中性粒细胞百分比 | 72.1 | 40.0 | 75.0 | % | EDTA-K2抗凝血 |\n| 血小板计数 | 301 | 125 | 350 | X10^9/L | EDTA-K2抗凝血 |\n| 白细胞计数 | 8.79 | 3.50 | 9.50 | X10^9/L | EDTA-K2抗凝血 |\n| 嗜酸性粒细胞数 | 0.23 | 0.02 | 0.52 | X10^9/L | EDTA-K2抗凝血 |\n| 血小板压积 | 0.30 | 0.10 | 0.40 | % | EDTA-K2抗凝血 |\n| 红细胞体积分布宽度SD | 43.0 | 34.0 | 86.0 | fL | EDTA-K2抗凝血 |\n| 嗜酸性粒细胞百分比 | 2.6 | 0.4 | 8.0 | % | EDTA-K2抗凝血 |\n| 嗜碱性粒细胞百分比 | 0.8 | 0.0 | 1.0 | % | EDTA-K2抗凝血 |\n| 平均红细胞体积 | 91.1 | 82.0 | 100.0 | fL | EDTA-K2抗凝血 |\n| 红细胞体积分布宽度CV | 13.2 | 8.0 | 16.0 | % | EDTA-K2抗凝血 |\n| 血小板体积分布宽度 | 16.3 | 9.0 | 21.0 | % | EDTA-K2抗凝血 |\n| 平均血红蛋白量 | 30.4 | 27.0 | 34.0 | pg | EDTA-K2抗凝血 |\n| 平均血小板体积 | 9.9 | 9.4 | 18.5 | fL | EDTA-K2抗凝血 |\n| 嗜碱性粒细胞数 | 0.07 | 0.00 | 0.06 | X10^9/L | EDTA-K2抗凝血 |\n| 单核细胞数 | 0.33 | 0.1 | 0.6 | X10^9/L | EDTA-K2抗凝血 |\n| 淋巴细胞数 | 1.8 | 1.1 | 3.2 | X10^9/L | EDTA-K2抗凝血 |\n| 红细胞压积 | 43.8 | 40 | 50 | % | EDTA-K2抗凝血 |\n| 单核细胞百分比 | 3.7 | 3.0 | 10.0 | % | EDTA-K2抗凝血 |\n| 血红蛋白 | 146 | 130 | 175 | g/L | EDTA-K2抗凝血 |\n\n### 尿液检查+尿常规\n| subitemchinesename | testresult | referencevaluelowerlimit | referencevaluehighlimit | unit | sampletype |\n| --- | --- | --- | --- | --- | --- |\n| 尿胆原 | 正常 |  |  |  | 尿 |\n| 蛋白 | + |  |  |  | 尿 |\n| 比重 | 1.023 | 1.003 | 1.030 |  | 尿 |\n| 病理性管型 | 阴性 |  |  |  | 尿 |\n| 酵母菌 | 阴性 |  |  |  | 尿 |\n| 电导率 | 15.4 | 4.0 | 38.0 | mS/cm | 尿 |\n| pH | 6.00 | 5.0 | 8.0 |  | 尿 |\n| 亚硝酸盐 | 阴性 |  |  |  | 尿 |\n| 红细胞计数 | 3 | 0 | 25 | /uL | 尿 |\n| 尿隐血 | 阴性 |  |  |  | 尿 |\n| 小圆上皮细胞 | 阴性 |  |  |  | 尿 |\n| 胆红素 | 阴性 |  |  |  | 尿 |\n| 细菌计数 | 7 | 0 | 5000 | /uL | 尿 |\n| 白细胞酯酶 | 阴性 |  |  |  | 尿 |\n| 白细胞计数 | 7 | 0 | 25 | /uL | 尿 |\n| 酮体 | 阴性 |  |  |  | 尿 |\n| 结晶检查 | 阴性 |  |  |  | 尿 |\n| 透明度 | 清 |  |  |  | 尿 |\n| 红细胞信息 | 阴性 |  |  |  | 尿 |\n| 上皮细胞计数 | 3 | 2 | 10 | /uL | 尿 |\n| 葡萄糖 | 阴性 |  |  |  | 尿 |\n| 颜色 | 黄色 |  |  |  | 尿 |\n\n### 心脏标志物\n| subitemchinesename | testresult | referencevaluelowerlimit | referencevaluehighlimit | unit | sampletype |\n| --- | --- | --- | --- | --- | --- |\n| 心肌肌钙蛋白T | 0.021 |  | 0.014 | ng/mL | 血 |\n| 氨基末端利钠肽前体 | 45.7 | 0 | 100 | pg/mL | 血 |\n| 肌酸激酶MB质量 | 1.9 | 0 | 4.87 | ng/mL | 血 |\n\n### 止血与血栓+出凝血功能+凝血\n| subitemchinesename | testresult | referencevaluelowerlimit | referencevaluehighlimit | unit | sampletype |\n| --- | --- | --- | --- | --- | --- |\n| 凝血酶原时间比值 | 1.06 | 0.80 | 1.20 |  | 枸橼酸钠抗凝血 |\n| 国际标准化比值 | 1.01 | 0.50 | 1.20 |  | 枸橼酸钠抗凝血 |\n| 纤维蛋白原降解产物 | 0.62 | 0.00 | 5.00 | ug/mL | 枸橼酸钠抗凝血 |\n| D-二聚体 | <0.15 | 0.00 | 0.80 | mg/L | 枸橼酸钠抗凝血 |\n| 凝血酶原时间 | 12.0 | 10.0 | 13.0 | 秒 | 枸橼酸钠抗凝血 |\n| 活化部分凝血活酶时间 | 31.1 | 25 | 31.3 | 秒 | 枸橼酸钠抗凝血 |",
            "检查": "### 超声: 常规超声心动图(心脏彩色多普勒超声+左心功能测定+TDI)\n**(心脏彩色多普勒超声+左心功能测定+TDI)** **(H(cm):** / **W(kg):** / **BSA:** / **)**  \n**常规检查切面观:** 胸骨旁长轴观(√); 胸骨旁短轴观(√); 心尖切面观(√)     透声条件: 中\n\n| <table><tbody><tr><th><strong><font>一、M型及血流多普勒超声测量：</font></strong></th></tr><tr><th><table><tbody><tr><th></th><th>名称</th><th>测量值</th><th>正常值</th></tr><tr><th></th><th>主动脉根部内径</th><th><font><span>32</span></font></th><th><font><span>23-37mm</span></font></th></tr><tr><th></th><th>左房内径</th><th><font><span>40</span></font></th><th><font><span>22-39mm</span></font></th></tr><tr><th></th><th>左室舒张末内径</th><th><font><span>48</span></font></th><th><font><span>39-55mm</span></font></th></tr><tr><th></th><th>左室收缩末内径</th><th><font><span>32</span></font></th><th><font><span>24-39mm</span></font></th></tr><tr><th></th><th>室间隔厚度</th><th><font><span>12</span></font></th><th><font><span>6-11mm</span></font></th></tr><tr><th></th><th>左室后壁厚度</th><th><font><span>12</span></font></th><th><font><span>6-11mm</span></font></th></tr><tr><th></th><th>肺动脉收缩压</th><th><font><span>35</span></font></th><th><font><span>&lt;40mmHg</span></font></th></tr></tbody></table></th></tr></tbody></table> |  | 医学图像序列2行2列,宽：110 |\n| --- | --- | --- |\n\n**二、左心功能测定及组织多普勒显像测量:**  \n\n|  | 左室射血分数（LVEF）： 62 %二尖瓣血流图： EA双峰 ，E/A \\> 0.8; DT： 196 msDTI示S波峰值： 12 cm/s；e'/a' \\> 1 |\n| --- | --- |\n\n**三、普通二维超声心动图和各心腔及大血管血流显像：**\n\n|  | 1、左房内径 增大 ，左室内径 正常 ， 左室壁 增厚 ， 左室流出道未见异常 ，左室 各节段 收缩活动未见异常 。2、二尖瓣 不增厚 ，瓣叶 开放不受限 ，瓣口 面积正常范围 ， 瓣叶 关闭形态未见异常 ， 彩色多普勒 示轻微 二尖瓣 反流 。3、主动脉窦部 不增宽 ，升主动脉 不增宽 ，主动脉瓣 三叶式 ，瓣膜 不增厚 ， 开放不受限 ，彩色多普勒 未测及 主动脉瓣 反流 。4、 下腔静脉 内径 正常 ，右 心腔 内 未见异常回声 ， 房间隔 未见回声缺失 ，彩色多普勒 未见房水平分流 。右房内径 正常 ，右室基底段内径 正常 ，右室流出道 内径正常 ， 右室 壁 厚度正常 ，右室 收缩活动未见异常 ，TAPSE 示正常 。肺动脉 不增宽 ，肺动脉瓣 不增厚 ， 开放不受限 ，肺动脉平均压 未测及 ，三尖瓣 不增厚 ，瓣叶 开放不受限 ， 瓣叶 关闭形态未见异常 ，彩色多普勒 示轻微 三尖瓣 反流 。5、心包腔内 未见明显积液 。  |\n| --- | --- |\n\n**四、结论：**\n左房增大，左室壁增厚\n\n### 心电图: 常规心电图\n窦性心律  陈旧性前间隔心肌梗死  T波改变(T波在Ⅰ aVL V5 V6 导联低平、双相)"
        },
        "maindiagnosis": "冠状动脉支架植入后状态",
        "treatments": [
            "今来院完成血常规，尿常规，肝功能，肾功能，电解质，血脂，心脏标记物，凝血，CRP，ST2，TGF-β，心电图，心超，NYHA评分I分，6分钟步行测试。药品及空包装，日记卡未带，后续寄回。发放药品3中盒，药品编号0032，嘱下次空包装及药品，日记卡带回，下次随访时间2024年11月7日。应服药物：1404粒。",
            "药物服从性：不详",
            "1、雷贝拉唑钠肠溶片,qd,20mg,po,2024.04.30-至今，护胃，2、(倍利舒)替格瑞洛片，bid,po,90mg，2024.04.27-至今，抗凝3、(拜阿司匹灵)阿司匹林肠溶片，qd,po,0.10g,2024.04327-至今，抗凝4、(美达信)阿托伐他汀钙片,qn,po,20mg,2024.04.27-至今，调酯稳斑5、沙库巴曲缬沙坦钠片,bid,150mg,2024.04.27-至今，控制血压6、(立方)硝苯地平控释片,30mg.bid,po,2024.04.27-至今，控制血压7、(金络)卡维地洛片,bid,10mg,2024.04.27-至今，降压8、(瑞百安)依洛尤单抗注射液,q2w,140mg,2024.04.27-至今，调酯稳斑"
        ]
	}]
    """
    info = response_body.get("body").get("data")
    return info


"""
接口用途：从 HIS 中获取当前患者在某一就诊科室的最近就诊记录，作为多轮问诊的上下文，用于针对性问诊。
"""
def get_first_visit_data(treatment_id: str):
    # TODO：模拟获取最近的就诊记录
    pass


"""
接口用途：以轮训的方式获取患者的所有报告结果，主要用于更新诊断
"""
def get_report(treatment_id: str):
    url = f"{his_service_url}/ai-doctor/get_report"
    body = {
        "treatmentid": treatment_id
    }
    response_body = send_request(url, body=body)
    if response_body.get("status_code") != 200:
        service_logger.error(f"get report failed, treatment_id: {treatment_id}, response_body: {response_body}")
        return None
    
    info = response_body.get("body").get("data")
    return info


"""
接口用途：AI 页面生成的电子病历文本，写入 HIS 数据表。医生工作站通过点击刷新按钮，可读取该电子病历，更新至工作站电子病历输入框
"""
def upload_ai_emr(treatment_id: str, ai_emr: dict, doctor_code: str, section_name: str, emr_id: str):
    service_logger.info(f"upload ai emr to his, treatment_id: {treatment_id}, ai_emr: {ai_emr}, doctor_code: {doctor_code}, section_name: {section_name}, emr_id: {emr_id}")
    if IS_DEMO_MODE:
        # 演示模式下，不写入 HIS
        service_logger.info(f"DEMO MODE, skip upload ai emr to his, treatment_id: {treatment_id}")
        return {
            "status": "success",
            "spare": ""
        }
    
    url = f"{his_service_url}/ai-doctor/upload_ai_emr"
    body = {
        "treatmentid": treatment_id,
        "ai_emr": ai_emr,
        "doctor_code": doctor_code,
        "section_name": section_name,
    }
    if emr_id and emr_id != "":
        body["emr_id"] = emr_id
    response_body = send_request(url, body=body)
    service_logger.info(f"upload ai emr to his, treatment_id: {treatment_id}, response_body: {response_body}")
    if response_body.get("status_code") != 200:
        service_logger.error(f"upload ai emr to his failed, body: {body}, treatment_id: {treatment_id}, response_body: {response_body}")
        return {
            "status": "fail",
            "spare": ""
        }
    
    return response_body.get("body").get("data")


if __name__ == "__main__":
    #result = get_patient_base_info("10_877621196")
    # result = get_report(treatment_id="10_877621196")
    # print(result)
    
    # result = get_report(treatment_id="10_880653606")
    # print(result)
    #get_history_data(treatment_id="10_880653606")
    upload_ai_emr(
        treatment_id="10_880653606", 
        ai_emr={"主诉": "111", "现病史": "222", "既往史": "333", "个人史": "111", "家族史": "111", "婚育史": "111", "体格检查": "444", "辅助检查": "555", "诊断": "666", "处置": "777"}, 
        doctor_code="1011", 
        section_name="初诊演示"
    )