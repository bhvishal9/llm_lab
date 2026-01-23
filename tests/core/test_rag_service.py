from llm_lab.core.rag_service import RagService
from tests.fakes import FakeVectorStoreClient, NoCallLlmClient


class TestRagService:
    def test_rag_service_short_circuits_when_no_chunks(
        self, no_call_llm_client: NoCallLlmClient
    ) -> None:
        rag_service = RagService(
            client=no_call_llm_client,
            dataset="test_dataset",
            vector_store=FakeVectorStoreClient(),
        )

        answer, chunks = rag_service.answer_question(
            query="nonsense query that should match nothing",
            top_k=3,
        )

        assert answer == "No relevant information found to answer the question."
        assert chunks == []
