import json
from pathlib import Path

import pytest

import llm_lab.retrieval.indexing as indexing
from llm_lab.retrieval.indexing import Indexer, _create_chunks
from llm_lab.retrieval.types import ChunkingConfig
from tests.fakes import FakeLlmClient


class TestChunking:
    def test_create_chunks_happy_path(self) -> None:
        text = "This is a sample document. It has several sentences. We will chunk it."
        chunk_size = 70
        chunk_separator = ". "
        chunking_config = ChunkingConfig(
            chunk_size=chunk_size, chunk_separator=chunk_separator
        )
        file_path = Path("assets/docs/kubernetes_intro.md")

        chunks = _create_chunks(text, file_path, chunking_config)

        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].doc_path == "assets/docs/kubernetes_intro.md"

    def test_create_chunks_splits_on_separator_before_limit(self) -> None:
        text = "This is a sample document. It has several sentences. We will chunk it."
        chunk_size = 65
        chunk_separator = ". "
        chunking_config = ChunkingConfig(
            chunk_size=chunk_size, chunk_separator=chunk_separator
        )
        file_path = Path("assets/docs/kubernetes_intro.md")

        chunks = _create_chunks(text, file_path, chunking_config)

        assert len(chunks) == 2
        assert chunks[0].text == "This is a sample document. It has several sentences."
        assert chunks[1].text == "We will chunk it."

    def test_create_chunks_empty_content_returns_empty_list(self) -> None:
        text = ""
        config = ChunkingConfig(chunk_size=10, chunk_separator="\\n\\n")
        chunks = _create_chunks(text, Path("assets/docs/whatever.md"), config)
        assert chunks == []


class TestIndexer:
    def test_indexer_happy_path(
        self, tmp_path: Path, monkeypatch, fake_llm_client: FakeLlmClient
    ) -> None:
        # Setup: create a fake source directory with a text file
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        file_path = source_dir / "test.md"
        file_content = "This is a test document. It will be indexed."
        file_path.write_text(file_content, encoding="utf-8")

        dest_dir = tmp_path / "dest"

        monkeypatch.setattr(indexing, "BASE_DIR", tmp_path)

        # Create Indexer instance
        indexer = Indexer(
            source_dir=source_dir,
            dest_dir=dest_dir,
            chunking_config=ChunkingConfig(chunk_size=50, chunk_separator=". "),
            embedding_model="models/embedding-001",
            dataset="test_dataset",
            max_chunks_per_index=1000,
        )

        # Run indexing
        docs_count, chunks_count = indexer.run(fake_llm_client)
        assert docs_count == 1
        assert chunks_count == 1

        manifest_path = dest_dir / "indexes" / "test_dataset" / "manifest.json"
        assert manifest_path.exists()

        data = json.loads(manifest_path.read_text())
        assert data["total_docs"] == 1
        assert data["total_chunks"] == 1

    def test_indexer_no_markdown_files_returns_error(
        self,
        tmp_path: Path,
        monkeypatch,
        fake_llm_client: FakeLlmClient,
    ) -> None:
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        dest_dir = tmp_path / "dest"

        # Patch indexing.BASE_DIR to tmp_path
        monkeypatch.setattr(indexing, "BASE_DIR", tmp_path)

        indexer = Indexer(
            source_dir=source_dir,
            dest_dir=dest_dir,
            chunking_config=ChunkingConfig(chunk_size=50, chunk_separator=". "),
            embedding_model="models/embedding-001",
            dataset="test_dataset",
            max_chunks_per_index=1000,
        )

        with pytest.raises(ValueError) as excinfo:
            indexer.run(fake_llm_client)

        assert (
            str(excinfo.value) == f"No Markdown files found in directory {source_dir}"
        )
