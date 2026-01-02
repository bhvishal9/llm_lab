from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str


@dataclass
class IndexedChunk(Chunk):
    embedding: list[float]
    chunk_id: int
