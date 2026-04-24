from typing import Protocol

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    text: str = Field(description="The textual content of the chunk.")
    doc_path: str = Field(
        description="The path to the document from which the chunk was extracted."
    )


class IndexedChunk(Chunk):
    source: str = Field(description="The source of the chunk (e.g., 'document').")
    embedding: list[float] = Field(description="The embedding vector of the chunk.")
    chunk_id: int = Field(
        description="A unique identifier for the chunk within its index."
    )


class ScoredChunk(IndexedChunk):
    score: float = Field(description="The score of the chunk.")


class VectorStoreClient(Protocol):
    """Protocol describing the interface for Vector Store clients."""

    def get_embedding_model(self, dataset: str) -> str:
        """Get the embedding model for the given dataset."""

    def store(
        self,
        indexed_chunks: list[IndexedChunk],
        dataset: str,
        embedding_model: str,
        docs_count: int,
    ) -> None:
        """Store the indexed chunks into a vector store."""
        ...

    def query(self, dataset: str, query_embedding: list[float]) -> list[ScoredChunk]:
        """Query the vector store and return a list of the top_k most relevant IndexedChunks."""
        ...
