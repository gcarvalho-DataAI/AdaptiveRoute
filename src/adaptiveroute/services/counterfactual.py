from __future__ import annotations

from dataclasses import dataclass

from adaptiveroute.domain.models import RoutingPlan, RoutingScenario, ValidationResult, VehicleRoute
from adaptiveroute.services.validation import validate_plan


@dataclass(frozen=True)
class CounterfactualAnalysis:
    candidate_plan: RoutingPlan
    validation: ValidationResult
    distance_delta_vs_reference: float
    reference_total_distance: float
    candidate_total_distance: float


def build_plan_from_route_sequences(
    scenario: RoutingScenario,
    route_sequences: dict[str, list[str]],
) -> RoutingPlan:
    customer_by_id = {customer.id: customer for customer in scenario.active_customers}
    depot_id = scenario.depot.id
    routes: list[VehicleRoute] = []

    for vehicle_id, raw_stops in route_sequences.items():
        stops = tuple(raw_stops)
        if not stops or stops[0] != depot_id:
            stops = (depot_id, *stops)
        if stops[-1] != depot_id:
            stops = (*stops, depot_id)

        load = sum(customer_by_id[stop].demand for stop in stops if stop in customer_by_id)
        distance = 0.0
        for origin, destination in zip(stops, stops[1:]):
            distance += scenario.distance(origin, destination)

        routes.append(
            VehicleRoute(
                vehicle_id=vehicle_id,
                stops=stops,
                load=load,
                distance=round(distance, 2),
            )
        )

    total_distance = round(sum(route.distance for route in routes), 2)
    return RoutingPlan(scenario_id=scenario.id, routes=tuple(routes), total_distance=total_distance)


def analyze_counterfactual(
    scenario: RoutingScenario,
    reference_plan: RoutingPlan,
    route_sequences: dict[str, list[str]],
) -> CounterfactualAnalysis:
    candidate_plan = build_plan_from_route_sequences(scenario, route_sequences)
    validation = validate_plan(scenario, candidate_plan)
    return CounterfactualAnalysis(
        candidate_plan=candidate_plan,
        validation=validation,
        distance_delta_vs_reference=round(candidate_plan.total_distance - reference_plan.total_distance, 2),
        reference_total_distance=reference_plan.total_distance,
        candidate_total_distance=candidate_plan.total_distance,
    )


def counterfactual_to_dict(analysis: CounterfactualAnalysis) -> dict:
    return {
        "candidate_plan": {
            "scenario_id": analysis.candidate_plan.scenario_id,
            "total_distance": analysis.candidate_plan.total_distance,
            "routes": [
                {
                    "vehicle_id": route.vehicle_id,
                    "stops": list(route.stops),
                    "load": route.load,
                    "distance": route.distance,
                }
                for route in analysis.candidate_plan.routes
            ],
        },
        "validation": {
            "passed": analysis.validation.passed,
            "violations": [
                {"code": violation.code, "message": violation.message, "severity": violation.severity}
                for violation in analysis.validation.violations
            ],
        },
        "distance_delta_vs_reference": analysis.distance_delta_vs_reference,
        "reference_total_distance": analysis.reference_total_distance,
        "candidate_total_distance": analysis.candidate_total_distance,
    }

