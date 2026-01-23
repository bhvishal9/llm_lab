from pathlib import Path

from llm_lab.retrieval.types import ChunkingConfig, IndexedChunk
from llm_lab.vector_store.types import VectorStoreClient


class FakeLlmClient:
    def embed_text(self, text: str, embedding_model: str | None = None) -> list[float]:
        return [0.1, 0.2, 0.3]

    def generate_response(self, prompt: str, model: str | None = None) -> str:
        raise NotImplementedError


class NoCallLlmClient:
    def embed_text(self, text: str, embedding_model: str | None = None) -> list[float]:
        # Not really used in this test because we stub Retriever,
        # but implemented for interface completeness.
        return [1.0, 0.0]

    def generate_response(self, prompt: str, model: str | None = None) -> str:
        raise AssertionError(
            "generate_response should not be called when no chunks are returned."
        )


class FakeVectorStoreClient(VectorStoreClient):
    """Fake implementation of VectorStoreClient that returns no chunks."""

    def index_dataset(
        self,
        source_dir: Path,
        embedding_model: str,
        dataset: str,
        max_chunks_per_index: int,
        chunking_config: ChunkingConfig,
    ) -> tuple[int, int]:
        return 0, 0

    def query(self, dataset: str, query_text: str, top_k: int) -> list[IndexedChunk]:
        return []
