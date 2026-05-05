from __future__ import annotations

import heapq
import json
import math
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_OSM_FEATURES_PATH = ROOT / "unity" / "MetaSW" / "Assets" / "Data" / "osm_features.json"

METERS_PER_LAT = 111_320.0


@dataclass(frozen=True)
class GraphNode:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class RoutePlan:
    reachable: bool
    distance_meters: float
    path: list[dict]
    access_distance_meters: float = 0.0
    reason: str = ""


class WalkableRouteGraph:
    def __init__(
        self,
        nodes: list[GraphNode],
        adjacency: list[list[tuple[int, float]]],
        movement_rules: object | None = None,
        blocked_polygons: list[dict] | None = None,
        strict_blocked_polygons: list[dict] | None = None,
    ) -> None:
        self.nodes = nodes
        self.adjacency = adjacency
        self.movement_rules = movement_rules
        self.blocked_polygons = blocked_polygons or []
        self.strict_blocked_polygons = strict_blocked_polygons or []
        self.blocked_clearance_meters = (
            float(getattr(movement_rules, "blocked_clearance_meters", 0.0))
            if movement_rules is not None
            else 0.0
        )
        self._nearest_cache: dict[tuple[float, float], int] = {}
        self._distance_cache: dict[int, list[float]] = {}
        self._path_cache: dict[tuple[int, int], tuple[float, list[int]]] = {}
        self._direct_blocked_cache: dict[tuple[float, float, float, float], bool] = {}
        self._direct_strict_cache: dict[tuple[float, float, float, float], bool] = {}

    @classmethod
    def from_osm_features(
        cls,
        path: Path = DEFAULT_OSM_FEATURES_PATH,
        movement_rules: object | None = None,
    ) -> "WalkableRouteGraph":
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        node_index_by_key: dict[tuple[int, int], int] = {}
        nodes: list[GraphNode] = []
        edge_map: dict[int, dict[int, float]] = {}
        blocked_polygons = []
        strict_blocked_polygons = []
        if movement_rules is not None and getattr(movement_rules, "block_osm_buildings", True):
            buildings = payload.get("buildings", [])
            blocked_polygons.extend(buildings)
            strict_blocked_polygons.extend(buildings)
        if movement_rules is not None and getattr(movement_rules, "block_osm_blocked_areas", True):
            blocked_areas = payload.get("blockedAreas", [])
            blocked_polygons.extend(blocked_areas)
            blocked_polygons.extend(payload.get("excludedZones", []))
            strict_blocked_polygons.extend(
                area for area in blocked_areas if str(area.get("natural", "")).lower() == "water"
            )
        if movement_rules is not None:
            manual_blocked_polygons = [
                {"id": area.id, "name": area.name, "points": area.points}
                for area in getattr(movement_rules, "manual_blocked_areas", []) or []
            ]
            blocked_polygons.extend(manual_blocked_polygons)
            strict_blocked_polygons.extend(manual_blocked_polygons)

        def get_node_index(point: dict) -> int:
            lat = float(point["latitude"])
            lon = float(point["longitude"])
            key = (round(lat, 7), round(lon, 7))
            if key in node_index_by_key:
                return node_index_by_key[key]
            node_index = len(nodes)
            node_index_by_key[key] = node_index
            nodes.append(GraphNode(latitude=lat, longitude=lon))
            edge_map[node_index] = {}
            return node_index

        for way in payload.get("walkableWays", []):
            indices = [get_node_index(point) for point in way.get("points", [])]
            for left, right in zip(indices, indices[1:]):
                if edge_crosses_blocked_polygon(
                    nodes[left],
                    nodes[right],
                    blocked_polygons,
                    ignore_natural_water=True,
                    clearance_meters=float(getattr(movement_rules, "blocked_clearance_meters", 0.0))
                    if movement_rules is not None
                    else 0.0,
                ):
                    continue
                distance = distance_meters(
                    nodes[left].latitude,
                    nodes[left].longitude,
                    nodes[right].latitude,
                    nodes[right].longitude,
                )
                if distance <= 0:
                    continue
                edge_map[left][right] = min(distance, edge_map[left].get(right, distance))
                edge_map[right][left] = min(distance, edge_map[right].get(left, distance))

        adjacency = [
            [(neighbor, weight) for neighbor, weight in edge_map[index].items()]
            for index in range(len(nodes))
        ]
        return cls(
            nodes=nodes,
            adjacency=adjacency,
            movement_rules=movement_rules,
            blocked_polygons=blocked_polygons,
            strict_blocked_polygons=strict_blocked_polygons,
        )

    def nearest_node_index(self, latitude: float, longitude: float) -> int:
        key = (round(latitude, 7), round(longitude, 7))
        cached = self._nearest_cache.get(key)
        if cached is not None:
            return cached

        nearest_index = 0
        nearest_distance = float("inf")
        for index, node in enumerate(self.nodes):
            distance = distance_meters(latitude, longitude, node.latitude, node.longitude)
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_index = index

        self._nearest_cache[key] = nearest_index
        return nearest_index

    def shortest_distances_from(self, start_index: int) -> list[float]:
        cached = self._distance_cache.get(start_index)
        if cached is not None:
            return cached

        distances = [float("inf")] * len(self.nodes)
        distances[start_index] = 0.0
        queue = [(0.0, start_index)]

        while queue:
            current_distance, current = heapq.heappop(queue)
            if current_distance > distances[current]:
                continue
            for neighbor, weight in self.adjacency[current]:
                next_distance = current_distance + weight
                if next_distance < distances[neighbor]:
                    distances[neighbor] = next_distance
                    heapq.heappush(queue, (next_distance, neighbor))

        self._distance_cache[start_index] = distances
        return distances

    def shortest_path_indices(self, start_index: int, goal_index: int) -> tuple[float, list[int]]:
        cache_key = (start_index, goal_index)
        cached = self._path_cache.get(cache_key)
        if cached is not None:
            return cached

        distances = [float("inf")] * len(self.nodes)
        previous = [-1] * len(self.nodes)
        distances[start_index] = 0.0
        queue = [(0.0, start_index)]

        while queue:
            current_distance, current = heapq.heappop(queue)
            if current == goal_index:
                break
            if current_distance > distances[current]:
                continue
            for neighbor, weight in self.adjacency[current]:
                next_distance = current_distance + weight
                if next_distance < distances[neighbor]:
                    distances[neighbor] = next_distance
                    previous[neighbor] = current
                    heapq.heappush(queue, (next_distance, neighbor))

        if math.isinf(distances[goal_index]):
            result = (float("inf"), [])
            self._path_cache[cache_key] = result
            return result

        path = []
        current = goal_index
        while current != -1:
            path.append(current)
            if current == start_index:
                break
            current = previous[current]
        path.reverse()
        result = (distances[goal_index], path)
        self._path_cache[cache_key] = result
        return result

    def shortest_distance_between_points(
        self,
        from_latitude: float,
        from_longitude: float,
        to_latitude: float,
        to_longitude: float,
    ) -> float:
        if self.is_trash_excluded(to_latitude, to_longitude):
            return float("inf")
        if self.is_point_blocked(to_latitude, to_longitude):
            return float("inf")

        start = self.nearest_node_index(from_latitude, from_longitude)
        goal = self.nearest_node_index(to_latitude, to_longitude)
        snap_start = self.nodes[start]
        snap_goal = self.nodes[goal]
        if not self.can_travel_direct_avoiding_strict_blocked(
            from_latitude,
            from_longitude,
            snap_start.latitude,
            snap_start.longitude,
        ):
            return float("inf")
        if not self.can_travel_direct_avoiding_strict_blocked(
            snap_goal.latitude,
            snap_goal.longitude,
            to_latitude,
            to_longitude,
        ):
            return float("inf")
        graph_distance = self.shortest_distances_from(start)[goal]
        if math.isinf(graph_distance):
            return float("inf")

        pickup_access = distance_meters(snap_goal.latitude, snap_goal.longitude, to_latitude, to_longitude)
        if pickup_access > self.pickup_access_radius_meters() and not self.is_point_manually_allowed(
            to_latitude,
            to_longitude,
        ):
            return float("inf")

        return (
            distance_meters(from_latitude, from_longitude, snap_start.latitude, snap_start.longitude)
            + graph_distance
            + pickup_access
        )

    def shortest_route_between_points(
        self,
        from_latitude: float,
        from_longitude: float,
        to_latitude: float,
        to_longitude: float,
    ) -> RoutePlan:
        if self.is_trash_excluded(to_latitude, to_longitude):
            return RoutePlan(False, float("inf"), [], reason="trash_excluded")

        if self.is_point_blocked(to_latitude, to_longitude):
            return RoutePlan(False, float("inf"), [], reason="target_blocked")

        start = self.nearest_node_index(from_latitude, from_longitude)
        goal = self.nearest_node_index(to_latitude, to_longitude)
        snap_start = self.nodes[start]
        snap_goal = self.nodes[goal]
        if not self.can_travel_direct_avoiding_strict_blocked(
            from_latitude,
            from_longitude,
            snap_start.latitude,
            snap_start.longitude,
        ):
            return RoutePlan(False, float("inf"), [], reason="start_access_blocked")
        if not self.can_travel_direct_avoiding_strict_blocked(
            snap_goal.latitude,
            snap_goal.longitude,
            to_latitude,
            to_longitude,
        ):
            return RoutePlan(False, float("inf"), [], reason="target_access_blocked")
        graph_distance, graph_path = self.shortest_path_indices(start, goal)
        if math.isinf(graph_distance) or not graph_path:
            return RoutePlan(False, float("inf"), [], reason="no_walkable_route")

        start_access = distance_meters(from_latitude, from_longitude, snap_start.latitude, snap_start.longitude)
        pickup_access = distance_meters(snap_goal.latitude, snap_goal.longitude, to_latitude, to_longitude)
        pickup_radius = self.pickup_access_radius_meters()
        target_manually_allowed = self.is_point_manually_allowed(to_latitude, to_longitude)
        if pickup_access > pickup_radius and not target_manually_allowed:
            return RoutePlan(
                False,
                float("inf"),
                [],
                access_distance_meters=pickup_access,
                reason="target_too_far_from_walkable_route",
            )

        path = [{"latitude": from_latitude, "longitude": from_longitude}]
        for node_index in graph_path:
            node = self.nodes[node_index]
            path.append({"latitude": node.latitude, "longitude": node.longitude})
        path.append({"latitude": to_latitude, "longitude": to_longitude})

        distance = start_access + graph_distance + pickup_access
        return RoutePlan(True, distance, collapse_duplicate_points(path), pickup_access)

    def pickup_access_radius_meters(self) -> float:
        if self.movement_rules is None:
            return 15.0
        return float(getattr(self.movement_rules, "pickup_access_radius_meters", 15.0))

    def is_point_manually_allowed(self, latitude: float, longitude: float) -> bool:
        if self.movement_rules is None:
            return False
        return bool(getattr(self.movement_rules, "is_point_manually_allowed")(latitude, longitude))

    def is_trash_excluded(self, latitude: float, longitude: float) -> bool:
        if self.movement_rules is None:
            return False
        return bool(getattr(self.movement_rules, "is_trash_excluded")(latitude, longitude))

    def is_point_blocked(self, latitude: float, longitude: float) -> bool:
        if self.is_point_manually_allowed(latitude, longitude):
            return False
        if self.movement_rules is not None and bool(
            getattr(self.movement_rules, "is_point_manually_blocked")(latitude, longitude)
        ):
            return True
        for polygon in self.blocked_polygons:
            points = polygon.get("points", [])
            if len(points) >= 3 and point_in_latlon_polygon(latitude, longitude, points):
                return True
        return False

    def can_travel_direct_between_points(
        self,
        from_latitude: float,
        from_longitude: float,
        to_latitude: float,
        to_longitude: float,
    ) -> bool:
        cache_key = normalized_segment_key(from_latitude, from_longitude, to_latitude, to_longitude)
        cached = self._direct_blocked_cache.get(cache_key)
        if cached is not None:
            return cached
        if self.is_point_blocked(from_latitude, from_longitude):
            self._direct_blocked_cache[cache_key] = False
            return False
        if self.is_point_blocked(to_latitude, to_longitude):
            self._direct_blocked_cache[cache_key] = False
            return False
        can_travel = not edge_crosses_blocked_polygon(
            GraphNode(from_latitude, from_longitude),
            GraphNode(to_latitude, to_longitude),
            self.blocked_polygons,
            clearance_meters=self.blocked_clearance_meters,
        )
        self._direct_blocked_cache[cache_key] = can_travel
        return can_travel

    def can_travel_direct_avoiding_strict_blocked(
        self,
        from_latitude: float,
        from_longitude: float,
        to_latitude: float,
        to_longitude: float,
    ) -> bool:
        cache_key = normalized_segment_key(from_latitude, from_longitude, to_latitude, to_longitude)
        cached = self._direct_strict_cache.get(cache_key)
        if cached is not None:
            return cached
        if not self.strict_blocked_polygons:
            self._direct_strict_cache[cache_key] = True
            return True
        if edge_crosses_blocked_polygon(
            GraphNode(from_latitude, from_longitude),
            GraphNode(to_latitude, to_longitude),
            self.strict_blocked_polygons,
            clearance_meters=self.blocked_clearance_meters,
        ):
            self._direct_strict_cache[cache_key] = False
            return False
        self._direct_strict_cache[cache_key] = True
        return True


def collapse_duplicate_points(path: list[dict]) -> list[dict]:
    collapsed = []
    for point in path:
        if collapsed:
            previous = collapsed[-1]
            if (
                abs(float(previous["latitude"]) - float(point["latitude"])) < 1e-10
                and abs(float(previous["longitude"]) - float(point["longitude"])) < 1e-10
            ):
                continue
        collapsed.append(point)
    return collapsed


def normalized_segment_key(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float, float, float]:
    left = (round(lat1, 7), round(lon1, 7))
    right = (round(lat2, 7), round(lon2, 7))
    if right < left:
        left, right = right, left
    return left[0], left[1], right[0], right[1]


def point_in_latlon_polygon(latitude: float, longitude: float, polygon: list[dict]) -> bool:
    x = longitude
    y = latitude
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        pi = polygon[i]
        pj = polygon[j]
        xi = float(pi["longitude"])
        yi = float(pi["latitude"])
        xj = float(pj["longitude"])
        yj = float(pj["latitude"])
        denominator = yj - yi
        if abs(denominator) < 1e-12:
            j = i
            continue
        intersects = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / denominator + xi)
        if intersects:
            inside = not inside
        j = i
    return inside


def edge_crosses_blocked_polygon(
    left: GraphNode,
    right: GraphNode,
    blocked_polygons: list[dict],
    ignore_natural_water: bool = False,
    clearance_meters: float = 0.0,
) -> bool:
    min_lat = min(left.latitude, right.latitude)
    max_lat = max(left.latitude, right.latitude)
    min_lon = min(left.longitude, right.longitude)
    max_lon = max(left.longitude, right.longitude)
    clearance_degrees = clearance_meters / METERS_PER_LAT if clearance_meters > 0 else 0.0
    for polygon in blocked_polygons:
        if ignore_natural_water and str(polygon.get("natural", "")).lower() == "water":
            continue
        points = polygon.get("points", [])
        if len(points) < 3:
            continue
        bounds = polygon.get("_bounds")
        if bounds is None:
            bounds = polygon_bounds(points)
            polygon["_bounds"] = bounds
        poly_min_lat, poly_max_lat, poly_min_lon, poly_max_lon = bounds
        if (
            max_lat < poly_min_lat - clearance_degrees
            or min_lat > poly_max_lat + clearance_degrees
            or max_lon < poly_min_lon - clearance_degrees
            or min_lon > poly_max_lon + clearance_degrees
        ):
            continue
        if point_in_latlon_polygon(left.latitude, left.longitude, points):
            return True
        if point_in_latlon_polygon(right.latitude, right.longitude, points):
            return True
        if segment_intersects_latlon_polygon(left.latitude, left.longitude, right.latitude, right.longitude, points):
            return True
        if clearance_meters > 0 and segment_distance_to_latlon_polygon_meters(
            left.latitude,
            left.longitude,
            right.latitude,
            right.longitude,
            points,
        ) <= clearance_meters:
            return True
    return False


def polygon_bounds(points: list[dict]) -> tuple[float, float, float, float]:
    latitudes = [float(point["latitude"]) for point in points]
    longitudes = [float(point["longitude"]) for point in points]
    return min(latitudes), max(latitudes), min(longitudes), max(longitudes)


def segment_intersects_latlon_polygon(lat1: float, lon1: float, lat2: float, lon2: float, polygon: list[dict]) -> bool:
    for left, right in zip(polygon, polygon[1:] + polygon[:1]):
        if segments_intersect_latlon(
            lon1,
            lat1,
            lon2,
            lat2,
            float(left["longitude"]),
            float(left["latitude"]),
            float(right["longitude"]),
            float(right["latitude"]),
        ):
            return True
    return False


def segment_distance_to_latlon_polygon_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    polygon: list[dict],
) -> float:
    if not polygon:
        return float("inf")

    origin_lat = (lat1 + lat2) * 0.5
    origin_lon = (lon1 + lon2) * 0.5
    ax, ay = project_to_local_meters(lat1, lon1, origin_lat, origin_lon)
    bx, by = project_to_local_meters(lat2, lon2, origin_lat, origin_lon)

    best = float("inf")
    for left, right in zip(polygon, polygon[1:] + polygon[:1]):
        cx, cy = project_to_local_meters(
            float(left["latitude"]),
            float(left["longitude"]),
            origin_lat,
            origin_lon,
        )
        dx, dy = project_to_local_meters(
            float(right["latitude"]),
            float(right["longitude"]),
            origin_lat,
            origin_lon,
        )
        best = min(best, segment_distance_meters_2d(ax, ay, bx, by, cx, cy, dx, dy))
    return best


def project_to_local_meters(latitude: float, longitude: float, origin_latitude: float, origin_longitude: float) -> tuple[float, float]:
    meters_per_lon = METERS_PER_LAT * math.cos(math.radians(origin_latitude))
    return (
        (longitude - origin_longitude) * meters_per_lon,
        (latitude - origin_latitude) * METERS_PER_LAT,
    )


def segment_distance_meters_2d(
    ax: float,
    ay: float,
    bx: float,
    by: float,
    cx: float,
    cy: float,
    dx: float,
    dy: float,
) -> float:
    if segments_intersect_xy(ax, ay, bx, by, cx, cy, dx, dy):
        return 0.0
    return min(
        point_segment_distance_meters(ax, ay, cx, cy, dx, dy),
        point_segment_distance_meters(bx, by, cx, cy, dx, dy),
        point_segment_distance_meters(cx, cy, ax, ay, bx, by),
        point_segment_distance_meters(dx, dy, ax, ay, bx, by),
    )


def point_segment_distance_meters(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx = bx - ax
    dy = by - ay
    denom = dx * dx + dy * dy
    if denom <= 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
    closest_x = ax + t * dx
    closest_y = ay + t * dy
    return math.hypot(px - closest_x, py - closest_y)


def segments_intersect_xy(ax: float, ay: float, bx: float, by: float, cx: float, cy: float, dx: float, dy: float) -> bool:
    def orient(px: float, py: float, qx: float, qy: float, rx: float, ry: float) -> float:
        return (qy - py) * (rx - qx) - (qx - px) * (ry - qy)

    def on_segment(px: float, py: float, qx: float, qy: float, rx: float, ry: float) -> bool:
        return min(px, rx) <= qx <= max(px, rx) and min(py, ry) <= qy <= max(py, ry)

    o1 = orient(ax, ay, bx, by, cx, cy)
    o2 = orient(ax, ay, bx, by, dx, dy)
    o3 = orient(cx, cy, dx, dy, ax, ay)
    o4 = orient(cx, cy, dx, dy, bx, by)

    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    if abs(o1) < 1e-9 and on_segment(ax, ay, cx, cy, bx, by):
        return True
    if abs(o2) < 1e-9 and on_segment(ax, ay, dx, dy, bx, by):
        return True
    if abs(o3) < 1e-9 and on_segment(cx, cy, ax, ay, dx, dy):
        return True
    if abs(o4) < 1e-9 and on_segment(cx, cy, bx, by, dx, dy):
        return True
    return False


def segments_intersect_latlon(ax: float, ay: float, bx: float, by: float, cx: float, cy: float, dx: float, dy: float) -> bool:
    def orient(px: float, py: float, qx: float, qy: float, rx: float, ry: float) -> float:
        return (qy - py) * (rx - qx) - (qx - px) * (ry - qy)

    def on_segment(px: float, py: float, qx: float, qy: float, rx: float, ry: float) -> bool:
        return (
            min(px, rx) - 1e-12 <= qx <= max(px, rx) + 1e-12
            and min(py, ry) - 1e-12 <= qy <= max(py, ry) + 1e-12
        )

    o1 = orient(ax, ay, bx, by, cx, cy)
    o2 = orient(ax, ay, bx, by, dx, dy)
    o3 = orient(cx, cy, dx, dy, ax, ay)
    o4 = orient(cx, cy, dx, dy, bx, by)

    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    if abs(o1) < 1e-12 and on_segment(ax, ay, cx, cy, bx, by):
        return True
    if abs(o2) < 1e-12 and on_segment(ax, ay, dx, dy, bx, by):
        return True
    if abs(o3) < 1e-12 and on_segment(cx, cy, ax, ay, dx, dy):
        return True
    if abs(o4) < 1e-12 and on_segment(cx, cy, bx, by, dx, dy):
        return True
    return False


def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    avg_lat_rad = math.radians((lat1 + lat2) * 0.5)
    meters_per_lon = METERS_PER_LAT * math.cos(avg_lat_rad)
    d_lat = (lat2 - lat1) * METERS_PER_LAT
    d_lon = (lon2 - lon1) * meters_per_lon
    return math.hypot(d_lat, d_lon)
