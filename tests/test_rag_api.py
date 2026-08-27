from __future__ import annotations

from fastapi.testclient import TestClient

from adaptiveroute.api.app import create_app
from adaptiveroute.api.dependencies import clear_dependency_caches


def test_rag_api_ingests_lists_and_queries_documents(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_RAG_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_RAG_EMBEDDING_BACKEND", "hash")
    monkeypatch.setenv("ADAPTIVEROUTE_RAG_EMBEDDING_DIM", "64")
    clear_dependency_caches()

    doc = tmp_path / "model.md"
    doc.write_text("The LoRA routing policy proposes candidate routes and validation checks feasibility.", encoding="utf-8")
    client = TestClient(create_app())

    ingest_response = client.post("/v1/rag/ingest", json={"paths": [str(doc)]})
    documents_response = client.get("/v1/rag/documents")
    query_response = client.post("/v1/rag/query", json={"query": "routing policy validation", "limit": 1})

    assert ingest_response.status_code == 200
    assert ingest_response.json()["chunk_count"] == 1
    assert documents_response.status_code == 200
    assert documents_response.json()["chunk_count"] == 1
    assert query_response.status_code == 200
    assert query_response.json()["results"][0]["document"]["title"] == "model.md"
    clear_dependency_caches()
