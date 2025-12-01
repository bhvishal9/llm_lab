from datetime import datetime, timezone
import json
import time
import logging

from pydantic import BaseModel
from fastapi import FastAPI, Request

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

logger = logging.getLogger(__name__)


class EchoRequest(BaseModel):
    name: str


app = FastAPI(title="llm_lab", version="0.0.1")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000

    log_payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "logger": logger.name,
        "level": "INFO",
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": round(duration_ms, 3),
    }

    logger.info(json.dumps(log_payload))
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/echo")
async def echo(body: EchoRequest) -> EchoRequest:
    return body
