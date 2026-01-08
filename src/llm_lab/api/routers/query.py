from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from llm_lab.api.dependencies import get_llm_client
from llm_lab.api.exceptions import CustomException
from llm_lab.config.paths import DEFAULT_INDEXED_CHUNKS_FILE
from llm_lab.llm.types import LlmClient
from llm_lab.rag_core import build_prompt
from llm_lab.retrieval.retriever import Retriever
from llm_lab.retrieval.types import IndexedChunk


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


router = APIRouter(prefix="", tags=["Query"])


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


@router.post("/query")
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
