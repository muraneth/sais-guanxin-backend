from service.config.config import algo_config
from util.sync_http_request import send_request
from util.logger import service_logger
import traceback

report_summary_url = algo_config.medical_algo_service_http_url + "/assistant/medical_summary"

"""
report_info: 如果做报告摘要，请保证该字段不为空,str
"""
def report_summary(report_info: str = None):
    if not report_info or len(report_info) == 0:
        service_logger.error(f"report_info is empty")
        return None
    
    # 构造请求参数
    data = {
        "config": {},
        "report_info": report_info,
    }
        
    try:
        result = send_request(url=report_summary_url, body=data)
        status_code = result["status_code"] 
        if status_code == 200:
            body = result["body"]
            body_code = body["code"]
            if body_code == 0:
                summary = body["data"]["answer"]
                service_logger.info(f"medical_summary data: {data}, result: {summary}")
                return summary

        service_logger.error(f"failed to get medical summary, data: {data}, status_code: {status_code}, body: {result['body']}")
        return None

    except Exception as e:
        service_logger.error(f"failed to request: {str(e)}, data: {data}, stack: {traceback.format_exc()}")
        return None


if __name__ == "__main__":
    report_info = """
    复旦大学附属中山医院青浦分院检验报告单 临检体液
    门诊
    姓名：  科室：  就诊卡号：  打印次数：0  第1页 共1页
    性别：  病区：  送检医生：  样本编号：47
    年龄：  床号：  备注：  条形码号：
    临床诊断：肾功能不全
    检验项目  结果  参考区间  检验项目  结果  参考区间
    PH  6.5  4.5—8  尿渗透压  523  40—1400 mOsm/Kg
    尿胆红素  阴性  阴性  颜色  稻黄色  淡黄色
    尿酮体  阴性  阴性  透明度  透明  透明
    尿蛋白质  阴性  阴性
    亚硝酸盐  阴性  阴性
    尿葡萄糖  正常  正常
    尿比重  1.018  1.003—1.03
    尿胆原  正常  正常
    尿白细胞酯酶  阴性  阴性
    尿潜血  阴性  阴性
    白细胞总数  5.0  <25/ul
    红细胞计数  2.00  <23/ul
    上皮细胞计数  1.5  <31/ul
    病理性管型检查  阴性  阴性
    管型计数  0.00  <1/ul
    小圆上皮细胞  0.5  /ul
    酵母菌  阴性  阴性
    红细胞信息  未提示
    结晶检查  阴性  阴性
    报告评语：
    采样时间：2024-05-09 14:27:37  接收时间：2024-05-09 14:27:42  报告时间：2024-05-09 14:46:22  打印时间：2024-05-09 14:58:20
    注：本检验结果仅对该标本负责数据仅供临床参考。“↓”表示低于参考区间，“↑”表示高于参考区间，“*”表示为危急值。
    检验者：  审核者：
    """
    print(report_summary(report_info))