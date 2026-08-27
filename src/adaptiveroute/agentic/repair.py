from __future__ import annotations

from adaptiveroute.domain.models import RoutingPlan, RoutingScenario, VehicleRoute


def repair_candidate_plan(scenario: RoutingScenario, plan: RoutingPlan) -> RoutingPlan:
    """Apply conservative local repairs that cannot invent new optimization choices.

    The repair layer intentionally handles only safe structural cleanups:
    scenario id alignment, inactive-customer removal, duplicate customer removal,
    depot boundary normalization, load recomputation, and distance recomputation.
    Capacity violations, missing customers, and complex rerouting remain the
    responsibility of the solver fallback.
    """

    depot_id = scenario.depot.id
    active_customer_ids = {customer.id for customer in scenario.active_customers}
    customer_by_id = {customer.id: customer for customer in scenario.active_customers}
    vehicle_ids = {vehicle.id for vehicle in scenario.vehicles}

    seen: set[str] = set()
    repaired_routes: list[VehicleRoute] = []

    for route in plan.routes:
        if route.vehicle_id not in vehicle_ids:
            continue

        normalized_stops: list[str] = [depot_id]
        for stop in route.stops:
            if stop == depot_id:
                continue
            if stop not in active_customer_ids:
                continue
            if stop in seen:
                continue
            normalized_stops.append(stop)
            seen.add(stop)
        normalized_stops.append(depot_id)

        if len(normalized_stops) <= 2:
            continue

        distance = _route_distance(scenario, normalized_stops)
        load = sum(customer_by_id[stop].demand for stop in normalized_stops if stop in customer_by_id)
        repaired_routes.append(
            VehicleRoute(
                vehicle_id=route.vehicle_id,
                stops=tuple(normalized_stops),
                load=load,
                distance=round(distance, 2),
            )
        )

    return RoutingPlan(
        scenario_id=scenario.id,
        routes=tuple(repaired_routes),
        total_distance=round(sum(route.distance for route in repaired_routes), 2),
    )


def _route_distance(scenario: RoutingScenario, stops: list[str]) -> float:
    return sum(scenario.distance(origin, destination) for origin, destination in zip(stops, stops[1:]))
