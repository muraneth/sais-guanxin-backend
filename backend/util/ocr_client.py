import os
import asyncio
import base64
import requests
from io import BytesIO
from util.logger import service_logger
from util.sync_http_request import send_request
from util.aiohttp_sse_client import aiosseclient
from service.config.config import ZUOYI_API_KEY, algo_config
import traceback

zuoyi_url = f"https://api.zuoshouyisheng.com/ocr_structure?apikey={ZUOYI_API_KEY}"
ocr_server_url = algo_config.medical_algo_service_http_url + "/assistant/report_interpretation"

def _url_to_base64(image_url: str) -> str:
    try:
        # 判断 image_url 是否为本地文件
        if os.path.exists(image_url):
            # 读取本地文件
            with open(image_url, 'rb') as image_file:
                base64_data = base64.b64encode(image_file.read()).decode('utf-8')
        else:
            # 读取网络文件
            response = requests.get(url=image_url) 
            base64_data = base64.b64encode(BytesIO(response.content).read()).decode('utf-8')
    except:
        service_logger.error(traceback.format_exc())
        return ""
        
    # 判断 base64_data 是否为空
    if not base64_data or base64_data == "":
        return ""
    
    # 判断 image_url 是否为 png 格式
    image_format = "jpeg"
    if image_url.find(".png") >= 0:
        image_format = "png"

    # 返回 base64 数据
    return f"data:image/{image_format};base64," + base64_data
    
        
# 左医OCR接口
class OcrZuoyiClient:

    def process_image(self, image_url: str):
        image_base64 = _url_to_base64(image_url)
        #service_logger.info(f"image_base64: {image_base64}")    
        # 如果 image_base64 为空，则返回空字符串
        if not image_base64 or image_base64 == "":
            return {'message': 'image_base64 is empty'}
        
        try:
            response = send_request(
                url=zuoyi_url,
                method="POST",
                headers={"Content-Type": "application/json"},
                body={"action": "auto", "image_data": image_base64}
            )
            response_body = response["body"]
        except:
            service_logger.error(traceback.format_exc())
            response_body = {"result" : "error"}
        
        return response_body


# 算法端提供的OCR接口
class OCRClient:

    def process_image(self, image_url: str):
        try:
            base64_data = _url_to_base64(image_url=image_url)
            data = {
                    "config": {}, 
                    "need_encode": False,
                    "img_base64": base64_data
                }
            
            async def call():
                answer = ""
                async for event in aiosseclient(url=ocr_server_url, data=data):
                    if "answer" in event.data_json:
                        answer = event.data_json["answer"]
                return answer
            response_body = asyncio.run(call())
            process_image_result = {
                "result": response_body,
                "status": 0,
            }
        except:
            service_logger.error(traceback.format_exc())
            process_image_result = {"result" : "error", "status": 1}
        
        return process_image_result


ocr_client = OCRClient()
zuoyi_client = OcrZuoyiClient()
