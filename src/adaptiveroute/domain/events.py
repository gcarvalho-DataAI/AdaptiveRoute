from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class EventType(StrEnum):
    BLOCK_ARC = "BLOCK_ARC"
    CUSTOMER_UNAVAILABLE = "CUSTOMER_UNAVAILABLE"
    CUSTOMER_PRIORITY_CHANGE = "CUSTOMER_PRIORITY_CHANGE"


@dataclass(frozen=True)
class OperationalEvent:
    type: EventType
    payload: dict[str, Any]
    description: str


@dataclass(frozen=True)
class MutationResult:
    event: OperationalEvent
    diff: dict[str, Any]

