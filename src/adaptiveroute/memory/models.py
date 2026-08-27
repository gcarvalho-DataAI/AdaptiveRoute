from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal


MessageRole = Literal["user", "assistant", "system", "tool"]
AgentRunStatus = Literal["succeeded", "failed"]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class ConversationRecord:
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MessageRecord:
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextWindowRecord:
    id: str
    conversation_id: str
    summary: str
    recent_message_ids: list[str]
    facts: list[str]
    open_constraints: list[str]
    last_event: dict[str, Any] | None
    last_plan: dict[str, Any] | None
    updated_at: datetime


@dataclass(frozen=True)
class AgentRunRecord:
    id: str
    conversation_id: str
    input_message_id: str
    status: AgentRunStatus
    trace: list[dict[str, Any]]
    result: dict[str, Any]
    created_at: datetime
