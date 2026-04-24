from pydantic import ValidationError

from llm_lab.api.exceptions import CustomException
from llm_lab.config.settings import VectorStoreType, get_settings
from llm_lab.llm.gemini_client import GeminiClient
from llm_lab.llm.types import LlmClient
from llm_lab.retrieval.retriever import Retriever
from llm_lab.vector_store.file.file_store import FileStoreClient
from llm_lab.vector_store.types import VectorStoreClient


def get_llm_client() -> LlmClient:
    try:
        settings = get_settings()
    except ValidationError as err:
        # Config is broken: missing/invalid env vars
        raise CustomException(
            status_code=500,
            message="LLM configuration error: missing or invalid environment variables",
        ) from err

    return GeminiClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        embedding_model=settings.llm_embedding_model,
    )


def get_vector_store_client() -> VectorStoreClient:
    try:
        settings = get_settings()
    except ValidationError as err:
        raise CustomException(
            status_code=500,
            message="Vector Store configuration error: missing or invalid environment variables",
        ) from err

    if settings.vector_store == VectorStoreType.FILE:
        return FileStoreClient()


def get_retriever_client() -> Retriever:
    return Retriever(get_llm_client(), get_vector_store_client())
