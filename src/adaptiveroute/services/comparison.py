from __future__ import annotations

from dataclasses import dataclass

from adaptiveroute.domain.models import RoutingPlan, RoutingScenario


@dataclass(frozen=True)
class PlanComparison:
    scenario_id_before: str
    scenario_id_after: str
    total_distance_before: float
    total_distance_after: float
    distance_delta: float
    served_customers_before: tuple[str, ...]
    served_customers_after: tuple[str, ...]
    removed_customers: tuple[str, ...]
    added_customers: tuple[str, ...]
    changed_edges: tuple[tuple[str, str], ...]
    removed_edges: tuple[tuple[str, str], ...]
    unchanged_edges: tuple[tuple[str, str], ...]
    vehicle_loads_before: dict[str, int]
    vehicle_loads_after: dict[str, int]
    priority_customers_served_after: tuple[str, ...]
    blocked_arcs_after: tuple[tuple[str, str], ...]


def compare_plans(
    before_scenario: RoutingScenario,
    before_plan: RoutingPlan,
    after_scenario: RoutingScenario,
    after_plan: RoutingPlan,
) -> PlanComparison:
    before_customers = _served_customers(before_plan, before_scenario.depot.id)
    after_customers = _served_customers(after_plan, after_scenario.depot.id)
    before_edges = _edges(before_plan)
    after_edges = _edges(after_plan)
    priority_after = tuple(
        sorted(customer.id for customer in after_scenario.active_customers if customer.priority >= 3 and customer.id in after_customers)
    )

    return PlanComparison(
        scenario_id_before=before_scenario.id,
        scenario_id_after=after_scenario.id,
        total_distance_before=before_plan.total_distance,
        total_distance_after=after_plan.total_distance,
        distance_delta=round(after_plan.total_distance - before_plan.total_distance, 2),
        served_customers_before=tuple(sorted(before_customers)),
        served_customers_after=tuple(sorted(after_customers)),
        removed_customers=tuple(sorted(before_customers - after_customers)),
        added_customers=tuple(sorted(after_customers - before_customers)),
        changed_edges=tuple(sorted(after_edges - before_edges)),
        removed_edges=tuple(sorted(before_edges - after_edges)),
        unchanged_edges=tuple(sorted(after_edges & before_edges)),
        vehicle_loads_before={route.vehicle_id: route.load for route in before_plan.routes},
        vehicle_loads_after={route.vehicle_id: route.load for route in after_plan.routes},
        priority_customers_served_after=priority_after,
        blocked_arcs_after=tuple(sorted(after_scenario.blocked_arcs)),
    )


def comparison_to_dict(comparison: PlanComparison) -> dict:
    return {
        "scenario_id_before": comparison.scenario_id_before,
        "scenario_id_after": comparison.scenario_id_after,
        "total_distance_before": comparison.total_distance_before,
        "total_distance_after": comparison.total_distance_after,
        "distance_delta": comparison.distance_delta,
        "served_customers_before": list(comparison.served_customers_before),
        "served_customers_after": list(comparison.served_customers_after),
        "removed_customers": list(comparison.removed_customers),
        "added_customers": list(comparison.added_customers),
        "changed_edges": [{"from": origin, "to": destination} for origin, destination in comparison.changed_edges],
        "removed_edges": [{"from": origin, "to": destination} for origin, destination in comparison.removed_edges],
        "unchanged_edges": [{"from": origin, "to": destination} for origin, destination in comparison.unchanged_edges],
        "vehicle_loads_before": comparison.vehicle_loads_before,
        "vehicle_loads_after": comparison.vehicle_loads_after,
        "priority_customers_served_after": list(comparison.priority_customers_served_after),
        "blocked_arcs_after": [{"from": origin, "to": destination} for origin, destination in comparison.blocked_arcs_after],
    }


def _served_customers(plan: RoutingPlan, depot_id: str) -> set[str]:
    return {stop for route in plan.routes for stop in route.stops if stop != depot_id}


def _edges(plan: RoutingPlan) -> set[tuple[str, str]]:
    return {edge for route in plan.routes for edge in zip(route.stops, route.stops[1:])}
