import json
from datetime import datetime
from pathlib import Path

from llm_lab.llm.types import LlmClient
from llm_lab.retrieval.types import Chunk, IndexedChunk


def _create_chunks(file_content: str, file: Path) -> list[Chunk]:
    """Create chunks from a file content."""
    chunks = []
    for chunk in file_content.split("\n\n"):
        if not chunk.strip():
            continue
        chunks.append(Chunk(chunk.strip(), str(file)))
    return chunks


def _read_file(file_path: Path) -> str:
    """Read a file and return its content."""
    try:
        file_content = file_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise ValueError(f"File {file_path} not found")
    if not file_content:
        raise ValueError(f"File {file_path} is empty")
    return file_content


class Indexer:
    """Indexer to create embeddings for documents in a directory."""

    def __init__(self, source_dir: Path, dest_file: Path, embedding_model: str) -> None:
        self.dest_file = dest_file
        self.source_dir = source_dir
        self.embedding_model = embedding_model

    def load_docs(self) -> list[Path]:
        """Load all Markdown files from the source directory."""
        if not self.source_dir.exists():
            raise ValueError(f"Directory {self.source_dir} does not exist")
        files = list(self.source_dir.glob("**/*.md"))
        if not files:
            raise ValueError(f"No Markdown files found in directory {self.source_dir}")
        return files

    def save_indexed_chunks(
        self,
        indexed_chunks: list[IndexedChunk],
    ) -> None:
        """Save indexed chunks to a file."""
        self.dest_file.parent.mkdir(parents=True, exist_ok=True)
        self.dest_file.write_text(
            json.dumps(
                {
                    "model_name": self.embedding_model,
                    "created_at": datetime.now().isoformat(),
                    "chunks": [chunk.__dict__ for chunk in indexed_chunks],
                }
            )
        )

    def build_index(
        self, llm_client: LlmClient, docs: list[Path]
    ) -> list[IndexedChunk]:
        """Build the index from source documents."""
        all_chunks: list[Chunk] = []
        indexed_chunks: list[IndexedChunk] = []
        for file in docs:
            file_content = _read_file(file)
            file_chunks = _create_chunks(file_content, file)
            all_chunks.extend(file_chunks)
        for idx, chunk in enumerate(all_chunks):
            embedding = llm_client.embed_text(chunk.text)
            indexed_chunks.append(
                IndexedChunk(
                    text=chunk.text,
                    source=chunk.source,
                    embedding=embedding,
                    chunk_id=idx,
                )
            )
        return indexed_chunks
