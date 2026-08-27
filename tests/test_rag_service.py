from __future__ import annotations

from adaptiveroute.rag.chunking import chunk_text
from adaptiveroute.rag.embeddings import HashEmbeddingClient
from adaptiveroute.rag.repository import InMemoryRagRepository
from adaptiveroute.rag.service import RagService


def test_chunk_text_uses_overlap() -> None:
    chunks = chunk_text("alpha beta gamma delta epsilon zeta", chunk_size=18, overlap=5)

    assert len(chunks) > 1
    assert all(chunks)


def test_rag_service_ingests_and_queries_file(tmp_path) -> None:
    doc = tmp_path / "solver.md"
    doc.write_text("Pyomo and HiGHS solve the CVRP optimization model.", encoding="utf-8")
    service = RagService(
        repository=InMemoryRagRepository(),
        embedding_client=HashEmbeddingClient(dimension=64),
        chunk_size=200,
        chunk_overlap=20,
    )

    ingest = service.ingest_paths([doc])
    query = service.query("How is CVRP solved?", limit=1)

    assert ingest["document_count"] == 1
    assert ingest["chunk_count"] == 1
    assert query["results"][0]["document"]["title"] == "solver.md"
    assert "HiGHS" in query["results"][0]["chunk"]["content"]
