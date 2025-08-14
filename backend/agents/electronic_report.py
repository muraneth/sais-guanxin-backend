# -*- coding: utf-8 -*-
# 电子病历生成 agent
# 接口设计文档：https://inflytech.feishu.cn/wiki/TNZOwwBBkikjzUklJXScYc4gnQe
from service.config.config import algo_config
from util.sync_http_request import send_request
from util.logger import service_logger
import traceback

electronic_report_url = algo_config.ai_doctor_service_http_url + "/ai-doctor/electronic-report"

def electronic_report(chat_history: list[dict], 
                      previous_auxiliary_report: list[dict] = None, 
                      current_auxiliary_report: list[dict] = None, 
                      enable_trace: bool = True):
    
    data = {
        "chat_history": chat_history,
        "previous_auxiliary_report": previous_auxiliary_report,
        "current_auxiliary_report": current_auxiliary_report,
        "enable_trace": enable_trace,
    }
    try:
        result = send_request(url=electronic_report_url, body=data)
        status_code = result["status_code"] 
        if status_code == 200:
            body = result["body"]
            body_code = body["code"]
            if body_code == 0:
                service_logger.info(f"electronic_report request data: {data}, successfully get electronic report, response body: {body}")
                return body["data"]

        service_logger.error(f"electronic_report request data: {data}, failed to get electronic report, status_code: {status_code}, body: {result['body']}")
        return None

    except Exception as e:
        service_logger.error(f"failed to request: {str(e)}, stack: {traceback.format_exc()}")
        return None


def main():

	chat_history = [{
		"role": "assistant",
		"content": "你好，请问你有何不适？"
	}, {
		"role": "user",
		"content": "最近胸闷"
	}, {
		"role": "assistant",
		"content": "<think>\n患者提到最近出现胸闷的症状，这是收集主诉阶段的重要信息。接下来，我需要询问胸闷的起始时间，以了解症状是急性发作还是慢性持续。这将帮助我们判断是急性事件（如急性心肌梗死）还是慢性疾病（如慢性心功能不全）导致的胸闷。此外，急性发作可能需要紧急处理，而慢性症状可能与长期的健康问题相关。\n</think>\n\n请问您的胸闷是什么时候开始的？是最近几天还是更早之前呢？"
	}, {
		"role": "user",
		"content": "几天前"
	}, {
		"role": "assistant",
		"content": "<think>\n患者表示胸闷是几天前开始的，这提示我们正在处理一个相对较新的症状，可能与急性事件有关，也可能与慢性病的急性加重有关。接下来，我需要询问胸闷的起始方式，以了解它是突然发生的还是逐渐加重的。突然发作可能提示急性冠脉综合征、肺栓塞等急性心血管或呼吸系统问题。逐渐加重可能与慢性心肺疾病、焦虑或压力有关。明确起始方式将帮助我们缩小可能的病因范围。\n</think>\n\n您的胸闷是突然出现的，还是慢慢加重的呢？"
	}, {
		"role": "user",
		"content": "慢慢加重"
	}, {
		"role": "assistant",
		"content": "<think>\n患者表示胸闷是慢慢加重的，这可能指向慢性心肺疾病或非心肺系统性因素，如焦虑或压力相关问题。由于胸闷可能涉及心肺系统，我接下来需要询问是否有伴随症状，如呼吸困难、心悸、出汗、恶心或晕厥等，这些伴随症状可以帮助识别心血管疾病、呼吸系统疾病或焦虑症等可能性。了解伴随症状将有助于进一步缩小病因范围。\n</think>\n\n在胸闷的时候，您有没有感到呼吸困难、心悸、出汗、恶心或晕厥等其他不适？"
	}, {
		"role": "user",
		"content": "有呼吸困难"
	}, {
		"role": "assistant",
		"content": "<think>\n患者同时出现胸闷和呼吸困难，这些症状可能与心血管疾病（如心力衰竭、冠心病）或呼吸系统疾病（如慢性阻塞性肺疾病、哮喘）有关。接下来，我需要询问呼吸困难的具体特征，如是否有活动后加重或夜间加重，这有助于判断是否存在运动性或夜间发作性问题。活动后加重可能与心功能不全或肺功能障碍相关，夜间加重可能提示心衰或睡眠呼吸障碍。此外，了解这些特征也能帮助排除或确认焦虑相关呼吸困难。\n</think>\n\n您的呼吸困难是在活动后会加重，还是在夜间更明显呢？"
	}, {
		"role": "user",
		"content": "活动后加重"
	}, {
		"role": "assistant",
		"content": "<think>\n患者描述呼吸困难在活动后加重，这通常提示心肺系统的问题，例如心力衰竭、冠心病或慢性阻塞性肺疾病。接下来，我需要进一步了解患者是否有其他心血管系统相关的症状，如心悸、胸痛或下肢水肿等，这些症状可能指向心力衰竭或冠心病。了解这些症状有助于确定心脏功能状态，以及是否需要进一步的心血管系统评估。\n</think>\n\n除了胸闷和呼吸困难，您有没有感到心悸、胸痛或下肢水肿等其他不适？"
	}, {
		"role": "user",
		"content": "有下肢水肿"
	}, {
		"role": "assistant",
		"content": "<think>\n患者同时存在胸闷、呼吸困难和下肢水肿，这组症状高度提示心力衰竭的可能性，尤其是右心衰竭。下肢水肿通常与体液潴留相关，而体液潴留是心力衰竭的典型表现。为了进一步明确心力衰竭的诊断，我需要询问患者的既往病史，包括是否有心脏病史、高血压、糖尿病或其他可能影响心脏功能的慢性疾病。这些信息将帮助确认潜在的心脏病因，并指导进一步的评估和治疗。\n</think>\n\n您过去有没有被诊断出心脏病、高血压、糖尿病或其他慢性疾病？"
	}, {
		"role": "user",
		"content": "没有"
	}, {
		"role": "assistant",
		"content": "<think>\n患者没有既往的心脏病、高血压或糖尿病等慢性病史，这使得原发性心力衰竭的可能性降低。然而，胸闷、呼吸困难和下肢水肿的组合仍需要考虑其他潜在原因，如心脏瓣膜病、肺部疾病或甲状腺功能异常等。为了进一步评估，我需要询问是否有其他可能影响心脏或肺功能的病史，如长期吸烟史、职业暴露或家族中有类似病史等，这些信息将帮助排除或确认其他系统性疾病。\n</think>\n\n您有长期吸烟史、职业暴露史或家族中有类似病史吗？"
	}, {
		"role": "user",
		"content": "有吸烟"
	}, {
		"role": "assistant",
		"content": "<think>\n患者有吸烟史，这显著增加了患心血管和呼吸系统疾病的风险，如慢性阻塞性肺疾病（COPD）或冠心病。吸烟与下肢水肿、呼吸困难和胸闷的组合，可能提示慢性阻塞性肺疾病或肺心病。接下来，我需要了解吸烟的频率和持续时间，这将有助于评估吸烟对肺功能的潜在影响，并确认是否存在长期肺损伤的可能性。吸烟的详细情况也将有助于进一步评估肺部疾病风险。\n</think>\n\n您能告诉我吸烟的频率和持续时间吗？例如，每天吸多少支烟，吸了多少年了？"
	}, {
		"role": "user",
		"content": "每天一包，20 年了"
	}, {
		"role": "assistant",
		"content": "<think>\n患者有长达20年的每天一包烟的吸烟史，这显著增加了患慢性阻塞性肺疾病（COPD）的风险，并可能导致肺心病，从而引起下肢水肿和呼吸困难。这种长期吸烟史还可能与慢性心力衰竭有关，因为吸烟是心血管疾病的风险因素之一。接下来，我需要询问患者是否有其他慢性阻塞性肺疾病或心血管疾病的症状，如慢性咳嗽、咳痰或胸痛，以帮助进一步明确诊断方向。\n</think>\n\n您有没有慢性咳嗽、咳痰或胸痛等其他症状？"
	}, {
		"role": "user",
		"content": "没有"
	}, {
		"role": "assistant",
		"content": "<think>\n患者没有慢性咳嗽、咳痰或胸痛等症状，这可能排除了某些常见的慢性阻塞性肺疾病（COPD）表现。然而，长期吸烟史仍然可能导致肺心病，这是一种由慢性肺部疾病导致右心室肥大和功能障碍的状况，表现为下肢水肿和呼吸困难。为了进一步评估，我需要询问患者是否有既往的肺功能检查或心功能检查，以及是否有定期的健康检查记录，这将有助于确认是否存在潜在的心肺功能异常。\n</think>\n\n您有没有做过肺功能检查或心功能检查？或者有定期的健康检查记录吗？"
	}, {
		"role": "user",
		"content": "没有"
	}, {
		"role": "assistant",
		"content": "<think>\n患者没有进行过肺功能检查或心功能检查，这使得我们无法通过客观检查结果来确认心肺功能状态。然而，患者的症状和长期吸烟史提示我们需要高度警惕潜在的心肺问题，尤其是肺心病或慢性心力衰竭。接下来，我需要询问患者是否有其他可能影响心肺功能的药物使用史或过敏史，因为某些药物（如利尿剂、降压药）和过敏反应也可能导致类似症状。\n</think>\n\n您目前正在使用哪些药物，或者有没有药物过敏史？"
	}, {
		"role": "user",
		"content": "有吃阿司匹林"
	}, {
		"role": "assistant",
		"content": "<think>\n患者正在服用阿司匹林，这是一种常用的抗血小板药物，用于预防心脑血管事件。阿司匹林通常不会直接导致胸闷、呼吸困难和下肢水肿，但长期使用可能与胃肠道副作用相关，如胃溃疡或出血。为了确保药物使用安全，我需要询问患者是否有胃肠道不适症状，如腹痛、黑便或消化不良，以排除药物相关的胃肠道问题。\n</think>\n\n您有没有腹痛、黑便或消化不良等胃肠道不适症状？"
	}, {
		"role": "user",
		"content": "没有"
	}, {
		"role": "assistant",
		"content": "<think>\n患者没有胃肠道不适症状，这使得药物（阿司匹林）引起的胃肠道问题的可能性较小。考虑到患者的胸闷、呼吸困难和下肢水肿，以及长期吸烟史，我们仍然需要高度怀疑慢性心肺问题，如肺心病或慢性心力衰竭。尽管患者没有进行过心肺功能检查，但症状和吸烟史提示需要进一步医学评估。在问诊结束前，我需要询问患者的一般情况，如睡眠、食欲和精神状态，以评估其整体健康状况。\n</think>\n\n您的睡眠、食欲和精神状态怎么样？有没有变化？"
	}, {
		"role": "user",
		"content": "没有变化"
	}, {
		"role": "assistant",
		"content": "<think>\n患者的睡眠、食欲和精神状态没有变化，这表明尽管存在胸闷、呼吸困难和下肢水肿等症状，但患者的整体健康状况相对稳定。这可能意味着症状尚未严重影响到其日常生活。尽管如此，患者长期吸烟史和当前症状仍提示需要进一步的医学评估，以排除潜在的心肺疾病。在结束问诊前，我需要向患者说明接下来的步骤，包括可能需要进行心肺功能检查，并安抚其情绪，避免过度担忧。\n</think>\n\n感谢您提供的信息，问诊环节已经完成。我们会分析这些信息，为您提供进一步的评估结果。请问您还有其他信息需要补充吗？</end>"
	}, {
		"role": "user",
		"content": "没有了"
	}, {
		"role": "assistant",
		"content": "<think>\n患者表示没有其他变化，这表明其整体健康状况除了胸闷、呼吸困难和下肢水肿外，其他方面相对稳定。然而，鉴于患者的症状和长期吸烟史，心肺系统的问题仍不能排除，尤其是肺心病或慢性心力衰竭。问诊环节已基本完成，接下来需要通过医学检查来进一步确认诊断。我将结束问诊，并告知患者等待后续分析结果，同时给予适当的情绪安抚。\n</think>\n\n感谢您提供的信息，问诊环节已经完成。我们会分析这些信息，为您提供进一步的评估结果。请问您还有其他信息需要补充吗？</end>"
	}],
	previous_auxiliary_report =  ["复旦大学附属中山医院\n超声心动图诊断报告\n\n患者姓名：  性别：男  年龄：58  心超号：ZS21002863  仪器：东16 EPIQ7-1\n门诊号：  住院号：  病室：  病床：\n\n(心脏彩色多普勒超声+左心功能测定+TDI)\n常规检查切面观：胸骨旁长轴观(√); 胸骨旁短轴观(√); 心尖切面观(√)  透声条件：中\n\n一、M型及血流多普勒超声测量：\n名称  测量值  正常值\n主动脉根部内径  33  20-37mm\n左房内径  39  19-40mm\n左室舒张末内径  51  35-56mm\n左室收缩末内径  33  23-35mm\n室间隔厚度  10  6-11mm\n左室后壁厚度  10  6-11mm\n肺动脉收缩压  30  <40mmHg\n\n二、左心功能测定及组织多普勒显像测量：\n① 左室射血分数(LVEF)：48%  <50%  60-70%\n二尖瓣血流图：EA双峰，E/A<0.8; DT：182 ms\nDTI示S波峰值：8.1 cm/s; e' / a '<1\n\n三、普通二维超声心动图和各心腔及大血管血流显像：\n1、左房内径正常，左室内径正常，左室壁厚度正常，左室流出道未见异常，左室乳头肌水平以下室间隔、前壁稍变薄，收缩活动减弱，心尖部各节段变薄膨出，收缩活动减弱至消失，局部呈矛盾运动，范围约2.5*3cm，心尖部见两处相邻附壁血栓，大小相似，约1.7*2cm，位于室间隔及下壁处，余节段收缩活动未见异常。\n2、二尖瓣不增厚，瓣叶开放不受限，瓣口面积正常范围，瓣叶关闭形态未见异常，彩色多普勒未测及二尖瓣反流。\n3、主动脉窦部不增宽，升主动脉不增宽，主动脉瓣三叶式，瓣膜形态正常，开放不受限，彩色多普勒未测及主动脉瓣反流。\n4、下腔静脉内径正常，右心腔内未见异常回声，房间隔未见回声缺失，彩色多普勒未见分流。右房内径正常，右室基底段内径正常，右室壁厚度正常，右室收缩活动未见异常，TAPSE示正常。肺动脉不增宽，肺动脉瓣不增厚，开放不受限，肺动脉平均压未测及，三尖瓣不增厚，瓣叶开放不受限，瓣叶关闭形态未见异常，彩色多普勒示轻微三尖瓣反流。\n5、心包腔内未见明显积液。\n\n四、结论：\n① 左室多壁段收缩活动异常，心尖部室壁瘤及附壁血栓形成（LVEF：48%）\n\n(报告仅供参考，请结合临床)\n检查时间：2021-01-05 15:12:52  检查医师：孔德红  审核医师：董丽莉"],
	current_auxiliary_report = []
	enable_trace = True

	result = electronic_report(chat_history, previous_auxiliary_report, current_auxiliary_report, enable_trace)
	print(result)

if __name__ == "__main__":
    main()