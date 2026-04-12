import json
import logging
import time
import uuid
from datetime import datetime, timezone

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from llm_lab.observability.context import (
    embed_ms_context_var,
    generate_ms_context_var,
    request_id_context_var,
    retrieve_ms_context_var,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("llm_lab.api")


class LoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start_time = time.perf_counter()
        request_id_context_var.set(str(uuid.uuid4()))
        result = {}

        async def wrapped_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                result["status_code"] = message["status"]
                headers = list(message.get("headers", []))
                headers.append(
                    (
                        b"x-request-id",
                        request_id_context_var.get().encode("utf-8"),
                    )
                )
                message["headers"] = headers
            elif message["type"] == "http.response.body":
                result["body"] = message["body"]
            await send(message)

        await self.app(scope, receive, wrapped_send)
        duration_ms = (time.perf_counter() - start_time) * 1000
        log_payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "logger": logger.name,
            "path": scope["path"],
            "method": scope["method"],
            "status_code": result["status_code"],
            "request_id": request_id_context_var.get(),
            "embed_ms": embed_ms_context_var.get(),
            "generate_ms": generate_ms_context_var.get(),
            "retrieve_ms": retrieve_ms_context_var.get(),
            "duration_ms": round(duration_ms, 3),
            "dataset": scope.get("state", {}).get("dataset", None),
            "top_k": scope.get("state", {}).get("top_k", None),
            "candidate_k": scope.get("state", {}).get("candidate_k", None),
            "num_chunks_returned": scope.get("state", {}).get(
                "num_chunks_returned", None
            ),
        }
        if result["status_code"] >= 400:
            error_message = None
            try:
                error_message = json.loads(result["body"].decode("utf-8")).get("error")
            except Exception:
                pass
            log_payload["level"] = "ERROR"
            if error_message:
                log_payload["error"] = error_message
        else:
            log_payload["level"] = "INFO"
        logger.info(json.dumps(log_payload))
