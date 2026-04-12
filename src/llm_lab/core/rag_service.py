import time
from typing import Protocol

from pydantic import BaseModel

from llm_lab.config.paths import DEFAULT_DESTINATION_DIR
from llm_lab.config.settings import VectorStoreType, get_settings
from llm_lab.llm.types import LlmClient
from llm_lab.observability.context import generate_ms_context_var
from llm_lab.retrieval.types import IndexedChunk
from llm_lab.vector_store.file_store import FileStoreClient
from llm_lab.vector_store.types import VectorStoreClient


class HasVectorStore(Protocol):
    """Minimal settings interface needed to build a vector store client."""

    vector_store: VectorStoreType


class QueryResult(BaseModel):
    answer: str
    chunks: list[IndexedChunk]
    candidate_k: int
    num_chunks_returned: int


def create_vector_store_client(
    settings: HasVectorStore,
    llm_client: LlmClient,
) -> VectorStoreClient:
    """
    Create a vector store client based on the provided settings.
    """
    if settings.vector_store == VectorStoreType.FILE:
        return FileStoreClient(client=llm_client, dest_dir=DEFAULT_DESTINATION_DIR)
    raise ValueError(f"Unsupported vector store type: {settings.vector_store}")


def build_prompt(question: str, chunks: list[IndexedChunk]) -> str:
    """Build a prompt for the LLM based on the question and chunks."""
    context_parts = []
    for chunk in chunks:
        context_parts.append(
            f"Source: {chunk.source} (chunk {chunk.chunk_id})\n{chunk.text}"
        )
    context = "\n\n".join(context_parts)

    prompt = (
        "You are a helpful assistant. Use ONLY the context below to answer the question.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n"
        "Answer:"
    )
    return prompt


class RagService:
    def __init__(
        self,
        client: LlmClient,
        dataset: str,
    ) -> None:
        self.client = client
        self.dataset = dataset
        self.vector_store_client: VectorStoreClient
        self.vector_store_client = create_vector_store_client(
            settings=get_settings(),
            llm_client=client,
        )

    def answer_question(
        self,
        query: str,
        top_k: int,
    ) -> QueryResult:
        """Answer a question using a simple RAG pipeline."""

        top_chunks, candidate_k = self.vector_store_client.query(
            self.dataset, query, top_k
        )
        if not top_chunks:
            return QueryResult(
                answer="No relevant information found to answer the question.",
                chunks=top_chunks,
                candidate_k=candidate_k,
                num_chunks_returned=len(top_chunks),
            )
        prompt = build_prompt(query, top_chunks)
        start_time = time.perf_counter()
        response = self.client.generate_response(prompt)
        generate_ms = round(((time.perf_counter() - start_time) * 1000), 3)
        generate_ms_context_var.set(generate_ms)
        return QueryResult(
            answer=response,
            chunks=top_chunks,
            candidate_k=candidate_k,
            num_chunks_returned=len(top_chunks),
        )
