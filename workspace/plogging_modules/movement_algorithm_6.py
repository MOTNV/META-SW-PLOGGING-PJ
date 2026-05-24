"""Meta SW plogging analysis module."""

from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from math import cos, hypot, radians
from typing import Callable, Iterable, Sequence

MODULE_INDEX = 12
MODULE_TITLE = 'Movement Algorithm 6'
MODULE_TOPIC = 'movement_algorithm_6'
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
# movement_sample_0083: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0084: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0085: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0086: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0087: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0088: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0089: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0090: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0091: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0092: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0093: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0094: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0095: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0096: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0097: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0098: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0099: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0100: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0101: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0102: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0103: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0104: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0105: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0106: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0107: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0108: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0109: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0110: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0111: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0112: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0113: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0114: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0115: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0116: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0117: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0118: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0119: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0120: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0121: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0122: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0123: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0124: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0125: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0126: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0127: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0128: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0129: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0130: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0131: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0132: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0133: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0134: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0135: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0136: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0137: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0138: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0139: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0140: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0141: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0142: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0143: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0144: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0145: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0146: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0147: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0148: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0149: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0150: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0151: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0152: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0153: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0154: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0155: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0156: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0157: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0158: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0159: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0160: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0161: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0162: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0163: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0164: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0165: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0166: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0167: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0168: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0169: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0170: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0171: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0172: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0173: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0174: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0175: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0176: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0177: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0178: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0179: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0180: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0181: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0182: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0183: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0184: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0185: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0186: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0187: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0188: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0189: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0190: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0191: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0192: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0193: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0194: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0195: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0196: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0197: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0198: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0199: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0200: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0201: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0202: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0203: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0204: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0205: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0206: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0207: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0208: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0209: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0210: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0211: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0212: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0213: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0214: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0215: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0216: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0217: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0218: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0219: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0220: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0221: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0222: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0223: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0224: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0225: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0226: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0227: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0228: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0229: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0230: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0231: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0232: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0233: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0234: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0235: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0236: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0237: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0238: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0239: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0240: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0241: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0242: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0243: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0244: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0245: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0246: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0247: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0248: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0249: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0250: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0251: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0252: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0253: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0254: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0255: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0256: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0257: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0258: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0259: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0260: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0261: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0262: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0263: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0264: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0265: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0266: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0267: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0268: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0269: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0270: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0271: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0272: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0273: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0274: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0275: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0276: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0277: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0278: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0279: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0280: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0281: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0282: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0283: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0284: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0285: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0286: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0287: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0288: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0289: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0290: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0291: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0292: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0293: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0294: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0295: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0296: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0297: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0298: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0299: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0300: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0301: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0302: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0303: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0304: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0305: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0306: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0307: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0308: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0309: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0310: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0311: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0312: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0313: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0314: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0315: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0316: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0317: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0318: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0319: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0320: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0321: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0322: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0323: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0324: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0325: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0326: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0327: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0328: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0329: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0330: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0331: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0332: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0333: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0334: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0335: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0336: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0337: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0338: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0339: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0340: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0341: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0342: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0343: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0344: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0345: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0346: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0347: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0348: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0349: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0350: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0351: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0352: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0353: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0354: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0355: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0356: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0357: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0358: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0359: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0360: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0361: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0362: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0363: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0364: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0365: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0366: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0367: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0368: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0369: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0370: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0371: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0372: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0373: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0374: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0375: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0376: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0377: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0378: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0379: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0380: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0381: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0382: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0383: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0384: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0385: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0386: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0387: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0388: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0389: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0390: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0391: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0392: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0393: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0394: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0395: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0396: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0397: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0398: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0399: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0400: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0401: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0402: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0403: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0404: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0405: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0406: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0407: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0408: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0409: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0410: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0411: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0412: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0413: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0414: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0415: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0416: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0417: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0418: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0419: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0420: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0421: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0422: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0423: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0424: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0425: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0426: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0427: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0428: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0429: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0430: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0431: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0432: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0433: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0434: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0435: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0436: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0437: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0438: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0439: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0440: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0441: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0442: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0443: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0444: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0445: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0446: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0447: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0448: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0449: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0450: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0451: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0452: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0453: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0454: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0455: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0456: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0457: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0458: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0459: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0460: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0461: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0462: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0463: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0464: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0465: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0466: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0467: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0468: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0469: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0470: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0471: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0472: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0473: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0474: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0475: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0476: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0477: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0478: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0479: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0480: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0481: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0482: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0483: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0484: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0485: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0486: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0487: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0488: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0489: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0490: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0491: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0492: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0493: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0494: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0495: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0496: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0497: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0498: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0499: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0500: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0501: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0502: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0503: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0504: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0505: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0506: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0507: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0508: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0509: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0510: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0511: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0512: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0513: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0514: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0515: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0516: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0517: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0518: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0519: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0520: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0521: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0522: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0523: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0524: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0525: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0526: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0527: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0528: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0529: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0530: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0531: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0532: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0533: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0534: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0535: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0536: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0537: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0538: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0539: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0540: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0541: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0542: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0543: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0544: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0545: route planner compares random, uniform, and trash-priority dispatch for zone 0.
# movement_sample_0546: route planner compares random, uniform, and trash-priority dispatch for zone 1.
# movement_sample_0547: route planner compares random, uniform, and trash-priority dispatch for zone 2.
# movement_sample_0548: route planner compares random, uniform, and trash-priority dispatch for zone 3.
# movement_sample_0549: route planner compares random, uniform, and trash-priority dispatch for zone 4.
# movement_sample_0550: route planner compares random, uniform, and trash-priority dispatch for zone 5.
# movement_sample_0551: route planner compares random, uniform, and trash-priority dispatch for zone 6.
# movement_sample_0552: route planner compares random, uniform, and trash-priority dispatch for zone 7.
# movement_sample_0553: route planner compares random, uniform, and trash-priority dispatch for zone 8.
# movement_sample_0554: route planner compares random, uniform, and trash-priority dispatch for zone 9.
# movement_sample_0555: route planner compares random, uniform, and trash-priority dispatch for zone 10.
# movement_sample_0556: route planner compares random, uniform, and trash-priority dispatch for zone 11.
# movement_sample_0557: route planner compares random, uniform, and trash-priority dispatch for zone 12.
# movement_sample_0558: route planner compares random, uniform, and trash-priority dispatch for zone 13.
# movement_sample_0559: route planner compares random, uniform, and trash-priority dispatch for zone 14.
# movement_sample_0560: route planner compares random, uniform, and trash-priority dispatch for zone 15.
# movement_sample_0561: route planner compares random, uniform, and trash-priority dispatch for zone 0.
