from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal

from adaptiveroute.data.generator import generate_scenario
from adaptiveroute.domain.serialization import event_to_dict, plan_to_dict, scenario_to_dict, validation_to_dict
from adaptiveroute.domain.events import EventType, OperationalEvent
from adaptiveroute.domain.models import RoutingPlan, RoutingScenario
from adaptiveroute.services.mutations import apply_event, generate_training_event
from adaptiveroute.services.validation import validate_plan
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine

DatasetProfile = Literal[
    "balanced",
    "capacity_tight",
    "blocked_arc",
    "mixed_hard",
    "capacity_extreme",
    "blocked_capacity",
]


@dataclass(frozen=True)
class DatasetBuildStats:
    requested: int
    written: int
    skipped: int


def build_sft_examples(
    *,
    n: int,
    seed_start: int = 1,
    num_customers: int = 8,
    num_vehicles: int = 2,
    output_format: str = "full",
    profile: DatasetProfile = "balanced",
) -> tuple[list[dict], DatasetBuildStats]:
    engine = PyomoHighsEngine()
    examples: list[dict] = []
    skipped = 0
    seed = seed_start

    while len(examples) < n and seed < seed_start + n * 10:
        profile_rng = random.Random(seed + 20_000)
        scenario = generate_scenario(
            seed=seed,
            num_customers=num_customers,
            num_vehicles=num_vehicles,
            clustered=seed % 2 == 0,
            capacity_slack=capacity_slack_for_profile(profile, profile_rng),
            demand_range=demand_range_for_profile(profile),
        )
        base_result = engine.solve(scenario)
        if base_result.plan is None:
            skipped += 1
            seed += 1
            continue

        event = generate_training_event(
            scenario,
            base_result.plan,
            seed=seed + 10_000,
            event_types=event_types_for_profile(profile, seed),
        )
        mutated_scenario, mutation = apply_event(scenario, event)
        replanned_result = engine.solve(mutated_scenario)
        if replanned_result.plan is None:
            skipped += 1
            seed += 1
            continue

        validation = validate_plan(mutated_scenario, replanned_result.plan)
        if not validation.passed:
            skipped += 1
            seed += 1
            continue

        examples.append(
            build_sft_example(
                scenario=scenario,
                base_plan=base_result.plan,
                event=event,
                replanned_plan=replanned_result.plan,
                seed=seed,
                validation=validation_to_dict(validation),
                mutation_diff=mutation.diff,
                output_format=output_format,
            )
        )
        seed += 1

    return examples, DatasetBuildStats(requested=n, written=len(examples), skipped=skipped)


def capacity_slack_for_profile(profile: DatasetProfile, rng: random.Random) -> float:
    if profile == "capacity_extreme":
        return rng.uniform(1.02, 1.08)
    if profile == "blocked_capacity":
        return rng.uniform(1.04, 1.10)
    if profile == "capacity_tight":
        return rng.uniform(1.0, 1.08)
    if profile == "mixed_hard":
        return rng.uniform(1.0, 1.12)
    return 1.25


def demand_range_for_profile(profile: DatasetProfile) -> tuple[int, int]:
    if profile in {"capacity_extreme", "blocked_capacity"}:
        return (2, 8)
    return (2, 8)


def event_types_for_profile(profile: DatasetProfile, seed: int) -> tuple[EventType, ...] | None:
    if profile == "blocked_arc":
        return (EventType.BLOCK_ARC,)
    if profile == "blocked_capacity":
        return (EventType.BLOCK_ARC,) if seed % 4 != 0 else (EventType.CUSTOMER_UNAVAILABLE,)
    if profile == "capacity_extreme":
        return (EventType.BLOCK_ARC, EventType.CUSTOMER_UNAVAILABLE)
    if profile == "capacity_tight":
        return (EventType.BLOCK_ARC, EventType.CUSTOMER_UNAVAILABLE)
    if profile == "mixed_hard":
        return (EventType.BLOCK_ARC,) if seed % 3 != 0 else (EventType.CUSTOMER_UNAVAILABLE,)
    return None


def build_sft_example(
    *,
    scenario: RoutingScenario,
    base_plan: RoutingPlan,
    event: OperationalEvent,
    replanned_plan: RoutingPlan,
    seed: int,
    validation: dict,
    mutation_diff: dict,
    output_format: str,
) -> dict:
    if output_format == "full":
        input_payload = {
            "base_scenario": scenario_to_dict(scenario),
            "base_plan": plan_to_dict(base_plan),
            "event": event_to_dict(event),
        }
    elif output_format == "compact":
        input_payload = compact_input_payload(scenario, base_plan, event)
    else:
        raise ValueError(f"Unsupported SFT output format: {output_format}")

    return {
        "instruction": "Return a feasible replanned CVRP route as JSON.",
        "input": input_payload,
        "output": {"routes": {route.vehicle_id: [stop for stop in route.stops] for route in replanned_plan.routes}},
        "metadata": {
            "seed": seed,
            "solver": "pyomo_highs",
            "format": output_format,
            "base_total_distance": base_plan.total_distance,
            "replanned_total_distance": replanned_plan.total_distance,
            "validation": validation,
            "mutation_diff": mutation_diff,
        },
    }


def compact_input_payload(scenario: RoutingScenario, base_plan: RoutingPlan, event: OperationalEvent) -> dict:
    return {
        "depot": {"id": scenario.depot.id, "x": scenario.depot.x, "y": scenario.depot.y},
        "vehicles": [{"id": vehicle.id, "capacity": vehicle.capacity} for vehicle in scenario.vehicles],
        "customers": [
            {
                "id": customer.id,
                "x": customer.x,
                "y": customer.y,
                "demand": customer.demand,
                "priority": customer.priority,
                "active": customer.active,
                "required": customer.required,
            }
            for customer in scenario.customers
        ],
        "base_routes": {route.vehicle_id: [stop for stop in route.stops] for route in base_plan.routes},
        "event": compact_event_payload(event),
    }


def compact_event_payload(event: OperationalEvent) -> dict:
    if event.type == EventType.BLOCK_ARC:
        return {
            "type": event.type.value,
            "from_node": event.payload["from_node"],
            "to_node": event.payload["to_node"],
            "bidirectional": event.payload.get("bidirectional", True),
        }
    if event.type == EventType.CUSTOMER_UNAVAILABLE:
        return {"type": event.type.value, "customer_id": event.payload["customer_id"]}
    if event.type == EventType.CUSTOMER_PRIORITY_CHANGE:
        return {
            "type": event.type.value,
            "customer_id": event.payload["customer_id"],
            "priority": event.payload.get("priority", 3),
        }
    return event_to_dict(event)
