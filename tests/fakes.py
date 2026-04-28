from llm_lab.vector_store.types import IndexedChunk, ScoredChunk, VectorStoreClient


class FakeLlmClient:
    def embed_text(self, text: str, embedding_model: str | None = None) -> list[float]:
        return [0.1, 0.2, 0.3]

    def generate_response(self, prompt: str, model: str | None = None) -> str:
        raise NotImplementedError


class NoCallLlmClient:
    def embed_text(self, text: str, embedding_model: str | None = None) -> list[float]:
        return [1.0, 0.0]

    def generate_response(self, prompt: str, model: str | None = None) -> str:
        raise AssertionError(
            "generate_response should not be called when no chunks are returned."
        )


class FakeVectorStoreClient(VectorStoreClient):
    """Fake VectorStoreClient that returns a configurable list of ScoredChunks."""

    def __init__(self, scored_chunks: list[ScoredChunk] | None = None) -> None:
        self._scored_chunks = scored_chunks or []

    def get_embedding_model(self, dataset: str) -> str:
        return "fake-embedding-model"

    def store(
        self,
        indexed_chunks: list[IndexedChunk],
        dataset: str,
        embedding_model: str,
        docs_count: int,
    ) -> None:
        pass

    def query(self, dataset: str, query_embedding: list[float]) -> list[ScoredChunk]:
        return self._scored_chunks
