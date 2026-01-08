from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from llm_lab.api.dependencies import get_rag_service
from llm_lab.api.exceptions import CustomException
from llm_lab.core.rag_service import RagService
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
    rag: RagService = Depends(get_rag_service),
) -> QueryResponse:
    validate_query_request(body)
    try:
        response, top_chunks = rag.answer_question(
            query=body.query,
            top_k=body.top_k,
        )
    except (ValueError, FileNotFoundError) as err:
        raise CustomException(status_code=500, message=str(err)) from err
    return build_response(top_chunks, response)
