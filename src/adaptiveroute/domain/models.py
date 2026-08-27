from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SolveStatus(StrEnum):
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    ERROR = "error"


@dataclass(frozen=True)
class Node:
    id: str
    x: float
    y: float


@dataclass(frozen=True)
class Customer(Node):
    demand: int
    required: bool = True
    priority: int = 1
    active: bool = True


@dataclass(frozen=True)
class Depot(Node):
    pass


@dataclass(frozen=True)
class Vehicle:
    id: str
    capacity: int


@dataclass(frozen=True)
class RoutingScenario:
    id: str
    depot: Depot
    customers: tuple[Customer, ...]
    vehicles: tuple[Vehicle, ...]
    distance_matrix: dict[tuple[str, str], float]
    blocked_arcs: frozenset[tuple[str, str]] = frozenset()

    @property
    def active_customers(self) -> tuple[Customer, ...]:
        return tuple(customer for customer in self.customers if customer.active and customer.required)

    @property
    def node_ids(self) -> tuple[str, ...]:
        return (self.depot.id, *(customer.id for customer in self.active_customers))

    def distance(self, from_node: str, to_node: str) -> float:
        try:
            return self.distance_matrix[(from_node, to_node)]
        except KeyError as exc:
            raise KeyError(f"Missing distance for arc {from_node}->{to_node}") from exc


@dataclass(frozen=True)
class VehicleRoute:
    vehicle_id: str
    stops: tuple[str, ...]
    load: int
    distance: float


@dataclass(frozen=True)
class RoutingPlan:
    scenario_id: str
    routes: tuple[VehicleRoute, ...]
    total_distance: float


@dataclass(frozen=True)
class SolverResult:
    status: SolveStatus
    plan: RoutingPlan | None
    message: str = ""
    solve_time_ms: float | None = None


@dataclass(frozen=True)
class ValidationViolation:
    code: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    violations: tuple[ValidationViolation, ...] = field(default_factory=tuple)

