from pathlib import Path

from llm_lab.config.paths import BASE_DIR
from llm_lab.llm.types import LlmClient
from llm_lab.retrieval.types import (
    ChunkingConfig,
)
from llm_lab.vector_store.types import Chunk, IndexedChunk


def _create_chunks(
    file_content: str, file_name: Path, chunking_config: ChunkingConfig
) -> list[Chunk]:
    """Create chunks from a file content."""
    chunks = []
    separator = chunking_config.chunk_separator
    chunk_size = chunking_config.chunk_size
    content_length = len(file_content)
    start = 0
    while start < content_length:
        end = min(start + chunk_size, content_length)
        if end < content_length:
            sep_index = file_content.rfind(separator, start, end)
            if sep_index != -1 and sep_index > start:
                end = sep_index + len(separator)

        chunk_text = file_content[start:end].strip()
        if chunk_text:
            chunk = Chunk(
                text=chunk_text,
                doc_path=str(file_name),
            )
            chunks.append(chunk)
        start = end

    return chunks


def _read_file(file_path: Path) -> str:
    """Read a file and return its content."""
    try:
        file_content = file_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as err:
        raise ValueError(f"File {file_path} not found: {err}") from err
    if not file_content:
        raise ValueError(f"File {file_path} is empty")
    return file_content


class Indexer:
    """Indexer to create embeddings for documents in a directory."""

    def __init__(
        self,
        source_dir: Path,
        embedding_model: str,
        dataset: str,
        chunking_config: ChunkingConfig,
    ) -> None:
        self.source_dir = source_dir
        self.embedding_model = embedding_model
        self.dataset = dataset
        self.chunking_config = chunking_config

    def load_docs(self) -> list[Path]:
        """Load all Markdown files from the source directory."""
        if not self.source_dir.exists():
            raise ValueError(f"Directory {self.source_dir} does not exist")
        files = list(self.source_dir.glob("**/*.md"))
        if not files:
            raise ValueError(f"No Markdown files found in directory {self.source_dir}")
        return files

    def build_index(
        self, llm_client: LlmClient, docs: list[Path]
    ) -> list[IndexedChunk]:
        """Build index by creating embeddings for document chunks."""
        indexed_chunks = []
        for doc in docs:
            file_content = _read_file(doc)
            doc_path = doc.relative_to(BASE_DIR)
            chunks = _create_chunks(file_content, doc_path, self.chunking_config)
            for chunk_id, chunk in enumerate(chunks):
                embedding = llm_client.embed_text(chunk.text, self.embedding_model)
                source = f"{doc_path}#chunk-{chunk_id}"
                indexed_chunk = IndexedChunk(
                    text=chunk.text,
                    doc_path=chunk.doc_path,
                    source=source,
                    embedding=embedding,
                    chunk_id=chunk_id,
                )
                indexed_chunks.append(indexed_chunk)
        return indexed_chunks

    def run(self, llm_client: LlmClient) -> tuple[list[IndexedChunk], int]:
        """Run the indexing process."""
        docs = self.load_docs()
        indexed_chunks = self.build_index(llm_client, docs)
        return indexed_chunks, len(docs)
