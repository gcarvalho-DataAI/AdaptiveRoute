from __future__ import annotations

from uuid import uuid4

from adaptiveroute.memory.models import ContextWindowRecord, MessageRecord, utc_now


def build_updated_context_window(
    *,
    conversation_id: str,
    previous: ContextWindowRecord | None,
    messages: list[MessageRecord],
    agentic_result: dict,
    recent_message_limit: int,
    summary_max_chars: int,
) -> ContextWindowRecord:
    recent_messages = messages[-recent_message_limit:] if recent_message_limit > 0 else []
    summary_parts: list[str] = []
    if previous and previous.summary:
        summary_parts.append(previous.summary)

    new_event = None if agentic_result.get("source") == "context_window" else agentic_result.get("event")
    event = new_event or (previous.last_event if previous else None)
    comparison = agentic_result.get("comparison")
    final_validation = agentic_result.get("final_validation")
    new_final_plan = agentic_result.get("final_plan")
    final_plan = new_final_plan or (previous.last_plan if previous else None)

    if new_event:
        summary_parts.append(f"Latest event: {new_event}")
    if final_validation:
        summary_parts.append(f"Latest validation: {final_validation}")
    if comparison:
        delta = comparison.get("distance_delta")
        removed = comparison.get("removed_customers", [])
        summary_parts.append(f"Latest replanning impact: distance_delta={delta}, removed_customers={removed}")

    summary = "\n".join(part for part in summary_parts if part).strip()
    if summary_max_chars > 0 and len(summary) > summary_max_chars:
        summary = summary[-summary_max_chars:]

    facts = list(previous.facts) if previous else []
    open_constraints = list(previous.open_constraints) if previous else []
    if event:
        constraint = f"Active operational event: {event}"
        if constraint not in open_constraints:
            open_constraints.append(constraint)

    return ContextWindowRecord(
        id=previous.id if previous else str(uuid4()),
        conversation_id=conversation_id,
        summary=summary,
        recent_message_ids=[message.id for message in recent_messages],
        facts=facts,
        open_constraints=open_constraints[-20:],
        last_event=event if isinstance(event, dict) else None,
        last_plan=final_plan if isinstance(final_plan, dict) else None,
        updated_at=utc_now(),
    )
