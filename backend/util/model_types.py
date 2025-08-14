import uuid
from enum import Enum
from typing import Any


class MessageCollectionModel:
    domain = "domain"
    user_id = "user_id"
    dialog_id = "dialog_id"
    like = "like"
    dislike = "dislike"
    client_cost = "client_cost"
    user_data = "user_data"
    content = "content"
    cost = "cost"
    time = "time"
    conversation_id = "conversation_id"
    message_id = "message_id"
    stop_generating = "stop_generating"
    stop_generating_reason = "stop_generating_reason"
    unlike = "unlike"
    sources = "sources"
    enable_think = "enable_think"


class DialogCollectionModel:
    user = "user"
    name = "name"
    user_name = "user_name"
    company = "company"
    domain = "domain"
    time = "time"
    deleted = "deleted"
    user_id = "user_id"
    keyword = "keyword"
    dialog_id = "dialog_id"
    id = "id"
    sources = "sources"
    activated = "activated"


class RequestCollectionModel:
    user_id = "user_id"
    tag = "tag"
    task_state = "task_state"
    dialog_id = "dialog_id"
    message_id = "message_id"
    sources = "sources"


class TaskCollectionModel:
    status = "status"
    task_type = "task_type"
    params = "params"
    check_time = "check_time"
    created_at = "created_at"
    updated_at = "updated_at"


class StatusCode:
    Success = 0
    InternalError = 1
    BadRequest = 422

class RpcStatusCode:
    Success = 200000
    BadRequest = 400000


class DialogMgrCollectionType(Enum):
    MESSAGE = 1
    DIALOG = 2
    REQUEST = 3


class WikiSource(Enum):
    SYSTEM = 1
    PRIVATE = 2


class SearchSate(Enum):
    INITIALIZED = 1
    ON_GOING = 2
    FINISHED = 3
    CANCELLED = 4


class ReferenceType(Enum):
    PDF = 1
    MARKDOWN = 2
    URL = 3

class StopGeneratingReason(Enum):
    TIMEOUT = 1
    NEW_CONVERSATION = 2
    MANUAL = 3

class User:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __eq__(self, other):
        if other and isinstance(other, User):
            return other.id == self.id
        else:
            return False


class AppResponse:
    status_code = "code"
    message = "msg"
    latency = "latency"
    trace_id = "trace_id"


class ServiceException(Exception):
    def __init__(self, error_code: int, error_message: str = '', detail: Any = None) -> None:
        super().__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message
        self.detail = detail


class SearchTask:
    def __init__(self):
        self.state = SearchSate.INITIALIZED
        self.conversation_id = None
        self.tag = str(uuid.uuid4())

    def set_conversation_id(self, conversation_id: str) -> None:
        self.conversation_id = conversation_id

    def __eq__(self, other):
        return self.tag == other.tag


class LackFormatException(Exception):
    def __init__(self, message="Lack of file format") -> None:
        self.message = message
        super().__init__(self.message)


class Wiki:
    def __init__(self):
        self.doc_key = None
        self.file_name = None
        self.file_key = None
        self.desc = None
        self.stage = None
        self.stage_hint = None
        self.create_time = None
