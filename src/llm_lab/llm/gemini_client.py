from google import genai
from google.genai import types

from llm_lab.llm.types import LlmClient


class GeminiClient(LlmClient):
    """Client for interacting with Google Gemini LLM."""

    def __init__(self, api_key: str, model: str, embedding_model: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.embedding_model = embedding_model

    def embed_text(self, text: str, embedding_model: str | None = None) -> list[float]:
        """Embed the given text. If embedding_model is provided, use that; otherwise use the client’s default"""
        embedding = self.client.models.embed_content(
            model=embedding_model or self.embedding_model,
            contents=text,
            config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
        )
        return embedding.embeddings[0].values

    def generate_response(self, prompt: str, model: str | None = None) -> str:
        """Generate a response for the given prompt. If model is provided, use that; otherwise use the client’s default"""
        response = self.client.models.generate_content(
            model=model or self.model,
            contents=prompt,
        )
        return response.text
