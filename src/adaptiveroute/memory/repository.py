from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any, Protocol

from adaptiveroute.memory.models import AgentRunRecord, ContextWindowRecord, ConversationRecord, MessageRecord


class ConversationRepository(Protocol):
    def create_conversation(self, conversation: ConversationRecord) -> ConversationRecord: ...
    def get_conversation(self, conversation_id: str) -> ConversationRecord | None: ...
    def list_conversations(self) -> list[ConversationRecord]: ...
    def delete_conversation(self, conversation_id: str) -> bool: ...
    def save_message(self, message: MessageRecord) -> MessageRecord: ...
    def list_messages(self, conversation_id: str) -> list[MessageRecord]: ...
    def save_context_window(self, context_window: ContextWindowRecord) -> ContextWindowRecord: ...
    def get_context_window(self, conversation_id: str) -> ContextWindowRecord | None: ...
    def save_agent_run(self, run: AgentRunRecord) -> AgentRunRecord: ...
    def list_agent_runs(self, conversation_id: str) -> list[AgentRunRecord]: ...


class InMemoryConversationRepository:
    def __init__(self):
        self._conversations: dict[str, ConversationRecord] = {}
        self._messages: dict[str, MessageRecord] = {}
        self._contexts: dict[str, ContextWindowRecord] = {}
        self._agent_runs: dict[str, AgentRunRecord] = {}

    def create_conversation(self, conversation: ConversationRecord) -> ConversationRecord:
        self._conversations[conversation.id] = conversation
        return conversation

    def get_conversation(self, conversation_id: str) -> ConversationRecord | None:
        return self._conversations.get(conversation_id)

    def list_conversations(self) -> list[ConversationRecord]:
        return sorted(self._conversations.values(), key=lambda item: item.updated_at, reverse=True)

    def delete_conversation(self, conversation_id: str) -> bool:
        deleted = self._conversations.pop(conversation_id, None) is not None
        self._messages = {
            message_id: message
            for message_id, message in self._messages.items()
            if message.conversation_id != conversation_id
        }
        self._contexts.pop(conversation_id, None)
        self._agent_runs = {
            run_id: run
            for run_id, run in self._agent_runs.items()
            if run.conversation_id != conversation_id
        }
        return deleted

    def save_message(self, message: MessageRecord) -> MessageRecord:
        self._messages[message.id] = message
        return message

    def list_messages(self, conversation_id: str) -> list[MessageRecord]:
        messages = [message for message in self._messages.values() if message.conversation_id == conversation_id]
        return sorted(messages, key=lambda item: item.created_at)

    def save_context_window(self, context_window: ContextWindowRecord) -> ContextWindowRecord:
        self._contexts[context_window.conversation_id] = context_window
        return context_window

    def get_context_window(self, conversation_id: str) -> ContextWindowRecord | None:
        return self._contexts.get(conversation_id)

    def save_agent_run(self, run: AgentRunRecord) -> AgentRunRecord:
        self._agent_runs[run.id] = run
        return run

    def list_agent_runs(self, conversation_id: str) -> list[AgentRunRecord]:
        runs = [run for run in self._agent_runs.values() if run.conversation_id == conversation_id]
        return sorted(runs, key=lambda item: item.created_at)


class MongoConversationRepository:
    def __init__(self, *, uri: str, database: str):
        from pymongo import ASCENDING, DESCENDING, MongoClient

        self._client = MongoClient(uri)
        self._db = self._client[database]
        self._conversations = self._db["conversations"]
        self._messages = self._db["messages"]
        self._contexts = self._db["context_windows"]
        self._agent_runs = self._db["agent_runs"]

        self._conversations.create_index([("updated_at", DESCENDING)])
        self._messages.create_index([("conversation_id", ASCENDING), ("created_at", ASCENDING)])
        self._contexts.create_index([("conversation_id", ASCENDING)], unique=True)
        self._agent_runs.create_index([("conversation_id", ASCENDING), ("created_at", ASCENDING)])

    def create_conversation(self, conversation: ConversationRecord) -> ConversationRecord:
        self._conversations.insert_one(_to_document(conversation))
        return conversation

    def get_conversation(self, conversation_id: str) -> ConversationRecord | None:
        document = self._conversations.find_one({"_id": conversation_id})
        return _conversation_from_document(document) if document else None

    def list_conversations(self) -> list[ConversationRecord]:
        return [_conversation_from_document(document) for document in self._conversations.find().sort("updated_at", -1)]

    def delete_conversation(self, conversation_id: str) -> bool:
        result = self._conversations.delete_one({"_id": conversation_id})
        self._messages.delete_many({"conversation_id": conversation_id})
        self._contexts.delete_many({"conversation_id": conversation_id})
        self._agent_runs.delete_many({"conversation_id": conversation_id})
        return result.deleted_count > 0

    def save_message(self, message: MessageRecord) -> MessageRecord:
        self._messages.insert_one(_to_document(message))
        self._conversations.update_one({"_id": message.conversation_id}, {"$set": {"updated_at": message.created_at}})
        return message

    def list_messages(self, conversation_id: str) -> list[MessageRecord]:
        return [
            _message_from_document(document)
            for document in self._messages.find({"conversation_id": conversation_id}).sort("created_at", 1)
        ]

    def save_context_window(self, context_window: ContextWindowRecord) -> ContextWindowRecord:
        self._contexts.replace_one(
            {"conversation_id": context_window.conversation_id},
            _to_document(context_window),
            upsert=True,
        )
        return context_window

    def get_context_window(self, conversation_id: str) -> ContextWindowRecord | None:
        document = self._contexts.find_one({"conversation_id": conversation_id})
        return _context_from_document(document) if document else None

    def save_agent_run(self, run: AgentRunRecord) -> AgentRunRecord:
        self._agent_runs.insert_one(_to_document(run))
        return run

    def list_agent_runs(self, conversation_id: str) -> list[AgentRunRecord]:
        return [
            _agent_run_from_document(document)
            for document in self._agent_runs.find({"conversation_id": conversation_id}).sort("created_at", 1)
        ]


def _to_document(record: Any) -> dict[str, Any]:
    document = asdict(record)
    document["_id"] = document.pop("id")
    return document


def _conversation_from_document(document: dict[str, Any]) -> ConversationRecord:
    return ConversationRecord(
        id=document["_id"],
        title=document["title"],
        created_at=_dt(document["created_at"]),
        updated_at=_dt(document["updated_at"]),
        metadata=document.get("metadata", {}),
    )


def _message_from_document(document: dict[str, Any]) -> MessageRecord:
    return MessageRecord(
        id=document["_id"],
        conversation_id=document["conversation_id"],
        role=document["role"],
        content=document["content"],
        created_at=_dt(document["created_at"]),
        metadata=document.get("metadata", {}),
    )


def _context_from_document(document: dict[str, Any]) -> ContextWindowRecord:
    return ContextWindowRecord(
        id=document["_id"],
        conversation_id=document["conversation_id"],
        summary=document.get("summary", ""),
        recent_message_ids=list(document.get("recent_message_ids", [])),
        facts=list(document.get("facts", [])),
        open_constraints=list(document.get("open_constraints", [])),
        last_event=document.get("last_event"),
        last_plan=document.get("last_plan"),
        updated_at=_dt(document["updated_at"]),
    )


def _agent_run_from_document(document: dict[str, Any]) -> AgentRunRecord:
    return AgentRunRecord(
        id=document["_id"],
        conversation_id=document["conversation_id"],
        input_message_id=document["input_message_id"],
        status=document["status"],
        trace=list(document.get("trace", [])),
        result=document.get("result", {}),
        created_at=_dt(document["created_at"]),
    )


def _dt(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
