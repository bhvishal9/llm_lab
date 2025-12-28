import json
import time
import logging

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from pydantic import BaseModel, ConfigDict, Field
from google import genai
from google.genai.errors import ClientError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import iterate_in_threadpool
from llm_lab.rag_core import (
    IndexedChunk,
    load_indexed_chunks,
    embed_text,
    score_chunks,
    build_prompt,
    generate_response,
)
from llm_lab.config.settings import get_settings

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


def load_indexed_data(file_path: Path) -> Tuple[str, list[IndexedChunk]]:
    try:
        return load_indexed_chunks(file_path)
    except (ValueError, FileNotFoundError) as err:
        raise CustomException(status_code=500, message=str(err)) from err


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


@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message},
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
async def query(body: QueryRequest) -> QueryResponse:
    validate_query_request(body)
    try:
        settings = get_settings()
        embedding_model_name, indexed_chunks = load_indexed_data(
            DEFAULT_INDEXED_CHUNKS_FILE
        )
        client = genai.Client(api_key=settings.llm_api_key)
        query_embedding = embed_text(client, body.query, embedding_model_name)
        top_chunks = score_chunks(query_embedding, indexed_chunks, top_k=body.top_k)
        prompt = build_prompt(body.query, top_chunks)
        response = generate_response(client, settings.llm_model, prompt)
    except ClientError as err:
        raise CustomException(status_code=502, message=str(err)) from err
    except (ValueError, FileNotFoundError) as err:
        raise CustomException(status_code=500, message=str(err)) from err
    return build_response(top_chunks, response)
