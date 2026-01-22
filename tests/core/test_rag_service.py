from llm_lab.core.rag_service import RagService
from tests.fakes import NoCallLlmClient


class TestRagService:
    def test_rag_service_short_circuits_when_no_chunks(
        self, monkeypatch, no_call_llm_client: NoCallLlmClient
    ) -> None:
        # Stub Retriever.load_indexed_chunks → returns valid model name + empty chunk list
        monkeypatch.setattr(
            "llm_lab.core.rag_service.Retriever.load_indexed_chunks",
            lambda self: ("models/embedding-001", []),
        )

        # Stub Retriever.score_chunks → always returns empty list
        monkeypatch.setattr(
            "llm_lab.core.rag_service.Retriever.score_chunks",
            lambda self, embedding_model_name, indexed_chunks: [],
        )

        rag_service = RagService(
            client=no_call_llm_client,
            dataset="test_dataset",
        )

        answer, chunks = rag_service.answer_question(
            query="nonsense query that should match nothing",
            top_k=3,
        )

        assert answer == "No relevant information found to answer the question."
        assert chunks == []
