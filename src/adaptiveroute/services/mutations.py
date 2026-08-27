from __future__ import annotations

import random
from dataclasses import replace

from adaptiveroute.domain.events import EventType, MutationResult, OperationalEvent
from adaptiveroute.domain.models import RoutingPlan, RoutingScenario, VehicleRoute


def apply_event(scenario: RoutingScenario, event: OperationalEvent) -> tuple[RoutingScenario, MutationResult]:
    if event.type == EventType.BLOCK_ARC:
        return _apply_block_arc(scenario, event)
    if event.type == EventType.CUSTOMER_UNAVAILABLE:
        return _apply_customer_unavailable(scenario, event)
    if event.type == EventType.CUSTOMER_PRIORITY_CHANGE:
        return _apply_customer_priority_change(scenario, event)
    raise ValueError(f"Unsupported event type: {event.type}")


def _apply_block_arc(scenario: RoutingScenario, event: OperationalEvent) -> tuple[RoutingScenario, MutationResult]:
    from_node = str(event.payload["from_node"])
    to_node = str(event.payload["to_node"])
    bidirectional = bool(event.payload.get("bidirectional", True))
    blocked = set(scenario.blocked_arcs)
    blocked.add((from_node, to_node))
    if bidirectional:
        blocked.add((to_node, from_node))
    mutated = replace(scenario, id=f"{scenario.id}-block-{from_node}-{to_node}", blocked_arcs=frozenset(blocked))
    diff = {
        "blocked_arcs_added": [{"from": from_node, "to": to_node}],
        "bidirectional": bidirectional,
    }
    return mutated, MutationResult(event=event, diff=diff)


def _apply_customer_unavailable(scenario: RoutingScenario, event: OperationalEvent) -> tuple[RoutingScenario, MutationResult]:
    customer_id = str(event.payload["customer_id"])
    customers = tuple(
        replace(customer, active=False, required=False) if customer.id == customer_id else customer
        for customer in scenario.customers
    )
    mutated = replace(scenario, id=f"{scenario.id}-unavailable-{customer_id}", customers=customers)
    diff = {"customer_unavailable": customer_id}
    return mutated, MutationResult(event=event, diff=diff)


def _apply_customer_priority_change(scenario: RoutingScenario, event: OperationalEvent) -> tuple[RoutingScenario, MutationResult]:
    customer_id = str(event.payload["customer_id"])
    priority = int(event.payload.get("priority", 3))
    customers = tuple(
        replace(customer, priority=priority) if customer.id == customer_id else customer for customer in scenario.customers
    )
    mutated = replace(scenario, id=f"{scenario.id}-priority-{customer_id}", customers=customers)
    diff = {"customer_priority_changed": customer_id, "priority": priority}
    return mutated, MutationResult(event=event, diff=diff)


def generate_training_event(
    scenario: RoutingScenario,
    base_plan: RoutingPlan,
    *,
    seed: int,
    event_types: tuple[EventType, ...] | None = None,
) -> OperationalEvent:
    rng = random.Random(seed)
    candidates = event_types or (EventType.BLOCK_ARC, EventType.CUSTOMER_UNAVAILABLE)
    event_type = rng.choice(candidates)
    if event_type == EventType.CUSTOMER_UNAVAILABLE:
        customer = rng.choice(scenario.active_customers)
        return OperationalEvent(
            type=EventType.CUSTOMER_UNAVAILABLE,
            payload={"customer_id": customer.id},
            description=f"Customer {customer.id} is unavailable and cannot receive a delivery on this run.",
        )

    candidate_edges = _non_depot_edges(base_plan)
    if not candidate_edges:
        route = rng.choice(base_plan.routes)
        stops = list(route.stops)
        candidate_edges = list(zip(stops, stops[1:]))
    from_node, to_node = rng.choice(candidate_edges)
    return OperationalEvent(
        type=EventType.BLOCK_ARC,
        payload={"from_node": from_node, "to_node": to_node, "bidirectional": True},
        description=f"There is an accident between {from_node} and {to_node}. Avoid that road.",
    )


def _non_depot_edges(plan: RoutingPlan) -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []
    for route in plan.routes:
        depot = route.stops[0]
        for origin, destination in zip(route.stops, route.stops[1:]):
            if origin != depot and destination != depot:
                edges.append((origin, destination))
    return edges
