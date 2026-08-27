from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import hypot
from pathlib import Path
from typing import Any

from adaptiveroute.domain.events import EventType, OperationalEvent
from adaptiveroute.domain.models import Customer, Depot, RoutingScenario, Vehicle
from adaptiveroute.services.counterfactual import build_plan_from_route_sequences
from adaptiveroute.services.mutations import apply_event
from adaptiveroute.services.validation import validate_plan


@dataclass(frozen=True)
class DatasetAudit:
    total_rows: int
    event_counts: dict[str, int]
    invalid_rows: int
    avg_input_chars: float
    avg_output_chars: float
    avg_customers: float
    split_counts: dict[str, int]


def audit_dataset(paths: list[Path]) -> DatasetAudit:
    event_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    total_input_chars = 0
    total_output_chars = 0
    total_customers = 0
    invalid_rows = 0
    total_rows = 0

    for path in paths:
        split_counts[path.name] += count_lines(path)
        for row in iter_jsonl(path):
            total_rows += 1
            input_payload = row["input"]
            output_payload = row["output"]
            event_type = input_payload["event"]["type"]
            event_counts[event_type] += 1
            total_input_chars += len(str(input_payload))
            total_output_chars += len(str(output_payload))
            total_customers += len(input_payload.get("customers", []))
            if not validate_sft_row(row):
                invalid_rows += 1

    return DatasetAudit(
        total_rows=total_rows,
        event_counts=dict(sorted(event_counts.items())),
        invalid_rows=invalid_rows,
        avg_input_chars=round(total_input_chars / total_rows, 2) if total_rows else 0.0,
        avg_output_chars=round(total_output_chars / total_rows, 2) if total_rows else 0.0,
        avg_customers=round(total_customers / total_rows, 2) if total_rows else 0.0,
        split_counts=dict(sorted(split_counts.items())),
    )


def validate_sft_row(row: dict[str, Any]) -> bool:
    scenario = scenario_from_compact_input(row["input"])
    event = event_from_compact_input(row["input"]["event"])
    mutated_scenario, _ = apply_event(scenario, event)
    candidate_plan = build_plan_from_route_sequences(mutated_scenario, row["output"]["routes"])
    return validate_plan(mutated_scenario, candidate_plan).passed


def scenario_from_compact_input(payload: dict[str, Any]) -> RoutingScenario:
    depot_payload = payload["depot"]
    depot = Depot(id=depot_payload["id"], x=float(depot_payload["x"]), y=float(depot_payload["y"]))
    customers = tuple(
        Customer(
            id=customer["id"],
            x=float(customer["x"]),
            y=float(customer["y"]),
            demand=int(customer["demand"]),
            priority=int(customer.get("priority", 1)),
            active=bool(customer.get("active", True)),
            required=bool(customer.get("required", True)),
        )
        for customer in payload["customers"]
    )
    vehicles = tuple(Vehicle(id=vehicle["id"], capacity=int(vehicle["capacity"])) for vehicle in payload["vehicles"])
    nodes = (depot, *customers)
    return RoutingScenario(
        id="audit-scenario",
        depot=depot,
        customers=customers,
        vehicles=vehicles,
        distance_matrix=euclidean_distance_matrix(nodes),
    )


def event_from_compact_input(payload: dict[str, Any]) -> OperationalEvent:
    event_type = EventType(payload["type"])
    if event_type == EventType.BLOCK_ARC:
        event_payload = {
            "from_node": payload["from_node"],
            "to_node": payload["to_node"],
            "bidirectional": payload.get("bidirectional", True),
        }
    elif event_type == EventType.CUSTOMER_UNAVAILABLE:
        event_payload = {"customer_id": payload["customer_id"]}
    elif event_type == EventType.CUSTOMER_PRIORITY_CHANGE:
        event_payload = {"customer_id": payload["customer_id"], "priority": payload.get("priority", 3)}
    else:
        event_payload = payload
    return OperationalEvent(type=event_type, payload=event_payload, description=f"Audit event {event_type.value}")


def euclidean_distance_matrix(nodes: tuple[Depot | Customer, ...]) -> dict[tuple[str, str], float]:
    matrix: dict[tuple[str, str], float] = {}
    for origin in nodes:
        for destination in nodes:
            if origin.id == destination.id:
                matrix[(origin.id, destination.id)] = 0.0
            else:
                matrix[(origin.id, destination.id)] = round(hypot(origin.x - destination.x, origin.y - destination.y), 2)
    return matrix


def iter_jsonl(path: Path):
    import json

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                yield json.loads(line)


def count_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8") as file:
        return sum(1 for line in file if line.strip())


def audit_to_dict(audit: DatasetAudit) -> dict[str, Any]:
    return {
        "total_rows": audit.total_rows,
        "split_counts": audit.split_counts,
        "event_counts": audit.event_counts,
        "invalid_rows": audit.invalid_rows,
        "avg_input_chars": audit.avg_input_chars,
        "avg_output_chars": audit.avg_output_chars,
        "avg_customers": audit.avg_customers,
    }
