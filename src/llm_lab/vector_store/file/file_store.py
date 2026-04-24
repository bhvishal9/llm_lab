import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from llm_lab.config.paths import DEFAULT_DESTINATION_DIR
from llm_lab.vector_store.file.types import IndexFile, ManifestFile
from llm_lab.vector_store.types import IndexedChunk, ScoredChunk, VectorStoreClient

MAX_CHUNKS_PER_INDEX_FILE = 10


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


class FileStoreClient(VectorStoreClient):
    """File-based implementation of VectorStoreClient."""

    def get_embedding_model(self, dataset: str) -> str:
        """Get the embedding model used for the dataset"""
        manifest_path = Path(DEFAULT_DESTINATION_DIR / dataset / "manifest.json")
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
        except json.JSONDecodeError as err:
            raise ValueError(
                f"Manifest file at {manifest_path} is malformed: {err}"
            ) from err

        return manifest.embedding_model

    def store(
        self,
        indexed_chunks: list[IndexedChunk],
        dataset: str,
        embedding_model: str,
        docs_count: int,
    ) -> None:
        """Store the indexed chunks into a file based indexed chunk store."""
        dest_dir = DEFAULT_DESTINATION_DIR
        max_chunks_per_index_file = int(MAX_CHUNKS_PER_INDEX_FILE)
        manifest_file = Path(dest_dir / dataset / "manifest.json")
        index_creation_dir = Path(dest_dir / dataset / "indexes")
        _create_dest_dir(index_creation_dir)
        timestamp = datetime.now(tz=UTC)
        file_counter = 0
        for idx in range(0, len(indexed_chunks), max_chunks_per_index_file):
            chunk_slice = indexed_chunks[idx : idx + max_chunks_per_index_file]
            index_id = f"index-{file_counter:04}"
            index_file_name = f"{index_id}.json"
            index_path = index_creation_dir / index_file_name
            index_data = IndexFile(
                dataset=dataset,
                embedding_model=embedding_model,
                created_at=timestamp,
                index_id=index_id,
                chunks=chunk_slice,
            )
            index_path.write_text(index_data.model_dump_json(indent=2))
            file_counter += 1  # noqa: SIM113
        manifest = ManifestFile(
            dataset=dataset,
            embedding_model=embedding_model,
            created_at=timestamp,
            total_docs=docs_count,
            total_chunks=len(indexed_chunks),
        )
        manifest_file.write_text(manifest.model_dump_json(indent=2))

    def query(self, dataset: str, query_embedding: list[float]) -> list[ScoredChunk]:
        """Query the vector store and return a list of the top_k most relevant chunks."""
