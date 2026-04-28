import json
from pathlib import Path

import pytest

from llm_lab.vector_store.file.file_store import FileStoreClient


class TestFileStoreClient:
    def test_get_embedding_model_returns_model_from_manifest(
        self, tmp_path: Path
    ) -> None:
        dataset = "test_dataset"
        dataset_dir = tmp_path / dataset
        dataset_dir.mkdir()
        manifest = {
            "dataset": dataset,
            "embedding_model": "models/text-embedding-004",
            "created_at": "2026-01-01T00:00:00Z",
            "total_docs": 1,
            "total_chunks": 5,
            "index_files": [],
        }
        (dataset_dir / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

        client = FileStoreClient(dest_dir=tmp_path)
        assert client.get_embedding_model(dataset) == "models/text-embedding-004"

    def test_get_embedding_model_raises_when_manifest_missing(
        self, tmp_path: Path
    ) -> None:
        client = FileStoreClient(dest_dir=tmp_path)
        with pytest.raises(FileNotFoundError):
            client.get_embedding_model("nonexistent_dataset")

    def test_get_embedding_model_raises_when_manifest_malformed(
        self, tmp_path: Path
    ) -> None:
        dataset = "test_dataset"
        dataset_dir = tmp_path / dataset
        dataset_dir.mkdir()
        (dataset_dir / "manifest.json").write_text("not valid json{", encoding="utf-8")

        client = FileStoreClient(dest_dir=tmp_path)
        with pytest.raises(ValueError, match="malformed"):
            client.get_embedding_model(dataset)
