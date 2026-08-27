from __future__ import annotations

from math import hypot

from adaptiveroute.domain.models import Customer, Depot, RoutingScenario, Vehicle


def _euclidean_distance_matrix(nodes: tuple[Depot | Customer, ...]) -> dict[tuple[str, str], float]:
    matrix: dict[tuple[str, str], float] = {}
    for origin in nodes:
        for destination in nodes:
            if origin.id == destination.id:
                matrix[(origin.id, destination.id)] = 0.0
                continue
            matrix[(origin.id, destination.id)] = round(hypot(origin.x - destination.x, origin.y - destination.y), 2)
    return matrix


def build_demo_scenario() -> RoutingScenario:
    depot = Depot(id="D0", x=50.0, y=50.0)
    customers = (
        Customer(id="C1", x=18.0, y=72.0, demand=4, priority=2),
        Customer(id="C2", x=24.0, y=28.0, demand=6, priority=1),
        Customer(id="C3", x=38.0, y=82.0, demand=5, priority=1),
        Customer(id="C4", x=62.0, y=78.0, demand=7, priority=3),
        Customer(id="C5", x=75.0, y=55.0, demand=4, priority=1),
        Customer(id="C6", x=82.0, y=22.0, demand=6, priority=2),
        Customer(id="C7", x=47.0, y=17.0, demand=3, priority=1),
        Customer(id="C8", x=15.0, y=42.0, demand=5, priority=2),
    )
    vehicles = (
        Vehicle(id="V1", capacity=20),
        Vehicle(id="V2", capacity=20),
    )
    nodes = (depot, *customers)
    return RoutingScenario(
        id="demo-cvrp-8",
        depot=depot,
        customers=customers,
        vehicles=vehicles,
        distance_matrix=_euclidean_distance_matrix(nodes),
    )

