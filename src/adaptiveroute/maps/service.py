from __future__ import annotations

import json
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Any
from urllib import error, parse, request


@dataclass(frozen=True)
class MapRoutingService:
    backend: str = "fallback"
    osrm_base_url: str = "http://osrm:5000"
    timeout_seconds: float = 8.0

    def route_geometry(
        self,
        *,
        plan: dict[str, Any],
        locations: dict[str, dict[str, Any]],
        overview: str = "full",
    ) -> dict[str, Any]:
        routes = plan.get("routes") or []
        if self.backend == "osrm":
            return self._osrm_geometry(routes=routes, locations=locations, overview=overview)
        return self._fallback_geometry(routes=routes, locations=locations, warning=None)

    def distance_matrix(self, locations: dict[str, dict[str, Any]]) -> dict[tuple[str, str], float]:
        if self.backend == "osrm":
            matrix = self._osrm_distance_matrix(locations)
            if matrix:
                return matrix
        return _haversine_distance_matrix(locations)

    def _osrm_distance_matrix(self, locations: dict[str, dict[str, Any]]) -> dict[tuple[str, str], float] | None:
        ids = list(locations)
        coordinates = [_location_coordinates(locations[node_id]) for node_id in ids]
        if any(coordinate is None for coordinate in coordinates):
            return None

        coordinate_path = ";".join(f"{lng},{lat}" for lat, lng in coordinates if lat is not None and lng is not None)
        query = parse.urlencode({"annotations": "distance"})
        url = f"{self.osrm_base_url.rstrip('/')}/table/v1/driving/{coordinate_path}?{query}"
        try:
            with request.urlopen(url, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, error.URLError, TimeoutError, json.JSONDecodeError):
            return None

        distances = payload.get("distances")
        if payload.get("code") != "Ok" or not distances:
            return None

        matrix: dict[tuple[str, str], float] = {}
        for origin_index, origin_id in enumerate(ids):
            for destination_index, destination_id in enumerate(ids):
                distance_meters = distances[origin_index][destination_index]
                matrix[(origin_id, destination_id)] = 0.0 if distance_meters is None else round(distance_meters / 1000, 3)
        return matrix

    def _osrm_geometry(
        self,
        *,
        routes: list[dict[str, Any]],
        locations: dict[str, dict[str, Any]],
        overview: str,
    ) -> dict[str, Any]:
        geometries: list[dict[str, Any]] = []
        warnings: list[str] = []

        for route in routes:
            stops = [str(stop) for stop in route.get("stops", [])]
            coordinates = [_location_coordinates(locations.get(stop)) for stop in stops]
            if any(coordinate is None for coordinate in coordinates) or len(coordinates) < 2:
                warnings.append(f"Missing map coordinates for {route.get('vehicle_id', 'unknown vehicle')}.")
                geometries.append(_fallback_route_geometry(route, locations))
                continue

            coordinate_path = ";".join(f"{lng},{lat}" for lat, lng in coordinates if lat is not None and lng is not None)
            query = parse.urlencode(
                {
                    "overview": overview,
                    "geometries": "geojson",
                    "steps": "false",
                    "alternatives": "false",
                }
            )
            url = f"{self.osrm_base_url.rstrip('/')}/route/v1/driving/{coordinate_path}?{query}"

            try:
                with request.urlopen(url, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except (OSError, error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                warnings.append(f"OSRM unavailable for {route.get('vehicle_id', 'unknown vehicle')}: {exc}.")
                geometries.append(_fallback_route_geometry(route, locations))
                continue

            osrm_routes = payload.get("routes") or []
            if payload.get("code") != "Ok" or not osrm_routes:
                warnings.append(
                    f"OSRM could not route {route.get('vehicle_id', 'unknown vehicle')}: {payload.get('message') or payload.get('code')}."
                )
                geometries.append(_fallback_route_geometry(route, locations))
                continue

            best = osrm_routes[0]
            geometry = best.get("geometry", {})
            coordinates_lon_lat = geometry.get("coordinates") or []
            geometries.append(
                {
                    "vehicle_id": route.get("vehicle_id"),
                    "stops": stops,
                    "geometry": [[lat, lng] for lng, lat in coordinates_lon_lat],
                    "distance_meters": best.get("distance"),
                    "duration_seconds": best.get("duration"),
                    "source": "osrm",
                }
            )

        if any(item.get("source") != "osrm" for item in geometries):
            source = "mixed"
        else:
            source = "osrm"
        return {"source": source, "routes": geometries, "warnings": warnings}

    def _fallback_geometry(
        self,
        *,
        routes: list[dict[str, Any]],
        locations: dict[str, dict[str, Any]],
        warning: str | None,
    ) -> dict[str, Any]:
        warnings = [warning] if warning else []
        return {
            "source": "fallback",
            "routes": [_fallback_route_geometry(route, locations) for route in routes],
            "warnings": warnings,
        }


def _fallback_route_geometry(route: dict[str, Any], locations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    stops = [str(stop) for stop in route.get("stops", [])]
    geometry = [
        [coordinate[0], coordinate[1]]
        for coordinate in (_location_coordinates(locations.get(stop)) for stop in stops)
        if coordinate is not None
    ]
    return {
        "vehicle_id": route.get("vehicle_id"),
        "stops": stops,
        "geometry": geometry,
        "distance_meters": None,
        "duration_seconds": None,
        "source": "fallback",
    }


def _location_coordinates(location: dict[str, Any] | None) -> tuple[float, float] | None:
    if not location:
        return None
    lat = location.get("lat")
    lng = location.get("lng", location.get("lon"))
    if lat is None or lng is None:
        return None
    return (float(lat), float(lng))


def _haversine_distance_matrix(locations: dict[str, dict[str, Any]]) -> dict[tuple[str, str], float]:
    matrix: dict[tuple[str, str], float] = {}
    for origin_id, origin in locations.items():
        origin_coordinates = _location_coordinates(origin)
        for destination_id, destination in locations.items():
            destination_coordinates = _location_coordinates(destination)
            if origin_id == destination_id:
                matrix[(origin_id, destination_id)] = 0.0
            elif origin_coordinates is None or destination_coordinates is None:
                matrix[(origin_id, destination_id)] = 0.0
            else:
                matrix[(origin_id, destination_id)] = round(_haversine_km(origin_coordinates, destination_coordinates), 3)
    return matrix


def _haversine_km(origin: tuple[float, float], destination: tuple[float, float]) -> float:
    lat1, lon1 = origin
    lat2, lon2 = destination
    radius_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * radius_km * asin(sqrt(a))
