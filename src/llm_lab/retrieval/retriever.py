import json
import math
from pathlib import Path
from typing import Sequence, Tuple

from llm_lab.llm.types import LlmClient
from llm_lab.retrieval.types import IndexedChunk, IndexFile, ManifestFile


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
        indexed_chunks_dir: Path,
        top_k: int,
    ) -> None:
        self.client = client
        self.query_text = query_text
        self.indexed_chunks_dir = indexed_chunks_dir
        self.top_k = top_k

    def load_indexed_chunks(self) -> Tuple[str, list[IndexedChunk]]:
        """Load indexed chunks from the dataset directory."""
        manifest_path = self.indexed_chunks_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"Manifest file not found at {manifest_path}, make sure to index the dataset first."
            )
        manifest_data = manifest_path.read_text(encoding="utf-8")
        if not manifest_data:
            raise ValueError(
                f"Manifest file at {manifest_path} is empty, make sure to index the dataset first."
            )
        try:
            manifest = ManifestFile.model_validate_json(manifest_data)
        except json.JSONDecodeError:
            raise ValueError(f"Manifest file at {manifest_path} is malformed.")

        embedding_model = manifest.embedding_model
        indexed_chunks = []
        for index_file in manifest.index_files:
            index_file_path = self.indexed_chunks_dir / index_file.path
            if not index_file_path.exists():
                raise FileNotFoundError(
                    f"Index file {index_file_path} not found, make sure to index the dataset first."
                )
            try:
                index_file_data = index_file_path.read_text(encoding="utf-8")
                index_file_validated_data = IndexFile.model_validate_json(
                    index_file_data
                )
            except json.JSONDecodeError:
                raise ValueError(f"Index file at {index_file_path} is malformed.")
            index_file_chunks = index_file_validated_data.chunks
            indexed_chunks.extend(index_file_chunks)
        return embedding_model, indexed_chunks

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
