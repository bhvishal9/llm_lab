import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

from llm_lab.config.paths import BASE_DIR
from llm_lab.llm.types import LlmClient
from llm_lab.retrieval.types import (
    Chunk,
    IndexedChunk,
    IndexFile,
    ManifestDocument,
    ManifestFile,
    ManifestIndexFile,
)


def _create_chunks(file_content: str, file_name: Path) -> list[Chunk]:
    """Create chunks from a file content."""
    chunks = []
    for chunk in file_content.split("\n\n"):
        if not chunk.strip():
            continue
        chunks.append(Chunk(text=chunk.strip(), doc_path=str(file_name)))
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


def _create_dest_dir(dest_dir: Path) -> None:
    """Create destination directory, removing it first if it exists."""
    try:
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
    except (FileExistsError, PermissionError) as e:
        raise ValueError(
            f"Could not create destination directory {dest_dir}: {e}"
        ) from e


class Indexer:
    """Indexer to create embeddings for documents in a directory."""

    def __init__(
        self,
        source_dir: Path,
        dest_dir: Path,
        embedding_model: str,
        dataset: str,
        max_chunks_per_index: int,
    ) -> None:
        self.dest_dir = dest_dir
        self.source_dir = source_dir
        self.embedding_model = embedding_model
        self.dataset = dataset
        self.max_chunks_per_index = max_chunks_per_index
        self.index_creation_dir = self.dest_dir / "indexes" / self.dataset

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
    ) -> tuple[list[IndexedChunk], list[ManifestDocument]]:
        """Build index by creating embeddings for document chunks."""
        indexed_chunks = []
        manifest_documents = []
        for doc in docs:
            file_content = _read_file(doc)
            doc_hash = hashlib.sha256(file_content.encode("utf-8")).hexdigest()
            doc_path = doc.relative_to(BASE_DIR)
            chunks = _create_chunks(file_content, doc_path)
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
            manifest_documents.append(
                ManifestDocument(
                    doc_id=doc.name,
                    doc_path=str(doc_path),
                    hash=str(doc_hash),
                    last_indexed_at=datetime.now(tz=timezone.utc),
                )
            )
        return indexed_chunks, manifest_documents

    def _save_manifest(
        self,
        manifest_index_files: list[ManifestIndexFile],
        manifest_documents: list[ManifestDocument],
    ) -> None:
        """Save the manifest file."""
        total_docs = len(manifest_documents)
        total_chunks = sum(mf.num_chunks for mf in manifest_index_files)
        manifest_file = ManifestFile(
            dataset=self.dataset,
            embedding_model=self.embedding_model,
            created_at=datetime.now(tz=timezone.utc),
            total_docs=total_docs,
            total_chunks=total_chunks,
            index_files=manifest_index_files,
            documents=manifest_documents,
        )
        manifest_path = self.index_creation_dir / "manifest.json"
        manifest_path.write_text(manifest_file.model_dump_json(indent=2))

    def save_indexed_chunks(
        self,
        indexed_chunks: list[IndexedChunk],
        manifest_documents: list[ManifestDocument],
    ) -> None:
        """Save indexed chunks to JSON files."""
        file_counter = 0
        manifest_index_files = []
        _create_dest_dir(self.index_creation_dir)
        for idx in range(0, len(indexed_chunks), self.max_chunks_per_index):
            chunk_slice = indexed_chunks[idx : idx + self.max_chunks_per_index]
            index_id = f"index-{file_counter:04}"
            index_file_name = f"{index_id}.json"
            index_path = self.index_creation_dir / index_file_name
            index_data = IndexFile(
                dataset=self.dataset,
                embedding_model=self.embedding_model,
                created_at=datetime.now(tz=timezone.utc),
                index_id=index_id,
                chunks=chunk_slice,
            )
            index_path.write_text(index_data.model_dump_json(indent=2))
            manifest_index_files.append(
                ManifestIndexFile(
                    index_id=index_id,
                    path=str(index_path.relative_to(self.dest_dir)),
                    num_chunks=len(chunk_slice),
                )
            )
            file_counter += 1
        self._save_manifest(manifest_index_files, manifest_documents)

    def run(self, llm_client: LlmClient) -> tuple[int, int]:
        """Run the indexing process."""
        docs = self.load_docs()
        indexed_chunks, manifest_documents = self.build_index(llm_client, docs)
        self.save_indexed_chunks(indexed_chunks, manifest_documents)
        return len(docs), len(indexed_chunks)
