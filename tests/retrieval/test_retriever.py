import json
from pathlib import Path

from llm_lab.retrieval.indexing import IndexedChunk
from llm_lab.retrieval.retriever import Retriever
from tests.fakes import FakeLlmClient


class TestRetriever:
    def test_retriever_loads_chunks_from_manifest_and_index_file(
        self, tmp_path: Path, fake_llm_client: FakeLlmClient
    ) -> None:
        # Setup: create a fake indexed chunks directory with manifest and index file
        indexed_chunks_dir = tmp_path / "indexes" / "test_dataset"
        indexed_chunks_dir.mkdir(parents=True)

        # Create a fake index file
        index_file_path = indexed_chunks_dir / "index-0001.json"
        index_file_content = {
            "chunks": [
                {
                    "text": "Chunk about Kubernetes pods",
                    "source": "assets/docs/kubernetes_intro.md",
                    "embedding": [1.0, 0.0],
                    "chunk_id": 0,
                    "doc_path": "assets/docs/kubernetes_intro.md",
                }
            ],
            "dataset": "test_dataset",
            "embedding_model": "models/embedding-001",
            "created_at": "2024-01-01T00:00:00Z",
            "index_id": "index-0001",
        }
        index_file_path.write_text(json.dumps(index_file_content), encoding="utf-8")

        # Create a fake manifest file
        manifest_path = indexed_chunks_dir / "manifest.json"
        manifest_content = {
            "dataset": "test_dataset",
            "embedding_model": "models/embedding-001",
            "created_at": "2024-01-01T00:00:00Z",
            "total_docs": 1,
            "total_chunks": 1,
            "index_files": [
                {
                    "index_id": "index-0001",
                    "path": "index-0001.json",
                    "num_chunks": 1,
                }
            ],
            "documents": [
                {
                    "doc_id": "kubernetes_intro.md",
                    "doc_path": "assets/docs/kubernetes_intro.md",
                    "hash": "dummyhash",
                    "last_indexed_at": "2024-01-01T00:00:00Z",
                }
            ],
        }
        manifest_path.write_text(json.dumps(manifest_content), encoding="utf-8")
        retriever = Retriever(
            client=fake_llm_client,
            query_text="What is a Kubernetes pod?",
            indexed_chunks_dir=indexed_chunks_dir,
            top_k=1,
        )
        embedding_model, indexed_chunks = retriever.load_indexed_chunks()
        assert embedding_model == "models/embedding-001"
        assert len(indexed_chunks) == 1
        assert indexed_chunks[0].text == "Chunk about Kubernetes pods"
        assert indexed_chunks[0].source == "assets/docs/kubernetes_intro.md"
        assert indexed_chunks[0].chunk_id == 0
        assert isinstance(indexed_chunks[0], IndexedChunk)
        assert indexed_chunks[0].doc_path == "assets/docs/kubernetes_intro.md"

    def test_score_chunks_applies_threshold_and_top_k(
        self, monkeypatch, tmp_path: Path, fake_llm_client: FakeLlmClient
    ) -> None:
        # Query embedding will always be [1.0, 0.0]
        def fake_embed_text(
            self, text: str, embedding_model: str | None = None
        ) -> list[float]:
            return [1.0, 0.0]

        # Use the same FakeLlmClient type from above tests
        monkeypatch.setattr(FakeLlmClient, "embed_text", fake_embed_text)

        retriever = Retriever(
            client=fake_llm_client,
            query_text="pod",
            indexed_chunks_dir=tmp_path,  # not used by score_chunks
            top_k=2,
        )

        # Three chunks with different similarity to [1.0, 0.0]
        # A: identical → cosine = 1.0 (should pass)
        # B: [1,1] → cosine ≈ 0.707 (should pass with threshold 0.70)
        # C: orthogonal-ish → cosine near 0 (should fail)
        chunk_a = IndexedChunk(
            text="high similarity A",
            doc_path="assets/docs/a.md",
            source="assets/docs/a.md#chunk-0",
            embedding=[1.0, 0.0],
            chunk_id=0,
        )
        chunk_b = IndexedChunk(
            text="medium similarity B",
            doc_path="assets/docs/b.md",
            source="assets/docs/b.md#chunk-0",
            embedding=[1.0, 1.0],
            chunk_id=1,
        )
        chunk_c = IndexedChunk(
            text="low similarity C",
            doc_path="assets/docs/c.md",
            source="assets/docs/c.md#chunk-0",
            embedding=[0.0, 1.0],
            chunk_id=2,
        )

        indexed_chunks = [chunk_a, chunk_b, chunk_c]

        top_chunks = retriever.score_chunks(
            embedding_model_name="models/embedding-001",
            indexed_chunks=indexed_chunks,
        )

        # We asked for top_k=2. Two chunks should pass threshold and be returned.
        assert len(top_chunks) == 2
        texts = {c.text for c in top_chunks}
        assert "high similarity A" in texts
        assert "medium similarity B" in texts
        assert "low similarity C" not in texts
