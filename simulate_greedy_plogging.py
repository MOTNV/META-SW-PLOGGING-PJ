from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass, asdict
from pathlib import Path

from movement_rules import DEFAULT_MOVEMENT_RULES_PATH, MovementRules
from walkable_route_graph import DEFAULT_OSM_FEATURES_PATH, WalkableRouteGraph
from obstacle_aware_distance import ObstacleAwareDistance

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    tqdm = None


ROOT = Path(__file__).resolve().parent
DEFAULT_ZONE_PATH = ROOT / "simulation" / "simple_zones.json"
DEFAULT_ASSIGNMENT_PATH = ROOT / "simulation" / "assignments" / "trash_priority_assignment.json"
DEFAULT_OUTPUT_PATH = ROOT / "simulation" / "greedy_simulation_result.json"

SIZE_WEIGHT = {
    "small": 1,
    "medium": 2,
    "large": 3,
}

METERS_PER_LAT = 111_320.0
DIRECT_REACHABILITY_CACHE: dict[tuple[float, float, int], bool] = {}


@dataclass
class AgentState:
    agent_id: str
    assigned_zone_id: str
    latitude: float
    longitude: float
    speed_mps: float
    target_trash_index: int | None = None
    collected_mass: int = 0
    collected_count: int = 0
    travel_distance_m: float = 0.0
    idle_time_s: float = 0.0
    collect_time_remaining_s: float = 0.0
    route_time_remaining_s: float = 0.0
    route_start_latitude: float | None = None
    route_start_longitude: float | None = None
    route_target_latitude: float | None = None
    route_target_longitude: float | None = None
    route_total_time_s: float = 0.0
    route_path: list[dict] | None = None
    route_distance_traveled_m: float = 0.0
    route_total_distance_m: float = 0.0
    cleanup_anchor_latitude: float | None = None
    cleanup_anchor_longitude: float | None = None
    force_direct_target: bool = False


@dataclass
class TrashState:
    trash_index: int
    zone_id: str
    latitude: float
    longitude: float
    trash_count: int
    trash_mass: int
    collected: bool = False
    walkable_node_index: int | None = None
    pickup_access_distance_m: float = 0.0
    pickup_latitude: float | None = None
    pickup_longitude: float | None = None
    pickup_mode: str = "trash_location"
    reachable: bool = True
    unreachable_reason: str = ""


def trash_pickup_latitude(trash: TrashState) -> float:
    return trash.latitude if trash.pickup_latitude is None else trash.pickup_latitude


def trash_pickup_longitude(trash: TrashState) -> float:
    return trash.longitude if trash.pickup_longitude is None else trash.pickup_longitude


def allow_off_path_direct_movement(route_graph: WalkableRouteGraph | ObstacleAwareDistance | None) -> bool:
    return isinstance(route_graph, WalkableRouteGraph) and bool(
        getattr(route_graph.movement_rules, "allow_off_path_pickup", True)
    )


def allow_local_direct_pickup(
    route_graph: WalkableRouteGraph | ObstacleAwareDistance | None,
    agent: AgentState,
    trash: TrashState,
    direct_distance_meters: float,
    local_cleanup_radius_meters: float,
) -> bool:
    if not (
        allow_off_path_direct_movement(route_graph)
        and local_cleanup_radius_meters > 0.0
        and direct_distance_meters <= local_cleanup_radius_meters
    ):
        return False
    if isinstance(route_graph, WalkableRouteGraph):
        return route_graph.can_travel_direct_avoiding_strict_blocked(
            agent.latitude,
            agent.longitude,
            trash_pickup_latitude(trash),
            trash_pickup_longitude(trash),
        )
    return True


def can_travel_direct_to_trash(
    agent: AgentState,
    trash: TrashState,
    route_graph: WalkableRouteGraph,
) -> bool:
    target_latitude = trash_pickup_latitude(trash)
    target_longitude = trash_pickup_longitude(trash)
    cache_key = (round(agent.latitude, 7), round(agent.longitude, 7), trash.trash_index)
    can_reach = DIRECT_REACHABILITY_CACHE.get(cache_key)
    if can_reach is None:
        can_reach = route_graph.can_travel_direct_between_points(
            agent.latitude,
            agent.longitude,
            target_latitude,
            target_longitude,
        )
        DIRECT_REACHABILITY_CACHE[cache_key] = can_reach
    return can_reach


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a simple greedy plogging simulation.")
    parser.add_argument("--zones", type=Path, default=DEFAULT_ZONE_PATH)
    parser.add_argument("--assignment", type=Path, default=DEFAULT_ASSIGNMENT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--step-seconds", type=float, default=1.0)
    parser.add_argument("--max-seconds", type=float, default=1800.0)
    parser.add_argument("--agent-speed", type=float, default=1.2)
    parser.add_argument("--spawn-seed", type=int, default=42)
    parser.add_argument("--collect-seconds", type=float, default=3.0)
    parser.add_argument(
        "--distance-mode",
        choices=["straight", "route", "obstacle"],
        default="route",
        help="straight uses direct distance; route uses OSM walkable graph; obstacle uses straight movement with blocked-area detours.",
    )
    parser.add_argument("--osm-features", type=Path, default=DEFAULT_OSM_FEATURES_PATH)
    parser.add_argument("--movement-rules", type=Path, default=DEFAULT_MOVEMENT_RULES_PATH)
    parser.add_argument(
        "--local-cleanup-radius",
        type=float,
        default=0.0,
        help="If greater than zero, keep cleaning trash within this cluster radius before choosing a global route target.",
    )
    parser.add_argument(
        "--max-target-route-distance",
        type=float,
        default=0.0,
        help="Do not assign a new trash target if the route distance is longer than this many meters. 0 disables this limit.",
    )
    parser.add_argument(
        "--blocked-pickup-access-radius",
        type=float,
        default=80.0,
        help="Allow trash inside blocked areas to be collected from the nearest walkable graph node within this many meters.",
    )
    parser.add_argument(
        "--allow-duplicate-targets",
        dest="allow_duplicate_targets",
        action="store_true",
        default=True,
        help="Allow multiple agents to target the same trash record.",
    )
    parser.add_argument(
        "--prevent-duplicate-targets",
        dest="allow_duplicate_targets",
        action="store_false",
        help="Prevent multiple agents from targeting the same trash record.",
    )
    parser.add_argument("--no-progress", action="store_true", help="Disable tqdm progress bars.")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def calculate_trash_metrics(items: list[dict]) -> tuple[int, int]:
    total_count = 0
    total_mass = 0
    for item in items or []:
        quantity = max(1, int(item.get("quantity", 1)))
        size = str(item.get("size", "small")).strip().lower()
        weight = SIZE_WEIGHT.get(size, 1)
        total_count += quantity
        total_mass += quantity * weight
    return total_count, total_mass


def build_zone_lookup(zone_payload: dict) -> dict[str, dict]:
    return {zone["zoneId"]: zone for zone in zone_payload["zones"]}


def build_trash_states(zone_payload: dict) -> list[TrashState]:
    trash_states: list[TrashState] = []
    for record in zone_payload["trashRecords"]:
        trash_count, trash_mass = calculate_trash_metrics(record.get("items") or [])
        if trash_count <= 0 or trash_mass <= 0:
            continue

        trash_states.append(
            TrashState(
                trash_index=int(record["recordIndex"]),
                zone_id=record["zoneId"],
                latitude=float(record["latitude"]),
                longitude=float(record["longitude"]),
                trash_count=trash_count,
                trash_mass=trash_mass,
            )
        )
    return trash_states


def attach_trash_to_walkable_graph(
    trash_states: list[TrashState],
    route_graph: WalkableRouteGraph | ObstacleAwareDistance | None,
    blocked_pickup_access_radius_meters: float = 80.0,
) -> None:
    if not isinstance(route_graph, WalkableRouteGraph):
        return

    pickup_access_radius = route_graph.pickup_access_radius_meters()
    blocked_pickup_access_radius_meters = max(blocked_pickup_access_radius_meters, pickup_access_radius)
    allow_off_path_pickup = bool(getattr(route_graph.movement_rules, "allow_off_path_pickup", True))

    for trash in trash_states:
        if route_graph.is_trash_excluded(trash.latitude, trash.longitude):
            trash.reachable = False
            trash.unreachable_reason = "trash_excluded"
            continue
        if route_graph.is_point_blocked(trash.latitude, trash.longitude):
            node_index = route_graph.nearest_node_index(trash.latitude, trash.longitude)
            node = route_graph.nodes[node_index]
            access_distance = distance_meters(node.latitude, node.longitude, trash.latitude, trash.longitude)
            if access_distance > blocked_pickup_access_radius_meters:
                trash.reachable = False
                trash.unreachable_reason = "target_blocked"
                trash.walkable_node_index = node_index
                trash.pickup_access_distance_m = access_distance
                continue
            trash.walkable_node_index = node_index
            trash.pickup_access_distance_m = 0.0
            trash.pickup_latitude = node.latitude
            trash.pickup_longitude = node.longitude
            trash.pickup_mode = "blocked_area_nearest_walkable"
            trash.reachable = True
            continue

        node_index = route_graph.nearest_node_index(trash.latitude, trash.longitude)
        node = route_graph.nodes[node_index]
        access_distance = distance_meters(node.latitude, node.longitude, trash.latitude, trash.longitude)
        if not route_graph.can_travel_direct_avoiding_strict_blocked(
            node.latitude,
            node.longitude,
            trash.latitude,
            trash.longitude,
        ):
            trash.walkable_node_index = node_index
            trash.pickup_access_distance_m = 0.0
            trash.pickup_latitude = node.latitude
            trash.pickup_longitude = node.longitude
            trash.pickup_mode = "strict_access_nearest_walkable"
            trash.reachable = True
            continue
        if (
            access_distance > pickup_access_radius
            and not allow_off_path_pickup
            and not route_graph.is_point_manually_allowed(
            trash.latitude,
            trash.longitude,
            )
        ):
            trash.reachable = False
            trash.unreachable_reason = "target_too_far_from_walkable_route"
            trash.walkable_node_index = node_index
            trash.pickup_access_distance_m = access_distance
            continue

        trash.walkable_node_index = node_index
        trash.pickup_access_distance_m = access_distance
        trash.reachable = True


def spawn_agents(
    assignment_payload: dict,
    zone_lookup: dict[str, dict],
    speed_mps: float,
    route_graph: WalkableRouteGraph | ObstacleAwareDistance | None,
    spawn_seed: int,
) -> list[AgentState]:
    agents: list[AgentState] = []
    rng = random.Random(spawn_seed)

    for zone in assignment_payload["zones"]:
        assigned_count = int(zone.get("assignedAgentCount", 0))
        if assigned_count <= 0:
            continue

        zone_id = zone["zoneId"]
        zone_info = zone_lookup[zone_id]

        for index in range(assigned_count):
            lat, lon = make_random_spawn_point(zone_info, route_graph, rng)
            agents.append(
                AgentState(
                    agent_id=f"{zone_id}_A{index:02d}",
                    assigned_zone_id=zone_id,
                    latitude=lat,
                    longitude=lon,
                    speed_mps=speed_mps,
                )
            )

    return agents


def make_random_spawn_point(
    zone_info: dict,
    route_graph: WalkableRouteGraph | ObstacleAwareDistance | None,
    rng: random.Random,
) -> tuple[float, float]:
    min_lat = float(zone_info["minLatitude"])
    max_lat = float(zone_info["maxLatitude"])
    min_lon = float(zone_info["minLongitude"])
    max_lon = float(zone_info["maxLongitude"])

    for _ in range(500):
        lat = rng.uniform(min_lat, max_lat)
        lon = rng.uniform(min_lon, max_lon)
        if not isinstance(route_graph, WalkableRouteGraph) or not route_graph.is_point_blocked(lat, lon):
            return lat, lon

    if isinstance(route_graph, WalkableRouteGraph):
        candidate_nodes = [
            (index, node)
            for index, node in enumerate(route_graph.nodes)
            if min_lat <= node.latitude <= max_lat
            and min_lon <= node.longitude <= max_lon
            and route_graph.adjacency[index]
            and not route_graph.is_point_blocked(node.latitude, node.longitude)
        ]
        if candidate_nodes:
            _, node = rng.choice(candidate_nodes)
            return node.latitude, node.longitude

    return (min_lat + max_lat) * 0.5, (min_lon + max_lon) * 0.5


def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    avg_lat_rad = math.radians((lat1 + lat2) * 0.5)
    meters_per_lon = METERS_PER_LAT * math.cos(avg_lat_rad)
    d_lat = (lat2 - lat1) * METERS_PER_LAT
    d_lon = (lon2 - lon1) * meters_per_lon
    return math.hypot(d_lat, d_lon)


def move_toward(lat1: float, lon1: float, lat2: float, lon2: float, max_step_m: float) -> tuple[float, float, float]:
    total_distance = distance_meters(lat1, lon1, lat2, lon2)
    if total_distance <= max_step_m or total_distance <= 1e-6:
        return lat2, lon2, total_distance

    ratio = max_step_m / total_distance
    next_lat = lat1 + (lat2 - lat1) * ratio
    next_lon = lon1 + (lon2 - lon1) * ratio
    return next_lat, next_lon, max_step_m


def interpolate_route_path(path: list[dict], distance_along_m: float) -> tuple[float, float]:
    if not path:
        raise ValueError("route path is empty")
    if len(path) == 1 or distance_along_m <= 0:
        return float(path[0]["latitude"]), float(path[0]["longitude"])

    remaining = distance_along_m
    for left, right in zip(path, path[1:]):
        left_lat = float(left["latitude"])
        left_lon = float(left["longitude"])
        right_lat = float(right["latitude"])
        right_lon = float(right["longitude"])
        segment = distance_meters(left_lat, left_lon, right_lat, right_lon)
        if segment <= 1e-9:
            continue
        if remaining <= segment:
            ratio = remaining / segment
            return (
                left_lat + (right_lat - left_lat) * ratio,
                left_lon + (right_lon - left_lon) * ratio,
            )
        remaining -= segment

    final = path[-1]
    return float(final["latitude"]), float(final["longitude"])


def estimate_distance_meters(
    agent: AgentState,
    trash: TrashState,
    route_graph: WalkableRouteGraph | ObstacleAwareDistance | None,
) -> float:
    target_latitude = trash_pickup_latitude(trash)
    target_longitude = trash_pickup_longitude(trash)
    if route_graph is None:
        return distance_meters(agent.latitude, agent.longitude, target_latitude, target_longitude)
    return route_graph.shortest_distance_between_points(
        agent.latitude,
        agent.longitude,
        target_latitude,
        target_longitude,
    )


def build_route_plan(
    agent: AgentState,
    trash: TrashState,
    route_graph: WalkableRouteGraph | ObstacleAwareDistance | None,
) -> tuple[float, list[dict] | None, str]:
    target_latitude = trash_pickup_latitude(trash)
    target_longitude = trash_pickup_longitude(trash)
    if route_graph is None:
        distance = distance_meters(agent.latitude, agent.longitude, target_latitude, target_longitude)
        return distance, [
            {"latitude": agent.latitude, "longitude": agent.longitude},
            {"latitude": target_latitude, "longitude": target_longitude},
        ], ""

    if hasattr(route_graph, "shortest_route_between_points"):
        plan = route_graph.shortest_route_between_points(
            agent.latitude,
            agent.longitude,
            target_latitude,
            target_longitude,
        )
        return plan.distance_meters, plan.path if plan.reachable else None, plan.reason

    distance = route_graph.shortest_distance_between_points(
        agent.latitude,
        agent.longitude,
        target_latitude,
        target_longitude,
    )
    return distance, [
        {"latitude": agent.latitude, "longitude": agent.longitude},
        {"latitude": target_latitude, "longitude": target_longitude},
    ], ""


def clear_agent_route(agent: AgentState) -> None:
    agent.route_time_remaining_s = 0.0
    agent.route_total_time_s = 0.0
    agent.route_start_latitude = None
    agent.route_start_longitude = None
    agent.route_target_latitude = None
    agent.route_target_longitude = None
    agent.route_path = None
    agent.route_distance_traveled_m = 0.0
    agent.route_total_distance_m = 0.0
    agent.force_direct_target = False


def find_nearest_trash(
    agent: AgentState,
    trash_states: list[TrashState],
    route_graph: WalkableRouteGraph | ObstacleAwareDistance | None,
    claimed_trash_indices: set[int] | None = None,
    local_cleanup_radius_meters: float = 0.0,
    max_target_route_distance_meters: float = 0.0,
) -> TrashState | None:
    claimed_trash_indices = claimed_trash_indices or set()
    local_target = find_nearest_cleanup_cluster_trash(
        agent,
        trash_states,
        route_graph,
        claimed_trash_indices,
        local_cleanup_radius_meters,
        max_target_route_distance_meters,
    )
    if local_target is not None:
        return local_target
    agent.cleanup_anchor_latitude = None
    agent.cleanup_anchor_longitude = None

    if isinstance(route_graph, WalkableRouteGraph):
        graph_target = find_nearest_trash_on_walkable_graph(
            agent,
            trash_states,
            route_graph,
            claimed_trash_indices,
            max_target_route_distance_meters,
        )
        if graph_target is not None:
            return graph_target
        fallback_target = find_nearest_uncollected_trash_by_direct_distance(
            agent,
            trash_states,
            claimed_trash_indices,
            max_target_route_distance_meters,
        )
        if fallback_target is not None:
            agent.force_direct_target = True
        return fallback_target

    nearest = None
    nearest_distance = float("inf")

    for trash in trash_states:
        if trash.collected or not trash.reachable or trash.trash_index in claimed_trash_indices:
            continue

        dist = estimate_distance_meters(agent, trash, route_graph)
        if max_target_route_distance_meters > 0.0 and dist > max_target_route_distance_meters:
            continue
        if dist < nearest_distance:
            nearest_distance = dist
            nearest = trash

    return nearest


def find_nearest_uncollected_trash_by_direct_distance(
    agent: AgentState,
    trash_states: list[TrashState],
    claimed_trash_indices: set[int],
    max_target_route_distance_meters: float = 0.0,
) -> TrashState | None:
    nearest = None
    nearest_distance = float("inf")
    for trash in trash_states:
        if trash.collected or not trash.reachable or trash.trash_index in claimed_trash_indices:
            continue
        dist = distance_meters(
            agent.latitude,
            agent.longitude,
            trash_pickup_latitude(trash),
            trash_pickup_longitude(trash),
        )
        if max_target_route_distance_meters > 0.0 and dist > max_target_route_distance_meters:
            continue
        if dist < nearest_distance:
            nearest = trash
            nearest_distance = dist
    return nearest


def find_nearest_direct_reachable_trash(
    agent: AgentState,
    trash_states: list[TrashState],
    route_graph: WalkableRouteGraph,
    claimed_trash_indices: set[int],
    max_target_route_distance_meters: float = 0.0,
) -> TrashState | None:
    candidates: list[tuple[float, TrashState, float, float]] = []
    for trash in trash_states:
        if trash.collected or not trash.reachable or trash.trash_index in claimed_trash_indices:
            continue

        target_latitude = trash_pickup_latitude(trash)
        target_longitude = trash_pickup_longitude(trash)
        dist = distance_meters(agent.latitude, agent.longitude, target_latitude, target_longitude)
        if max_target_route_distance_meters > 0.0 and dist > max_target_route_distance_meters:
            continue
        candidates.append((dist, trash, target_latitude, target_longitude))

    candidates.sort(key=lambda item: item[0])
    for dist, trash, target_latitude, target_longitude in candidates:
        if not can_travel_direct_to_trash(agent, trash, route_graph):
            continue
        return trash
    return None


def find_nearest_cleanup_cluster_trash(
    agent: AgentState,
    trash_states: list[TrashState],
    route_graph: WalkableRouteGraph | ObstacleAwareDistance | None,
    claimed_trash_indices: set[int],
    local_cleanup_radius_meters: float,
    max_target_route_distance_meters: float,
) -> TrashState | None:
    if local_cleanup_radius_meters <= 0:
        return None
    nearest = None
    nearest_distance = float("inf")

    graph_distances = None
    start_access = 0.0
    if isinstance(route_graph, WalkableRouteGraph):
        start_index = route_graph.nearest_node_index(agent.latitude, agent.longitude)
        start_node = route_graph.nodes[start_index]
        start_access_ok = route_graph.can_travel_direct_avoiding_strict_blocked(
            agent.latitude,
            agent.longitude,
            start_node.latitude,
            start_node.longitude,
        )
        start_access = distance_meters(agent.latitude, agent.longitude, start_node.latitude, start_node.longitude)
        graph_distances = route_graph.shortest_distances_from(start_index) if start_access_ok else None

    for trash in trash_states:
        if trash.collected or not trash.reachable or trash.trash_index in claimed_trash_indices:
            continue

        target_latitude = trash_pickup_latitude(trash)
        target_longitude = trash_pickup_longitude(trash)
        current_direct_distance = distance_meters(
            agent.latitude,
            agent.longitude,
            target_latitude,
            target_longitude,
        )
        anchor_distance = float("inf")
        if agent.cleanup_anchor_latitude is not None and agent.cleanup_anchor_longitude is not None:
            anchor_distance = distance_meters(
                agent.cleanup_anchor_latitude,
                agent.cleanup_anchor_longitude,
                target_latitude,
                target_longitude,
            )
        if min(current_direct_distance, anchor_distance) > local_cleanup_radius_meters:
            continue

        if allow_local_direct_pickup(route_graph, agent, trash, current_direct_distance, local_cleanup_radius_meters):
            route_distance = current_direct_distance
        elif graph_distances is not None:
            if trash.walkable_node_index is None:
                continue
            target_node = route_graph.nodes[trash.walkable_node_index]
            target_access_ok = route_graph.can_travel_direct_avoiding_strict_blocked(
                target_node.latitude,
                target_node.longitude,
                target_latitude,
                target_longitude,
            )
            if not target_access_ok:
                continue
            graph_distance = graph_distances[trash.walkable_node_index]
            route_distance = (
                float("inf")
                if math.isinf(graph_distance)
                else start_access + graph_distance + trash.pickup_access_distance_m
            )
        else:
            route_distance = estimate_distance_meters(agent, trash, route_graph)
        if (
            allow_off_path_direct_movement(route_graph)
            and isinstance(route_graph, WalkableRouteGraph)
            and current_direct_distance < route_distance
            and can_travel_direct_to_trash(agent, trash, route_graph)
        ):
            route_distance = current_direct_distance
        if math.isinf(route_distance) or (
            max_target_route_distance_meters > 0.0 and route_distance > max_target_route_distance_meters
        ):
            continue

        candidate_distance = current_direct_distance
        if candidate_distance < nearest_distance:
            nearest = trash
            nearest_distance = candidate_distance
    return nearest


def find_nearest_trash_on_walkable_graph(
    agent: AgentState,
    trash_states: list[TrashState],
    route_graph: WalkableRouteGraph,
    claimed_trash_indices: set[int] | None = None,
    max_target_route_distance_meters: float = 0.0,
) -> TrashState | None:
    claimed_trash_indices = claimed_trash_indices or set()
    start_index = route_graph.nearest_node_index(agent.latitude, agent.longitude)
    start_node = route_graph.nodes[start_index]
    start_access_ok = route_graph.can_travel_direct_avoiding_strict_blocked(
        agent.latitude,
        agent.longitude,
        start_node.latitude,
        start_node.longitude,
    )
    start_access = distance_meters(agent.latitude, agent.longitude, start_node.latitude, start_node.longitude)
    distances = route_graph.shortest_distances_from(start_index) if start_access_ok else None

    nearest = None
    nearest_distance = float("inf")
    for trash in trash_states:
        if (
            trash.collected
            or not trash.reachable
            or trash.walkable_node_index is None
            or trash.trash_index in claimed_trash_indices
        ):
            continue

        dist = float("inf")

        if distances is not None:
            target_node = route_graph.nodes[trash.walkable_node_index]
            target_access_ok = route_graph.can_travel_direct_avoiding_strict_blocked(
                target_node.latitude,
                target_node.longitude,
                trash_pickup_latitude(trash),
                trash_pickup_longitude(trash),
            )
            if target_access_ok:
                graph_distance = distances[trash.walkable_node_index]
                if not math.isinf(graph_distance):
                    dist = min(dist, start_access + graph_distance + trash.pickup_access_distance_m)

        if allow_off_path_direct_movement(route_graph):
            target_latitude = trash_pickup_latitude(trash)
            target_longitude = trash_pickup_longitude(trash)
            direct_distance = distance_meters(agent.latitude, agent.longitude, target_latitude, target_longitude)
            if direct_distance < dist and can_travel_direct_to_trash(agent, trash, route_graph):
                dist = direct_distance

        if math.isinf(dist):
            continue
        if max_target_route_distance_meters > 0.0 and dist > max_target_route_distance_meters:
            continue
        if dist < nearest_distance:
            nearest_distance = dist
            nearest = trash

    return nearest


def build_claimed_trash_indices(agents: list[AgentState], current_agent: AgentState, allow_duplicate_targets: bool) -> set[int]:
    if allow_duplicate_targets:
        return set()
    claimed = set()
    for agent in agents:
        if agent.agent_id == current_agent.agent_id:
            continue
        if agent.target_trash_index is not None:
            claimed.add(agent.target_trash_index)
    return claimed


def assign_target_route(
    agent: AgentState,
    target: TrashState,
    route_graph: WalkableRouteGraph | ObstacleAwareDistance | None,
    direct_roam_radius_meters: float = 0.0,
    max_target_route_distance_meters: float = 0.0,
) -> bool:
    route_distance = 0.0
    route_path = None
    target_latitude = trash_pickup_latitude(target)
    target_longitude = trash_pickup_longitude(target)
    direct_distance = distance_meters(agent.latitude, agent.longitude, target_latitude, target_longitude)
    strict_direct_ok = not isinstance(route_graph, WalkableRouteGraph) or route_graph.can_travel_direct_avoiding_strict_blocked(
        agent.latitude,
        agent.longitude,
        target_latitude,
        target_longitude,
    )
    local_direct_ok = allow_local_direct_pickup(route_graph, agent, target, direct_distance, direct_roam_radius_meters)
    can_use_direct_route = False
    if agent.force_direct_target:
        can_use_direct_route = strict_direct_ok
    elif local_direct_ok:
        can_use_direct_route = True
    elif allow_off_path_direct_movement(route_graph) and isinstance(route_graph, WalkableRouteGraph):
        can_use_direct_route = can_travel_direct_to_trash(agent, target, route_graph)
    elif route_graph is None:
        can_use_direct_route = True
    if can_use_direct_route:
        route_distance = direct_distance
        route_path = [
            {"latitude": agent.latitude, "longitude": agent.longitude},
            {"latitude": target_latitude, "longitude": target_longitude},
        ]
    elif route_graph is not None:
        route_distance, route_path, _ = build_route_plan(agent, target, route_graph)
        if (route_path is None or math.isinf(route_distance)) and isinstance(route_graph, WalkableRouteGraph):
            if (
                (max_target_route_distance_meters <= 0.0 or direct_distance <= max_target_route_distance_meters)
                and route_graph.can_travel_direct_between_points(
                agent.latitude,
                agent.longitude,
                target_latitude,
                target_longitude,
                )
            ):
                route_distance = direct_distance
                route_path = [
                    {"latitude": agent.latitude, "longitude": agent.longitude},
                    {"latitude": target_latitude, "longitude": target_longitude},
                ]
        if route_path is None or math.isinf(route_distance):
            return False

    clear_agent_route(agent)
    agent.target_trash_index = target.trash_index
    if agent.cleanup_anchor_latitude is None or agent.cleanup_anchor_longitude is None:
        agent.cleanup_anchor_latitude = target_latitude
        agent.cleanup_anchor_longitude = target_longitude
    if route_graph is None and route_path is None:
        return True
    agent.route_time_remaining_s = route_distance / max(1e-9, agent.speed_mps)
    agent.route_total_time_s = agent.route_time_remaining_s
    agent.route_path = route_path
    agent.route_distance_traveled_m = 0.0
    agent.route_total_distance_m = route_distance
    agent.route_start_latitude = agent.latitude
    agent.route_start_longitude = agent.longitude
    agent.route_target_latitude = target_latitude
    agent.route_target_longitude = target_longitude
    return True


def summarize_zone_status(zone_lookup: dict[str, dict], agents: list[AgentState], trash_states: list[TrashState]) -> list[dict]:
    remaining_by_zone: dict[str, dict] = {
        zone_id: {
            "zoneId": zone_id,
            "remainingTrashMass": 0,
            "remainingTrashCount": 0,
            "agentCount": 0,
        }
        for zone_id in zone_lookup
    }

    for trash in trash_states:
        if trash.collected:
            continue
        zone_stat = remaining_by_zone[trash.zone_id]
        zone_stat["remainingTrashMass"] += trash.trash_mass
        zone_stat["remainingTrashCount"] += trash.trash_count

    for agent in agents:
        zone_id = resolve_agent_zone(agent, zone_lookup)
        remaining_by_zone[zone_id]["agentCount"] += 1

    return list(remaining_by_zone.values())


def resolve_agent_zone(agent: AgentState, zone_lookup: dict[str, dict]) -> str:
    for zone_id, zone in zone_lookup.items():
        if (
            float(zone["minLatitude"]) <= agent.latitude <= float(zone["maxLatitude"])
            and float(zone["minLongitude"]) <= agent.longitude <= float(zone["maxLongitude"])
        ):
            return zone_id
    return agent.assigned_zone_id


def compute_zone_imbalance(zone_status: list[dict]) -> float:
    loads = []
    for zone in zone_status:
        agent_count = max(1, int(zone["agentCount"]))
        loads.append(float(zone["remainingTrashMass"]) / agent_count)

    if not loads:
        return 0.0

    mean_load = sum(loads) / len(loads)
    return sum((load - mean_load) ** 2 for load in loads) / len(loads)


def build_step_snapshot(elapsed_time: float, agents: list[AgentState], zone_lookup: dict[str, dict], trash_states: list[TrashState]) -> dict:
    zone_status = summarize_zone_status(zone_lookup, agents, trash_states)
    idle_agents = sum(1 for agent in agents if agent.target_trash_index is None)
    remaining_mass = sum(trash.trash_mass for trash in trash_states if not trash.collected)
    remaining_count = sum(trash.trash_count for trash in trash_states if not trash.collected)

    return {
        "timeSeconds": elapsed_time,
        "remainingTrashMass": remaining_mass,
        "remainingTrashCount": remaining_count,
        "idleAgentCount": idle_agents,
        "zoneImbalance": compute_zone_imbalance(zone_status),
        "zoneStatus": zone_status,
        "agentSnapshots": [
            {
                "agentId": agent.agent_id,
                "assignedZoneId": agent.assigned_zone_id,
                "latitude": agent.latitude,
                "longitude": agent.longitude,
                "targetTrashIndex": agent.target_trash_index,
                "collectedMass": agent.collected_mass,
                "collectedCount": agent.collected_count,
                "collectTimeRemainingSeconds": agent.collect_time_remaining_s,
                "routeTimeRemainingSeconds": agent.route_time_remaining_s,
            }
            for agent in agents
        ],
        "collectedTrashIndices": sorted(trash.trash_index for trash in trash_states if trash.collected),
    }


def run_simulation(
    zone_payload: dict,
    assignment_payload: dict,
    step_seconds: float,
    max_seconds: float,
    agent_speed: float,
    collect_seconds: float,
    route_graph: WalkableRouteGraph | ObstacleAwareDistance | None,
    spawn_seed: int = 42,
    local_cleanup_radius_meters: float = 0.0,
    max_target_route_distance_meters: float = 0.0,
    blocked_pickup_access_radius_meters: float = 30.0,
    allow_duplicate_targets: bool = True,
    show_progress: bool = False,
    progress_label: str = "simulation",
) -> dict:
    DIRECT_REACHABILITY_CACHE.clear()
    zone_lookup = build_zone_lookup(zone_payload)
    trash_states = build_trash_states(zone_payload)
    attach_trash_to_walkable_graph(
        trash_states,
        route_graph,
        blocked_pickup_access_radius_meters=blocked_pickup_access_radius_meters,
    )
    original_trash_record_count = len(trash_states)
    unreachable_trash_states = [trash for trash in trash_states if not trash.reachable]
    trash_states = [trash for trash in trash_states if trash.reachable]
    agents = spawn_agents(
        assignment_payload,
        zone_lookup,
        speed_mps=agent_speed,
        route_graph=route_graph,
        spawn_seed=spawn_seed,
    )

    history = []
    elapsed = 0.0
    history.append(build_step_snapshot(elapsed, agents, zone_lookup, trash_states))

    total_steps = int(math.ceil(max_seconds / step_seconds)) if step_seconds > 0 else 0
    progress = tqdm(
        total=total_steps,
        desc=progress_label,
        unit="step",
        leave=False,
    ) if show_progress and tqdm is not None else None

    try:
        while elapsed < max_seconds:
            if all(trash.collected for trash in trash_states):
                break

            for agent in agents:
                current_target = None
                if agent.target_trash_index is not None:
                    current_target = next(
                        (trash for trash in trash_states if trash.trash_index == agent.target_trash_index and not trash.collected),
                        None,
                    )

                if current_target is None:
                    clear_agent_route(agent)
                    claimed_trash_indices = build_claimed_trash_indices(agents, agent, allow_duplicate_targets)
                    current_target = find_nearest_trash(
                        agent,
                        trash_states,
                        route_graph,
                        claimed_trash_indices=claimed_trash_indices,
                        local_cleanup_radius_meters=local_cleanup_radius_meters,
                        max_target_route_distance_meters=max_target_route_distance_meters,
                    )
                    if current_target is not None and not assign_target_route(
                        agent,
                        current_target,
                        route_graph,
                        direct_roam_radius_meters=local_cleanup_radius_meters,
                        max_target_route_distance_meters=max_target_route_distance_meters,
                    ):
                        continue

                if current_target is None:
                    agent.idle_time_s += step_seconds
                    continue

                if agent.collect_time_remaining_s > 0.0:
                    agent.collect_time_remaining_s = max(0.0, agent.collect_time_remaining_s - step_seconds)
                    if agent.collect_time_remaining_s <= 0.0:
                        current_target.collected = True
                        agent.collected_count += current_target.trash_count
                        agent.collected_mass += current_target.trash_mass
                        agent.target_trash_index = None
                        clear_agent_route(agent)
                    continue

                if route_graph is not None:
                    previous_remaining = agent.route_time_remaining_s
                    agent.route_time_remaining_s = max(0.0, agent.route_time_remaining_s - step_seconds)
                    moved_m = agent.speed_mps * min(step_seconds, max(0.0, previous_remaining))
                    agent.route_distance_traveled_m = min(agent.route_total_distance_m, agent.route_distance_traveled_m + moved_m)
                    if agent.route_path:
                        agent.latitude, agent.longitude = interpolate_route_path(
                            agent.route_path,
                            agent.route_distance_traveled_m,
                        )
                    agent.travel_distance_m += moved_m
                    if agent.route_time_remaining_s <= 0.0:
                        agent.latitude = trash_pickup_latitude(current_target)
                        agent.longitude = trash_pickup_longitude(current_target)
                        agent.collect_time_remaining_s = collect_seconds
                    continue

                target_latitude = trash_pickup_latitude(current_target)
                target_longitude = trash_pickup_longitude(current_target)
                next_lat, next_lon, moved_m = move_toward(
                    agent.latitude,
                    agent.longitude,
                    target_latitude,
                    target_longitude,
                    agent.speed_mps * step_seconds,
                )
                agent.latitude = next_lat
                agent.longitude = next_lon
                agent.travel_distance_m += moved_m

                reached = target_latitude == next_lat and target_longitude == next_lon
                if reached:
                    agent.collect_time_remaining_s = collect_seconds

            elapsed += step_seconds
            history.append(build_step_snapshot(elapsed, agents, zone_lookup, trash_states))
            if progress is not None:
                progress.update(1)
                remaining_mass = sum(trash.trash_mass for trash in trash_states if not trash.collected)
                progress.set_postfix(remaining=remaining_mass, agents=len(agents))
    finally:
        if progress is not None:
            progress.close()

    total_initial_mass = sum(trash.trash_mass for trash in trash_states)
    total_remaining_mass = sum(trash.trash_mass for trash in trash_states if not trash.collected)
    total_collected_mass = total_initial_mass - total_remaining_mass
    total_idle_time = sum(agent.idle_time_s for agent in agents)
    total_travel_distance = sum(agent.travel_distance_m for agent in agents)

    return {
        "metadata": {
            "strategy": assignment_payload["strategy"],
            "stepSeconds": step_seconds,
            "maxSeconds": max_seconds,
            "agentCount": len(agents),
            "spawnSeed": spawn_seed,
            "spawnMode": "random_point_within_assigned_zone",
            "trashRecordCount": len(trash_states),
            "originalTrashRecordCount": original_trash_record_count,
            "reachableTrashRecordCount": len(trash_states),
            "unreachableTrashRecordCount": len(unreachable_trash_states),
            "excludedUnreachableTrashMass": sum(trash.trash_mass for trash in unreachable_trash_states),
            "distanceMode": type(route_graph).__name__ if route_graph is not None else "straight",
            "pickupAccessRadiusMeters": (
                route_graph.pickup_access_radius_meters()
                if hasattr(route_graph, "pickup_access_radius_meters")
                else None
            ),
            "localCleanupRadiusMeters": local_cleanup_radius_meters,
            "localCleanupSelectionMode": "direct_distance",
            "localCleanupMovementMode": (
                "local_direct_then_off_path_with_nearest_fallback"
                if allow_off_path_direct_movement(route_graph)
                else "direct_if_unblocked"
            ),
            "maxTargetRouteDistanceMeters": max_target_route_distance_meters,
            "blockedPickupAccessRadiusMeters": blocked_pickup_access_radius_meters,
            "blockedPickupProxyTrashRecordCount": sum(
                1 for trash in trash_states if trash.pickup_mode == "blocked_area_nearest_walkable"
            ),
            "allowDuplicateTargets": allow_duplicate_targets,
        },
        "summary": {
            "elapsedTimeSeconds": elapsed,
            "initialTrashMass": total_initial_mass,
            "remainingTrashMass": total_remaining_mass,
            "collectedTrashMass": total_collected_mass,
            "collectionRate": 0.0 if total_initial_mass <= 0 else total_collected_mass / total_initial_mass,
            "totalIdleTimeSeconds": total_idle_time,
            "totalTravelDistanceMeters": total_travel_distance,
            "allTrashCollected": total_remaining_mass == 0,
        },
        "activeTrashRecordIndices": sorted(trash.trash_index for trash in trash_states),
        "excludedTrashRecordIndices": sorted(trash.trash_index for trash in unreachable_trash_states),
        "agents": [asdict(agent) for agent in agents],
        "history": history,
    }


def main() -> None:
    args = parse_args()
    zone_payload = load_json(args.zones)
    assignment_payload = load_json(args.assignment)
    movement_rules = MovementRules.load(args.movement_rules)
    result = run_simulation(
        zone_payload=zone_payload,
        assignment_payload=assignment_payload,
        step_seconds=args.step_seconds,
        max_seconds=args.max_seconds,
        agent_speed=args.agent_speed,
        collect_seconds=args.collect_seconds,
        route_graph=(
                WalkableRouteGraph.from_osm_features(args.osm_features, movement_rules=movement_rules)
                if args.distance_mode == "route"
                else ObstacleAwareDistance.from_osm_features(args.osm_features)
                if args.distance_mode == "obstacle"
                else None
            ),
        spawn_seed=args.spawn_seed,
        local_cleanup_radius_meters=args.local_cleanup_radius,
        max_target_route_distance_meters=args.max_target_route_distance,
        blocked_pickup_access_radius_meters=args.blocked_pickup_access_radius,
        allow_duplicate_targets=args.allow_duplicate_targets,
        show_progress=not args.no_progress,
        progress_label=assignment_payload["strategy"],
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"saved\t{args.output}")
    print(f"strategy\t{result['metadata']['strategy']}")
    print(f"collection_rate\t{result['summary']['collectionRate']:.4f}")
    print(f"remaining_trash_mass\t{result['summary']['remainingTrashMass']}")


if __name__ == "__main__":
    main()
