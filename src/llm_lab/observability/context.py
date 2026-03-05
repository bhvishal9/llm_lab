from contextvars import ContextVar

request_id = ContextVar("request_id", default="uuid-not-set")
