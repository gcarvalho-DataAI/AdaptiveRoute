from __future__ import annotations

from adaptiveroute.agentic import AgenticRoutingService
from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.memory.repository import InMemoryConversationRepository
from adaptiveroute.memory.service import ConversationService, _assistant_message_from_result
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def test_conversation_service_persists_messages_context_and_agent_run() -> None:
    repository = InMemoryConversationRepository()
    service = ConversationService(
        repository=repository,
        agentic_service=AgenticRoutingService(PyomoHighsEngine()),
        recent_message_limit=2,
        summary_max_chars=1000,
    )

    response = service.replan(message="Customer C3 cannot receive now.")

    conversation_id = response["conversation_id"]
    messages = repository.list_messages(conversation_id)
    runs = repository.list_agent_runs(conversation_id)
    context = repository.get_context_window(conversation_id)

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert len(runs) == 1
    assert runs[0].status == "succeeded"
    assert context is not None
    assert context.recent_message_ids == [messages[0].id, messages[1].id]
    assert context.last_event == {"type": "CUSTOMER_UNAVAILABLE", "payload": {"customer_id": "C3"}, "description": "Customer C3 cannot receive now."}
    assert context.last_plan is not None
    assert response["agentic_result"]["succeeded"] is True


def test_conversation_service_uses_existing_conversation() -> None:
    repository = InMemoryConversationRepository()
    service = ConversationService(
        repository=repository,
        agentic_service=AgenticRoutingService(PyomoHighsEngine()),
    )
    conversation = service.create_conversation(title="Existing")

    response = service.replan(conversation_id=conversation.id, message="There is an accident between C7 and C6.")

    assert response["conversation_id"] == conversation.id
    assert len(repository.list_messages(conversation.id)) == 2


def test_conversation_service_loads_previous_context_window_on_next_turn() -> None:
    repository = InMemoryConversationRepository()
    service = ConversationService(
        repository=repository,
        agentic_service=AgenticRoutingService(PyomoHighsEngine()),
    )

    first = service.replan(message="Customer C3 cannot receive now.")
    second = service.replan(
        conversation_id=first["conversation_id"],
        message="There is an accident between C7 and C6.",
    )

    assert first["context_window_before"] is None
    assert second["context_window_before"] is not None
    assert second["context_window_before"]["last_event"]["payload"] == {"customer_id": "C3"}


def test_replanning_assistant_explains_no_change_when_blocked_arc_is_not_used() -> None:
    message = "There is an accident blocking the segment between C2 and C3. Can you check if my route needs to be replanned?"
    result = AgenticRoutingService(PyomoHighsEngine()).run(build_demo_scenario(), message)

    answer = _assistant_message_from_result(result.response, message=message)

    assert "does not use that segment" in answer
    assert "no route sequence change is required" in answer
    assert "Distance impact: +0.00" in answer
    assert "Generated a validated replanning candidate" not in answer
