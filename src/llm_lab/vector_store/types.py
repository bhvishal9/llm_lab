from pathlib import Path
from typing import Protocol

from llm_lab.retrieval.types import ChunkingConfig, IndexedChunk


class VectorStoreClient(Protocol):
    """Protocol describing the interface for Vector Store clients."""

    def index_dataset(
        self,
        source_dir: Path,
        embedding_model: str,
        dataset: str,
        max_chunks_per_index: int,
        chunking_config: ChunkingConfig,
    ) -> tuple[int, int]:
        """Index a dataset located in source_dir and store the index in dest_dir."""
        ...

    def query(self, dataset: str, query_text: str, top_k: int) -> list[IndexedChunk]:
        """Query the vector store and return a list of the top_k most relevant IndexedChunks."""
        ...
