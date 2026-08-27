from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any

from adaptiveroute.drivers.models import DriverRecord, utc_now
from adaptiveroute.drivers.repository import DriverRepository


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
            metadata=metadata or {},
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
            metadata=metadata or existing.metadata,
            updated_at=utc_now(),
        )
        return self._repository.save_driver(driver)

    def delete_driver(self, driver_id: str) -> bool:
        return self._repository.delete_driver(driver_id)

    def authenticate(self, *, username: str, password: str) -> DriverRecord | None:
        for driver in self.list_drivers():
            metadata = driver.metadata or {}
            if metadata.get("username") == username and metadata.get("temporary_password") == password:
                return driver
        return None

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
    return asdict(driver)
