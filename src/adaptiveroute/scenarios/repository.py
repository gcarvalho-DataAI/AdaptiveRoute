from __future__ import annotations

from typing import Any, Protocol

from adaptiveroute.domain.models import RoutingScenario
from adaptiveroute.domain.serialization import scenario_from_dict, scenario_to_dict


class ScenarioRepository(Protocol):
    def save_scenario(self, scenario: RoutingScenario) -> RoutingScenario: ...
    def get_scenario(self, scenario_id: str) -> RoutingScenario | None: ...
    def list_scenarios(self) -> list[RoutingScenario]: ...
    def delete_scenario(self, scenario_id: str) -> bool: ...


class InMemoryScenarioRepository:
    def __init__(self):
        self._scenarios: dict[str, RoutingScenario] = {}

    def save_scenario(self, scenario: RoutingScenario) -> RoutingScenario:
        self._scenarios[scenario.id] = scenario
        return scenario

    def get_scenario(self, scenario_id: str) -> RoutingScenario | None:
        return self._scenarios.get(scenario_id)

    def list_scenarios(self) -> list[RoutingScenario]:
        return sorted(self._scenarios.values(), key=lambda scenario: scenario.id)

    def delete_scenario(self, scenario_id: str) -> bool:
        return self._scenarios.pop(scenario_id, None) is not None


class MongoScenarioRepository:
    def __init__(self, *, uri: str, database: str):
        from pymongo import MongoClient

        self._client = MongoClient(uri)
        self._collection = self._client[database]["routing_scenarios"]

    def save_scenario(self, scenario: RoutingScenario) -> RoutingScenario:
        document = scenario_to_dict(scenario)
        document["_id"] = scenario.id
        self._collection.replace_one({"_id": scenario.id}, document, upsert=True)
        return scenario

    def get_scenario(self, scenario_id: str) -> RoutingScenario | None:
        document = self._collection.find_one({"_id": scenario_id})
        return _scenario_from_document(document) if document else None

    def list_scenarios(self) -> list[RoutingScenario]:
        return [_scenario_from_document(document) for document in self._collection.find().sort("_id", 1)]

    def delete_scenario(self, scenario_id: str) -> bool:
        result = self._collection.delete_one({"_id": scenario_id})
        return result.deleted_count > 0


def _scenario_from_document(document: dict[str, Any]) -> RoutingScenario:
    payload = dict(document)
    payload["id"] = payload.pop("_id", payload.get("id"))
    return scenario_from_dict(payload)
