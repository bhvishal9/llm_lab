from datetime import datetime

from pydantic import BaseModel, Field

from llm_lab.vector_store.types import IndexedChunk


class IndexFile(BaseModel):
    dataset: str = Field(description="The name of the dataset this index belongs to.")
    embedding_model: str = Field(
        description="The embedding model used to create the chunk embeddings."
    )
    created_at: datetime = Field(
        description="The timestamp when this index file was created."
    )
    index_id: str = Field(description="A unique identifier for this index file.")
    chunks: list[IndexedChunk] = Field(
        description="A list of indexed chunks contained in this file."
    )


class ManifestFile(BaseModel):
    dataset: str = Field(
        description="The name of the dataset to which this manifest belongs, as passed to the CLI."
    )
    embedding_model: str = Field(
        description="The embedding model used for the dataset documented in this manifest."
    )
    created_at: datetime = Field(
        description="The timestamp when this manifest file was created."
    )
    total_docs: int = Field(
        description="The total number of documents recorded in this manifest."
    )
    total_chunks: int = Field(
        description="The total number of chunks across all documents and index files in this manifest."
    )
