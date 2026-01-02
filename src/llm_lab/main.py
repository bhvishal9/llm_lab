import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import iterate_in_threadpool

from llm_lab.config.settings import Settings, get_settings
from llm_lab.llm.errors import (
    LlmAuthenticationError,
    LlmError,
    LlmInvalidRequestError,
    LlmRateLimitError,
    LlmUnavailableError,
)
from llm_lab.llm.gemini_client import GeminiClient
from llm_lab.llm.types import LlmClient
from llm_lab.rag_core import build_prompt
from llm_lab.retrieval.retriever import Retriever
from llm_lab.retrieval.types import IndexedChunk

DEFAULT_INDEXED_CHUNKS_FILE = Path("assets/indexed_chunks.json")


class CustomException(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class EchoRequest(BaseModel):
    name: str


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str
    top_k: int = Field(default=3)


class SourceChunk(BaseModel):
    source: str
    chunk_id: int


class QueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)
    answer: str
    sources: List[SourceChunk]


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

logger = logging.getLogger(__name__)


app = FastAPI(title="llm_lab", version="0.0.1")


def validate_query_request(request: QueryRequest) -> None:
    if not request.query:
        raise CustomException(
            status_code=400, message="Question must be a non-empty string"
        )
    if request.top_k < 1 or request.top_k > 10:
        raise CustomException(status_code=400, message="top_k must be between 1 and 10")


def build_response(
    top_chunks: list[IndexedChunk],
    response: str,
) -> QueryResponse:
    return QueryResponse(
        answer=response,
        sources=[
            SourceChunk(source=chunk.source, chunk_id=chunk.chunk_id)
            for chunk in top_chunks
        ],
    )


def get_llm_client(settings: Settings = Depends(get_settings)) -> LlmClient:
    return GeminiClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        embedding_model=settings.llm_embedding_model,
    )


@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message},
    )


@app.exception_handler(LlmRateLimitError)
async def llm_rate_limit_exception_handler(request: Request, exc: LlmRateLimitError):
    return JSONResponse(
        status_code=429,
        content={"error": str(exc)},
    )


@app.exception_handler(LlmAuthenticationError)
async def llm_authentication_exception_handler(
    request: Request, exc: LlmAuthenticationError
):
    return JSONResponse(
        status_code=502,
        content={"error": str(exc)},
    )


@app.exception_handler(LlmInvalidRequestError)
async def llm_invalid_request_exception_handler(
    request: Request, exc: LlmInvalidRequestError
):
    return JSONResponse(
        status_code=502,
        content={"error": str(exc)},
    )


@app.exception_handler(LlmUnavailableError)
async def llm_unavailable_exception_handler(request: Request, exc: LlmUnavailableError):
    return JSONResponse(
        status_code=502,
        content={"error": str(exc)},
    )


@app.exception_handler(LlmError)
async def llm_generic_error_exception_handler(request: Request, exc: LlmError):
    return JSONResponse(
        status_code=502,
        content={"error": str(exc)},
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/echo")
async def echo(body: EchoRequest) -> EchoRequest:
    return body


@app.post("/query")
async def query(
    body: QueryRequest,
    client: LlmClient = Depends(get_llm_client),
) -> QueryResponse:
    validate_query_request(body)
    try:
        scoring = Retriever(
            client, body.query, DEFAULT_INDEXED_CHUNKS_FILE, top_k=body.top_k
        )
        embedding_model_name, indexed_chunks = scoring.load_indexed_chunks()
        top_chunks = scoring.score_chunks(embedding_model_name, indexed_chunks)
        prompt = build_prompt(body.query, top_chunks)
        response = client.generate_response(prompt)
    except (ValueError, FileNotFoundError) as err:
        raise CustomException(status_code=500, message=str(err)) from err
    return build_response(top_chunks, response)
