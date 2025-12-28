from google import genai
from google.genai import types
from google.genai.errors import ClientError

from llm_lab.llm.errors import (
    LlmAuthenticationError,
    LlmError,
    LlmInvalidRequestError,
    LlmRateLimitError,
    LlmUnavailableError,
)
from llm_lab.llm.types import LlmClient


def _map_gemini_error(err: ClientError) -> LlmError:
    """Map Google Gemini ClientError to custom LlmError."""
    error_code = int(err.code)
    if error_code == 400:
        return LlmInvalidRequestError(str(err))
    elif error_code in [401, 403]:
        return LlmAuthenticationError(str(err))
    elif error_code == 429:
        return LlmRateLimitError(str(err))
    elif 500 <= error_code < 600:
        return LlmUnavailableError(str(err))
    else:
        return LlmError(str(err))


class GeminiClient(LlmClient):
    """Client for interacting with Google Gemini LLM."""

    def __init__(self, api_key: str, model: str, embedding_model: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.embedding_model = embedding_model

    def embed_text(self, text: str, embedding_model: str | None = None) -> list[float]:
        """Embed the given text. If embedding_model is provided, use that; otherwise use the client’s default"""
        try:
            embedding = self.client.models.embed_content(
                model=embedding_model or self.embedding_model,
                contents=text,
                config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
            )
            return embedding.embeddings[0].values
        except ClientError as err:
            raise _map_gemini_error(err) from err

    def generate_response(self, prompt: str, model: str | None = None) -> str:
        """Generate a response for the given prompt. If model is provided, use that; otherwise use the client’s default"""
        try:
            response = self.client.models.generate_content(
                model=model or self.model,
                contents=prompt,
            )
            return response.text
        except ClientError as err:
            raise _map_gemini_error(err) from err
