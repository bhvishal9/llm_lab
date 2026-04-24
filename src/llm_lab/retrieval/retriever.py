import time

from llm_lab.config.variables import (
    CANDIDATE_MULTIPLIER,
    MAX_CANDIDATES,
    SIMILARITY_SCORE_THRESHOLD,
)
from llm_lab.llm.types import LlmClient
from llm_lab.observability.context import embed_ms_context_var
from llm_lab.vector_store.types import VectorStoreClient


class Retriever:
    """Class for scoring chunks based on cosine similarity."""

    def __init__(
        self,
        llm_client: LlmClient,
        vector_store_client: VectorStoreClient,
    ) -> None:
        self.llm_client = llm_client
        self.vector_store_client = vector_store_client

    def search(self, dataset: str, query: str, top_k: int):
        candidate_k = min(top_k * CANDIDATE_MULTIPLIER, MAX_CANDIDATES)
        embedding_model = self.vector_store_client.get_embedding_model(dataset)
        start_time = time.perf_counter()
        query_embedding = self.llm_client.embed_text(query, embedding_model)
        embedding_time = round((time.perf_counter() - start_time) * 1000, 3)
        embed_ms_context_var.set(embedding_time)
        scored_chunks = self.vector_store_client.query(dataset, query_embedding)
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        selected_chunks = [
            chunk
            for score, chunk in scored_chunks[:candidate_k]
            if score >= SIMILARITY_SCORE_THRESHOLD
        ]
        top_chunks = selected_chunks[:top_k]
        return top_chunks
