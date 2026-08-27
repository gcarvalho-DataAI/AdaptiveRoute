from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

from adaptiveroute.rag.chunking import chunk_text, iter_supported_files, load_text_file
from adaptiveroute.rag.embeddings import EmbeddingClient
from adaptiveroute.rag.models import DocumentChunkRecord, DocumentRecord, now
from adaptiveroute.rag.repository import RagRepository


class RagService:
    def __init__(
        self,
        *,
        repository: RagRepository,
        embedding_client: EmbeddingClient,
        chunk_size: int = 1200,
        chunk_overlap: int = 160,
    ):
        self._repository = repository
        self._embedding_client = embedding_client
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def ingest_paths(self, paths: list[str | Path]) -> dict:
        files = iter_supported_files([Path(path) for path in paths])
        documents: list[dict] = []
        total_chunks = 0
        for file_path in files:
            result = self.ingest_file(file_path)
            documents.append(result)
            total_chunks += result["chunk_count"]
        return {"document_count": len(documents), "chunk_count": total_chunks, "documents": documents}

    def ingest_file(self, path: str | Path) -> dict:
        file_path = Path(path)
        text = load_text_file(file_path)
        chunks_text = chunk_text(text, chunk_size=self._chunk_size, overlap=self._chunk_overlap)
        document_id = _stable_id(f"document:{file_path.resolve()}")
        document = DocumentRecord(
            id=document_id,
            title=file_path.name,
            source_path=str(file_path),
            source_type=file_path.suffix.lower().lstrip(".") or "text",
            created_at=now(),
            metadata={"size_bytes": file_path.stat().st_size},
        )

        embeddings = self._embedding_client.embed(chunks_text)
        chunks = [
            DocumentChunkRecord(
                id=_stable_id(f"chunk:{document_id}:{idx}"),
                document_id=document_id,
                chunk_index=idx,
                content=content,
                embedding=embedding,
                created_at=now(),
                metadata={"source_path": str(file_path)},
            )
            for idx, (content, embedding) in enumerate(zip(chunks_text, embeddings))
        ]
        self._repository.upsert_document(document, chunks)
        return {"document": asdict(document), "chunk_count": len(chunks)}

    def list_documents(self) -> list[dict]:
        return [asdict(document) for document in self._repository.list_documents()]

    def query(self, query: str, *, limit: int = 5) -> dict:
        query_embedding = self._embedding_client.embed([query])[0]
        results = self._repository.search(query_embedding, limit=limit)
        return {
            "query": query,
            "results": [
                {
                    "score": result.score,
                    "document": asdict(result.document),
                    "chunk": {
                        "id": result.chunk.id,
                        "document_id": result.chunk.document_id,
                        "chunk_index": result.chunk.chunk_index,
                        "content": result.chunk.content,
                        "metadata": result.chunk.metadata,
                    },
                }
                for result in results
            ],
        }

    def count_chunks(self) -> int:
        return self._repository.count_chunks()


def _stable_id(value: str) -> str:
    return str(uuid5(NAMESPACE_URL, value))
