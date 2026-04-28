from contextvars import ContextVar

dataset_context_var: ContextVar[str | None] = ContextVar("dataset", default=None)
top_k_context_var: ContextVar[int | None] = ContextVar("top_k", default=None)
candidate_k_context_var: ContextVar[int | None] = ContextVar(
    "candidate_k", default=None
)
request_id_context_var = ContextVar("request_id", default="not-set")
embed_ms_context_var: ContextVar[float | None] = ContextVar("embed_ms", default=None)
retrieve_ms_context_var: ContextVar[float | None] = ContextVar(
    "retrieve_ms", default=None
)
generate_ms_context_var: ContextVar[float | None] = ContextVar(
    "generate_ms", default=None
)
chunks_return_context_var: ContextVar[int | None] = ContextVar(
    "chunks_returned", default=None
)
