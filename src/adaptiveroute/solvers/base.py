from __future__ import annotations

from abc import ABC, abstractmethod

from adaptiveroute.domain.models import RoutingScenario, SolverResult


class RoutingEngine(ABC):
    @abstractmethod
    def solve(self, scenario: RoutingScenario) -> SolverResult:
        """Solve a routing scenario and return a structured result."""

