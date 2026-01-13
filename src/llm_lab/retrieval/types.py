from datetime import datetime

from pydantic import BaseModel


class Chunk(BaseModel):
    text: str
    doc_path: str


class IndexedChunk(Chunk):
    source: str
    embedding: list[float]
    chunk_id: int


class IndexFile(BaseModel):
    dataset: str
    embedding_model: str
    created_at: datetime
    index_id: str
    chunks: list[IndexedChunk]


class ManifestIndexFile(BaseModel):
    index_id: str  # e.g. "index-0001"
    path: str  # e.g. "index-0001.json"
    num_chunks: int  # number of chunks in that shard


class ManifestDocument(BaseModel):
    doc_id: str  # stable ID for the doc (e.g. filename or UUID)
    doc_path: str  # absolute/relative path on disk at index time
    hash: str  # content hash (e.g. sha256) at index time
    last_indexed_at: datetime


class ManifestFile(BaseModel):
    dataset: str  # dataset name passed to the CLI
    embedding_model: str  # embedding model used for this dataset
    created_at: datetime  # when this manifest was created
    total_docs: int
    total_chunks: int
    index_files: list[ManifestIndexFile]
    documents: list[ManifestDocument]
