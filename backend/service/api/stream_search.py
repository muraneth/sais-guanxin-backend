import asyncio
import traceback
import json
from fastapi import APIRouter, Depends
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from rag.rag_http import rag_search_http
from medical_inquiry.inquiry_with_rag import inquiry_with_rag
from service.config.config import service_config
from service.repository.mongo_dialog_manager import dialog_manager
from service.exceptions import BackendServiceExceptionReasonCode
from service.exceptions.stream_search_exceptions import StopGeneratingException
from service.package.auth import authenticate, check_user, CMS_USER
from service.package.dumper_client import HttpAsyncDumperClient
from service.package.file_service_client import HttpAsyncFileServiceClient
from util.execution_context import ExecutionContext
from util.stream.response_queue import ResponseQueue
from util.logger import service_logger
from util.stream.stream_search_model import StreamSearchData
from util.tracker.stream_search_tracker import StreamingSearchTracker
from util.model_types import MessageCollectionModel, User, ReferenceType, AppResponse, StatusCode, StopGeneratingReason
from util.timer import Timer
from service.config.config import algo_config
from util.mode import MODE_INQUIRY, MODE_INQUIRY_MINI, DOMAIN_SEARCH, DOMAIN_INQUIRY, DOMAIN_INQUIRY_MINI, get_domain_from_mode
from service.repository.mongo_task_manager import task_manager
from worker.process_upload_report import get_report_info_by_id
router = APIRouter(
    prefix="/api"
)

AUTHz_HEADER_KEY = "Authorization"
file_service_client = HttpAsyncFileServiceClient(service_config.file_service.url)
tittle_getter = HttpAsyncDumperClient(service_config.dump_service.url, service_config.tenant_id)

@router.post('/search/stop_generating')
async def stop_generating(request: Request, requester: User = Depends(authenticate)):
    check_user(requester)
    timer = Timer()
    # 参数检查 - message_id
    data = await request.json()
    if MessageCollectionModel.message_id not in data:
        raise StopGeneratingException('empty message_id',
                                    BackendServiceExceptionReasonCode.Lack_of_Parameter.value,
                                    ExecutionContext.current())
    message_id = data[MessageCollectionModel.message_id]
    # 参数检查 - stop_generating_reason
    if MessageCollectionModel.stop_generating_reason not in data:
        raise StopGeneratingException('empty stop_generating_reason',
                                    BackendServiceExceptionReasonCode.Lack_of_Parameter.value,
                                    ExecutionContext.current())
    stop_generating_reason = data[MessageCollectionModel.stop_generating_reason]
    if stop_generating_reason not in StopGeneratingReason.__members__:
        raise StopGeneratingException('unknown stop_generating_reason',
                                    BackendServiceExceptionReasonCode.Interface_Parameter_Incorrect.value,
                                    ExecutionContext.current())

    result = dialog_manager.stop_generating(message_id, stop_generating_reason)
    
    if result.matched_count == 1:
        resp = {
            AppResponse.status_code: StatusCode.Success,
            AppResponse.latency: timer.duration()
        }
    else:
        raise StopGeneratingException(message_id,
                                    BackendServiceExceptionReasonCode.General_Internal_Error_Redouble.value,
                                    ExecutionContext.current())
    return JSONResponse(resp)

@router.post('/search/stream')
async def search(request: Request, requester: User = Depends(authenticate)):
    status_code = 200
    msg = ""
    carrier = {}
    tracker = StreamingSearchTracker(dialog_manager) # 存入db
    dialog_id = ""
    is_debugging = False
    data_event = asyncio.Event()
    data = await request.json()
    domain = DOMAIN_SEARCH
    if "mode" in data:
        domain = get_domain_from_mode(data["mode"])
        
    service_logger.info(f"search_stream got request: {data}")
    # 过滤
    def on_next_callback(item: StreamSearchData):
        # 过滤
        if item is None:
            filter_result = item
        elif not is_debugging and item.event == StreamSearchData.SearchEvent.Debug:
            filter_result = None
        elif item.event == StreamSearchData.SearchEvent.Recalled:
            # 召回和溯源信息都在 trace，所以暂时不需要 event: recalled，
            filter_result = None
        else:
            item.meta = carrier
            filter_result = item
        # 保存
        tracker.track(item)
        return filter_result

    def on_error_callback(error: Exception):
        service_logger.error(f"error during stream search: {str(error)}, stack: {traceback.format_exc()}")
        return StreamSearchData.build_from_error(dialog_id, carrier)

    def on_completed_callback():
        service_logger.info(f"response complete request: {data}")
        tracker.untrack()
        data_event.set()

    response_queue = ResponseQueue(next_action=on_next_callback, error_action=on_error_callback, complete_action=on_completed_callback, tracker=tracker)
    try:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("search") as span:
            TraceContextTextMapPropagator().inject(carrier)
            carrier.update({
                "trace_id": hex(span.get_span_context().trace_id)
            })
            app_id = request.headers.get(AUTHz_HEADER_KEY)
            if app_id is None or app_id != service_config.app_id_from_fr:
                check_user(requester)
            else:
                requester = CMS_USER
            
            if data.get("message_id"):
                dialog_manager.clear_stop_generating(message_id=data.get("message_id"))
            raw_query = data['query']
            is_debugging = data.get('is_debugging', False)
            dialog_id = await add_dialog(data.get("dialog_id"), requester, raw_query, data.get("sources"), domain)
            # 查询 DB 历史对话记录
            history = dialog_manager.get_dialog_messages_context(domain, dialog_id)
            if len(history) == 1:
                # 激活 dialog
                service_logger.info(f"activate dialog: {dialog_id}")
                dialog_manager.activate_dialog(dialog_id)
            # 初始化 message
            message_id = await overwrite_ans(dialog_id, data.get("message_id"), carrier, domain, data.get("enable_think"))
            model_query = await build_model_query(kb_key=requester.id,
                                                  raw_query=data.get("query"),
                                                  sources=data.get("sources"),
                                                  history=history,
                                                  enable_think=data.get("enable_think"))

            # 构造查体请求
            if data.get("physical_choice"):
                model_query["physical_choice"] = get_physical_choice(history=history, data=data)
            
            # 构造上传报告解读的请求
            if data.get("auxiliary_choice"):
                model_query["auxiliary_choice"] = get_auxiliary_choice(history=history, data=data)

            # 构造上传多份检验检查报告的请求
            if data.get("previous_auxiliary_upload"):
                model_query["previous_auxiliary_upload"] = build_previous_auxiliary_upload_query(data)

            # There are some sync calls in algo modules, thus put it in an executor to avoid blocking the elp
            response_queue.put(StreamSearchData.Builder()
                             .event(StreamSearchData.SearchEvent.Received)
                             .query(raw_query)
                             .dialog_id(dialog_id)
                             .message_id(message_id)
                             .meta(carrier)
                             .build())
            if domain == DOMAIN_INQUIRY_MINI or domain == DOMAIN_INQUIRY:
                service_logger.info(f"medical_inquiry by query: {model_query}")
                if domain == DOMAIN_INQUIRY_MINI:
                    # multi_step 可选参数，默认是 True，如果用户选了 mini 版本就传 False
                    model_query["multi_step"] = data["multi_step"]
                asyncio.get_event_loop().run_in_executor(None, inquiry_with_rag, response_queue, model_query, tracer, carrier, tracker)
            else:
                service_logger.info(f"rag_search_http by query: {model_query}")
                asyncio.get_event_loop().run_in_executor(None, rag_search_http, response_queue, model_query, tracer, carrier, tracker)

    except Exception as search_ex:
        service_logger.error(f"failed to do search: {str(search_ex)}, stack: {traceback.format_exc()}")
        carrier.update({"message": str(search_ex)})
        response_queue.put(StreamSearchData.build_from_error(dialog_id, carrier))
        response_queue.put(None)

    finally:
        if status_code == 401:
            carrier.update({"msg": msg})
            return StreamingResponse(status_code=401, content=StreamSearchData.build_from_error(dialog_id, carrier))

        async def flush():
            try:
                await data_event.wait()
                tracker.store_message(dialog_id, message_id, data.get("sources"), domain=domain)
            except asyncio.CancelledError:
                service_logger.warning("asyncio.CancelledError in flush")
            except Exception as flush_ex:
                service_logger.error(f"flush failed: {flush_ex}")

        a = asyncio.create_task(flush())
        return StreamingResponse(response_queue.subscribe(), media_type="text/event-stream", status_code=status_code)


async def add_dialog(dialog_id, requester: User, query: str, sources: dict, domain: str) -> str:
    if dialog_id is None or dialog_id == '':
        new_dialog = dialog_manager.add_dialog(user_id=requester.id,
                                                  user_name=requester.username,
                                                  company=requester.company,
                                                  name=query,
                                                  sources=sources,
                                                  domain=domain)
        if new_dialog:
            return str(new_dialog.inserted_id)
    else:
        return dialog_id


async def overwrite_ans(dialog_id, message_id, meta, domain, enable_think):
    if enable_think is None:
        enable_think = False
    try:
        new_message_id = dialog_manager.upsert_message(
            StreamSearchData.get_non_answering_data(StreamSearchData.SearchEvent.Init, meta).dict(),
            dialog_id,
            message_id,
            {},
            0.0,
            domain,
            enable_think)
        return new_message_id
    except Exception as e:
        service_logger.error(f"Error in overwrite_ans: {str(e)}")
        raise


def get_physical_choice(history, data):
    history_info = get_info_from_history(history)
    # 构造查体请求
    choice = data.get("physical_choice")["choice"]
    if choice == "simulate":
        # 模拟查体
        physical_examine = history_info.get("physical_examine")
        if isinstance(physical_examine, dict):
            additional_info = json.dumps(physical_examine, ensure_ascii=False)
        elif isinstance(physical_examine, list):
            additional_info = json.dumps(physical_examine, ensure_ascii=False)
        else:
            additional_info = physical_examine
    elif choice == "upload":
        # 上传查体
        additional_info = data.get("physical_choice")["additional_info"]
    elif choice == "skip":
        # 跳过查体
        additional_info = ""
    else:
        # 未知选择
        service_logger.error(f"unknown physical choice: {choice}")
        additional_info = ""
    
    return {
        "choice": choice,
        "additional_info": additional_info,
        "electronic_report": history_info["electronic_report"],
    }


def get_auxiliary_choice(history, data):
    history_info = get_info_from_history(history)
    choice = data.get("auxiliary_choice")["choice"]
    if choice == "simulate":
        # 模拟辅助检查
        auxiliary_examine = history_info["auxiliary_examine"]
        if isinstance(auxiliary_examine, dict):
            additional_info = json.dumps(auxiliary_examine, ensure_ascii=False)
        elif isinstance(auxiliary_examine, list):
            additional_info = json.dumps(auxiliary_examine, ensure_ascii=False)
        else:
            additional_info = auxiliary_examine

    elif choice == "upload":
        # 上传报告
        report_ids = data.get("auxiliary_choice")["report_id"]
        additional_info = get_additional_info_from_id(report_ids)

    elif choice == "skip":
        # 跳过上传报告
        additional_info = ""

    else:
        # 未知选择
        service_logger.error(f"unknown auxiliary choice: {choice}")
        additional_info = ""
    
    return {
        "choice": choice,
        "additional_info": additional_info,
        "auxiliary_items": history_info["auxiliary_items"],
        "electronic_report": history_info["electronic_report"]
    }


def get_additional_info_from_id(report_ids):
    additional_info_list = []
    for report_id in report_ids:
        additional_info = get_report_info_by_id(report_id)
        if additional_info:
            additional_info_list.append(additional_info)

    if len(additional_info_list) == 0:
        return ""
    elif len(additional_info_list) == 1:
        return additional_info_list[0]
    else:
        return additional_info_list


def build_previous_auxiliary_upload_query(data):
    """
    data = {
        "previous_auxiliary_upload": {
            "report_id": ["xxxx", "yyy"]
        }
    }
    """
    # 上传报告
    report_ids = data.get("previous_auxiliary_upload")["report_id"]
    additional_info = get_additional_info_from_id(report_ids=report_ids)
    if isinstance(additional_info, str):
        # 保证 previous_auxiliary_upload 返回的是 list
        additional_info = [additional_info]
    return {
        "additional_info": additional_info
    }


# 开启个人知识库: "sources": [{ "type": "private", "index": "health-kb-inf-private", "docs": ["98bd7112-e5bb-41b6-9d51-bd6f843396f3"]}
# 开启内置知识库 'sources': [{'type': 'system', 'index': 'health-guideline'}, {'type': 'system', 'index': 'health-knowledge'}]
# 开启外网搜索： "bing_searcher" 作为index名
async def build_model_query(kb_key, raw_query, sources, history, enable_think):
    request = {}
    # 配置
    config = {}
    private_sources = []
    specify_sources = []
    if len(sources) > 0:
        for s in sources:
            # 点击推荐问题，指定 doc_id
            #print(f"source={s}")
            if 'index' in s and 'docid' in s and s['docid']:
                if isinstance(s['docid'], str):
                    s['docid'] = [int(s['docid'])]
                elif isinstance(s['docid'], int):
                    s['docid'] = [s['docid']]
                #print(f"specify_source={s}")
                specify_sources.append(s)
            # 个人知识库
            if "private" == s.get('type'):
                s["index"] = algo_config.private_index
                s["kb_key"] = kb_key
                private_sources.append(s)
            # 外网搜索（bing）
            if "public" == s.get('type'):
                config['bing_searcher_config'] = {
                    'enabled': True,
                }
            # 系统知识库支持用户指定
            elif 'system' == s.get('type') and 'index' in s:
                for index in s.get('index'):
                    specify_sources.append({'index': index})
    
    # 是否开启推理
    if enable_think:
        if "answer_fuser_config" not in config:
            config["answer_fuser_config"] = {}
        config["answer_fuser_config"]["enable_think"] = True
    request["config"] = config

    request["sources"] = []
    if len(private_sources) > 0:
        request["sources"] = private_sources
    if len(specify_sources) > 0:
        request["sources"].extend(specify_sources)
    
    # 组装历史对话
    messages_context = []
    for content in history:
        query = content.get("query")
        if query is not None and query != "":
            messages_context.append({
                "role": "user",
                "content": query
            })
        answer = content.get("answer")
        if answer is not None and answer != "":
            messages_context.append({
                "role": "assistant",
                "content": answer
            })
        # 有预问诊结束的标志
        if content.get("diagnose_finished"):
            request["diagnose_finished"] = True

    messages_context.append({
        "role": "user",
        "content": raw_query
    })
    request["chat_history"] = messages_context
    
    return request


# 从 history 中获取最后一次信息
def get_info_from_history(history):
    electronic_report = None
    auxiliary_items = None
    physical_examine = None
    auxiliary_examine = None
    for each in history:
        if each.get(StreamSearchData.SearchEvent.Electronic_Report.__str__()):
            electronic_report = each.get(StreamSearchData.SearchEvent.Electronic_Report.__str__())
        if each.get(StreamSearchData.SearchEvent.Auxiliary_Items.__str__()):
            auxiliary_items = each.get(StreamSearchData.SearchEvent.Auxiliary_Items.__str__())
        if each.get(StreamSearchData.SearchEvent.Physical_Examine.__str__()):
            physical_examine = each.get(StreamSearchData.SearchEvent.Physical_Examine.__str__())
        if each.get(StreamSearchData.SearchEvent.Auxiliary_Examine.__str__()):
            auxiliary_examine = each.get(StreamSearchData.SearchEvent.Auxiliary_Examine.__str__())
    return {
        "electronic_report": electronic_report,
        "auxiliary_items": auxiliary_items,
        "physical_examine": physical_examine,
        "auxiliary_examine": auxiliary_examine
    }


def build_ka_link(link: bool, source: str, file_format: str) -> str:
    if file_format is None:
        file_format = "pdf"
    if link:
        return (service_config.search_domain + "/api/self/download" + "?link="
                + source + "&file_format=" + file_format)
    else:
        return (service_config.search_domain + "/api/self/download" + "?file_key="
                + source + "&file_format=" + file_format)
