import sys
import typer
import json

from datetime import datetime
from pathlib import Path
from google import genai
from google.genai.errors import ClientError
from llm_lab.rag_core import (
    Chunk,
    IndexedChunk,
    load_indexed_chunks,
    embed_text,
    score_chunks,
    build_prompt,
    generate_response,
    get_required_env,
    get_optional_env,
)

DEFAULT_DOCS_DIR = Path("assets/docs")
DEFAULT_INDEXED_CHUNKS_FILE = Path("assets/indexed_chunks.json")
DEFAULT_EMBEDDING_MODEL_NAME = "gemini-embedding-001"
DEFAULT_MODEL_NAME = "gemini-2.5-flash"

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


@app.command()
def index():
    typer.echo(f"Indexing directory: {DEFAULT_DOCS_DIR}")
    api_key = get_required_env("LLM_API_KEY")
    embedding_model_name = get_optional_env(
        "LLM_EMBEDDING_MODEL_NAME", DEFAULT_EMBEDDING_MODEL_NAME
    )
    client = genai.Client(api_key=api_key)
    docs = load_docs(DEFAULT_DOCS_DIR)
    chunks, indexed_chunks = [], []

    if not docs:
        raise ValueError(f"No markdown files found in {DEFAULT_DOCS_DIR}")
    for doc in docs:
        file_content = read_file(doc)
        file_chunks = create_chunks(file_content, doc)
        chunks.extend(file_chunks)
    for idx, chunk in enumerate(chunks):
        embedding = embed_text(client, chunk.text, embedding_model_name)
        indexed_chunks.append(
            IndexedChunk(
                text=chunk.text,
                source=chunk.source,
                embedding=embedding,
                chunk_id=idx,
            )
        )
    save_indexed_chunks(
        indexed_chunks, DEFAULT_INDEXED_CHUNKS_FILE, embedding_model_name
    )
    typer.echo(
        f"Indexed {len(docs)} documents into {len(indexed_chunks)} chunks, saved to {DEFAULT_INDEXED_CHUNKS_FILE}"
    )


@app.command()
def query():
    typer.echo("Loading the index...")
    api_key = get_required_env("LLM_API_KEY")
    model_name = get_optional_env("LLM_MODEL_NAME", DEFAULT_MODEL_NAME)
    embedding_model_name, indexed_chunks = load_indexed_chunks(
        DEFAULT_INDEXED_CHUNKS_FILE
    )
    typer.echo("Index loaded successfully")
    client = genai.Client(api_key=api_key)
    query = take_user_input()
    query_embedding = embed_text(client, query, embedding_model_name)
    top_chunks = score_chunks(query_embedding, indexed_chunks, top_k=3)
    prompt = build_prompt(query, top_chunks)
    response = generate_response(client, model_name, prompt)
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
    except ClientError as err:
        typer.echo(f"LLM Client Error: {err}", err=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
