from pathlib import Path

from llm_lab.llm.types import LlmClient
from llm_lab.retrieval.indexing import Indexer
from llm_lab.retrieval.retriever import Retriever
from llm_lab.retrieval.types import ChunkingConfig, IndexedChunk
from llm_lab.vector_store.types import VectorStoreClient


class FileStoreClient(VectorStoreClient):
    """File-based implementation of VectorStoreClient."""

    def __init__(self, client: LlmClient, dest_dir: Path) -> None:
        self.client = client
        self.dest_dir = dest_dir

    def index_dataset(
        self,
        source_dir: Path,
        embedding_model: str,
        dataset: str,
        max_chunks_per_index: int,
        chunking_config: ChunkingConfig,
    ) -> tuple[int, int]:
        """Index a dataset located in source_dir and store the index in dest_dir."""
        indexer = Indexer(
            source_dir=source_dir,
            dest_dir=self.dest_dir,
            embedding_model=embedding_model,
            dataset=dataset,
            max_chunks_per_index=max_chunks_per_index,
            chunking_config=chunking_config,
        )
        docs_count, chunks_count = indexer.run(self.client)
        return docs_count, chunks_count

    def query(self, dataset: str, query_text: str, top_k: int) -> list[IndexedChunk]:
        """Query the vector store and return the top_k most relevant documents along with their similarity scores."""
        indexed_chunks_dir = self.dest_dir / "indexes" / dataset
        retriever = Retriever(
            client=self.client,
            query_text=query_text,
            indexed_chunks_dir=indexed_chunks_dir,
            top_k=top_k,
        )
        embedding_model_name, indexed_chunks = retriever.load_indexed_chunks()
        top_chunks = retriever.score_chunks(embedding_model_name, indexed_chunks)
        return top_chunks
