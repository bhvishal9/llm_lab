import sys
from pathlib import Path
from typing import Annotated

import typer

from llm_lab.config.paths import (
    DEFAULT_DESTINATION_DIR,
    DEFAULT_DOCS_DIR,
)
from llm_lab.config.settings import Settings, get_settings
from llm_lab.core.rag_service import RagService
from llm_lab.llm.errors import (
    LlmAuthenticationError,
    LlmError,
    LlmInvalidRequestError,
    LlmRateLimitError,
    LlmUnavailableError,
)
from llm_lab.llm.gemini_client import GeminiClient
from llm_lab.llm.types import LlmClient
from llm_lab.retrieval.types import ChunkingConfig
from llm_lab.vector_store.file_store import FileStoreClient

app = typer.Typer()

DEFAULT_MAX_CHUNKS_PER_FILE = 1000


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
def index(
    dataset: Annotated[str, typer.Option(help="Dataset to index")],
    source_dir: Annotated[
        Path, typer.Option(help="Source directory")
    ] = DEFAULT_DOCS_DIR,
    max_chunks_per_index: Annotated[
        int, typer.Option(help="Maximum chunks per index file")
    ] = DEFAULT_MAX_CHUNKS_PER_FILE,
    chunk_size: Annotated[int, typer.Option(help="Chunk size in characters")] = 10000,
    chunk_separator: Annotated[
        str, typer.Option(help="Chunk separator string")
    ] = "\n\n",
):
    dest_dir = DEFAULT_DESTINATION_DIR
    typer.echo(f"Indexing dataset '{dataset}' from {source_dir} into {dest_dir}")
    settings = get_settings()
    client = create_llm_client(settings)
    chunking_config = ChunkingConfig(
        chunk_size=chunk_size,
        chunk_separator=chunk_separator,
    )
    vector_store_client = FileStoreClient(client, dest_dir)
    docs_count, chunks_count = vector_store_client.index_dataset(
        source_dir=source_dir,
        embedding_model=settings.llm_embedding_model,
        dataset=dataset,
        max_chunks_per_index=max_chunks_per_index,
        chunking_config=chunking_config,
    )
    typer.echo(
        f"Indexed {docs_count} documents into {chunks_count} chunks.\n"
        f"- Index files: {dest_dir / 'indexes' / dataset}\n"
        f"- Manifest:    {dest_dir / 'indexes' / dataset / 'manifest.json'}"
    )


@app.command()
def query(
    dataset: Annotated[str, typer.Option(help="Dataset to query")],
):
    typer.echo("Loading the index...")
    client = create_llm_client()
    query_text = take_user_input()
    rag_service = RagService(client, dataset)
    response, top_chunks = rag_service.answer_question(
        query=query_text,
        top_k=3,
    )
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
