import pytest
from pytest_mock import MockerFixture

from llm_lab.config.settings import VectorStoreType
from llm_lab.core.rag_service import RagService, create_vector_store_client
from tests.fakes import FakeSettings, FakeVectorStoreClient, NoCallLlmClient


class TestRagService:
    def test_rag_service_short_circuits_when_no_chunks(
        self, mocker: MockerFixture, no_call_llm_client: NoCallLlmClient
    ) -> None:
        mocker.patch(
            "llm_lab.core.rag_service.create_vector_store_client",
            return_value=FakeVectorStoreClient(),
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

    def test_create_vector_store_client_returns_file_store_client(
        self, mocker: MockerFixture, no_call_llm_client: NoCallLlmClient
    ) -> None:
        mock_file_store_client = mocker.patch(
            "llm_lab.core.rag_service.FileStoreClient"
        )
        settings = FakeSettings(VectorStoreType.FILE)

        vector_store_client = create_vector_store_client(settings, no_call_llm_client)

        assert vector_store_client == mock_file_store_client.return_value
        mock_file_store_client.assert_called_once_with(
            client=no_call_llm_client, dest_dir=mocker.ANY
        )

    def test_create_vector_store_client_raises_error_on_unsupported_type(
        self, no_call_llm_client: NoCallLlmClient
    ) -> None:
        settings = FakeSettings("unsupported")  # intentionally bad
        with pytest.raises(ValueError):
            create_vector_store_client(settings, no_call_llm_client)
