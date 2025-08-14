from service.exceptions import AppException
from util.execution_context import ExecutionContext


class UploadFileException(AppException):
    def __init__(self, reason_code: int, ctx: ExecutionContext):
        super().__init__(f"failed to upload file", reason_code, ctx)


class CreateDumpTaskException(AppException):
    def __init__(self, file_key, reason_code: int, ctx: ExecutionContext):
        super().__init__(f'failed to create dump task, file_key: {file_key}', reason_code, ctx)


class ListFilesException(AppException):
    def __init__(self, msg: str, reason_code: int, ctx: ExecutionContext):
        super().__init__(msg, reason_code, ctx)


class DeleteDocException(AppException):
    def __init__(self, doc_key, reason_code: int, ctx: ExecutionContext):
        super().__init__(f'failed to delete doc, doc_key: {doc_key}', reason_code, ctx)


class DownloadFileException(AppException):
    def __init__(self, file_key, reason_code: int, ctx: ExecutionContext):
        super().__init__(f'failed to download file, file_key: {file_key}', reason_code, ctx)
