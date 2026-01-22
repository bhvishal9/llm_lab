class FakeLlmClient:
    def embed_text(self, text: str, embedding_model: str | None = None) -> list[float]:
        return [0.1, 0.2, 0.3]

    def generate_response(self, prompt: str, model: str | None = None) -> str:
        raise NotImplementedError


class NoCallLlmClient:
    def embed_text(self, text: str, embedding_model: str | None = None) -> list[float]:
        # Not really used in this test because we stub Retriever,
        # but implemented for interface completeness.
        return [1.0, 0.0]

    def generate_response(self, prompt: str, model: str | None = None) -> str:
        raise AssertionError(
            "generate_response should not be called when no chunks are returned."
        )
