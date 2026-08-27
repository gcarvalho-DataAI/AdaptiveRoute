from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Callable
from uuid import uuid4

from adaptiveroute.agentic import AgenticRoutingService
from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.domain.models import RoutingScenario
from adaptiveroute.domain.serialization import scenario_from_dict
from adaptiveroute.llm.openai_compatible import OpenAICompatibleChatClient, OpenAICompatibleSettings
from adaptiveroute.memory.context import build_updated_context_window
from adaptiveroute.memory.models import AgentRunRecord, ContextWindowRecord, ConversationRecord, MessageRecord, utc_now
from adaptiveroute.memory.repository import ConversationRepository
from adaptiveroute.operations.models import OperationalRouteRecord
from adaptiveroute.operations.service import extract_route_id

RagQueryFn = Callable[[str, int], dict]


class ConversationService:
    def __init__(
        self,
        *,
        repository: ConversationRepository,
        agentic_service: AgenticRoutingService,
        scenario_resolver: Callable[[str], RoutingScenario | None] | None = None,
        scenario_saver: Callable[[RoutingScenario], RoutingScenario] | None = None,
        route_resolver: Callable[[str], OperationalRouteRecord | None] | None = None,
        route_plan_updater: Callable[..., OperationalRouteRecord | None] | None = None,
        rag_query: RagQueryFn | None = None,
        recent_message_limit: int = 8,
        summary_max_chars: int = 4000,
    ):
        self._repository = repository
        self._agentic_service = agentic_service
        self._scenario_resolver = scenario_resolver or _default_scenario_resolver
        self._scenario_saver = scenario_saver
        self._route_resolver = route_resolver
        self._route_plan_updater = route_plan_updater
        self._rag_query = rag_query
        self._recent_message_limit = recent_message_limit
        self._summary_max_chars = summary_max_chars

    def create_conversation(
        self,
        *,
        title: str | None = None,
        scenario_id: str = "demo-cvrp-8",
        metadata: dict | None = None,
    ) -> ConversationRecord:
        now = utc_now()
        conversation = ConversationRecord(
            id=str(uuid4()),
            title=title or "AdaptiveRoute conversation",
            created_at=now,
            updated_at=now,
            metadata={"scenario_id": scenario_id, **(metadata or {})},
        )
        return self._repository.create_conversation(conversation)

    def get_conversation(self, conversation_id: str) -> ConversationRecord | None:
        return self._repository.get_conversation(conversation_id)

    def list_conversations(self) -> list[ConversationRecord]:
        return self._repository.list_conversations()

    def delete_conversation(self, conversation_id: str) -> bool:
        return self._repository.delete_conversation(conversation_id)

    def list_messages(self, conversation_id: str) -> list[MessageRecord]:
        self._require_conversation(conversation_id)
        return self._repository.list_messages(conversation_id)

    def get_context_window(self, conversation_id: str) -> ContextWindowRecord | None:
        self._require_conversation(conversation_id)
        return self._repository.get_context_window(conversation_id)

    def list_agent_runs(self, conversation_id: str) -> list[AgentRunRecord]:
        self._require_conversation(conversation_id)
        return self._repository.list_agent_runs(conversation_id)

    def replan(
        self,
        *,
        message: str,
        conversation_id: str | None = None,
        scenario_id: str = "demo-cvrp-8",
    ) -> dict:
        existing_conversation = self._require_conversation(conversation_id) if conversation_id else None
        route_id = extract_route_id(message)
        if route_id is None and existing_conversation:
            route_id = existing_conversation.metadata.get("route_id")
        operational_route = self._resolve_operational_route(route_id) if route_id else None
        effective_scenario_id = operational_route.scenario_id if operational_route else scenario_id

        conversation = (
            existing_conversation
            if existing_conversation
            else self.create_conversation(
                title=_title_from_message(message),
                scenario_id=effective_scenario_id,
                metadata={"route_id": route_id, "driver_id": operational_route.driver_id}
                if operational_route and route_id
                else {},
            )
        )
        scenario = self._scenario_resolver(effective_scenario_id)
        if scenario is None:
            raise ValueError(f"Routing scenario not found: {effective_scenario_id}")

        user_message = self._repository.save_message(
            MessageRecord(
                id=str(uuid4()),
                conversation_id=conversation.id,
                role="user",
                content=message,
                created_at=utc_now(),
                metadata={
                    "scenario_id": effective_scenario_id,
                    **({"route_id": route_id} if route_id else {}),
                    **({"driver_id": operational_route.driver_id} if operational_route else {}),
                },
            )
        )

        context_before = self._repository.get_context_window(conversation.id)
        if operational_route and _is_route_question(message):
            result_response = _answer_route_question(
                message=message,
                route=operational_route,
                context_window=asdict(context_before) if context_before else None,
                rag_query=self._rag_query,
            )
            run_status = "succeeded" if result_response.get("succeeded") else "failed"
            run = self._repository.save_agent_run(
                AgentRunRecord(
                    id=str(uuid4()),
                    conversation_id=conversation.id,
                    input_message_id=user_message.id,
                    status=run_status,
                    trace=result_response.get("trace", []),
                    result=result_response,
                    created_at=utc_now(),
                )
            )
            assistant_content = result_response["message"]
            assistant_message = self._repository.save_message(
                MessageRecord(
                    id=str(uuid4()),
                    conversation_id=conversation.id,
                    role="assistant",
                    content=assistant_content,
                    created_at=utc_now(),
                    metadata={"agent_run_id": run.id, "status": run_status, "mode": "route_qa"},
                )
            )
            messages = self._repository.list_messages(conversation.id)
            context = build_updated_context_window(
                conversation_id=conversation.id,
                previous=self._repository.get_context_window(conversation.id),
                messages=messages,
                agentic_result=result_response,
                recent_message_limit=self._recent_message_limit,
                summary_max_chars=self._summary_max_chars,
            )
            self._repository.save_context_window(context)
            return {
                "conversation_id": conversation.id,
                "input_message_id": user_message.id,
                "assistant_message_id": assistant_message.id,
                "agent_run_id": run.id,
                "assistant_message": assistant_content,
                "agentic_result": result_response,
                "context_window_before": asdict(context_before) if context_before else None,
                "context_window": asdict(context),
                "operational_route": asdict(operational_route),
                "trace": result_response.get("trace", []),
            }

        result = self._agentic_service.run(
            scenario,
            message,
            context_window=asdict(context_before) if context_before else None,
        )
        status = "succeeded" if result.succeeded else "failed"
        updated_operational_route = operational_route
        if route_id and result.succeeded and result.response.get("final_plan") and self._route_plan_updater:
            updated_scenario_id = _save_replanning_scenario(
                result.response.get("replanning_scenario"),
                self._scenario_saver,
            )
            updated_operational_route = self._route_plan_updater(
                route_id,
                result.response["final_plan"],
                scenario_id=updated_scenario_id,
            ) or operational_route

        assistant_content = _assistant_message_from_result(
            result.response,
            message=message,
            context_window=asdict(context_before) if context_before else None,
            rag_query=self._rag_query,
        )

        run = self._repository.save_agent_run(
            AgentRunRecord(
                id=str(uuid4()),
                conversation_id=conversation.id,
                input_message_id=user_message.id,
                status=status,
                trace=result.response.get("trace", []),
                result=result.response,
                created_at=utc_now(),
            )
        )

        assistant_message = self._repository.save_message(
            MessageRecord(
                id=str(uuid4()),
                conversation_id=conversation.id,
                role="assistant",
                content=assistant_content,
                created_at=utc_now(),
                metadata={"agent_run_id": run.id, "status": status},
            )
        )

        messages = self._repository.list_messages(conversation.id)
        context = build_updated_context_window(
            conversation_id=conversation.id,
            previous=self._repository.get_context_window(conversation.id),
            messages=messages,
            agentic_result=result.response,
            recent_message_limit=self._recent_message_limit,
            summary_max_chars=self._summary_max_chars,
        )
        self._repository.save_context_window(context)

        return {
            "conversation_id": conversation.id,
            "input_message_id": user_message.id,
            "assistant_message_id": assistant_message.id,
            "agent_run_id": run.id,
            "assistant_message": assistant_content,
            "agentic_result": result.response,
            "context_window_before": asdict(context_before) if context_before else None,
            "context_window": asdict(context),
            "operational_route": asdict(updated_operational_route) if updated_operational_route else None,
            "trace": result.response.get("trace", []),
        }

    def append_message(self, *, conversation_id: str, role: str, content: str, metadata: dict | None = None) -> MessageRecord:
        self._require_conversation(conversation_id)
        if role not in {"user", "assistant", "system", "tool"}:
            raise ValueError("role must be one of: user, assistant, system, tool.")
        return self._repository.save_message(
            MessageRecord(
                id=str(uuid4()),
                conversation_id=conversation_id,
                role=role,  # type: ignore[arg-type]
                content=content,
                created_at=utc_now(),
                metadata=metadata or {},
            )
        )

    def _require_conversation(self, conversation_id: str) -> ConversationRecord:
        conversation = self._repository.get_conversation(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation not found: {conversation_id}")
        return conversation

    def _resolve_operational_route(self, route_id: str) -> OperationalRouteRecord:
        if self._route_resolver is None:
            raise ValueError(f"Operational route lookup is not configured: {route_id}")
        route = self._route_resolver(route_id)
        if route is None:
            raise ValueError(f"Operational route not found: {route_id}")
        return route


def _title_from_message(message: str) -> str:
    normalized = " ".join(message.strip().split())
    return normalized[:80] or "AdaptiveRoute conversation"


def _default_scenario_resolver(scenario_id: str) -> RoutingScenario | None:
    if scenario_id == "demo-cvrp-8":
        return build_demo_scenario()
    return None


def _save_replanning_scenario(
    payload: dict | None,
    scenario_saver: Callable[[RoutingScenario], RoutingScenario] | None,
) -> str | None:
    if not payload or scenario_saver is None:
        return None
    scenario = scenario_from_dict(payload)
    return scenario_saver(scenario).id


def _assistant_message_from_result(
    result: dict,
    *,
    message: str = "",
    context_window: dict | None = None,
    rag_query: RagQueryFn | None = None,
) -> str:
    if result.get("source") == "context_window":
        summary = result.get("context_summary") or "No additional replanning event was detected."
        return f"Using the current conversation context: {summary}"

    if not result.get("succeeded"):
        errors = result.get("errors") or ["The routing workflow failed."]
        return f"I could not produce a valid replanning result. Errors: {errors}"

    llm_answer = _compose_replanning_answer_with_llm(
        result=result,
        message=message,
        context_window=context_window,
        rag_query=rag_query,
    )
    if llm_answer:
        return llm_answer

    comparison = result.get("comparison") or {}
    final_plan = result.get("final_plan") or {}
    event_impact = _event_impact_summary_for_prompt(result)
    return _compose_grounded_replanning_fallback(
        event=result.get("event") or {},
        comparison=comparison,
        final_plan=final_plan,
        event_impact=event_impact,
    )


def _compose_grounded_replanning_fallback(
    *,
    event: dict,
    comparison: dict,
    final_plan: dict,
    event_impact: dict,
) -> str:
    event_type = event.get("type") or "UNKNOWN_EVENT"
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    distance_delta = comparison.get("distance_delta")
    removed_customers = comparison.get("removed_customers", []) or []
    route_count = len(final_plan.get("routes", [])) if isinstance(final_plan, dict) else 0
    total_distance = final_plan.get("total_distance") if isinstance(final_plan, dict) else None
    route_lines = _format_plan_routes(final_plan)

    lines = []
    if event_type == "BLOCK_ARC":
        from_node = payload.get("from_node", "unknown")
        to_node = payload.get("to_node", "unknown")
        lines.append(f"I checked the reported blockage between {from_node} and {to_node}.")
        if event_impact.get("blocked_arc_used_in_base_plan") is False and event_impact.get("blocked_arc_used_in_final_plan") is False:
            lines.append("The current modeled route does not use that segment, so no route sequence change is required.")
        elif event_impact.get("blocked_arc_used_in_final_plan") is False:
            lines.append("The blocked segment is avoided in the validated candidate.")
        else:
            lines.append("The blocked segment still appears in the candidate route sequence and should be reviewed before dispatch.")
    elif event_type == "CUSTOMER_UNAVAILABLE":
        customer_id = payload.get("customer_id", "the customer")
        lines.append(f"I checked the reported unavailability for {customer_id}.")
        if customer_id in removed_customers:
            lines.append(f"{customer_id} is deferred in the validated candidate.")
        else:
            lines.append(f"{customer_id} remains served in the validated candidate.")
    else:
        lines.append(f"I interpreted the event as {event_type} and validated the resulting route candidate.")

    notes = event_impact.get("event_node_notes") or []
    lines.extend(str(note) for note in notes)

    lines.append(
        "Validation passed. "
        f"The resulting plan has {route_count} route(s)"
        + (f" and total distance {float(total_distance):.2f}." if isinstance(total_distance, int | float) else ".")
    )
    lines.append(f"Distance impact: {distance_delta:+.2f}." if isinstance(distance_delta, int | float) else f"Distance impact: {distance_delta}.")
    if removed_customers:
        lines.append(f"Deferred/not served customers in this candidate: {', '.join(map(str, removed_customers))}.")
    else:
        lines.append("No customers were removed or deferred by this candidate.")

    if route_lines:
        lines.append("Validated sequence:\n" + "\n".join(route_lines))

    if event_type == "BLOCK_ARC" and event_impact.get("blocked_arc_used_in_base_plan") is False:
        lines.append("Recommended action: continue with the validated route and monitor nearby traffic conditions; replan again only if adjacent segments become unavailable.")
    elif removed_customers:
        lines.append("Recommended action: confirm the deferred customer handling policy before dispatching the updated route.")
    else:
        lines.append("Recommended action: proceed with the validated route candidate.")

    return "\n\n".join(lines)


def _format_plan_routes(plan: dict) -> list[str]:
    if not isinstance(plan, dict):
        return []
    routes = plan.get("routes") if isinstance(plan.get("routes"), list) else []
    lines = []
    for route in routes:
        if not isinstance(route, dict):
            continue
        vehicle_id = route.get("vehicle_id") or "vehicle"
        stops = route.get("stops") if isinstance(route.get("stops"), list) else []
        distance = route.get("distance")
        load = route.get("load")
        suffix_parts = []
        if isinstance(load, int | float):
            suffix_parts.append(f"load {load:g}")
        if isinstance(distance, int | float):
            suffix_parts.append(f"distance {distance:.2f}")
        suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
        lines.append(f"- {vehicle_id}: {' → '.join(map(str, stops))}{suffix}")
    return lines


def _compose_replanning_answer_with_llm(
    *,
    result: dict,
    message: str,
    context_window: dict | None,
    rag_query: RagQueryFn | None,
) -> str | None:
    if not _replanning_response_uses_llm():
        return None

    trace = result.setdefault("trace", [])
    rag_context = _retrieve_replanning_response_context(
        message=message,
        result=result,
        rag_query=rag_query,
        trace=trace,
    )
    try:
        client = OpenAICompatibleChatClient(OpenAICompatibleSettings.from_env(prefix="ADAPTIVEROUTE_ORCHESTRATOR"))
        response = client.chat(
            system=_REPLANNING_RESPONSE_SYSTEM_PROMPT,
            user=json.dumps(
                {
                    "user_message": message,
                    "validated_workflow_result": _compact_replanning_result_for_prompt(result),
                    "conversation_context": context_window or {},
                    "retrieved_context": rag_context["prompt_context"],
                    "response_contract": {
                        "format": "plain English, concise paragraphs or bullets",
                        "must_include": [
                            "what event was interpreted",
                            "whether the candidate is validated",
                            "what changed in the plan",
                            "distance impact",
                            "customers removed or deferred",
                            "any event_node_notes entries verbatim in operational language",
                            "recommended operational next action",
                        ],
                        "must_not": [
                            "invent live ETA, GPS, traffic or customer confirmation",
                            "override validation or solver facts",
                            "claim all customers are served if removed_customers is non-empty",
                        ],
                    },
                },
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            ),
            temperature=0.1,
        )
        trace.append(
            {
                "node": "replanning_response_model",
                "payload": {"model": response.model, "used_fallback": False},
            }
        )
        return response.content.strip()
    except Exception as exc:
        trace.append({"node": "replanning_response_model", "payload": {"used_fallback": True, "error": str(exc)}})
        return None


def _replanning_response_uses_llm() -> bool:
    explicit = os.getenv("ADAPTIVEROUTE_REPLANNING_RESPONSE_BACKEND")
    if explicit is not None:
        return explicit.strip().lower() in {"api", "llm", "openai-compatible", "openai_compatible", "true", "1", "yes"}
    backend = os.getenv("ADAPTIVEROUTE_ORCHESTRATOR_BACKEND", "rules").strip().lower()
    return backend in {"api", "openai-compatible", "openai_compatible"}


_REPLANNING_RESPONSE_SYSTEM_PROMPT = """You are AdaptiveRoute's operational replanning response agent.

You do not create routes. The solver/routing policy and deterministic validator already produced the plan.
Your job is to explain the validated result to an operations user using only supplied facts.

Grounding rules:
- Treat validated_workflow_result as authoritative.
- Do not invent distances, stops, ETAs, traffic telemetry, customer contact status, or driver behavior.
- If validation passed, say the candidate passed validation.
- If removed_customers is non-empty, explicitly say those customers are deferred/not served by this candidate.
- If scenario_summary.inactive_or_deferred_customers contains a customer mentioned in the new event, explain that it was already deferred before this what-if and distinguish that from new removals.
- If the blocked arc is not used by the current/final stop sequence, say no route sequence change is needed under the modeled plan.
- Use event_impact_summary.event_node_status to identify whether event nodes are active, inactive/deferred, depot, or unknown.
- If event_impact_summary.event_node_notes is non-empty, explicitly include those notes in the answer. This is mandatory.
- Use event_impact_summary.blocked_arc_used_in_base_plan and blocked_arc_used_in_final_plan to explain whether the blocked segment actually affects the route sequence.
- If the blocked arc was not used and distance_delta is zero, explicitly say no route sequence change is required under the modeled plan.
- If distance_delta is negative, explain it is usually because stops were removed/deferred or the feasible route became shorter; do not present that as a pure improvement without caveat.
- If the user asked "what if", answer as a scenario assessment, not as a command already executed in the real world.
- Mention blocked arcs and customer unavailability only when present in the event/comparison.
- Never answer with only a generic sentence such as "Generated a validated replanning candidate"; explain the operational reason and next action.
- Use concise operational English.
"""


def _retrieve_replanning_response_context(
    *,
    message: str,
    result: dict,
    rag_query: RagQueryFn | None,
    trace: list[dict],
) -> dict:
    if rag_query is None:
        trace.append({"node": "replanning_response_rag", "payload": {"enabled": False}})
        return {"prompt_context": "No RAG context provider is configured.", "results": []}

    event = result.get("event") or {}
    comparison = result.get("comparison") or {}
    query = (
        f"replanning what-if operational response: {message}\n"
        f"event type: {event.get('type')}\n"
        f"distance_delta: {comparison.get('distance_delta')}\n"
        f"removed_customers: {comparison.get('removed_customers')}\n"
        "validated route replanning explanation deferred customers blocked arcs distance impact"
    )
    try:
        payload = rag_query(query, 4)
        raw_results = payload.get("results", []) if isinstance(payload, dict) else []
        results = _compact_rag_results(raw_results)
        trace.append(
            {
                "node": "replanning_response_rag",
                "payload": {
                    "enabled": True,
                    "query": query,
                    "result_count": len(results),
                    "sources": [result.get("source_path") for result in results],
                },
            }
        )
        return {"prompt_context": _format_rag_prompt_context(results), "results": results}
    except Exception as exc:
        trace.append({"node": "replanning_response_rag", "payload": {"enabled": True, "error": str(exc)}})
        return {"prompt_context": f"RAG retrieval failed: {exc}", "results": []}


def _compact_replanning_result_for_prompt(result: dict) -> dict:
    return {
        "succeeded": result.get("succeeded"),
        "source": result.get("source"),
        "errors": result.get("errors"),
        "event": result.get("event"),
        "final_validation": result.get("final_validation"),
        "comparison": result.get("comparison"),
        "final_plan": result.get("final_plan"),
        "scenario_summary": _compact_replanning_scenario_for_prompt(result.get("replanning_scenario")),
        "event_impact_summary": _event_impact_summary_for_prompt(result),
        "candidate_source": result.get("candidate", {}).get("source") if isinstance(result.get("candidate"), dict) else None,
    }


def _compact_replanning_scenario_for_prompt(scenario: dict | None) -> dict | None:
    if not isinstance(scenario, dict):
        return None
    customers = scenario.get("customers") if isinstance(scenario.get("customers"), list) else []
    return {
        "id": scenario.get("id"),
        "active_customers": [customer.get("id") for customer in customers if customer.get("active") and customer.get("required")],
        "inactive_or_deferred_customers": [
            customer.get("id") for customer in customers if not (customer.get("active") and customer.get("required"))
        ],
        "blocked_arcs": scenario.get("blocked_arcs", []),
    }


def _event_impact_summary_for_prompt(result: dict) -> dict:
    event = result.get("event") if isinstance(result.get("event"), dict) else {}
    event_payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    scenario = result.get("replanning_scenario") if isinstance(result.get("replanning_scenario"), dict) else {}
    customers = scenario.get("customers") if isinstance(scenario.get("customers"), list) else []
    customer_status = {
        customer.get("id"): "active_customer" if customer.get("active") and customer.get("required") else "inactive_or_deferred_customer"
        for customer in customers
        if customer.get("id")
    }
    depot_id = scenario.get("depot", {}).get("id") if isinstance(scenario.get("depot"), dict) else None

    event_nodes = []
    if event.get("type") == "BLOCK_ARC":
        event_nodes = [event_payload.get("from_node"), event_payload.get("to_node")]
    elif event_payload.get("customer_id"):
        event_nodes = [event_payload.get("customer_id")]

    node_status = {}
    for node in event_nodes:
        if not node:
            continue
        if node == depot_id:
            node_status[node] = "depot"
        else:
            node_status[node] = customer_status.get(node, "not_found_in_scenario")

    blocked_arc = None
    arc_used_before = None
    arc_used_after = None
    if event.get("type") == "BLOCK_ARC" and event_payload.get("from_node") and event_payload.get("to_node"):
        blocked_arc = [event_payload["from_node"], event_payload["to_node"]]
        base_edges = _plan_edges(result.get("base_plan"))
        final_edges = _plan_edges(result.get("final_plan"))
        forward = (event_payload["from_node"], event_payload["to_node"])
        backward = (event_payload["to_node"], event_payload["from_node"])
        arc_used_before = forward in base_edges or backward in base_edges
        arc_used_after = forward in final_edges or backward in final_edges

    return {
        "event_node_status": node_status,
        "event_node_notes": _event_node_notes(node_status),
        "blocked_arc": blocked_arc,
        "blocked_arc_used_in_base_plan": arc_used_before,
        "blocked_arc_used_in_final_plan": arc_used_after,
    }


def _event_node_notes(node_status: dict[str, str]) -> list[str]:
    notes = []
    for node, status in sorted(node_status.items()):
        if status == "inactive_or_deferred_customer":
            notes.append(f"{node} is a known customer but is already inactive/deferred in the current scenario.")
        elif status == "not_found_in_scenario":
            notes.append(f"{node} is not present in the current scenario facts.")
    return notes


def _plan_edges(plan: dict | None) -> set[tuple[str, str]]:
    if not isinstance(plan, dict):
        return set()
    routes = plan.get("routes") if isinstance(plan.get("routes"), list) else []
    edges = set()
    for route in routes:
        stops = route.get("stops") if isinstance(route, dict) and isinstance(route.get("stops"), list) else []
        edges.update((str(origin), str(destination)) for origin, destination in zip(stops, stops[1:]))
    return edges


def _is_route_question(message: str) -> bool:
    text = message.strip().lower()
    if not text:
        return False
    replanning_markers = (
        "replan",
        "reroute",
        "blocked",
        "block",
        "accident",
        "closed",
        "avoid",
        "unavailable",
        "cannot receive",
        "can't receive",
        "priority",
        "urgent",
        "refaça",
        "refazer",
        "bloqueio",
        "bloqueada",
        "acidente",
        "evitar",
        "indisponível",
        "urgente",
    )
    if any(marker in text for marker in replanning_markers):
        return False
    question_markers = (
        "?",
        "what",
        "which",
        "who",
        "how",
        "tell me",
        "summarize",
        "explain",
        "show",
        "distance",
        "stops",
        "stop",
        "load",
        "capacity",
        "feasible",
        "status",
        "route",
        "pergunta",
        "qual",
        "quais",
        "quanto",
        "explique",
        "resuma",
        "mostre",
        "paradas",
        "capacidade",
        "distância",
        "distancia",
    )
    return any(marker in text for marker in question_markers)


def _answer_route_question(
    *,
    message: str,
    route: OperationalRouteRecord,
    context_window: dict | None,
    rag_query: RagQueryFn | None = None,
) -> dict:
    facts = _route_facts(route)
    trace = [
        {"node": "route_lookup", "payload": {"route_id": route.id, "driver_id": route.driver_id, "scenario_id": route.scenario_id}},
        {"node": "route_fact_builder", "payload": facts},
    ]
    rag_context = _retrieve_route_qa_context(message=message, facts=facts, rag_query=rag_query, trace=trace)
    fallback_answer = _deterministic_route_answer(facts, message)
    require_llm = _route_qa_requires_llm()
    try:
        client = OpenAICompatibleChatClient(OpenAICompatibleSettings.from_env(prefix="ADAPTIVEROUTE_ORCHESTRATOR"))
        response = client.chat(
            system=(
                "You are AdaptiveRoute's route operations assistant. "
                "Use a grounded, source-prioritized answering strategy. "
                "Priority 1: Route facts JSON is authoritative for route state, stops, driver assignment, capacity, load and distance. "
                "Priority 2: Retrieved RAG context explains domain semantics and operational policies. "
                "Priority 3: Conversation context preserves continuity only; it must not override route facts. "
                "If the facts do not contain something, say it is not available. "
                "Do not invent stops, distances, driver assignments or optimization status. "
                "When total_distance is available, always include the numeric value. "
                "Do not infer distance units; if distance_unit is not_available, write '<total_distance> route-distance units'. "
                "Answer only the user's question and avoid adding unrelated operational status fields. "
                "The depot stop is not a delivery stop; when asked for the first delivery, use first_delivery_stop. "
                "Keep answers concise, operational, and explicit about feasibility, next stop, blocked arcs, load/capacity, or route status when asked."
            ),
            user=(
                "User question:\n"
                f"{message}\n\n"
                "Route facts JSON:\n"
                f"{json.dumps(facts, ensure_ascii=False, sort_keys=True)}\n\n"
                "Retrieved RAG context:\n"
                f"{rag_context['prompt_context']}\n\n"
                "Conversation context JSON:\n"
                f"{json.dumps(context_window or {}, default=str, ensure_ascii=False, sort_keys=True)}"
            ),
            temperature=0.1,
        )
        answer = response.content.strip()
        source = f"route_qa:{response.model}"
        trace.append({"node": "route_qa_model", "payload": {"model": response.model, "used_fallback": False}})
    except Exception as exc:
        trace.append({"node": "route_qa_model", "payload": {"used_fallback": not require_llm, "error": str(exc)}})
        if require_llm:
            error_message = (
                "Route Q&A requires the configured OpenAI-compatible LLM, but the model request failed. "
                f"Error: {exc}"
            )
            return {
                "succeeded": False,
                "source": "route_qa:llm_error",
                "errors": [str(exc)],
                "mode": "route_qa",
                "answer": error_message,
                "message": error_message,
                "route_id": route.id,
                "driver_id": route.driver_id,
                "scenario_id": route.scenario_id,
                "route_facts": facts,
                "rag_context": rag_context["results"],
                "final_plan": route.current_plan,
                "final_validation": None,
                "comparison": None,
                "event": None,
                "trace": trace,
            }
        answer = fallback_answer
        source = "route_qa:deterministic_fallback"

    return {
        "succeeded": True,
        "source": source,
        "errors": [],
        "mode": "route_qa",
        "answer": answer,
        "message": answer,
        "route_id": route.id,
        "driver_id": route.driver_id,
        "scenario_id": route.scenario_id,
        "route_facts": facts,
        "rag_context": rag_context["results"],
        "final_plan": route.current_plan,
        "final_validation": None,
        "comparison": None,
        "event": None,
        "trace": trace,
    }


def _route_qa_requires_llm() -> bool:
    explicit = os.getenv("ADAPTIVEROUTE_ROUTE_QA_REQUIRE_LLM")
    if explicit is not None:
        return explicit.strip().lower() in {"1", "true", "yes", "on"}
    backend = os.getenv("ADAPTIVEROUTE_ORCHESTRATOR_BACKEND", "rules").strip().lower()
    return backend in {"api", "openai-compatible", "openai_compatible"}


def _retrieve_route_qa_context(
    *,
    message: str,
    facts: dict,
    rag_query: RagQueryFn | None,
    trace: list[dict],
) -> dict:
    if rag_query is None:
        trace.append({"node": "route_qa_rag", "payload": {"enabled": False}})
        return {"prompt_context": "No RAG context provider is configured.", "results": []}

    query = (
        f"route question: {message}\n"
        f"route status: {facts.get('status')}\n"
        f"driver removed: {facts.get('driver_removed')}\n"
        f"load capacity feasibility first delivery depot route facts operational policy"
    )
    try:
        payload = rag_query(query, 4)
        raw_results = payload.get("results", []) if isinstance(payload, dict) else []
        results = _compact_rag_results(raw_results)
        trace.append(
            {
                "node": "route_qa_rag",
                "payload": {
                    "enabled": True,
                    "query": query,
                    "result_count": len(results),
                    "sources": [result.get("source_path") for result in results],
                },
            }
        )
        return {"prompt_context": _format_rag_prompt_context(results), "results": results}
    except Exception as exc:
        trace.append({"node": "route_qa_rag", "payload": {"enabled": True, "error": str(exc)}})
        return {"prompt_context": f"RAG retrieval failed: {exc}", "results": []}


def _compact_rag_results(raw_results: list) -> list[dict]:
    compacted = []
    for index, item in enumerate(raw_results[:4], 1):
        if not isinstance(item, dict):
            continue
        document = item.get("document") if isinstance(item.get("document"), dict) else {}
        chunk = item.get("chunk") if isinstance(item.get("chunk"), dict) else {}
        content = str(chunk.get("content") or "").strip()
        if not content:
            continue
        compacted.append(
            {
                "rank": index,
                "score": item.get("score"),
                "title": document.get("title"),
                "source_path": document.get("source_path") or chunk.get("metadata", {}).get("source_path"),
                "chunk_index": chunk.get("chunk_index"),
                "content": content[:1400],
            }
        )
    return compacted


def _format_rag_prompt_context(results: list[dict]) -> str:
    if not results:
        return "No relevant RAG snippets were retrieved. Answer from route facts only."
    snippets = []
    for result in results:
        snippets.append(
            "[{rank}] source={source} score={score}\n{content}".format(
                rank=result.get("rank"),
                source=result.get("source_path") or result.get("title") or "unknown",
                score=result.get("score"),
                content=result.get("content"),
            )
        )
    return "\n\n".join(snippets)


def _route_facts(route: OperationalRouteRecord) -> dict:
    plan = route.current_plan or {}
    route_segments = []
    total_load = 0
    total_distance = plan.get("total_distance") if isinstance(plan, dict) else None
    depot_stop = None
    first_delivery_stop = None
    final_depot_stop = None
    for segment in (plan.get("routes") if isinstance(plan, dict) else []) or []:
        if not isinstance(segment, dict):
            continue
        total_load += int(segment.get("load") or 0)
        stops = segment.get("stops", [])
        if isinstance(stops, list) and stops:
            depot_stop = depot_stop or stops[0]
            final_depot_stop = stops[-1]
            if first_delivery_stop is None and len(stops) > 2:
                first_delivery_stop = stops[1]
        route_segments.append(
            {
                "vehicle_id": segment.get("vehicle_id"),
                "stops": stops,
                "depot_stop": stops[0] if isinstance(stops, list) and stops else None,
                "first_delivery_stop": stops[1] if isinstance(stops, list) and len(stops) > 2 else None,
                "final_depot_stop": stops[-1] if isinstance(stops, list) and stops else None,
                "load": segment.get("load"),
                "distance": segment.get("distance"),
                "stop_count": max(len(stops) - 2, 0) if isinstance(stops, list) else 0,
            }
        )
    driver_snapshot = route.metadata.get("driver") or route.metadata.get("removed_driver") or {}
    capacity = driver_snapshot.get("capacity")
    return {
        "route_id": route.id,
        "driver_id": route.driver_id,
        "driver_removed": bool(route.metadata.get("driver_removed")) or str(route.driver_id).startswith("removed:"),
        "driver_name": driver_snapshot.get("name"),
        "vehicle_id": route.metadata.get("solver_vehicle_id") or driver_snapshot.get("vehicle_id"),
        "vehicle_capacity": capacity,
        "scenario_id": route.scenario_id,
        "status": route.status,
        "total_distance": total_distance,
        "distance_unit": route.metadata.get("distance_unit") or "not_available",
        "total_load": total_load,
        "capacity_slack": (capacity - total_load) if isinstance(capacity, int | float) else None,
        "depot_stop": depot_stop,
        "first_delivery_stop": first_delivery_stop,
        "final_depot_stop": final_depot_stop,
        "blocked_arcs": route.metadata.get("blocked_arcs", "not_available"),
        "known_operational_issues": route.metadata.get("known_operational_issues", "not_available"),
        "segments": route_segments,
    }


def _deterministic_route_answer(facts: dict, question: str = "") -> str:
    segments = facts.get("segments") or []
    lowered = question.lower()
    stop_sequences = [
        f"{segment.get('vehicle_id')}: {' → '.join(segment.get('stops') or [])} "
        f"(load {segment.get('load')}, distance {segment.get('distance')})"
        for segment in segments
    ]
    removed_note = " The assigned driver was removed, so this route is currently historical/unassigned." if facts.get("driver_removed") else ""
    capacity = facts.get("vehicle_capacity")
    load = facts.get("total_load")
    slack = facts.get("capacity_slack")
    capacity_text = (
        f" Total load is {load} against capacity {capacity}, leaving slack {slack}."
        if capacity is not None
        else f" Total load is {load}; vehicle capacity is not available in the route metadata."
    )
    first_segment = segments[0] if segments else {}
    stops = first_segment.get("stops") if isinstance(first_segment, dict) else []
    first_delivery = stops[1] if isinstance(stops, list) and len(stops) > 2 else None

    if any(marker in lowered for marker in ("summarize", "summary", "resuma", "resumo")):
        return (
            f"Route {facts.get('route_id')} is assigned to {facts.get('driver_id')} "
            f"on scenario {facts.get('scenario_id')} with status {facts.get('status')}.{removed_note} "
            f"Total distance is {facts.get('total_distance')}.{capacity_text} "
            f"Stops: {' | '.join(stop_sequences) if stop_sequences else 'no stops available'}."
        )

    if any(marker in lowered for marker in ("feasible", "slack", "capacidade", "folga")) or (
        "capacity" in lowered and any(marker in lowered for marker in ("standpoint", "how much", "available"))
    ):
        if capacity is None:
            return (
                f"Route {facts.get('route_id')} has total load {load}, but vehicle capacity is not available "
                "in the route metadata, so I cannot confirm capacity feasibility from stored facts."
            )
        status = "feasible" if slack is not None and slack >= 0 else "not feasible"
        return (
            f"Route {facts.get('route_id')} is {status} from a capacity standpoint: "
            f"load {load} / capacity {capacity}, slack {slack}."
        )

    if any(marker in lowered for marker in ("first", "before starting", "primeira", "iniciar")):
        if not first_delivery:
            return f"Route {facts.get('route_id')} does not have a delivery stop sequence available."
        return (
            f"The first delivery stop after leaving the depot is {first_delivery}. "
            f"Before starting, verify vehicle {facts.get('vehicle_id')}, assigned driver {facts.get('driver_id')}, "
            f"load {load} against capacity {capacity}, and the full stop sequence: "
            f"{' | '.join(stop_sequences) if stop_sequences else 'not available'}."
        )

    return (
        f"Route {facts.get('route_id')} is assigned to {facts.get('driver_id')} "
        f"on scenario {facts.get('scenario_id')} with status {facts.get('status')}.{removed_note} "
        f"Total distance is {facts.get('total_distance')}.{capacity_text} "
        f"Stops: {' | '.join(stop_sequences) if stop_sequences else 'no stops available'}."
    )
