from contextvars import ContextVar

# from langfuse.client import StatefulTraceClient

# Create a context variable to store the request
# request_context: ContextVar[Request] = ContextVar(
#     "request_context", default=None
# )
# tracer_context: ContextVar[StatefulTraceClient] = ContextVar(
#     "tracer_context", default=None
# )
# user_query_context: ContextVar[str] = ContextVar(
#     "user_query_context", default=None
# )

context_variable_git_branch_name: ContextVar[str] = ContextVar(
    "git_branch_name", default=None
)
