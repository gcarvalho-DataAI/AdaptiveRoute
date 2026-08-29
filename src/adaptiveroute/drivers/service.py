from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any

from adaptiveroute.drivers.models import DriverRecord, utc_now
from adaptiveroute.drivers.repository import DriverRepository
from adaptiveroute.security import hash_password, verify_password


class DriverService:
    def __init__(self, repository: DriverRepository):
        self._repository = repository

    def create_driver(
        self,
        *,
        driver_id: str,
        name: str,
        vehicle_id: str,
        capacity: int,
        status: str = "available",
        region: str = "NYC",
        shift_start: str | None = None,
        shift_end: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DriverRecord:
        existing = self._repository.get_driver(driver_id)
        created_at = existing.created_at if existing else utc_now()
        safe_metadata = self._with_hashed_password(metadata or {})
        driver = DriverRecord(
            id=driver_id,
            name=name,
            vehicle_id=vehicle_id,
            capacity=capacity,
            status=status,  # type: ignore[arg-type]
            region=region,
            shift_start=shift_start,
            shift_end=shift_end,
            created_at=created_at,
            updated_at=utc_now(),
            metadata=safe_metadata,
        )
        return self._repository.save_driver(driver)

    def get_driver(self, driver_id: str) -> DriverRecord | None:
        return self._repository.get_driver(driver_id)

    def list_drivers(self) -> list[DriverRecord]:
        return self._repository.list_drivers()

    def update_driver(
        self,
        driver_id: str,
        *,
        name: str,
        vehicle_id: str,
        capacity: int,
        status: str = "available",
        region: str = "NYC",
        shift_start: str | None = None,
        shift_end: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DriverRecord:
        existing = self._repository.get_driver(driver_id)
        if existing is None:
            raise ValueError("Driver not found.")
        driver = replace(
            existing,
            name=name,
            vehicle_id=vehicle_id,
            capacity=capacity,
            status=status,  # type: ignore[arg-type]
            region=region,
            shift_start=shift_start,
            shift_end=shift_end,
            metadata=self._with_hashed_password(metadata or existing.metadata),
            updated_at=utc_now(),
        )
        return self._repository.save_driver(driver)

    def delete_driver(self, driver_id: str) -> bool:
        return self._repository.delete_driver(driver_id)

    def authenticate(self, *, username: str, password: str) -> DriverRecord | None:
        normalized_username = username.strip().lower()
        for driver in self.list_drivers():
            metadata = driver.metadata or {}
            if str(metadata.get("username", "")).strip().lower() != normalized_username:
                continue
            password_hash = metadata.get("password_hash")
            if password_hash and verify_password(password, password_hash):
                return driver
            legacy_password = metadata.get("temporary_password")
            if legacy_password and legacy_password == password:
                migrated_metadata = self._with_hashed_password(metadata)
                return self.update_driver(
                    driver.id,
                    name=driver.name,
                    vehicle_id=driver.vehicle_id,
                    capacity=driver.capacity,
                    status=driver.status,
                    region=driver.region,
                    shift_start=driver.shift_start,
                    shift_end=driver.shift_end,
                    metadata=migrated_metadata,
                )
        return None

    def _with_hashed_password(self, metadata: dict[str, Any]) -> dict[str, Any]:
        safe_metadata = dict(metadata or {})
        if "username" in safe_metadata:
            safe_metadata["username"] = str(safe_metadata["username"]).strip().lower()
        plain_password = safe_metadata.pop("temporary_password", None)
        if plain_password:
            safe_metadata["password_hash"] = hash_password(str(plain_password))
        return safe_metadata

    def mark_on_route(self, driver_id: str) -> DriverRecord | None:
        return self._repository.update_status(driver_id, "on_route")

    def ensure_demo_drivers(self) -> list[DriverRecord]:
        if self._repository.list_drivers():
            return self._repository.list_drivers()
        return [
            self.create_driver(
                driver_id="DRV-MANHATTAN-01",
                name="Maya Chen",
                vehicle_id="VAN-MH-014",
                capacity=22,
                region="Manhattan South",
                shift_start="07:00",
                shift_end="15:00",
                metadata={"username": "maya.chen", "temporary_password": "route-demo-01", "license_class": "Commercial Van"},
            ),
            self.create_driver(
                driver_id="DRV-MANHATTAN-02",
                name="Ethan Brooks",
                vehicle_id="VAN-MH-027",
                capacity=24,
                region="Manhattan Midtown",
                shift_start="08:00",
                shift_end="16:00",
                metadata={"username": "ethan.brooks", "temporary_password": "route-demo-02", "license_class": "Commercial Van"},
            ),
            self.create_driver(
                driver_id="DRV-BROOKLYN-01",
                name="Sofia Ramirez",
                vehicle_id="VAN-BK-033",
                capacity=20,
                region="Brooklyn North",
                shift_start="09:00",
                shift_end="17:00",
                metadata={"username": "sofia.ramirez", "temporary_password": "route-demo-03", "license_class": "Commercial Van"},
            ),
            self.create_driver(
                driver_id="DRV-QUEENS-01",
                name="Noah Patel",
                vehicle_id="VAN-QN-018",
                capacity=26,
                region="Queens West",
                shift_start="06:30",
                shift_end="14:30",
                metadata={"username": "noah.patel", "temporary_password": "route-demo-04", "license_class": "Box Truck"},
            ),
            self.create_driver(
                driver_id="DRV-BROOKLYN-02",
                name="Olivia Grant",
                vehicle_id="VAN-BK-041",
                capacity=21,
                region="Brooklyn South",
                shift_start="10:00",
                shift_end="18:00",
                metadata={"username": "olivia.grant", "temporary_password": "route-demo-05", "license_class": "Commercial Van"},
            ),
            self.create_driver(
                driver_id="DRV-NJ-01",
                name="Lucas Bennett",
                vehicle_id="VAN-NJ-012",
                capacity=23,
                region="Hudson County",
                shift_start="07:30",
                shift_end="15:30",
                metadata={"username": "lucas.bennett", "temporary_password": "route-demo-06", "license_class": "Commercial Van"},
            ),
        ]


def driver_to_dict(driver: DriverRecord) -> dict[str, Any]:
    payload = asdict(driver)
    metadata = dict(payload.get("metadata") or {})
    has_password = bool(metadata.pop("password_hash", None) or metadata.pop("temporary_password", None))
    if has_password:
        metadata["has_password"] = True
    payload["metadata"] = metadata
    return payload
