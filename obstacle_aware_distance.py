from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from walkable_route_graph import DEFAULT_OSM_FEATURES_PATH, METERS_PER_LAT, distance_meters


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass
class ObstaclePolygon:
    source: str
    points: list[dict]
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float


class ObstacleAwareDistance:
    def __init__(self, obstacles: list[ObstaclePolygon]) -> None:
        self.obstacles = obstacles
        self._cache: dict[tuple[float, float, float, float], float] = {}

    @classmethod
    def from_osm_features(cls, path: Path = DEFAULT_OSM_FEATURES_PATH) -> "ObstacleAwareDistance":
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        obstacles: list[ObstaclePolygon] = []
        for key in ("buildings", "blockedAreas", "excludedZones"):
            for area in payload.get(key, []):
                points = area.get("points", [])
                if len(points) >= 3:
                    latitudes = [float(point["latitude"]) for point in points]
                    longitudes = [float(point["longitude"]) for point in points]
                    obstacles.append(
                        ObstaclePolygon(
                            source=key,
                            points=points,
                            min_latitude=min(latitudes),
                            max_latitude=max(latitudes),
                            min_longitude=min(longitudes),
                            max_longitude=max(longitudes),
                        )
                    )

        return cls(obstacles)

    def shortest_distance_between_points(
        self,
        from_latitude: float,
        from_longitude: float,
        to_latitude: float,
        to_longitude: float,
    ) -> float:
        key = (
            round(from_latitude, 5),
            round(from_longitude, 5),
            round(to_latitude, 5),
            round(to_longitude, 5),
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        direct = distance_meters(from_latitude, from_longitude, to_latitude, to_longitude)
        crossing_obstacles = [
            obstacle for obstacle in self.obstacles
            if segment_bbox_overlaps_obstacle(
                from_latitude,
                from_longitude,
                to_latitude,
                to_longitude,
                obstacle,
            )
            and segment_crosses_polygon(from_latitude, from_longitude, to_latitude, to_longitude, obstacle.points)
        ]
        if not crossing_obstacles:
            self._cache[key] = direct
            return direct

        # Fast approximation: use direct movement plus the minimum perimeter detour around
        # crossed obstacle polygons. This avoids letting agents pass through blocked areas
        # without constraining them to OSM road centerlines.
        detour_extra = 0.0
        for obstacle in crossing_obstacles:
            detour_extra += estimate_polygon_detour_extra(
                from_latitude,
                from_longitude,
                to_latitude,
                to_longitude,
                obstacle.points,
            )

        distance = direct + detour_extra
        self._cache[key] = distance
        return distance


def segment_crosses_polygon(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    polygon: list[dict],
) -> bool:
    origin_lat = (lat1 + lat2) * 0.5
    origin_lon = (lon1 + lon2) * 0.5
    a = project(lat1, lon1, origin_lat, origin_lon)
    b = project(lat2, lon2, origin_lat, origin_lon)
    poly = [project(float(p["latitude"]), float(p["longitude"]), origin_lat, origin_lon) for p in polygon]

    if point_in_polygon(a, poly) or point_in_polygon(b, poly):
        return True

    for left, right in zip(poly, poly[1:] + poly[:1]):
        if segments_intersect(a, b, left, right):
            return True

    return False


def segment_bbox_overlaps_obstacle(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    obstacle: ObstaclePolygon,
) -> bool:
    min_lat = min(lat1, lat2)
    max_lat = max(lat1, lat2)
    min_lon = min(lon1, lon2)
    max_lon = max(lon1, lon2)
    return not (
        max_lat < obstacle.min_latitude
        or min_lat > obstacle.max_latitude
        or max_lon < obstacle.min_longitude
        or min_lon > obstacle.max_longitude
    )


def estimate_polygon_detour_extra(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    polygon: list[dict],
) -> float:
    perimeter = 0.0
    points = polygon[:]
    if points[0] != points[-1]:
        points.append(points[0])
    for left, right in zip(points, points[1:]):
        perimeter += distance_meters(
            float(left["latitude"]),
            float(left["longitude"]),
            float(right["latitude"]),
            float(right["longitude"]),
        )
    return perimeter * 0.5


def project(lat: float, lon: float, origin_lat: float, origin_lon: float) -> Point:
    avg_lat_rad = math.radians(origin_lat)
    meters_per_lon = METERS_PER_LAT * math.cos(avg_lat_rad)
    return Point(
        x=(lon - origin_lon) * meters_per_lon,
        y=(lat - origin_lat) * METERS_PER_LAT,
    )


def point_in_polygon(point: Point, polygon: list[Point]) -> bool:
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        pi = polygon[i]
        pj = polygon[j]
        denominator = pj.y - pi.y
        if abs(denominator) < 1e-9:
            j = i
            continue
        intersects = ((pi.y > point.y) != (pj.y > point.y)) and (
            point.x < (pj.x - pi.x) * (point.y - pi.y) / denominator + pi.x
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def orientation(a: Point, b: Point, c: Point) -> float:
    return (b.y - a.y) * (c.x - b.x) - (b.x - a.x) * (c.y - b.y)


def on_segment(a: Point, b: Point, c: Point) -> bool:
    return (
        min(a.x, c.x) - 1e-9 <= b.x <= max(a.x, c.x) + 1e-9
        and min(a.y, c.y) - 1e-9 <= b.y <= max(a.y, c.y) + 1e-9
    )


def segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    o1 = orientation(a, b, c)
    o2 = orientation(a, b, d)
    o3 = orientation(c, d, a)
    o4 = orientation(c, d, b)

    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    if abs(o1) < 1e-9 and on_segment(a, c, b):
        return True
    if abs(o2) < 1e-9 and on_segment(a, d, b):
        return True
    if abs(o3) < 1e-9 and on_segment(c, a, d):
        return True
    if abs(o4) < 1e-9 and on_segment(c, b, d):
        return True
    return False
