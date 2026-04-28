from pydantic import ValidationError

from llm_lab.api.exceptions import CustomException
from llm_lab.core.factories import create_llm_client, create_vector_store_client
from llm_lab.llm.types import LlmClient
from llm_lab.retrieval.retriever import Retriever
from llm_lab.vector_store.types import VectorStoreClient


def get_llm_client() -> LlmClient:
    try:
        return create_llm_client()
    except ValidationError as err:
        raise CustomException(
            status_code=500,
            message="LLM configuration error: missing or invalid environment variables",
        ) from err


def get_vector_store_client() -> VectorStoreClient:
    try:
        return create_vector_store_client()
    except ValidationError as err:
        raise CustomException(
            status_code=500,
            message="Vector Store configuration error: missing or invalid environment variables",
        ) from err


def get_retriever_client() -> Retriever:
    return Retriever(get_llm_client(), get_vector_store_client())
