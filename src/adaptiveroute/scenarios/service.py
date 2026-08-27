from __future__ import annotations

from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.domain.models import RoutingScenario
from adaptiveroute.scenarios.repository import ScenarioRepository


class ScenarioService:
    def __init__(self, repository: ScenarioRepository):
        self._repository = repository

    def save_scenario(self, scenario: RoutingScenario) -> RoutingScenario:
        return self._repository.save_scenario(scenario)

    def get_scenario(self, scenario_id: str) -> RoutingScenario | None:
        return self._repository.get_scenario(scenario_id)

    def list_scenarios(self) -> list[RoutingScenario]:
        return self._repository.list_scenarios()

    def delete_scenario(self, scenario_id: str) -> bool:
        if scenario_id == "demo-cvrp-8":
            raise ValueError("The default demo scenario cannot be deleted.")
        return self._repository.delete_scenario(scenario_id)

    def seed_demo_scenario(self) -> RoutingScenario:
        scenario = build_demo_scenario()
        return self.save_scenario(scenario)

    def get_or_seed_demo_scenario(self) -> RoutingScenario:
        scenario = self.get_scenario("demo-cvrp-8")
        return scenario if scenario is not None else self.seed_demo_scenario()
