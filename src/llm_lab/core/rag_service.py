from llm_lab.config.paths import DEFAULT_DESTINATION_DIR
from llm_lab.llm.types import LlmClient
from llm_lab.retrieval.retriever import Retriever
from llm_lab.retrieval.types import IndexedChunk


def build_prompt(question: str, chunks: list[IndexedChunk]) -> str:
    """Build a prompt for the LLM based on the question and chunks."""
    context_parts = []
    for chunk in chunks:
        context_parts.append(
            f"Source: {chunk.source} (chunk {chunk.chunk_id})\n{chunk.text}"
        )
    context = "\n\n".join(context_parts)

    prompt = (
        "You are a helpful assistant. Use ONLY the context below to answer the question.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n"
        "Answer:"
    )
    return prompt


class RagService:
    def __init__(self, client: LlmClient, dataset: str) -> None:
        self.client = client
        self.dataset = dataset
        self.index_dir = DEFAULT_DESTINATION_DIR / "indexes" / self.dataset

    def answer_question(
        self,
        query: str,
        top_k: int,
    ) -> tuple[str, list[IndexedChunk]]:
        """Answer a question using a simple RAG pipeline."""
        retriever = Retriever(self.client, query, self.index_dir, top_k=top_k)
        embedding_model_name, indexed_chunks = retriever.load_indexed_chunks()
        top_chunks = retriever.score_chunks(embedding_model_name, indexed_chunks)
        prompt = build_prompt(query, top_chunks)
        response = self.client.generate_response(prompt)
        return response, top_chunks
