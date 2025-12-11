from google.genai.errors import ClientError
from fastapi.testclient import TestClient
import llm_lab.main as main
from llm_lab.main import app
from llm_lab.rag_core import IndexedChunk

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
    # 1) Fake index: embedding model name + a couple of chunks
    def fake_load_indexed_chunks(_path):
        chunks = [
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
        # Same shape as real load_indexed_chunks: (embedding_model_name, chunks)
        return "fake-embedding-model", chunks

    # 2) Fake embed_text: always return [1.0, 0.0] so first chunk is most similar
    def fake_embed_text(_client, _text: str, _model_name: str):
        return [1.0, 0.0]

    # 3) Fake generate_response: avoid hitting real LLM
    def fake_generate_response(_client, _model_name: str, _prompt: str) -> str:
        return "fake answer from LLM"

    # 4) Patch env + functions on the main module
    monkeypatch.setenv("LLM_API_KEY", "dummy-key")
    monkeypatch.setattr(main, "load_indexed_chunks", fake_load_indexed_chunks)
    monkeypatch.setattr(main, "embed_text", fake_embed_text)
    monkeypatch.setattr(main, "generate_response", fake_generate_response)

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


def test_query_invalid_query_returns_400() -> None:
    payload = {"query": "", "top_k": 1}
    response = client.post("/query", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "Question must be a non-empty string"}


def test_query_invalid_top_k_returns_400() -> None:
    payload = {"query": "Test Query", "top_k": 0}
    response = client.post("/query", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "top_k must be between 1 and 10"}


def test_query_missing_index_returns_500(monkeypatch) -> None:
    payload = {"query": "Test Query", "top_k": 1}

    def fake_load_indexed_chunks(_path):
        raise ValueError(
            "File whatever not found, make sure to run the index command first"
        )

    monkeypatch.setattr(main, "load_indexed_chunks", fake_load_indexed_chunks)
    response = client.post("/query", json=payload)
    assert response.status_code == 500
    assert response.json() == {
        "error": "File whatever not found, make sure to run the index command first"
    }


def test_query_client_error_502(monkeypatch) -> None:
    payload = {"query": "Test Query", "top_k": 1}

    def fake_load_indexed_chunks(_path):
        chunks = [
            IndexedChunk(
                text="Chunk about Kubernetes pods",
                source="assets/docs/kubernetes_intro.md",
                embedding=[1.0, 0.0],
                chunk_id=0,
            )
        ]
        return "fake-embedding-model", chunks

    # 2) Fake embed_text: always return [1.0, 0.0] so first chunk is most similar
    def fake_embed_text(_client, _text: str, _model_name: str):
        return [1.0, 0.0]

    def fake_generate_response(_client, _model_name: str, _prompt: str) -> str:
        raise ClientError(
            response_json={"message": "Fake client unavailable"}, code=502
        )

    monkeypatch.setenv("LLM_API_KEY", "dummy-key")
    monkeypatch.setattr(main, "load_indexed_chunks", fake_load_indexed_chunks)
    monkeypatch.setattr(main, "embed_text", fake_embed_text)
    monkeypatch.setattr(main, "generate_response", fake_generate_response)
    response = client.post("/query", json=payload)
    assert response.status_code == 502
