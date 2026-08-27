from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime
from typing import Any, Protocol

from adaptiveroute.operations.models import OperationalRouteRecord, utc_now


class OperationalRouteRepository(Protocol):
    def save_route(self, route: OperationalRouteRecord) -> OperationalRouteRecord: ...
    def get_route(self, route_id: str) -> OperationalRouteRecord | None: ...
    def list_routes(self) -> list[OperationalRouteRecord]: ...
    def list_routes_by_driver(self, driver_id: str) -> list[OperationalRouteRecord]: ...
    def mark_driver_removed(self, driver_id: str, *, driver_snapshot: dict[str, Any]) -> int: ...
    def update_status(self, route_id: str, status: str) -> OperationalRouteRecord | None: ...
    def update_current_plan(
        self,
        route_id: str,
        plan: dict[str, Any],
        *,
        scenario_id: str | None = None,
    ) -> OperationalRouteRecord | None: ...


class InMemoryOperationalRouteRepository:
    def __init__(self):
        self._routes: dict[str, OperationalRouteRecord] = {}

    def save_route(self, route: OperationalRouteRecord) -> OperationalRouteRecord:
        self._routes[route.id] = route
        return route

    def get_route(self, route_id: str) -> OperationalRouteRecord | None:
        return self._routes.get(route_id)

    def list_routes(self) -> list[OperationalRouteRecord]:
        return sorted(self._routes.values(), key=lambda item: item.updated_at, reverse=True)

    def list_routes_by_driver(self, driver_id: str) -> list[OperationalRouteRecord]:
        return [route for route in self.list_routes() if route.driver_id == driver_id]

    def mark_driver_removed(self, driver_id: str, *, driver_snapshot: dict[str, Any]) -> int:
        updated_count = 0
        for route in list(self._routes.values()):
            if route.driver_id != driver_id:
                continue
            metadata = {
                **(route.metadata or {}),
                "driver_removed": True,
                "removed_driver": driver_snapshot,
            }
            updated = replace(
                route,
                driver_id=f"removed:{driver_id}",
                metadata=metadata,
                updated_at=utc_now(),
            )
            self._routes[route.id] = updated
            updated_count += 1
        return updated_count

    def update_status(self, route_id: str, status: str) -> OperationalRouteRecord | None:
        route = self.get_route(route_id)
        if route is None:
            return None
        updated = replace(route, status=status, updated_at=utc_now())  # type: ignore[arg-type]
        self._routes[route_id] = updated
        return updated

    def update_current_plan(
        self,
        route_id: str,
        plan: dict[str, Any],
        *,
        scenario_id: str | None = None,
    ) -> OperationalRouteRecord | None:
        route = self.get_route(route_id)
        if route is None:
            return None
        updated = replace(
            route,
            current_plan=plan,
            scenario_id=scenario_id or route.scenario_id,
            updated_at=utc_now(),
        )
        self._routes[route_id] = updated
        return updated


class MongoOperationalRouteRepository:
    def __init__(self, *, uri: str, database: str):
        from pymongo import ASCENDING, DESCENDING, MongoClient

        self._client = MongoClient(uri)
        self._collection = self._client[database]["operational_routes"]
        self._collection.create_index([("driver_id", ASCENDING), ("status", ASCENDING)])
        self._collection.create_index([("updated_at", DESCENDING)])

    def save_route(self, route: OperationalRouteRecord) -> OperationalRouteRecord:
        self._collection.replace_one({"_id": route.id}, _to_document(route), upsert=True)
        return route

    def get_route(self, route_id: str) -> OperationalRouteRecord | None:
        document = self._collection.find_one({"_id": route_id})
        return _route_from_document(document) if document else None

    def list_routes(self) -> list[OperationalRouteRecord]:
        return [_route_from_document(document) for document in self._collection.find().sort("updated_at", -1)]

    def list_routes_by_driver(self, driver_id: str) -> list[OperationalRouteRecord]:
        return [
            _route_from_document(document)
            for document in self._collection.find({"driver_id": driver_id}).sort("updated_at", -1)
        ]

    def mark_driver_removed(self, driver_id: str, *, driver_snapshot: dict[str, Any]) -> int:
        result = self._collection.update_many(
            {"driver_id": driver_id},
            {
                "$set": {
                    "driver_id": f"removed:{driver_id}",
                    "metadata.driver_removed": True,
                    "metadata.removed_driver": driver_snapshot,
                    "updated_at": utc_now(),
                }
            },
        )
        return result.modified_count

    def update_status(self, route_id: str, status: str) -> OperationalRouteRecord | None:
        from pymongo import ReturnDocument

        document = self._collection.find_one_and_update(
            {"_id": route_id},
            {"$set": {"status": status, "updated_at": utc_now()}},
            return_document=ReturnDocument.AFTER,
        )
        return _route_from_document(document) if document else None

    def update_current_plan(
        self,
        route_id: str,
        plan: dict[str, Any],
        *,
        scenario_id: str | None = None,
    ) -> OperationalRouteRecord | None:
        from pymongo import ReturnDocument

        updated_at = utc_now()
        fields: dict[str, Any] = {"current_plan": plan, "updated_at": updated_at}
        if scenario_id:
            fields["scenario_id"] = scenario_id
        document = self._collection.find_one_and_update(
            {"_id": route_id},
            {"$set": fields},
            return_document=ReturnDocument.AFTER,
        )
        return _route_from_document(document) if document else None


def _to_document(route: OperationalRouteRecord) -> dict[str, Any]:
    document = asdict(route)
    document["_id"] = document.pop("id")
    return document


def _route_from_document(document: dict[str, Any]) -> OperationalRouteRecord:
    return OperationalRouteRecord(
        id=document["_id"],
        driver_id=document["driver_id"],
        scenario_id=document["scenario_id"],
        current_plan=document.get("current_plan", {}),
        status=document.get("status", "assigned"),
        created_at=_dt(document["created_at"]),
        updated_at=_dt(document["updated_at"]),
        metadata=document.get("metadata", {}),
    )


def _dt(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
