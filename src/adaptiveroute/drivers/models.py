from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal


DriverStatus = Literal["available", "on_route", "off_duty", "inactive"]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class DriverRecord:
    id: str
    name: str
    vehicle_id: str
    capacity: int
    status: DriverStatus = "available"
    region: str = "NYC"
    shift_start: str | None = None
    shift_end: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)
