import asyncio
import traceback
from random import choice 
from metrics.meter_key import MeterKey
from metrics.meters import record_latency
from metrics.metrics import SEARCH_ALGO_LATENCY
from service.question_recommend.question_recommend import ThreadGetQuestionRecommend, question_filter
from service.config.config import algo_config
from util.aiohttp_sse_client import aiosseclient
from util.timer import Timer
from util.logger import algo_logger
from util.stream.response_queue import ResponseQueue
from util.stream.stream_search_model import StreamSearchData
from util.tracker.stream_search_tracker import StreamingSearchTracker

from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

rag_service_url = algo_config.medical_algo_service_http_url + "/assistant/rag_chat"

def rag_search_http(response_queue: ResponseQueue, model_query, tracer, carrier, tracker: StreamingSearchTracker):
    ctx = TraceContextTextMapPropagator().extract(carrier=carrier)
    with tracer.start_as_current_span("algo_task", context=ctx):
        result = {}
        timer = Timer()
        coroutine = None
        try:
            coroutine = http_request(
                url=rag_service_url, 
                response_queue=response_queue, 
                model_query=model_query, 
                tracker=tracker,
            )
            result = asyncio.run(coroutine, debug=True)
        except Exception as search_ex:
            carrier.update({"msg": str(search_ex)})
            response_queue.put(StreamSearchData.build_from_error("", carrier))
            response_queue.put(None)
            algo_logger.error(traceback.format_exc())
        finally:
            coroutine.close()
            record_latency(MeterKey(rag_search_http.__qualname__, rag_search_http.__name__), SEARCH_ALGO_LATENCY, timer.duration())
            return result


async def http_request(url: str, response_queue: ResponseQueue, model_query, tracker: StreamingSearchTracker):
    task = asyncio.create_task(request_work(url, response_queue, model_query))
    tracker.bind_to_task(task)
    result = await task
    return result


async def request_work(url: str, response_queue: ResponseQueue, model_query):
    unfinished_answer = ""
    cite_idx2ref={} # 引用编号到references_list的字典映射，用于问题推荐的过滤，格式 {0: {}, 1: {}}
    thread_rec_by_context = ThreadGetQuestionRecommend(chat_history=[], reference={})
    thread_rec_by_ref = ThreadGetQuestionRecommend(chat_history=[], reference={})
    async for raw_event in aiosseclient(url=url, data=model_query, timeout_total=2*60):
        event = {}

        try:
            event = raw_event.data_json
            if "msg_info" in event:
                algo_logger.error(f"get msg_info in event: {event}")
                # 有 msg_info 就表示失败了
                response_queue.put(StreamSearchData.Builder().event(StreamSearchData.SearchEvent.Debug).debug(event).build())
                response_queue.put(StreamSearchData.build_from_error("", event))
                response_queue.put(StreamSearchData.Builder().event(StreamSearchData.SearchEvent.Finished).build())
                # None 通知 ResponseQueue 结束
                response_queue.put(None)
                return
            
            event_type = event["event"]
            
        except Exception as e:
            # 输出 Exception 信息
            algo_logger.warning(f"can not get event type in {event}, error: {e}")
            continue

        # 处理参考资料
        if 'reference_list' in event:
            response_queue.put(StreamSearchData.Builder().event(StreamSearchData.SearchEvent.Recalled).reference(event['reference_list']).build())

        if "doc_reranked" in event:
            # 提前处理参考资料，用于问题推荐
            doc_reranked = event["doc_reranked"]
            # 提前展示参考资料
            response_queue.put(StreamSearchData.Builder().event(StreamSearchData.SearchEvent.Doc_Reranked).reference(doc_reranked).build())
            for idx in range(0, len(doc_reranked)):
                index_name = doc_reranked[idx][5]
                ref_info = doc_reranked[idx][1]
                doc_id = ref_info["fields"]["doc_id"]
                content = ref_info["fields"]["content"]
                cite_idx2ref[idx] = {
                    "index": index_name,
                    "doc_id": doc_id,
                    "content": content,
                }
            
        # debug 信息
        if "debug" in event:
            response_queue.put(StreamSearchData.Builder().event(StreamSearchData.SearchEvent.Debug).debug(event["debug"]).build())
            
        # 问题改写之后的query
        if "query_fixed_list" in event and len(event["query_fixed_list"]) > 0:
            query_rewrite = event["query_fixed_list"][-1]
            thread_rec_by_context.set(chat_history=model_query["chat_history"], reference=[], query_rewrite=query_rewrite)
            thread_rec_by_context.start_working()
        
        if event_type == StreamSearchData.SearchEvent.Trace.__str__():
            # 收集溯源信息，包括文档ID
            if "trace_info" in event:
                trace_info = event["trace_info"]
                ref_ids_dict = {}
                for info in trace_info:
                    for idx in info["cite_idx"]:
                        if idx in cite_idx2ref:
                            ref_ids_dict[idx] = True
                        else:
                            algo_logger.error(f"idx={idx} not found in cite_idx2ref={cite_idx2ref}")
                response_queue.put(StreamSearchData.Builder().event(StreamSearchData.SearchEvent.Trace).trace(event["trace_info"]).build())
        
        elif event_type == StreamSearchData.SearchEvent.Debug.__str__():
            #print(f"event={event}")
            del event["event"]
            response_queue.put(StreamSearchData.Builder().event(StreamSearchData.SearchEvent.Debug).debug(event).build())

        elif event_type == StreamSearchData.SearchEvent.Query_Understood.__str__():
            # 回复正在处理
            response_queue.put(StreamSearchData.Builder().event(StreamSearchData.SearchEvent.Query_Understood).build())
       
        elif event_type == StreamSearchData.SearchEvent.Answer.__str__() or event_type == StreamSearchData.SearchEvent.Refine_Answer.__str__():
            # Answer 与 Refine_Answer
            try:
                unfinished_answer = event[event_type.__str__()]
                response_queue.put(StreamSearchData
                            .Builder()
                            .event(StreamSearchData.SearchEvent.Answering)
                            .answer(unfinished_answer)
                            .build())
            except Exception as e:
                algo_logger.error(f"can not get unfinished answer, error: {e}")

        elif event_type in [StreamSearchData.SearchEvent.Diagnose_Finished.__str__(), 
                            StreamSearchData.SearchEvent.Electronic_Report.__str__(), 
                            StreamSearchData.SearchEvent.Department.__str__(), 
                            StreamSearchData.SearchEvent.Primary_Diagnose.__str__(), 
                            StreamSearchData.SearchEvent.Physical_Examine.__str__(), 
                            StreamSearchData.SearchEvent.Auxiliary_Examine.__str__(),
                            StreamSearchData.SearchEvent.Auxiliary_Items.__str__(),
                            StreamSearchData.SearchEvent.Update_Electronic_Report.__str__(),
                            StreamSearchData.SearchEvent.Final_Electronic_Report.__str__(),
                            StreamSearchData.SearchEvent.Definitive_Diagnose.__str__(),
                            StreamSearchData.SearchEvent.Gather_Additional_Info.__str__()]:
            response_queue.put(StreamSearchData.Builder().event(StreamSearchData.SearchEvent.from_str(event_type)).info(event[event_type.__str__()]).build())
            del event["event"]
            response_queue.put(StreamSearchData.Builder().event(StreamSearchData.SearchEvent.Debug).debug(event).build())

        elif event_type in [StreamSearchData.SearchEvent.Answering.__str__(),
                            StreamSearchData.SearchEvent.Answer_Thinking.__str__(),
                            StreamSearchData.SearchEvent.Answer_Content.__str__()]:
            # think 内容单独处理为 answer_thinking 事件
            if event_type == StreamSearchData.SearchEvent.Answer_Thinking.__str__():
                answer_event = StreamSearchData.SearchEvent.from_str(event_type)
            else:
                answer_event = StreamSearchData.SearchEvent.Answering
             # 收集回答片段
            try:
                if "answer" in event:
                    # 兼容新的回答格式
                    unfinished_answer = event["answer"]
                elif "messages" in event:
                    # 兼容旧的回答格式
                    unfinished_answer = event["messages"][0]["content"]["parts"][0]["content"]
                # 判断带不带溯源信息
                if "trace" in event:
                    trace_info = event["trace"]
                    response_queue.put(StreamSearchData
                                .Builder()
                                .event(answer_event)
                                .answer(unfinished_answer)
                                .trace(trace_info)
                                .build())
                    
                    if (not thread_rec_by_ref.has_started()) and ("cite_idx" in trace_info) and (len(trace_info["cite_idx"]) > 0):
                        cite_idx = event["trace"]["cite_idx"][0]
                        thread_rec_by_ref.set(chat_history=[], reference=[cite_idx2ref[cite_idx]])
                        thread_rec_by_ref.start_working()
                else:
                    response_queue.put(StreamSearchData
                                .Builder()
                                .event(answer_event)
                                .answer(unfinished_answer)
                                .build())
            except Exception as e:
                # 打印完整的 Exception 信息
                algo_logger.info(f"can not get unfinished answer, event={event}, error={e}")
        
        elif event_type == StreamSearchData.SearchEvent.Finished.__str__():
            # 处理结束
            # 结束之前先问题推荐
            if thread_rec_by_context.has_started():
                rec_by_context_result = thread_rec_by_context.wait_result()
                questions = rec_by_context_result["dial_questions"]
                if thread_rec_by_ref.has_started():
                    rec_by_ref_result = thread_rec_by_ref.wait_result()
                    if rec_by_ref_result and len(rec_by_ref_result["rag_questions"]) > 0:
                        if len(questions) >= 3:
                            questions.pop()
                        questions.append(choice(rec_by_ref_result["rag_questions"]))

                # 发送推荐问题
                response_queue.put(StreamSearchData.Builder().event(StreamSearchData.SearchEvent.Question_Recommend).question_recommend(questions).build())

            response_queue.put(StreamSearchData.Builder().event(StreamSearchData.SearchEvent.Finished).build())
            # None 通知 ResponseQueue 结束
            response_queue.put(None) 
            algo_logger.info(f"query RAG HTTP service successfully, url = {url}, model_query: {model_query}")
    