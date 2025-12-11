import json
import math
import os

from typing import Sequence, Tuple
from pathlib import Path
from dataclasses import dataclass

from google import genai
from google.genai import types


@dataclass
class Chunk:
    text: str
    source: str


@dataclass
class IndexedChunk(Chunk):
    embedding: list[float]
    chunk_id: int


def get_required_env(name: str) -> str:
    """Read, strip, and validate a required env var."""
    raw = os.getenv(name)
    if raw is None:
        raise ValueError(f"Environment variable {name} not found")
    value = raw.strip()
    if not value:
        raise ValueError(f"Environment variable {name} is empty")
    return value


def get_optional_env(name: str, default: str) -> str:
    """Read, strip, and fall back to default if empty/whitespace."""
    raw = os.getenv(name, default)
    value = raw.strip()
    if not value:
        return default
    return value


def embed_text(
    client: genai.Client, text: str, embedding_model_name: str
) -> list[float]:
    """Embed text using a model."""
    embedding = client.models.embed_content(
        model=embedding_model_name,
        contents=text,
        config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
    )
    return embedding.embeddings[0].values


def load_indexed_chunks(file_path: Path) -> Tuple[str, list[IndexedChunk]]:
    """Load indexed chunks from a file."""
    try:
        file_content = file_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as err:
        raise FileNotFoundError(
            f"File {file_path} not found, make sure to run the index command first"
        ) from err

    if not file_content:
        raise ValueError(
            f"File {file_path} is empty, make sure to run the index command first"
        )

    try:
        data = json.loads(file_content)
    except json.JSONDecodeError as err:
        raise ValueError(f"File {file_path} is not a valid JSON file") from err

    # Optional: validate structure
    chunks_data = data.get("chunks")
    if not isinstance(chunks_data, list):
        raise ValueError(f"Invalid index format in {file_path}: 'chunks' missing")
    embedding_model_name = data.get("model_name")
    if not isinstance(embedding_model_name, str):
        raise ValueError(f"Invalid index format in {file_path}: 'model_name' missing")

    return embedding_model_name, [IndexedChunk(**chunk) for chunk in chunks_data]


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
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


def score_chunks(
    query_embedding: list[float], indexed_chunks: list[IndexedChunk], top_k: int = 3
) -> list[IndexedChunk]:
    """Score chunks based on cosine similarity with the query embedding."""
    scored = []
    for chunk in indexed_chunks:
        score = cosine_similarity(query_embedding, chunk.embedding)
        scored.append((score, chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top_chunks = [chunk for score, chunk in scored[:top_k]]
    return top_chunks


def build_prompt(question: str, chunks: list[IndexedChunk]) -> str:
    """Build a prompt for the LLM based on the question and chunks."""
    context_parts = []
    for chunk in chunks:
        context_parts.append(
            f"Source: {chunk.source} (chunk {chunk.chunk_id})\n{chunk.text}"
        )
    context = "\n\n".join(context_parts)

    prompt = (
        "You are a helpful assistant. Use ONLY the context below to answer the question.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n"
        "Answer:"
    )
    return prompt


def generate_response(client: genai.Client, model_name: str, prompt: str) -> str:
    """Generate a response from the LLM based on the prompt."""
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
    )
    return response.text
