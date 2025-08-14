import asyncio

from service.repository.mongo_dialog_manager import MongoDialogManager
from util.logger import service_logger
from util.stream.stream_search_model import StreamSearchData
from util.timer import Timer


class StreamingSearchTracker:
    def __init__(self, dialog_manager: MongoDialogManager):
        self._task = None
        self._streaming_search_data = {}
        self._dialog_manager: MongoDialogManager = dialog_manager
        self._timer = Timer()
        # 需要保存到数据库的字段，可能散落在不同的 event 中，无法在 event 中统一处理
        # "answer" 不能删除，在获取历史对话中需要用到
        self._fields_to_save = ["query", "answer", "debug", "dialog_id", "prompt", "question_recommend"]

    # 跟踪数据: 将 data 中需要保存的字段数据保存到 self._streaming_search_data 中
    def track(self, data: StreamSearchData):
        for field_name in self._fields_to_save:
            if hasattr(data, field_name) and getattr(data, field_name) is not None:
                #service_logger.info(f"track field_name: {field_name}, value: {getattr(data, field_name)}")
                self._streaming_search_data[field_name] = getattr(data, field_name)


    def untrack(self):
        try:
            if self._task is not None and not self._task.done():
                self._task.cancel()
        except Exception as ex:
            service_logger.warn(f"cancel task failed: {ex}")  # The error is originated from cross-threads cancellation


    def store_message(self, dialog_id, message_id, sources, domain):
        #service_logger.info(f"store message dialog_id: {dialog_id}, message_id: {message_id}, content: {self._streaming_search_data}")
        self._dialog_manager.upsert_message(self._streaming_search_data,
                                               dialog_id,
                                               message_id,
                                               sources,
                                               self._timer.duration(),
                                               domain,
                                               enable_think=None)


    def bind_to_task(self, task: asyncio.Task):
        self._task = task


    def get_task(self):
        return self._task
