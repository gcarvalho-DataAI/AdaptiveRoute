from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal


OperationalRouteStatus = Literal["assigned", "in_progress", "completed", "cancelled"]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class OperationalRouteRecord:
    id: str
    driver_id: str
    scenario_id: str
    current_plan: dict[str, Any]
    status: OperationalRouteStatus = "assigned"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)
