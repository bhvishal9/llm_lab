import json
import logging
import uuid

from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient

from llm_lab.core.rag_service import QueryResult, RagService
from llm_lab.llm.errors import LlmUnavailableError
from llm_lab.retrieval.retriever import Retriever
from llm_lab.vector_store.types import IndexedChunk, ScoredChunk


class TestQueryApi:
    def test_query_happy_path(
        self, client: TestClient, monkeypatch: MonkeyPatch
    ) -> None:
        # 1) Fake chunks: what we expect the service to return
        fake_chunks = [
            ScoredChunk(
                score=0.95,
                indexed_chunk=IndexedChunk(
                    text="Chunk about Kubernetes pods",
                    source="assets/docs/kubernetes_intro.md",
                    embedding=[1.0, 0.0],
                    chunk_id=0,
                    doc_path="assets/docs/kubernetes_intro.md",
                ),
            ),
            ScoredChunk(
                score=0.80,
                indexed_chunk=IndexedChunk(
                    text="Some other chunk",
                    source="assets/docs/other.md",
                    embedding=[0.0, 1.0],
                    chunk_id=1,
                    doc_path="assets/docs/other.md",
                ),
            ),
        ]

        # 2) Fake RagService.answer_question so we don't touch real LLM / index
        def fake_answer_question(
            self: RagService, dataset: str, query: str, top_k: int
        ) -> QueryResult:
            assert query == "What is a Kubernetes pod?"
            assert top_k == 1
            assert dataset == "test_dataset"
            return QueryResult(
                answer="fake answer from LLM",
                chunks=fake_chunks[:top_k],
            )

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
                "dataset": "test_dataset",
                "query": "What is a Kubernetes pod?",
                "top_k": 1,
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

    def test_query_invalid_query_returns_400(
        self, client: TestClient, monkeypatch: MonkeyPatch
    ) -> None:
        payload = {"query": "", "top_k": 1, "dataset": "test_dataset"}
        monkeypatch.setenv("LLM_API_KEY", "dummy-key")
        response = client.post("/query", json=payload)
        assert response.status_code == 400
        assert response.json() == {"error": "Question must be a non-empty string"}

    def test_query_invalid_top_k_returns_400(
        self, client: TestClient, monkeypatch: MonkeyPatch
    ) -> None:
        payload = {"query": "Test Query", "top_k": 0, "dataset": "test_dataset"}
        monkeypatch.setenv("LLM_API_KEY", "dummy-key")
        response = client.post("/query", json=payload)
        assert response.status_code == 400
        assert response.json() == {"error": "top_k must be between 1 and 10"}

    def test_query_missing_index_returns_500(
        self, client: TestClient, monkeypatch: MonkeyPatch
    ) -> None:
        payload = {"query": "Test Query", "top_k": 1, "dataset": "test_dataset"}

        def fake_search(
            self: Retriever, dataset: str, query: str, top_k: int
        ) -> list[ScoredChunk]:
            raise ValueError(
                "Dataset test_dataset not found, make sure to run the index command first"
            )

        monkeypatch.setenv("LLM_API_KEY", "dummy-key")
        monkeypatch.setattr(Retriever, "search", fake_search)

        response = client.post("/query", json=payload)

        assert response.status_code == 500
        assert response.json() == {
            "error": "Dataset test_dataset not found, make sure to run the index command first"
        }

    def test_query_llm_unavailable_returns_502(
        self, client: TestClient, monkeypatch: MonkeyPatch
    ) -> None:
        payload = {"query": "Test Query", "top_k": 1, "dataset": "test_dataset"}

        # Make sure settings doesn't blow up
        monkeypatch.setenv("LLM_API_KEY", "dummy-key")

        # Fake RagService.answer_question to simulate an upstream 5xx from the LLM
        def fake_answer_question(
            self: RagService, dataset: str, query: str, top_k: int
        ) -> QueryResult:
            assert query == "Test Query"
            assert top_k == 1
            assert dataset == "test_dataset"
            raise LlmUnavailableError("Fake client unavailable")

        # Patch the method on RagService
        monkeypatch.setattr(RagService, "answer_question", fake_answer_question)

        # Call the API
        response = client.post("/query", json=payload)

        # Assert we mapped it to the correct HTTP status
        assert response.status_code == 502
        data = response.json()
        assert data["error"] == "Fake client unavailable"

    def test_query_log_fields_exists(
        self, client: TestClient, monkeypatch: MonkeyPatch, caplog: LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="llm_lab.api")
        # 1) Fake chunks: what we expect the service to return
        fake_chunks = [
            ScoredChunk(
                score=0.95,
                indexed_chunk=IndexedChunk(
                    text="Chunk about Kubernetes pods",
                    source="assets/docs/kubernetes_intro.md",
                    embedding=[1.0, 0.0],
                    chunk_id=0,
                    doc_path="assets/docs/kubernetes_intro.md",
                ),
            ),
        ]

        # 2) Fake RagService.answer_question so we don't touch real LLM / index
        def fake_answer_question(
            self: RagService, dataset: str, query: str, top_k: int
        ) -> QueryResult:
            assert query == "What is a Kubernetes pod?"
            assert top_k == 1
            assert dataset == "test_dataset"
            return QueryResult(
                answer="fake answer from LLM",
                chunks=fake_chunks[:top_k],
            )

        # 3) Patch env so Settings() doesn't explode
        monkeypatch.setenv("LLM_API_KEY", "dummy-key")

        # 4) Patch the method on RagService
        monkeypatch.setattr(
            RagService,
            "answer_question",
            fake_answer_question,
        )

        # 5) Call the API
        client.post(
            "/query",
            json={
                "query": "What is a Kubernetes pod?",
                "top_k": 1,
                "dataset": "test_dataset",
            },
        )

        # 6) Assertions
        logs = json.loads(caplog.messages[0])
        assert logs["request_id"] != ""
        assert logs["request_id"] != "uuid-not-set"
        uuid.UUID(logs["request_id"])
        assert logs["top_k"] == 1
        assert logs["dataset"] == "test_dataset"
