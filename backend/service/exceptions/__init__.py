from enum import Enum

from util.execution_context import ExecutionContext


class AppException(Exception):
    def __init__(self, msg: str, reason_code: int, ctx: ExecutionContext) -> None:
        super().__init__(msg)
        self.reason_code = reason_code
        self.ctx = ctx
        self.msg = msg

    def __str__(self) -> str:
        return f"{self.__class__.__name__}, msg: {self.msg}, reason_code: ({self.reason_code}), ctx: {self.ctx}"


class BackendServiceExceptionReasonCode(Enum):
    # dialog exceptions
    Match_Dialog_Count_Error = 410000
    # file service exceptions
    General_Error = 400000
    Access_Denied = 400001
    Invalid_Tenant = 400002
    Invalid_Operator = 400003
    Resource_Not_Found = 400004
    Lack_of_Parameter = 400005
    Interface_Parameter_Incorrect = 400006
    Duplicate_Resource = 400007
    Lack_of_Format = 400008
    Invalid_Format = 400009
    General_Internal_Error_Redouble = 500000
    Concurrent_Requests = 500001
    General_Internal_Error = 510000
    Rate_Limit_Exceeded = 510001
    Quota_Exceeded = 510002
