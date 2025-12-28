from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_EMBEDDING_MODEL_NAME = "gemini-embedding-001"
DEFAULT_MODEL_NAME = "gemini-2.5-flash"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
        frozen=True,
    )

    llm_api_key: str
    llm_model: str = Field(
        validation_alias="LLM_MODEL_NAME", default=DEFAULT_MODEL_NAME
    )
    llm_embedding_model: str = Field(
        validation_alias="LLM_EMBEDDING_MODEL_NAME",
        default=DEFAULT_EMBEDDING_MODEL_NAME,
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
