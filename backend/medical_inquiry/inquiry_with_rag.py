import asyncio
import traceback

from metrics.meter_key import MeterKey
from metrics.meters import record_latency
from metrics.metrics import SEARCH_ALGO_LATENCY
from rag.rag_http import http_request
from service.config.config import algo_config
from util.timer import Timer
from util.logger import algo_logger
from util.stream.response_queue import ResponseQueue
from util.stream.stream_search_model import StreamSearchData
from util.tracker.stream_search_tracker import StreamingSearchTracker

from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

inquiry_service_url = algo_config.medical_algo_service_http_url + "/assistant/medical-explorer-rag-stream"

def inquiry_with_rag(response_queue: ResponseQueue, model_query, tracer, carrier, tracker: StreamingSearchTracker):
    ctx = TraceContextTextMapPropagator().extract(carrier=carrier)
    with tracer.start_as_current_span("algo_task", context=ctx):
        result = {}
        timer = Timer()
        coroutine = None
        try:
            # 复用 rag http 接口 http_request
            coroutine = http_request(
                url=inquiry_service_url, 
                response_queue=response_queue, 
                model_query=model_query, 
                tracker=tracker
            )
            result = asyncio.run(coroutine, debug=True)
        except Exception as search_ex:
            carrier.update({"msg": str(search_ex)})
            response_queue.put(StreamSearchData.build_from_error("", carrier))
            response_queue.put(None)
            algo_logger.error(traceback.format_exc())
        finally:
            coroutine.close()
            record_latency(MeterKey(inquiry_with_rag.__qualname__, inquiry_with_rag.__name__), SEARCH_ALGO_LATENCY, timer.duration())
            return result
