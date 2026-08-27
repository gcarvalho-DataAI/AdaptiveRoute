from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime
from typing import Any, Protocol

from adaptiveroute.drivers.models import DriverRecord, utc_now


class DriverRepository(Protocol):
    def save_driver(self, driver: DriverRecord) -> DriverRecord: ...
    def get_driver(self, driver_id: str) -> DriverRecord | None: ...
    def list_drivers(self) -> list[DriverRecord]: ...
    def update_status(self, driver_id: str, status: str) -> DriverRecord | None: ...
    def delete_driver(self, driver_id: str) -> bool: ...


class InMemoryDriverRepository:
    def __init__(self):
        self._drivers: dict[str, DriverRecord] = {}

    def save_driver(self, driver: DriverRecord) -> DriverRecord:
        self._drivers[driver.id] = driver
        return driver

    def get_driver(self, driver_id: str) -> DriverRecord | None:
        return self._drivers.get(driver_id)

    def list_drivers(self) -> list[DriverRecord]:
        return sorted(self._drivers.values(), key=lambda item: item.updated_at, reverse=True)

    def update_status(self, driver_id: str, status: str) -> DriverRecord | None:
        driver = self.get_driver(driver_id)
        if driver is None:
            return None
        updated = replace(driver, status=status, updated_at=utc_now())  # type: ignore[arg-type]
        self._drivers[driver_id] = updated
        return updated

    def delete_driver(self, driver_id: str) -> bool:
        return self._drivers.pop(driver_id, None) is not None


class MongoDriverRepository:
    def __init__(self, *, uri: str, database: str):
        from pymongo import ASCENDING, DESCENDING, MongoClient

        self._client = MongoClient(uri)
        self._collection = self._client[database]["drivers"]
        self._collection.create_index([("status", ASCENDING), ("region", ASCENDING)])
        self._collection.create_index([("updated_at", DESCENDING)])

    def save_driver(self, driver: DriverRecord) -> DriverRecord:
        self._collection.replace_one({"_id": driver.id}, _to_document(driver), upsert=True)
        return driver

    def get_driver(self, driver_id: str) -> DriverRecord | None:
        document = self._collection.find_one({"_id": driver_id})
        return _driver_from_document(document) if document else None

    def list_drivers(self) -> list[DriverRecord]:
        return [_driver_from_document(document) for document in self._collection.find().sort("updated_at", -1)]

    def update_status(self, driver_id: str, status: str) -> DriverRecord | None:
        from pymongo import ReturnDocument

        document = self._collection.find_one_and_update(
            {"_id": driver_id},
            {"$set": {"status": status, "updated_at": utc_now()}},
            return_document=ReturnDocument.AFTER,
        )
        return _driver_from_document(document) if document else None

    def delete_driver(self, driver_id: str) -> bool:
        result = self._collection.delete_one({"_id": driver_id})
        return result.deleted_count > 0


def _to_document(driver: DriverRecord) -> dict[str, Any]:
    document = asdict(driver)
    document["_id"] = document.pop("id")
    return document


def _driver_from_document(document: dict[str, Any]) -> DriverRecord:
    return DriverRecord(
        id=document["_id"],
        name=document.get("name", document["_id"]),
        vehicle_id=document.get("vehicle_id", document["_id"]),
        capacity=int(document.get("capacity", 20)),
        status=document.get("status", "available"),
        region=document.get("region", "NYC"),
        shift_start=document.get("shift_start"),
        shift_end=document.get("shift_end"),
        created_at=_dt(document["created_at"]),
        updated_at=_dt(document["updated_at"]),
        metadata=document.get("metadata", {}),
    )


def _dt(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
