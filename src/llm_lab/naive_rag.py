import json
import sys
from datetime import datetime
from pathlib import Path

import typer

from llm_lab.config.settings import Settings, get_settings
from llm_lab.llm.errors import (
    LlmAuthenticationError,
    LlmError,
    LlmInvalidRequestError,
    LlmRateLimitError,
    LlmUnavailableError,
)
from llm_lab.llm.gemini_client import GeminiClient
from llm_lab.llm.types import LlmClient
from llm_lab.rag_core import (
    Chunk,
    IndexedChunk,
    build_prompt,
    load_indexed_chunks,
    score_chunks,
)

DEFAULT_DOCS_DIR = Path("assets/docs")
DEFAULT_INDEXED_CHUNKS_FILE = Path("assets/indexed_chunks.json")

app = typer.Typer()


def load_docs(dir_path: Path) -> list[Path]:
    """Load all Markdown files from a directory."""
    if not dir_path.exists():
        raise ValueError(f"Directory {dir_path} does not exist")
    return list(dir_path.glob("**/*.md"))


def read_file(file_path: Path) -> str:
    """Read a file and return its content."""
    try:
        file_content = file_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise ValueError(f"File {file_path} not found")
    if not file_content:
        raise ValueError(f"File {file_path} is empty")
    return file_content


def create_chunks(file_content: str, file: Path) -> list[Chunk]:
    """Create chunks from a file content."""
    chunks = []
    for chunk in file_content.split("\n\n"):
        if not chunk.strip():
            continue
        chunks.append(Chunk(chunk.strip(), str(file)))
    return chunks


def save_indexed_chunks(
    indexed_chunks: list[IndexedChunk], file_path: Path, embedding_model_name: str
) -> None:
    """Save indexed chunks to a file."""
    file_path.write_text(
        json.dumps(
            {
                "model_name": embedding_model_name,
                "created_at": datetime.now().isoformat(),
                "chunks": [chunk.__dict__ for chunk in indexed_chunks],
            }
        )
    )


def take_user_input() -> str:
    try:
        user_input = input("Enter the question:\n").strip()
    except (EOFError, KeyboardInterrupt):
        raise ValueError("User interrupted the input, exiting...")
    if not user_input:
        raise ValueError("User input is empty, exiting...")
    return user_input


def create_llm_client(settings: Settings | None = None) -> LlmClient:
    """Return a concrete LLM client based on settings."""
    if settings is None:
        settings = get_settings()

    return GeminiClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        embedding_model=settings.llm_embedding_model,
    )


@app.command()
def index():
    typer.echo(f"Indexing directory: {DEFAULT_DOCS_DIR}")
    settings = get_settings()
    client = create_llm_client(settings)
    docs = load_docs(DEFAULT_DOCS_DIR)
    chunks, indexed_chunks = [], []

    if not docs:
        raise ValueError(f"No markdown files found in {DEFAULT_DOCS_DIR}")
    for doc in docs:
        file_content = read_file(doc)
        file_chunks = create_chunks(file_content, doc)
        chunks.extend(file_chunks)
    for idx, chunk in enumerate(chunks):
        embedding = client.embed_text(chunk.text)
        indexed_chunks.append(
            IndexedChunk(
                text=chunk.text,
                source=chunk.source,
                embedding=embedding,
                chunk_id=idx,
            )
        )
    save_indexed_chunks(
        indexed_chunks, DEFAULT_INDEXED_CHUNKS_FILE, settings.llm_embedding_model
    )
    typer.echo(
        f"Indexed {len(docs)} documents into {len(indexed_chunks)} chunks, saved to {DEFAULT_INDEXED_CHUNKS_FILE}"
    )


@app.command()
def query():
    typer.echo("Loading the index...")
    embedding_model_name, indexed_chunks = load_indexed_chunks(
        DEFAULT_INDEXED_CHUNKS_FILE
    )
    typer.echo("Index loaded successfully")
    client = create_llm_client()
    query = take_user_input()
    query_embedding = client.embed_text(query, embedding_model_name)
    top_chunks = score_chunks(query_embedding, indexed_chunks, top_k=3)
    prompt = build_prompt(query, top_chunks)
    response = client.generate_response(prompt)
    typer.echo("\nSources used:")
    for chunk in top_chunks:
        typer.echo(f"- {chunk.source} (chunk {chunk.chunk_id})")
    typer.echo(f"\n\nResponse: {response}")


def main() -> int:
    try:
        app()
    except (ValueError, OSError) as err:
        typer.echo(f"Error: {err}", err=True)
        return 1
    except LlmRateLimitError as err:
        typer.echo(f"LLM Rate Limited Error: {err}", err=True)
        return 2
    except LlmAuthenticationError as err:
        typer.echo(f"LLM Authentication Error: {err}", err=True)
        return 3
    except LlmInvalidRequestError as err:
        typer.echo(f"LLM Invalid Request Error: {err}", err=True)
        return 4
    except LlmUnavailableError as err:
        typer.echo(f"LLM Unavailable Error: {err}", err=True)
        return 5
    except LlmError as err:
        typer.echo(f"LLM Error: {err}", err=True)
        return 6
    return 0


if __name__ == "__main__":
    sys.exit(main())
