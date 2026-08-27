from __future__ import annotations

from collections import Counter

from adaptiveroute.domain.models import RoutingPlan, RoutingScenario, ValidationResult, ValidationViolation


def validate_plan(scenario: RoutingScenario, plan: RoutingPlan) -> ValidationResult:
    violations: list[ValidationViolation] = []
    depot_id = scenario.depot.id
    active_customer_ids = {customer.id for customer in scenario.active_customers}
    customer_by_id = {customer.id: customer for customer in scenario.active_customers}
    vehicle_by_id = {vehicle.id: vehicle for vehicle in scenario.vehicles}

    visited_customers: list[str] = []

    if plan.scenario_id != scenario.id:
        violations.append(
            ValidationViolation(
                code="scenario_mismatch",
                message=f"Plan scenario_id {plan.scenario_id} does not match {scenario.id}.",
            )
        )

    for route in plan.routes:
        vehicle = vehicle_by_id.get(route.vehicle_id)
        if vehicle is None:
            violations.append(
                ValidationViolation(code="unknown_vehicle", message=f"Unknown vehicle id {route.vehicle_id}.")
            )
            continue

        if len(route.stops) < 2 or route.stops[0] != depot_id or route.stops[-1] != depot_id:
            violations.append(
                ValidationViolation(
                    code="route_depot_boundary",
                    message=f"Route for {route.vehicle_id} must start and end at {depot_id}.",
                )
            )

        load = 0
        for node_id in route.stops[1:-1]:
            if node_id not in active_customer_ids:
                violations.append(
                    ValidationViolation(
                        code="inactive_or_unknown_customer",
                        message=f"Route for {route.vehicle_id} visits inactive or unknown customer {node_id}.",
                    )
                )
                continue
            visited_customers.append(node_id)
            load += customer_by_id[node_id].demand

        if load > vehicle.capacity:
            violations.append(
                ValidationViolation(
                    code="capacity_violation",
                    message=f"Route for {route.vehicle_id} has load {load}, capacity {vehicle.capacity}.",
                )
            )

        for origin, destination in zip(route.stops, route.stops[1:]):
            if (origin, destination) in scenario.blocked_arcs:
                violations.append(
                    ValidationViolation(
                        code="blocked_arc_used",
                        message=f"Route for {route.vehicle_id} uses blocked arc {origin}->{destination}.",
                    )
                )

    visited_counts = Counter(visited_customers)
    missing = sorted(active_customer_ids - set(visited_customers))
    duplicates = sorted(customer_id for customer_id, count in visited_counts.items() if count > 1)

    for customer_id in missing:
        violations.append(
            ValidationViolation(code="missing_customer", message=f"Active customer {customer_id} was not visited.")
        )

    for customer_id in duplicates:
        violations.append(
            ValidationViolation(code="duplicate_customer", message=f"Customer {customer_id} was visited more than once.")
        )

    return ValidationResult(passed=not violations, violations=tuple(violations))

