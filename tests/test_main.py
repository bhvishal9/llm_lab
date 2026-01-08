from fastapi.testclient import TestClient

from llm_lab.core.rag_service import RagService
from llm_lab.llm.errors import LlmUnavailableError
from llm_lab.main import app
from llm_lab.retrieval.indexing import IndexedChunk
from llm_lab.retrieval.retriever import Retriever

client = TestClient(app)


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
        ),
        IndexedChunk(
            text="Some other chunk",
            source="assets/docs/other.md",
            embedding=[0.0, 1.0],
            chunk_id=1,
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
        json={"query": "What is a Kubernetes pod?", "top_k": 1},
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
    payload = {"query": "", "top_k": 1}
    monkeypatch.setenv("LLM_API_KEY", "dummy-key")
    response = client.post("/query", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "Question must be a non-empty string"}


def test_query_invalid_top_k_returns_400(monkeypatch) -> None:
    payload = {"query": "Test Query", "top_k": 0}
    monkeypatch.setenv("LLM_API_KEY", "dummy-key")
    response = client.post("/query", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "top_k must be between 1 and 10"}


def test_query_missing_index_returns_500(monkeypatch) -> None:
    payload = {"query": "Test Query", "top_k": 1}

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
    payload = {"query": "Test Query", "top_k": 1}

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
