# 医疗对话、问诊
# 文档：https://inflytech.feishu.cn/wiki/INlNwWGzviS2xDkHiBHc5fKGnGn
import asyncio
import traceback

from service.repository.mongo_dialog_manager import dialog_manager
from service.config.config import algo_config

from rag.rag_http import http_request

from util.logger import service_logger
from util.stream.response_queue import ResponseQueue
from util.stream.stream_search_model import StreamSearchData
from util.tracker.stream_search_tracker import StreamingSearchTracker

ai_doctor_dialogue_url = algo_config.ai_doctor_service_http_url + "/ai-doctor/medical-dialogue"

def medical_dialogue(response_queue, query_data, carrier, tracker):
    # 通过 http 请求调用 agent 服务
    coroutine = None
    try:
        service_logger.info(f"medical_dialogue query_data: {query_data}")
        # 复用 rag http 接口 http_request
        coroutine = http_request(
            url=ai_doctor_dialogue_url, 
            response_queue=response_queue, 
            model_query=query_data, 
            tracker=tracker
        )
        result = asyncio.run(coroutine, debug=True)
    except Exception as search_ex:
        response_queue.put(StreamSearchData.build_from_error("", carrier))
        response_queue.put(None)
        service_logger.error(traceback.format_exc())
    finally:
        coroutine.close()
        return result
