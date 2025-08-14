import asyncio
import re
import json
from typing import Any, Callable
from util.stream.stream_search_model import StreamSearchData
from util.tracker.stream_search_tracker import StreamingSearchTracker
from util.logger import service_logger
from metrics.meter_key import MeterKey
from metrics.meters import record_latency
from metrics.metrics import QUERY_UNDERSTAND_LATENCY, CHUNK_RETRIEVE_LATENCY, RE_RANK_LATENCY, ANSWER_FUSION_FIRST_TOKEN_LATENCY, ANSWER_FUSION_TOTAL_LATENCY, EXTRACT_INFO_LATENCY

class ResponseQueue:

    class __Differ:
        def __init__(self):
            self.pre_answer = ""

        def __str_subtract(self, str1, str2):
            len2 = len(str2)
            result = str1[len2:]
            return result

        def diff(self, current_stream_data: StreamSearchData):
            if (current_stream_data.answer is not None and current_stream_data.is_answer_event()):
                current_answer = current_stream_data.answer
                current_stream_data.answer = self.__str_subtract(current_stream_data.answer, self.pre_answer)
                self.pre_answer = current_answer

    def __init__(self,
                 next_action: Callable[[StreamSearchData], StreamSearchData],
                 error_action: Callable[[Any], StreamSearchData],
                 complete_action: Callable[[], None],
                 tracker: StreamingSearchTracker):
        self._queue = asyncio.Queue()
        self._done = False
        self._differ = ResponseQueue.__Differ()
        self._next_action = next_action
        self._error_action = error_action
        self._complete_action = complete_action
        self._references_info = []
        self._traces_info = {} # {"0":{"0.0":{}}, "1":{}, "2":{}}
        self._answer_with_cite = '' # SDK返回的 answer 不带引用信息，_answer_with_cite 是处理之后加了引用信息，用于保存到 DB 中
        self._answer_thinking = '' # 回答思考
        self._tracker = tracker
        self._debug = {}
        self._meterKey = MeterKey(path="/search/stream", method="post")

    def put(self, item: Any):
        self._queue.put_nowait(item)

    async def __await_get(self) -> Any:
        item = await self._queue.get()
        self._queue.task_done()
        if item is None:
            self._done = True
        return item
    
    def first_line(self, content: str) -> str:
        lines = content.split('\n', -1)
        for line in lines:
            #去除不可见字符
            line=re.sub('[^\u4e00-\u9fa5]+','', line)
            if len(line) > 0:
                return line
        return ""

    # 构建溯源和参考文献信息
    def build_trace_packet(self):
        for key in self._traces_info.keys():
            self._references_info[int(key)]['trace'] = self._traces_info[key]

        # 如果没有标题，
        for one_ref in self._references_info:
            if ('title' in one_ref) and (len(one_ref['title']) == 0):
                #print(f"one_ref={one_ref}")
                if ("extra" in one_ref) and ("file_name" in one_ref["extra"]) and (len(one_ref["extra"]["file_name"]) > 0):
                    # 用文件名作为标题
                    one_ref['title'] = one_ref["extra"]["file_name"]
                elif 'content' in one_ref:
                    # 用第一行汉字作为标题
                    one_ref['title'] = self.first_line(one_ref['content'])

        # reference 特殊处理，因此需要手动存入 DB
        self._tracker._streaming_search_data["reference"] = self._references_info
        # 将引用和溯源信息存入 debug 
        # self._debug['reference'] = self._references_info
        return StreamSearchData.Builder().event(StreamSearchData.SearchEvent.Trace).reference(self._references_info).build().to_packet()
    

    # 记录耗时
    def record_latency(self, key, debug_info):
        try:
            if key == "query_understand":
                latency = debug_info["query_understand"]["debug"]["time_debug"]["total_time"]
                record_latency(self._meterKey, QUERY_UNDERSTAND_LATENCY, latency=latency)
            elif key == "recall":
                for index_info in debug_info["recall"]["debug"].values():
                    if "time" in index_info:
                        latency = index_info["time"]["total_time"]
                        record_latency(self._meterKey, CHUNK_RETRIEVE_LATENCY, latency=latency)
            elif key == "rerank":
                latency = debug_info["rerank"]["time"]["total_duration"]
                record_latency(self._meterKey, RE_RANK_LATENCY, latency=latency)
            elif key == "answer_fuser":
                record_latency(self._meterKey, ANSWER_FUSION_FIRST_TOKEN_LATENCY, latency=debug_info["answer_fuser"]["answer_fusion_first_token_duration"])
                record_latency(self._meterKey, ANSWER_FUSION_TOTAL_LATENCY, latency=debug_info["answer_fuser"]["answer_fusion_total_duration"])
            elif key == "extract_info":
                record_latency(self._meterKey, EXTRACT_INFO_LATENCY, latency=debug_info["extract_info"]["duration_extract"])
                
        except Exception as e:
            service_logger.warning(f"record latency key: {key} failed: {e}")


    async def subscribe(self):
        try:
            while True:
                item = await self.__await_get()
                # 收集 debug 信息，debug event 可能多次返回
                if item and item.event == StreamSearchData.SearchEvent.Debug:
                    for key in item.debug:
                        self._debug[key] = item.debug[key]
                        self.record_latency(key, item.debug)
                    continue
                
                # 将 trace_info 放回到 debug 中
                if item and item.event == StreamSearchData.SearchEvent.Trace:
                    self._debug["trace_info"] = item.trace
                    continue
                
                # 提前展示参考文献
                if item and item.event == StreamSearchData.SearchEvent.Doc_Reranked and item.reference:
                    yield StreamSearchData.Builder().event(StreamSearchData.SearchEvent.Doc_Reranked).reference(self._extract_reference(item.reference)).build().to_packet()
                    continue
                
                # AI Doctor 相关事件
                if item and item.event in [StreamSearchData.SearchEvent.Diagnose_Finished,
                                           StreamSearchData.SearchEvent.Electronic_Report,
                                           StreamSearchData.SearchEvent.Department,
                                           StreamSearchData.SearchEvent.Primary_Diagnose,
                                           StreamSearchData.SearchEvent.Physical_Examine,
                                           StreamSearchData.SearchEvent.Auxiliary_Examine,
                                           StreamSearchData.SearchEvent.Auxiliary_Items,
                                           StreamSearchData.SearchEvent.Update_Electronic_Report,
                                           StreamSearchData.SearchEvent.Final_Electronic_Report,
                                           StreamSearchData.SearchEvent.Definitive_Diagnose,
                                           StreamSearchData.SearchEvent.Gather_Additional_Info]:
                    self._tracker._streaming_search_data[item.event.__str__()] = item.info
                    yield item.to_packet()
                    continue
               
                # 收集参考文献
                if item and item.event == StreamSearchData.SearchEvent.Recalled and item.reference:
                    self._references_info = item.reference
                
                # 收集溯源信息
                if item and item.is_answer_event() and item.trace:
                    self.collect_trace_info(item.trace)
                
                # 结束之前，综合所有的引用参考、溯源信息，以及 debug 信息，并返回
                if item and item.event == StreamSearchData.SearchEvent.Finished:
                    yield self.build_trace_packet() # 包括将引用和溯源信息存入 debug 
                    # 生成 debug 事件
                    yield StreamSearchData.Builder().event(StreamSearchData.SearchEvent.Debug).debug(self._debug).build().to_packet()
                    # debug 存入 DB
                    self._tracker._streaming_search_data["debug"] = self._debug

                element = self._next_action(item)
                if element is not None:
                    self._differ.diff(element)
                    if element.is_answer_event() == False or element.answer_length() != 0:
                        # 收集引用信息
                        self.add_cite_info(element)
                        if element.event == StreamSearchData.SearchEvent.Answer_Thinking:
                            # 收集回答思考内容
                            self._answer_thinking += element.answer
                        elif element.answer_length() != 0:
                            # 收集正式回答内容
                            self._answer_with_cite += element.answer
                        yield element.to_packet()

                # 结束之前，用带有引用信息的答案保存到数据库中，用于前端展示历史会话
                if self._done:
                    self._tracker._streaming_search_data["answer_with_cite"] = self._answer_with_cite
                    self._tracker._streaming_search_data["answer_thinking"] = self._answer_thinking
                    break
        
        except Exception as consume_ex:
            service_logger.warning(f"subscribe error: {consume_ex}")
            yield self._error_action(consume_ex).to_packet()
        finally:
            self._complete_action()

    # 当回答过程中出现溯源信息，添加进 answer 里面，便于前端实时渲染溯源
    def add_cite_info(self, element):
        if element.is_answer_event() == False:
            return
        if element.trace is None:
            return
        if 'cite_idx' not in element.trace:
            return
        if 'cite_infos' not in element.trace:
            return
        
        n_cnt = 0
        while str.endswith(element.answer, "\n"):
            n_cnt += 1
            element.answer = element.answer.removesuffix("\n")

        cite_infos = element.trace['cite_infos']
        if isinstance(cite_infos, list):
            for item in cite_infos:
                element.answer += f"[^{item}]"
        else:
            element.answer += f"[^{cite_infos}]"

        for i in range(n_cnt):
            element.answer += "\n"

    def collect_trace_info(self, trace):
        if not trace:
            return
        if "cite_idx" not in trace:
            return
        # 用于构建 answer 中的引用信息
        cite_infos = []
        for cite_idx in trace["cite_idx"]:
            # 初始化新的空列表
            if cite_idx not in self._traces_info:
                self._traces_info[cite_idx] = {}
            
            key2 = str(cite_idx)+"."+str(len(self._traces_info[cite_idx]))
            self._traces_info[cite_idx][key2] = trace

            cite_infos.append(key2)
        
        trace['cite_infos'] = cite_infos

    def _extract_reference(self, reference: list):
        result = []
        for ref_tuple in reference:
            ref_field = ref_tuple[1]["fields"]
            # 对于有文件名的文档，将文件名作为 title
            if len(ref_field["title"]) == 0 and ("reference" in ref_field) and ("file_name" in ref_field["reference"]) and (len(ref_field["reference"]["file_name"]) > 0):
                ref_field["title"] = ref_field["reference"]["file_name"]
            result.append(ref_field)
        return result