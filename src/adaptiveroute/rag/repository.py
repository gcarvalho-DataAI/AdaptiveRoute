from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any, Protocol

from adaptiveroute.rag.models import DocumentChunkRecord, DocumentRecord, RagSearchResult


class RagRepository(Protocol):
    def upsert_document(self, document: DocumentRecord, chunks: list[DocumentChunkRecord]) -> DocumentRecord: ...
    def list_documents(self) -> list[DocumentRecord]: ...
    def search(self, embedding: list[float], *, limit: int = 5) -> list[RagSearchResult]: ...
    def count_chunks(self) -> int: ...


class InMemoryRagRepository:
    def __init__(self):
        self._documents: dict[str, DocumentRecord] = {}
        self._chunks: dict[str, DocumentChunkRecord] = {}

    def upsert_document(self, document: DocumentRecord, chunks: list[DocumentChunkRecord]) -> DocumentRecord:
        stale_document_ids = [doc.id for doc in self._documents.values() if doc.source_path == document.source_path]
        for document_id in stale_document_ids:
            self._documents.pop(document_id, None)
            for chunk_id, chunk in list(self._chunks.items()):
                if chunk.document_id == document_id:
                    self._chunks.pop(chunk_id, None)
        self._documents[document.id] = document
        for chunk in chunks:
            self._chunks[chunk.id] = chunk
        return document

    def list_documents(self) -> list[DocumentRecord]:
        return sorted(self._documents.values(), key=lambda document: document.source_path)

    def search(self, embedding: list[float], *, limit: int = 5) -> list[RagSearchResult]:
        scored: list[RagSearchResult] = []
        for chunk in self._chunks.values():
            document = self._documents.get(chunk.document_id)
            if document is None:
                continue
            scored.append(RagSearchResult(chunk=chunk, document=document, score=_cosine_similarity(embedding, chunk.embedding)))
        return sorted(scored, key=lambda result: result.score, reverse=True)[:limit]

    def count_chunks(self) -> int:
        return len(self._chunks)


class PgVectorRagRepository:
    def __init__(self, *, dsn: str, embedding_dim: int):
        if embedding_dim <= 0:
            raise ValueError("embedding_dim must be positive.")
        self._dsn = dsn
        self._embedding_dim = embedding_dim
        self._ensure_schema()

    def upsert_document(self, document: DocumentRecord, chunks: list[DocumentChunkRecord]) -> DocumentRecord:
        import psycopg

        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM rag_documents WHERE source_path = %s", (document.source_path,))
                cur.execute(
                    """
                    INSERT INTO rag_documents (id, title, source_path, source_type, created_at, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        document.id,
                        document.title,
                        document.source_path,
                        document.source_type,
                        document.created_at,
                        _json(document.metadata),
                    ),
                )
                for chunk in chunks:
                    cur.execute(
                        """
                        INSERT INTO rag_document_chunks
                          (id, document_id, chunk_index, content, embedding, created_at, metadata)
                        VALUES (%s, %s, %s, %s, %s::vector, %s, %s::jsonb)
                        """,
                        (
                            chunk.id,
                            chunk.document_id,
                            chunk.chunk_index,
                            chunk.content,
                            _vector_literal(chunk.embedding),
                            chunk.created_at,
                            _json(chunk.metadata),
                        ),
                    )
        return document

    def list_documents(self) -> list[DocumentRecord]:
        import psycopg

        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, source_path, source_type, created_at, metadata
                    FROM rag_documents
                    ORDER BY source_path
                    """
                )
                return [_document_from_row(row) for row in cur.fetchall()]

    def search(self, embedding: list[float], *, limit: int = 5) -> list[RagSearchResult]:
        import psycopg

        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      c.id, c.document_id, c.chunk_index, c.content, c.embedding::text, c.created_at, c.metadata,
                      d.id, d.title, d.source_path, d.source_type, d.created_at, d.metadata,
                      1 - (c.embedding <=> %s::vector) AS score
                    FROM rag_document_chunks c
                    JOIN rag_documents d ON d.id = c.document_id
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (_vector_literal(embedding), _vector_literal(embedding), limit),
                )
                return [_search_result_from_row(row) for row in cur.fetchall()]

    def count_chunks(self) -> int:
        import psycopg

        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM rag_document_chunks")
                return int(cur.fetchone()[0])

    def _ensure_schema(self) -> None:
        import psycopg

        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rag_documents (
                      id text PRIMARY KEY,
                      title text NOT NULL,
                      source_path text NOT NULL UNIQUE,
                      source_type text NOT NULL,
                      created_at timestamptz NOT NULL,
                      metadata jsonb NOT NULL DEFAULT '{}'::jsonb
                    )
                    """
                )
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS rag_document_chunks (
                      id text PRIMARY KEY,
                      document_id text NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
                      chunk_index integer NOT NULL,
                      content text NOT NULL,
                      embedding vector({self._embedding_dim}) NOT NULL,
                      created_at timestamptz NOT NULL,
                      metadata jsonb NOT NULL DEFAULT '{{}}'::jsonb,
                      UNIQUE(document_id, chunk_index)
                    )
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_rag_documents_source_path ON rag_documents(source_path)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_document_id ON rag_document_chunks(document_id)")


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    length = min(len(left), len(right))
    return sum(left[i] * right[i] for i in range(length))


def _json(value: dict[str, Any]) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in vector) + "]"


def _document_from_row(row: tuple) -> DocumentRecord:
    return DocumentRecord(
        id=row[0],
        title=row[1],
        source_path=row[2],
        source_type=row[3],
        created_at=_dt(row[4]),
        metadata=dict(row[5] or {}),
    )


def _chunk_from_row(row: tuple) -> DocumentChunkRecord:
    return DocumentChunkRecord(
        id=row[0],
        document_id=row[1],
        chunk_index=row[2],
        content=row[3],
        embedding=[],
        created_at=_dt(row[5]),
        metadata=dict(row[6] or {}),
    )


def _search_result_from_row(row: tuple) -> RagSearchResult:
    chunk = _chunk_from_row(row[:7])
    document = DocumentRecord(
        id=row[7],
        title=row[8],
        source_path=row[9],
        source_type=row[10],
        created_at=_dt(row[11]),
        metadata=dict(row[12] or {}),
    )
    return RagSearchResult(chunk=chunk, document=document, score=float(row[13]))


def _dt(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
