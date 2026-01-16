import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import llm_lab.retrieval.indexing as indexing
from llm_lab.core.rag_service import RagService
from llm_lab.llm.errors import LlmUnavailableError
from llm_lab.main import app
from llm_lab.retrieval.indexing import IndexedChunk, Indexer, _create_chunks
from llm_lab.retrieval.retriever import Retriever
from llm_lab.retrieval.types import ChunkingConfig

client = TestClient(app)


class FakeLlmClient:
    def embed_text(self, text: str, embedding_model: str | None = None) -> list[float]:
        return [0.1, 0.2, 0.3]

    def generate_response(self, prompt: str, model: str | None = None) -> str:
        raise NotImplementedError


def test_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_echo_roundtrip() -> None:
    payload = {"name": "Vishal"}
    response = client.post("/echo", json=payload)
    assert response.status_code == 200
    assert response.json() == payload


def test_echo_invalid_body_returns_422() -> None:
    # Missing required field "name"
    response = client.post("/echo", json={})
    assert response.status_code == 422


def test_query_happy_path(monkeypatch) -> None:
    # 1) Fake chunks: what we expect the service to return
    fake_chunks = [
        IndexedChunk(
            text="Chunk about Kubernetes pods",
            source="assets/docs/kubernetes_intro.md",
            embedding=[1.0, 0.0],
            chunk_id=0,
            doc_path="assets/docs/kubernetes_intro.md",
        ),
        IndexedChunk(
            text="Some other chunk",
            source="assets/docs/other.md",
            embedding=[0.0, 1.0],
            chunk_id=1,
            doc_path="assets/docs/other.md",
        ),
    ]

    # 2) Fake RagService.answer_question so we don't touch real LLM / index
    def fake_answer_question(self, query: str, top_k: int):
        # optional: assert about inputs if you want
        assert query == "What is a Kubernetes pod?"
        assert top_k == 1
        return "fake answer from LLM", fake_chunks[:top_k]

    # 3) Patch env so Settings() doesn't explode
    monkeypatch.setenv("LLM_API_KEY", "dummy-key")

    # 4) Patch the method on RagService
    monkeypatch.setattr(
        RagService,
        "answer_question",
        fake_answer_question,
    )

    # 5) Call the API
    response = client.post(
        "/query",
        json={
            "query": "What is a Kubernetes pod?",
            "top_k": 1,
            "dataset": "test_dataset",
        },
    )

    # 6) Assertions
    assert response.status_code == 200
    data = response.json()

    assert data["answer"] == "fake answer from LLM"
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) == 1

    first_source = data["sources"][0]
    assert first_source["source"] == "assets/docs/kubernetes_intro.md"
    assert first_source["chunk_id"] == 0


def test_query_invalid_query_returns_400(monkeypatch) -> None:
    payload = {"query": "", "top_k": 1, "dataset": "test_dataset"}
    monkeypatch.setenv("LLM_API_KEY", "dummy-key")
    response = client.post("/query", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "Question must be a non-empty string"}


def test_query_invalid_top_k_returns_400(monkeypatch) -> None:
    payload = {"query": "Test Query", "top_k": 0, "dataset": "test_dataset"}
    monkeypatch.setenv("LLM_API_KEY", "dummy-key")
    response = client.post("/query", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "top_k must be between 1 and 10"}


def test_query_missing_index_returns_500(monkeypatch) -> None:
    payload = {"query": "Test Query", "top_k": 1, "dataset": "test_dataset"}

    def fake_load_indexed_chunks(self):
        raise FileNotFoundError(
            "File whatever not found, make sure to run the index command first"
        )

    monkeypatch.setenv("LLM_API_KEY", "dummy-key")
    monkeypatch.setattr(Retriever, "load_indexed_chunks", fake_load_indexed_chunks)

    response = client.post("/query", json=payload)

    assert response.status_code == 500
    assert response.json() == {
        "error": "File whatever not found, make sure to run the index command first"
    }


def test_query_llm_unavailable_returns_502(monkeypatch) -> None:
    payload = {"query": "Test Query", "top_k": 1, "dataset": "test_dataset"}

    # Make sure settings doesn't blow up
    monkeypatch.setenv("LLM_API_KEY", "dummy-key")

    # Fake RagService.answer_question to simulate an upstream 5xx from the LLM
    def fake_answer_question(self, query: str, top_k: int):
        assert query == "Test Query"
        assert top_k == 1
        raise LlmUnavailableError("Fake client unavailable")

    # Patch the method on RagService
    monkeypatch.setattr(RagService, "answer_question", fake_answer_question)

    # Call the API
    response = client.post("/query", json=payload)

    # Assert we mapped it to the correct HTTP status
    assert response.status_code == 502
    data = response.json()
    assert data["error"] == "Fake client unavailable"


def test_create_chunks_happy_path() -> None:
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


def test_create_chunks_splits_on_separator_before_limit() -> None:
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


def test_create_chunks_empty_content_returns_empty_list() -> None:
    text = ""
    config = ChunkingConfig(chunk_size=10, chunk_separator="\n\n")
    chunks = _create_chunks(text, Path("assets/docs/whatever.md"), config)
    assert chunks == []


def test_indexer_happy_path(tmp_path: Path, monkeypatch) -> None:
    # Setup: create a fake source directory with a text file
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    file_path = source_dir / "test.md"
    file_content = "This is a test document. It will be indexed."
    file_path.write_text(file_content, encoding="utf-8")

    dest_dir = tmp_path / "dest"

    monkeypatch.setattr(indexing, "BASE_DIR", tmp_path)
    llm_client = FakeLlmClient()

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
    docs_count, chunks_count = indexer.run(llm_client)
    assert docs_count == 1
    assert chunks_count == 1

    manifest_path = dest_dir / "indexes" / "test_dataset" / "manifest.json"
    assert manifest_path.exists()

    data = json.loads(manifest_path.read_text())
    assert data["total_docs"] == 1
    assert data["total_chunks"] == 1


def test_indexer_no_markdown_files_returns_error(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    dest_dir = tmp_path / "dest"

    # Patch indexing.BASE_DIR to tmp_path
    monkeypatch.setattr(indexing, "BASE_DIR", tmp_path)
    llm_client = FakeLlmClient()

    indexer = Indexer(
        source_dir=source_dir,
        dest_dir=dest_dir,
        chunking_config=ChunkingConfig(chunk_size=50, chunk_separator=". "),
        embedding_model="models/embedding-001",
        dataset="test_dataset",
        max_chunks_per_index=1000,
    )

    with pytest.raises(ValueError) as excinfo:
        indexer.run(llm_client)

    assert str(excinfo.value) == f"No Markdown files found in directory {source_dir}"


def test_retriever_loads_chunks_from_manifest_and_index_file(tmp_path: Path) -> None:
    # Setup: create a fake indexed chunks directory with manifest and index file
    indexed_chunks_dir = tmp_path / "indexes" / "test_dataset"
    indexed_chunks_dir.mkdir(parents=True)

    # Create a fake index file
    index_file_path = indexed_chunks_dir / "index-0001.json"
    index_file_content = {
        "chunks": [
            {
                "text": "Chunk about Kubernetes pods",
                "source": "assets/docs/kubernetes_intro.md",
                "embedding": [1.0, 0.0],
                "chunk_id": 0,
                "doc_path": "assets/docs/kubernetes_intro.md",
            }
        ],
        "dataset": "test_dataset",
        "embedding_model": "models/embedding-001",
        "created_at": "2024-01-01T00:00:00Z",
        "index_id": "index-0001",
    }
    index_file_path.write_text(json.dumps(index_file_content), encoding="utf-8")

    # Create a fake manifest file
    manifest_path = indexed_chunks_dir / "manifest.json"
    manifest_content = {
        "dataset": "test_dataset",
        "embedding_model": "models/embedding-001",
        "created_at": "2024-01-01T00:00:00Z",
        "total_docs": 1,
        "total_chunks": 1,
        "index_files": [
            {
                "index_id": "index-0001",
                "path": "index-0001.json",
                "num_chunks": 1,
            }
        ],
        "documents": [
            {
                "doc_id": "kubernetes_intro.md",
                "doc_path": "assets/docs/kubernetes_intro.md",
                "hash": "dummyhash",
                "last_indexed_at": "2024-01-01T00:00:00Z",
            }
        ],
    }
    manifest_path.write_text(json.dumps(manifest_content), encoding="utf-8")
    retriever = Retriever(
        client=FakeLlmClient(),
        query_text="What is a Kubernetes pod?",
        indexed_chunks_dir=indexed_chunks_dir,
        top_k=1,
    )
    embedding_model, indexed_chunks = retriever.load_indexed_chunks()
    assert embedding_model == "models/embedding-001"
    assert len(indexed_chunks) == 1
    assert indexed_chunks[0].text == "Chunk about Kubernetes pods"
    assert indexed_chunks[0].source == "assets/docs/kubernetes_intro.md"
    assert indexed_chunks[0].chunk_id == 0
    assert isinstance(indexed_chunks[0], IndexedChunk)
    assert indexed_chunks[0].doc_path == "assets/docs/kubernetes_intro.md"
