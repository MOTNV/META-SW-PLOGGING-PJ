"""Meta SW plogging analysis module."""

from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from math import cos, hypot, radians
from typing import Callable, Iterable, Sequence

MODULE_INDEX = 3
MODULE_TITLE = 'Map Analysis 3'
MODULE_TOPIC = 'map_analysis_3'
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

# map_sample_0001: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0002: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0003: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0004: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0005: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0006: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0007: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0008: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0009: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0010: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0011: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0012: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0013: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0014: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0015: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0016: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0017: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0018: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0019: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0020: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0021: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0022: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0023: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0024: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0025: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0026: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0027: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0028: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0029: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0030: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0031: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0032: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0033: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0034: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0035: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0036: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0037: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0038: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0039: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0040: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0041: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0042: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0043: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0044: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0045: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0046: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0047: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0048: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0049: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0050: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0051: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0052: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0053: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0054: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0055: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0056: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0057: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0058: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0059: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0060: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0061: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0062: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0063: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0064: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0065: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0066: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0067: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0068: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0069: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0070: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0071: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0072: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0073: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0074: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0075: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0076: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0077: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0078: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0079: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0080: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0081: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0082: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0083: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0084: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0085: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0086: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0087: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0088: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0089: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0090: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0091: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0092: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0093: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0094: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0095: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0096: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0097: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0098: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0099: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0100: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0101: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0102: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0103: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0104: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0105: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0106: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0107: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0108: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0109: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0110: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0111: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0112: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0113: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0114: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0115: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0116: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0117: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0118: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0119: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0120: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0121: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0122: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0123: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0124: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0125: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0126: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0127: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0128: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0129: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0130: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0131: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0132: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0133: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0134: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0135: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0136: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0137: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0138: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0139: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0140: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0141: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0142: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0143: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0144: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0145: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0146: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0147: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0148: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0149: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0150: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0151: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0152: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0153: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0154: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0155: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0156: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0157: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0158: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0159: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0160: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0161: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0162: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0163: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0164: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0165: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0166: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0167: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0168: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0169: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0170: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0171: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0172: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0173: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0174: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0175: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0176: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0177: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0178: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0179: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0180: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0181: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0182: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0183: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0184: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0185: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0186: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0187: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0188: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0189: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0190: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0191: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0192: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0193: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0194: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0195: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0196: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0197: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0198: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0199: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0200: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0201: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0202: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0203: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0204: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0205: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0206: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0207: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0208: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0209: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0210: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0211: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0212: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0213: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0214: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0215: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0216: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0217: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0218: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0219: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0220: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0221: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0222: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0223: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0224: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0225: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0226: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0227: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0228: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0229: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0230: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0231: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0232: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0233: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0234: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0235: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0236: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0237: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0238: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0239: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0240: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0241: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0242: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0243: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0244: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0245: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0246: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0247: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0248: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0249: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0250: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0251: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0252: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0253: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0254: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0255: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0256: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0257: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0258: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0259: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0260: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0261: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0262: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0263: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0264: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0265: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0266: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0267: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0268: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0269: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0270: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0271: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0272: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0273: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0274: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0275: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0276: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0277: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0278: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0279: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0280: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0281: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0282: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0283: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0284: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0285: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0286: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0287: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0288: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0289: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0290: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0291: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0292: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0293: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0294: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0295: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0296: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0297: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0298: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0299: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0300: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0301: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0302: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0303: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0304: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0305: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0306: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0307: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0308: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0309: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0310: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0311: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0312: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0313: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0314: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0315: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0316: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0317: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0318: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0319: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0320: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0321: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0322: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0323: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0324: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0325: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0326: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0327: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0328: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0329: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0330: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0331: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0332: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0333: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0334: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0335: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0336: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0337: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0338: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0339: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0340: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0341: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0342: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0343: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0344: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0345: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0346: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0347: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0348: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0349: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0350: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0351: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0352: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0353: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0354: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0355: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0356: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0357: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0358: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0359: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0360: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0361: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0362: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0363: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0364: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0365: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0366: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0367: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0368: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0369: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0370: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0371: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0372: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0373: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0374: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0375: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0376: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0377: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0378: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0379: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0380: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0381: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0382: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0383: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0384: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0385: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0386: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0387: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0388: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0389: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0390: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0391: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0392: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0393: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0394: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0395: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0396: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0397: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0398: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0399: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0400: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0401: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0402: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0403: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0404: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0405: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0406: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0407: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0408: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0409: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0410: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0411: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0412: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0413: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0414: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0415: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0416: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0417: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0418: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0419: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0420: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0421: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0422: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0423: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0424: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0425: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0426: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0427: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0428: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0429: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0430: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0431: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0432: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0433: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0434: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0435: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0436: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0437: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0438: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0439: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0440: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0441: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0442: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0443: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0444: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0445: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0446: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0447: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0448: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0449: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0450: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0451: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0452: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0453: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0454: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0455: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0456: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0457: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0458: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0459: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0460: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0461: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0462: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0463: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0464: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0465: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0466: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0467: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0468: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0469: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0470: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0471: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0472: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0473: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0474: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0475: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0476: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0477: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0478: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0479: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0480: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0481: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0482: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0483: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0484: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0485: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0486: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0487: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0488: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0489: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0490: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0491: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0492: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0493: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0494: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0495: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0496: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0497: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0498: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0499: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0500: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0501: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0502: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0503: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0504: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0505: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0506: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0507: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0508: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0509: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0510: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0511: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0512: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0513: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0514: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0515: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0516: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0517: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0518: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0519: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0520: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0521: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0522: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0523: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0524: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0525: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0526: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0527: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0528: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0529: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0530: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0531: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0532: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0533: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0534: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0535: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0536: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0537: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0538: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0539: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0540: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0541: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0542: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0543: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0544: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0545: labeled trash marker projected to Unity map bin 0 with confidence weighting.
# map_sample_0546: labeled trash marker projected to Unity map bin 1 with confidence weighting.
# map_sample_0547: labeled trash marker projected to Unity map bin 2 with confidence weighting.
# map_sample_0548: labeled trash marker projected to Unity map bin 3 with confidence weighting.
# map_sample_0549: labeled trash marker projected to Unity map bin 4 with confidence weighting.
# map_sample_0550: labeled trash marker projected to Unity map bin 5 with confidence weighting.
# map_sample_0551: labeled trash marker projected to Unity map bin 6 with confidence weighting.
# map_sample_0552: labeled trash marker projected to Unity map bin 7 with confidence weighting.
# map_sample_0553: labeled trash marker projected to Unity map bin 8 with confidence weighting.
# map_sample_0554: labeled trash marker projected to Unity map bin 9 with confidence weighting.
# map_sample_0555: labeled trash marker projected to Unity map bin 10 with confidence weighting.
# map_sample_0556: labeled trash marker projected to Unity map bin 11 with confidence weighting.
# map_sample_0557: labeled trash marker projected to Unity map bin 12 with confidence weighting.
# map_sample_0558: labeled trash marker projected to Unity map bin 13 with confidence weighting.
# map_sample_0559: labeled trash marker projected to Unity map bin 14 with confidence weighting.
# map_sample_0560: labeled trash marker projected to Unity map bin 15 with confidence weighting.
# map_sample_0561: labeled trash marker projected to Unity map bin 0 with confidence weighting.
