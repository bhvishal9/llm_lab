import json
import math
from pathlib import Path
from typing import Sequence, Tuple

from llm_lab.llm.types import LlmClient
from llm_lab.retrieval.types import IndexedChunk


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Calculate cosine similarity between two embedding vectors."""
    if len(a) != len(b):
        raise ValueError("Embedding vectors must have the same length")

    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0.0 or norm_b == 0.0:
        # should not happen with real embeddings, but guard anyway
        return 0.0

    return dot_product / (norm_a * norm_b)


class Retriever:
    """Class for scoring chunks based on cosine similarity."""

    def __init__(
        self,
        client: LlmClient,
        query_text: str,
        indexed_chunks_path: Path,
        top_k: int,
    ) -> None:
        self.client = client
        self.query_text = query_text
        self.indexed_chunks_path = indexed_chunks_path
        self.top_k = top_k

    def load_indexed_chunks(self) -> Tuple[str, list[IndexedChunk]]:
        """Load indexed chunks from a file."""
        try:
            indexed_chunks_file = self.indexed_chunks_path
            file_content = indexed_chunks_file.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            raise FileNotFoundError(
                f"File {indexed_chunks_file} not found, make sure to run the index command first"
            )
        if not file_content:
            raise ValueError(
                f"File {indexed_chunks_file} is empty, make sure to run the index command first"
            )

        try:
            data = json.loads(file_content)
        except json.decoder.JSONDecodeError:
            raise ValueError(f"File {indexed_chunks_file} is not a valid JSON file")
        embedding_model_name = data.get("model_name")
        if not isinstance(embedding_model_name, str):
            raise ValueError(f"Model name not found in {indexed_chunks_file}")

        chunks_data = data.get("chunks", [])
        if not isinstance(chunks_data, list):
            raise ValueError(f"Invalid chunks data in {indexed_chunks_file}")
        indexed_chunks = [IndexedChunk(**chunk) for chunk in chunks_data]

        return embedding_model_name, indexed_chunks

    def score_chunks(
        self, embedding_model_name: str, indexed_chunks: list[IndexedChunk]
    ) -> list[IndexedChunk]:
        """Score chunks based on cosine similarity with the query embedding."""
        query_embedding = self.client.embed_text(self.query_text, embedding_model_name)
        scored_chunks = []
        for chunk in indexed_chunks:
            similarity = _cosine_similarity(query_embedding, chunk.embedding)
            scored_chunks.append((similarity, chunk))

        # Sort by similarity in descending order and take top_k
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_chunks = [chunk for _, chunk in scored_chunks[: self.top_k]]
        return top_chunks
