from service.exceptions import AppException
from util.execution_context import ExecutionContext

class NewDialogException(AppException):
    def __init__(self, reason_code: int, ctx: ExecutionContext):
        super().__init__(f"failed to new dialog:", reason_code, ctx)

class UpdateDialogException(AppException):
    def __init__(self, dialog_id: str, reason_code: int, ctx: ExecutionContext):
        super().__init__(f"failed to update dialog: {dialog_id}", reason_code, ctx)


class DeleteDialogException(AppException):
    def __init__(self, dialog_id: str, reason_code: int, ctx: ExecutionContext):
        super().__init__(f"failed to delete dialog: {dialog_id}", reason_code, ctx)
