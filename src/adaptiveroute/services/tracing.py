from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class TraceRecord:
    trace_id: str
    timestamp: str
    event: str
    payload: dict[str, Any]


class JsonlTraceLogger:
    def __init__(self, output_dir: str | Path = "outputs/traces"):
        self.output_dir = Path(output_dir)

    def write(self, event: str, payload: dict[str, Any], trace_id: str | None = None) -> TraceRecord:
        current_trace_id = trace_id or str(uuid4())
        record = TraceRecord(
            trace_id=current_trace_id,
            timestamp=datetime.now(UTC).isoformat(),
            event=event,
            payload=payload,
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"{current_trace_id}.jsonl"
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(trace_record_to_dict(record), ensure_ascii=False, sort_keys=True))
            file.write("\n")
        return record


class InMemoryTraceLogger:
    def __init__(self) -> None:
        self.records: list[TraceRecord] = []

    def write(self, event: str, payload: dict[str, Any], trace_id: str | None = None) -> TraceRecord:
        current_trace_id = trace_id or str(uuid4())
        record = TraceRecord(
            trace_id=current_trace_id,
            timestamp=datetime.now(UTC).isoformat(),
            event=event,
            payload=payload,
        )
        self.records.append(record)
        return record


def trace_record_to_dict(record: TraceRecord) -> dict[str, Any]:
    return {
        "trace_id": record.trace_id,
        "timestamp": record.timestamp,
        "event": record.event,
        "payload": record.payload,
    }

