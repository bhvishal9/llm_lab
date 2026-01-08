from fastapi import Depends
from pydantic import ValidationError

from llm_lab.api.exceptions import CustomException
from llm_lab.config.paths import DEFAULT_INDEXED_CHUNKS_FILE
from llm_lab.config.settings import get_settings
from llm_lab.core.rag_service import RagService
from llm_lab.llm.gemini_client import GeminiClient
from llm_lab.llm.types import LlmClient


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


def get_rag_service(
    client: LlmClient = Depends(get_llm_client),
) -> RagService:
    return RagService(client=client, index_path=DEFAULT_INDEXED_CHUNKS_FILE)
