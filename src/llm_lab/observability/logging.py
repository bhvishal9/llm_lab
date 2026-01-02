import json
import logging
import time
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request
from starlette.concurrency import iterate_in_threadpool

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("llm_lab.api")


async def log_http_requests(request: Request, call_next: Callable):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000

    log_payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "logger": logger.name,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": round(duration_ms, 3),
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
