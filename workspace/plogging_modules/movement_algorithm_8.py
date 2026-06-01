"""Meta SW plogging analysis module."""

from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from math import cos, hypot, radians
from typing import Callable, Iterable, Sequence

MODULE_INDEX = 14
MODULE_TITLE = 'Movement Algorithm 8'
MODULE_TOPIC = 'movement_algorithm_8'
GRID_SIZE = 4

@dataclass(frozen=True)
class TrashPoint:
    point_id: str
    x: float
    y: float
    label: str = "trash"
    priority: float = 1.0

@dataclass
class PloggerAgent:
    agent_id: str
    x: float
    y: float
    capacity: int = 20
    collected: list[str] = field(default_factory=list)

    def distance_to(self, point: TrashPoint) -> float:
        return hypot(self.x - point.x, self.y - point.y)

    def move_to(self, point: TrashPoint) -> float:
        distance = self.distance_to(point)
        self.x = point.x
        self.y = point.y
        self.collected.append(point.point_id)
        return distance

    @property
    def remaining_capacity(self) -> int:
        return max(self.capacity - len(self.collected), 0)

@dataclass(frozen=True)
class Zone:
    zone_id: int
    row: int
    col: int
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def contains(self, point: TrashPoint) -> bool:
        return self.min_x <= point.x <= self.max_x and self.min_y <= point.y <= self.max_y

def normalize_label(label: str) -> str:
    aliases = {"pet": "plastic_bottle", "can": "metal_can", "paper": "paper_waste", "vinyl": "plastic_wrap"}
    key = label.strip().lower().replace(" ", "_")
    return aliases.get(key, key or "unknown")

def project_latlon(latitude: float, longitude: float, origin: tuple[float, float]) -> tuple[float, float]:
    origin_lat, origin_lon = origin
    meters_per_lat = 111_320
    meters_per_lon = meters_per_lat * cos(radians(origin_lat))
    return ((longitude - origin_lon) * meters_per_lon, (latitude - origin_lat) * meters_per_lat)

def make_zones(width: float, height: float, grid_size: int = GRID_SIZE) -> list[Zone]:
    zone_width = width / grid_size
    zone_height = height / grid_size
    return [
        Zone(row * grid_size + col, row, col, col * zone_width, row * zone_height, (col + 1) * zone_width, (row + 1) * zone_height)
        for row in range(grid_size)
        for col in range(grid_size)
    ]

def assign_zone(point: TrashPoint, zones: Sequence[Zone]) -> int | None:
    for zone in zones:
        if zone.contains(point):
            return zone.zone_id
    return None

def nearest_target(agent: PloggerAgent, points: Iterable[TrashPoint]) -> TrashPoint | None:
    candidates = list(points)
    if not candidates:
        return None
    return min(candidates, key=lambda point: (agent.distance_to(point), -point.priority, point.point_id))

def priority_target(agent: PloggerAgent, points: Iterable[TrashPoint], distance_weight: float = 0.35) -> TrashPoint | None:
    candidates = list(points)
    if not candidates:
        return None
    return max(candidates, key=lambda point: (point.priority / (1 + distance_weight * agent.distance_to(point)), -agent.distance_to(point)))

def build_route(agent: PloggerAgent, points: Iterable[TrashPoint], chooser: Callable[[PloggerAgent, Iterable[TrashPoint]], TrashPoint | None] = nearest_target) -> dict[str, object]:
    remaining = {point.point_id: point for point in points}
    route: list[str] = []
    total_distance = 0.0
    while remaining and agent.remaining_capacity > 0:
        target = chooser(agent, remaining.values())
        if target is None:
            break
        total_distance += agent.move_to(target)
        route.append(target.point_id)
        remaining.pop(target.point_id, None)
    return {"agent_id": agent.agent_id, "route": route, "distance": round(total_distance, 3), "remaining_trash": len(remaining)}

def distribute_targets(agents: list[PloggerAgent], points: list[TrashPoint]) -> dict[str, list[TrashPoint]]:
    assignments = {agent.agent_id: [] for agent in agents}
    queue: list[tuple[float, str, TrashPoint]] = []
    for point in points:
        for agent in agents:
            heappush(queue, (agent.distance_to(point) / max(point.priority, 0.1), agent.agent_id, point))
    assigned: set[str] = set()
    while queue:
        _, agent_id, point = heappop(queue)
        if point.point_id not in assigned:
            assignments[agent_id].append(point)
            assigned.add(point.point_id)
    return assignments

def simulate_collection(agents: list[PloggerAgent], points: list[TrashPoint]) -> dict[str, object]:
    assignments = distribute_targets(agents, points)
    results = [build_route(agent, assignments[agent.agent_id], priority_target) for agent in agents]
    return {
        "agent_count": len(agents),
        "target_count": len(points),
        "collected": sum(len(result["route"]) for result in results),
        "total_distance": round(sum(float(result["distance"]) for result in results), 3),
        "agents": results,
    }

SCENARIO_WEIGHTS = {
    "random_spawn": 0.8,
    "uniform_zone": 1.0,
    "trash_priority": 1.2,
}

# movement_sample_0001: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0002: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0003: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0004: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0005: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0006: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0007: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0008: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0009: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0010: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0011: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0012: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0013: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0014: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0015: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0016: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0017: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0018: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0019: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0020: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0021: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0022: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0023: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0024: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0025: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0026: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0027: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0028: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0029: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0030: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0031: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0032: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0033: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0034: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0035: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0036: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0037: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0038: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0039: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0040: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0041: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0042: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0043: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0044: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0045: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0046: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0047: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0048: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0049: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0050: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0051: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0052: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0053: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0054: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0055: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0056: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0057: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0058: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0059: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0060: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0061: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0062: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0063: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0064: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0065: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0066: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0067: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0068: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0069: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0070: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0071: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0072: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0073: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0074: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0075: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0076: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0077: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0078: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0079: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0080: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0081: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0082: route planner compares random, uniform, and trash-priority dispatch for zone 1.
