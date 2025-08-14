from contextvars import ContextVar
from typing import ClassVar

from opentelemetry import trace


class ExecutionContext:
    context: ClassVar[ContextVar] = ContextVar("ExecutionContext")
    USER_ID = "user_id"
    FILE_SVC_CLIENT = "file_service_client"
    EMPTY_TRACE_ID = ""

    def __init__(self):
        self.trace_id = ExecutionContext.EMPTY_TRACE_ID
        self.attr = {}

    def __enter__(self) -> "ExecutionContext":
        self.token = ExecutionContext.context.set(self)
        return self

    def __exit__(self, type_, value, traceback) -> None:
        ExecutionContext.context.reset(self.token)

    def __str__(self):
        return f"trace_id={self.trace_id}"

    @staticmethod
    def current() -> "ExecutionContext":
        """Returns the current ExecutionContext, or a clean one if there's no current context."""
        ctx = ExecutionContext.context.get(ExecutionContext())
        ctx._get_trace_id()
        return ctx

    def _get_trace_id(self):
        current_span = trace.get_current_span()
        self.trace_id = hex(current_span.get_span_context().trace_id)
