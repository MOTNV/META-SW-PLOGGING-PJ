from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from obstacle_aware_distance import Point, point_in_polygon, project, segment_crosses_polygon


METERS_PER_LAT = 111_320.0


DEFAULT_MOVEMENT_RULES_PATH = Path(__file__).resolve().parent / "simulation" / "movement_rules.json"


@dataclass(frozen=True)
class RulePolygon:
    id: str
    name: str
    points: list[dict]


@dataclass
class MovementRules:
    pickup_access_radius_meters: float = 15.0
    blocked_clearance_meters: float = 0.0
    allow_off_path_pickup: bool = True
    block_osm_buildings: bool = True
    block_osm_blocked_areas: bool = True
    manual_blocked_areas: list[RulePolygon] | None = None
    manual_pickup_only_areas: list[RulePolygon] | None = None
    manual_allowed_areas: list[RulePolygon] | None = None
    manual_excluded_trash_areas: list[RulePolygon] | None = None

    @classmethod
    def load(cls, path: Path | None) -> "MovementRules":
        if path is None:
            return cls()
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        return cls(
            pickup_access_radius_meters=float(payload.get("pickupAccessRadiusMeters", 15.0)),
            blocked_clearance_meters=float(payload.get("blockedClearanceMeters", 0.0)),
            allow_off_path_pickup=bool(payload.get("allowOffPathPickup", True)),
            block_osm_buildings=bool(payload.get("blockOsmBuildings", True)),
            block_osm_blocked_areas=bool(payload.get("blockOsmBlockedAreas", True)),
            manual_blocked_areas=parse_polygons(payload.get("manualBlockedAreas", [])),
            manual_pickup_only_areas=parse_polygons(payload.get("manualPickupOnlyAreas", [])),
            manual_allowed_areas=parse_polygons(payload.get("manualAllowedAreas", [])),
            manual_excluded_trash_areas=parse_polygons(payload.get("manualExcludedTrashAreas", [])),
        )

    def is_point_manually_allowed(self, latitude: float, longitude: float) -> bool:
        return any(point_inside_rule_polygon(latitude, longitude, area) for area in self.manual_allowed_areas or [])

    def is_point_manually_blocked(self, latitude: float, longitude: float) -> bool:
        return any(point_inside_rule_polygon(latitude, longitude, area) for area in self.manual_blocked_areas or [])

    def is_point_pickup_only(self, latitude: float, longitude: float) -> bool:
        return any(point_inside_rule_polygon(latitude, longitude, area) for area in self.manual_pickup_only_areas or [])

    def is_trash_excluded(self, latitude: float, longitude: float) -> bool:
        return any(point_inside_rule_polygon(latitude, longitude, area) for area in self.manual_excluded_trash_areas or [])


def parse_polygons(items: list[dict]) -> list[RulePolygon]:
    polygons = []
    for index, item in enumerate(items):
        if item.get("enabled") is False:
            continue
        points = item.get("points") or []
        if len(points) < 3:
            continue
        polygons.append(
            RulePolygon(
                id=str(item.get("id", f"area_{index:03d}")),
                name=str(item.get("name", "")),
                points=points,
            )
        )
    return polygons


def point_inside_rule_polygon(latitude: float, longitude: float, polygon: RulePolygon) -> bool:
    origin_lat = latitude
    origin_lon = longitude
    projected = [
        project(float(point["latitude"]), float(point["longitude"]), origin_lat, origin_lon)
        for point in polygon.points
    ]
    return point_in_polygon(Point(0.0, 0.0), projected)


def path_crosses_rule_polygon(path: list[dict], polygon: RulePolygon) -> bool:
    for left, right in zip(path, path[1:]):
        if segment_crosses_polygon(
            float(left["latitude"]),
            float(left["longitude"]),
            float(right["latitude"]),
            float(right["longitude"]),
            polygon.points,
        ):
            return True
    return False


def polyline_distance_meters(path: list[dict]) -> float:
    total = 0.0
    for left, right in zip(path, path[1:]):
        total += distance_meters(
            float(left["latitude"]),
            float(left["longitude"]),
            float(right["latitude"]),
            float(right["longitude"]),
        )
    return total


def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    avg_lat_rad = math.radians((lat1 + lat2) * 0.5)
    meters_per_lon = METERS_PER_LAT * math.cos(avg_lat_rad)
    d_lat = (lat2 - lat1) * METERS_PER_LAT
    d_lon = (lon2 - lon1) * meters_per_lon
    return math.hypot(d_lat, d_lon)
