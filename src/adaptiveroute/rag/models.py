from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from adaptiveroute.memory.models import utc_now


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    title: str
    source_path: str
    source_type: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentChunkRecord:
    id: str
    document_id: str
    chunk_index: int
    content: str
    embedding: list[float]
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RagSearchResult:
    chunk: DocumentChunkRecord
    document: DocumentRecord
    score: float


def now() -> datetime:
    return utc_now()
