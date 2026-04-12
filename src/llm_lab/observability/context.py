from contextvars import ContextVar

request_id_context_var = ContextVar("request_id", default="not-set")
embed_ms_context_var: ContextVar[float | None] = ContextVar("embed_ms", default=None)
retrieve_ms_context_var: ContextVar[float | None] = ContextVar(
    "retrieve_ms", default=None
)
generate_ms_context_var: ContextVar[float | None] = ContextVar(
    "generate_ms", default=None
)
