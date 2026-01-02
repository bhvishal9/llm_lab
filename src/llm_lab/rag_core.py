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
