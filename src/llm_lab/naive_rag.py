import sys
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
from llm_lab.rag_core import build_prompt
from llm_lab.retrieval.indexing import Indexer
from llm_lab.retrieval.retriever import Retriever

DEFAULT_DOCS_DIR = Path("assets/docs")
DEFAULT_INDEXED_CHUNKS_FILE = Path("assets/indexed_chunks.json")

app = typer.Typer()


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
    indexer = Indexer(
        source_dir=DEFAULT_DOCS_DIR,
        dest_file=DEFAULT_INDEXED_CHUNKS_FILE,
        embedding_model=settings.llm_embedding_model,
    )
    docs = indexer.load_docs()
    indexed_chunks = indexer.build_index(client, docs)
    indexer.save_indexed_chunks(indexed_chunks)
    typer.echo(
        f"Indexed {len(docs)} documents into {len(indexed_chunks)} chunks, saved to {DEFAULT_INDEXED_CHUNKS_FILE}"
    )


@app.command()
def query():
    typer.echo("Loading the index...")
    client = create_llm_client()
    query_text = take_user_input()
    scoring = Retriever(client, query_text, DEFAULT_INDEXED_CHUNKS_FILE, top_k=3)
    embedding_model_name, indexed_chunks = scoring.load_indexed_chunks()
    top_chunks = scoring.score_chunks(embedding_model_name, indexed_chunks)
    prompt = build_prompt(query_text, top_chunks)
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
