from datetime import datetime

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


class ManifestIndexFile(BaseModel):
    index_id: str = Field(
        description='Unique identifier for the index (e.g., "index-0001").'
    )
    path: str = Field(
        description='Relative path to the index file (e.g., "index-0001.json").'
    )
    num_chunks: int = Field(
        description="Number of chunks contained within this index file."
    )


class ManifestDocument(BaseModel):
    doc_id: str = Field(
        description="A stable, unique identifier for the document (e.g., filename or UUID)."
    )
    doc_path: str = Field(
        description="The absolute or relative path to the document on disk at the time of indexing."
    )
    hash: str = Field(
        description="The content hash of the document (e.g., SHA256) at the time of indexing, used for change detection."
    )
    last_indexed_at: datetime = Field(
        description="The timestamp when this document was last indexed."
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
    index_files: list[ManifestIndexFile] = Field(
        description="A list of index file entries, each detailing an index shard."
    )
    documents: list[ManifestDocument] = Field(
        description="A list of document entries, each detailing an indexed document."
    )


class ChunkingConfig(BaseModel):
    chunk_size: int = Field(
        description="The desired chunk size in characters for document processing.",
        gt=0,
    )
    chunk_separator: str = Field(
        description="The separator string used to delineate chunks.",
        min_length=1,
    )
