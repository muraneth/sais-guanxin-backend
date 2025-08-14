from service.exceptions import AppException
from util.execution_context import ExecutionContext


class StopGeneratingException(AppException):
    def __init__(self, message: str, reason_code: int, ctx: ExecutionContext):
        super().__init__(f"failed to stop generating: {message}", reason_code, ctx)

