import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request, Response
from starlette.concurrency import iterate_in_threadpool

from llm_lab.observability.context import (
    request_id_context_var,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("llm_lab.api")


async def log_http_requests(request: Request, call_next: Callable):
    start_time = time.perf_counter()
    request_id_context_var.set(str(uuid.uuid4()))
    response: Response = await call_next(request)
    response.headers["x-request-id"] = request_id_context_var.get()
    duration_ms = (time.perf_counter() - start_time) * 1000

    log_payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "logger": logger.name,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": round(duration_ms, 3),
        "request_id": request_id_context_var.get(),
        "dataset": getattr(request.state, "dataset", None),
        "top_k": getattr(request.state, "top_k", None),
        "candidate_k": getattr(request.state, "candidate_k", None),
        "num_chunks_returned": getattr(request.state, "num_chunks_returned", None),
    }

    if response.status_code >= 400:
        error_message = None
        try:
            response_body = [section async for section in response.body_iterator]
            response.body_iterator = iterate_in_threadpool(iter(response_body))

            body_content = b"".join(response_body).decode()
            if body_content:
                error_message = json.loads(body_content).get("error")
        except Exception:
            pass
        log_payload["level"] = "ERROR"
        if error_message:
            log_payload["error"] = error_message
    else:
        log_payload["level"] = "INFO"

    logger.info(json.dumps(log_payload))
    return response
