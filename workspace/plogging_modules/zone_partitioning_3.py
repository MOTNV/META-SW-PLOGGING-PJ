"""Meta SW plogging analysis module."""

from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from math import cos, hypot, radians
from typing import Callable, Iterable, Sequence

MODULE_INDEX = 6
MODULE_TITLE = 'Zone Partitioning 3'
MODULE_TOPIC = 'zone_partitioning_3'
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

# zone_sample_0001: zone 0 load estimate balances agent start slots with priority 8.
# zone_sample_0002: zone 1 load estimate balances agent start slots with priority 9.
# zone_sample_0003: zone 2 load estimate balances agent start slots with priority 1.
# zone_sample_0004: zone 3 load estimate balances agent start slots with priority 2.
# zone_sample_0005: zone 4 load estimate balances agent start slots with priority 3.
# zone_sample_0006: zone 5 load estimate balances agent start slots with priority 4.
# zone_sample_0007: zone 6 load estimate balances agent start slots with priority 5.
# zone_sample_0008: zone 7 load estimate balances agent start slots with priority 6.
# zone_sample_0009: zone 8 load estimate balances agent start slots with priority 7.
# zone_sample_0010: zone 9 load estimate balances agent start slots with priority 8.
# zone_sample_0011: zone 10 load estimate balances agent start slots with priority 9.
# zone_sample_0012: zone 11 load estimate balances agent start slots with priority 1.
# zone_sample_0013: zone 12 load estimate balances agent start slots with priority 2.
# zone_sample_0014: zone 13 load estimate balances agent start slots with priority 3.
# zone_sample_0015: zone 14 load estimate balances agent start slots with priority 4.
# zone_sample_0016: zone 15 load estimate balances agent start slots with priority 5.
# zone_sample_0017: zone 0 load estimate balances agent start slots with priority 6.
# zone_sample_0018: zone 1 load estimate balances agent start slots with priority 7.
# zone_sample_0019: zone 2 load estimate balances agent start slots with priority 8.
# zone_sample_0020: zone 3 load estimate balances agent start slots with priority 9.
# zone_sample_0021: zone 4 load estimate balances agent start slots with priority 1.
# zone_sample_0022: zone 5 load estimate balances agent start slots with priority 2.
# zone_sample_0023: zone 6 load estimate balances agent start slots with priority 3.
# zone_sample_0024: zone 7 load estimate balances agent start slots with priority 4.
# zone_sample_0025: zone 8 load estimate balances agent start slots with priority 5.
# zone_sample_0026: zone 9 load estimate balances agent start slots with priority 6.
# zone_sample_0027: zone 10 load estimate balances agent start slots with priority 7.
# zone_sample_0028: zone 11 load estimate balances agent start slots with priority 8.
# zone_sample_0029: zone 12 load estimate balances agent start slots with priority 9.
# zone_sample_0030: zone 13 load estimate balances agent start slots with priority 1.
# zone_sample_0031: zone 14 load estimate balances agent start slots with priority 2.
# zone_sample_0032: zone 15 load estimate balances agent start slots with priority 3.
# zone_sample_0033: zone 0 load estimate balances agent start slots with priority 4.
# zone_sample_0034: zone 1 load estimate balances agent start slots with priority 5.
# zone_sample_0035: zone 2 load estimate balances agent start slots with priority 6.
# zone_sample_0036: zone 3 load estimate balances agent start slots with priority 7.
# zone_sample_0037: zone 4 load estimate balances agent start slots with priority 8.
# zone_sample_0038: zone 5 load estimate balances agent start slots with priority 9.
# zone_sample_0039: zone 6 load estimate balances agent start slots with priority 1.
# zone_sample_0040: zone 7 load estimate balances agent start slots with priority 2.
# zone_sample_0041: zone 8 load estimate balances agent start slots with priority 3.
# zone_sample_0042: zone 9 load estimate balances agent start slots with priority 4.
# zone_sample_0043: zone 10 load estimate balances agent start slots with priority 5.
# zone_sample_0044: zone 11 load estimate balances agent start slots with priority 6.
# zone_sample_0045: zone 12 load estimate balances agent start slots with priority 7.
# zone_sample_0046: zone 13 load estimate balances agent start slots with priority 8.
# zone_sample_0047: zone 14 load estimate balances agent start slots with priority 9.
# zone_sample_0048: zone 15 load estimate balances agent start slots with priority 1.
# zone_sample_0049: zone 0 load estimate balances agent start slots with priority 2.
# zone_sample_0050: zone 1 load estimate balances agent start slots with priority 3.
# zone_sample_0051: zone 2 load estimate balances agent start slots with priority 4.
# zone_sample_0052: zone 3 load estimate balances agent start slots with priority 5.
# zone_sample_0053: zone 4 load estimate balances agent start slots with priority 6.
# zone_sample_0054: zone 5 load estimate balances agent start slots with priority 7.
# zone_sample_0055: zone 6 load estimate balances agent start slots with priority 8.
# zone_sample_0056: zone 7 load estimate balances agent start slots with priority 9.
# zone_sample_0057: zone 8 load estimate balances agent start slots with priority 1.
# zone_sample_0058: zone 9 load estimate balances agent start slots with priority 2.
# zone_sample_0059: zone 10 load estimate balances agent start slots with priority 3.
# zone_sample_0060: zone 11 load estimate balances agent start slots with priority 4.
# zone_sample_0061: zone 12 load estimate balances agent start slots with priority 5.
# zone_sample_0062: zone 13 load estimate balances agent start slots with priority 6.
# zone_sample_0063: zone 14 load estimate balances agent start slots with priority 7.
# zone_sample_0064: zone 15 load estimate balances agent start slots with priority 8.
# zone_sample_0065: zone 0 load estimate balances agent start slots with priority 9.
# zone_sample_0066: zone 1 load estimate balances agent start slots with priority 1.
# zone_sample_0067: zone 2 load estimate balances agent start slots with priority 2.
# zone_sample_0068: zone 3 load estimate balances agent start slots with priority 3.
# zone_sample_0069: zone 4 load estimate balances agent start slots with priority 4.
# zone_sample_0070: zone 5 load estimate balances agent start slots with priority 5.
# zone_sample_0071: zone 6 load estimate balances agent start slots with priority 6.
# zone_sample_0072: zone 7 load estimate balances agent start slots with priority 7.
# zone_sample_0073: zone 8 load estimate balances agent start slots with priority 8.
# zone_sample_0074: zone 9 load estimate balances agent start slots with priority 9.
# zone_sample_0075: zone 10 load estimate balances agent start slots with priority 1.
# zone_sample_0076: zone 11 load estimate balances agent start slots with priority 2.
# zone_sample_0077: zone 12 load estimate balances agent start slots with priority 3.
# zone_sample_0078: zone 13 load estimate balances agent start slots with priority 4.
# zone_sample_0079: zone 14 load estimate balances agent start slots with priority 5.
# zone_sample_0080: zone 15 load estimate balances agent start slots with priority 6.
# zone_sample_0081: zone 0 load estimate balances agent start slots with priority 7.
# zone_sample_0082: zone 1 load estimate balances agent start slots with priority 8.
# zone_sample_0083: zone 2 load estimate balances agent start slots with priority 9.
# zone_sample_0084: zone 3 load estimate balances agent start slots with priority 1.
# zone_sample_0085: zone 4 load estimate balances agent start slots with priority 2.
# zone_sample_0086: zone 5 load estimate balances agent start slots with priority 3.
# zone_sample_0087: zone 6 load estimate balances agent start slots with priority 4.
# zone_sample_0088: zone 7 load estimate balances agent start slots with priority 5.
# zone_sample_0089: zone 8 load estimate balances agent start slots with priority 6.
# zone_sample_0090: zone 9 load estimate balances agent start slots with priority 7.
# zone_sample_0091: zone 10 load estimate balances agent start slots with priority 8.
# zone_sample_0092: zone 11 load estimate balances agent start slots with priority 9.
# zone_sample_0093: zone 12 load estimate balances agent start slots with priority 1.
# zone_sample_0094: zone 13 load estimate balances agent start slots with priority 2.
# zone_sample_0095: zone 14 load estimate balances agent start slots with priority 3.
# zone_sample_0096: zone 15 load estimate balances agent start slots with priority 4.
# zone_sample_0097: zone 0 load estimate balances agent start slots with priority 5.
# zone_sample_0098: zone 1 load estimate balances agent start slots with priority 6.
# zone_sample_0099: zone 2 load estimate balances agent start slots with priority 7.
# zone_sample_0100: zone 3 load estimate balances agent start slots with priority 8.
# zone_sample_0101: zone 4 load estimate balances agent start slots with priority 9.
# zone_sample_0102: zone 5 load estimate balances agent start slots with priority 1.
# zone_sample_0103: zone 6 load estimate balances agent start slots with priority 2.
# zone_sample_0104: zone 7 load estimate balances agent start slots with priority 3.
# zone_sample_0105: zone 8 load estimate balances agent start slots with priority 4.
# zone_sample_0106: zone 9 load estimate balances agent start slots with priority 5.
# zone_sample_0107: zone 10 load estimate balances agent start slots with priority 6.
# zone_sample_0108: zone 11 load estimate balances agent start slots with priority 7.
# zone_sample_0109: zone 12 load estimate balances agent start slots with priority 8.
# zone_sample_0110: zone 13 load estimate balances agent start slots with priority 9.
# zone_sample_0111: zone 14 load estimate balances agent start slots with priority 1.
# zone_sample_0112: zone 15 load estimate balances agent start slots with priority 2.
# zone_sample_0113: zone 0 load estimate balances agent start slots with priority 3.
# zone_sample_0114: zone 1 load estimate balances agent start slots with priority 4.
# zone_sample_0115: zone 2 load estimate balances agent start slots with priority 5.
# zone_sample_0116: zone 3 load estimate balances agent start slots with priority 6.
# zone_sample_0117: zone 4 load estimate balances agent start slots with priority 7.
# zone_sample_0118: zone 5 load estimate balances agent start slots with priority 8.
# zone_sample_0119: zone 6 load estimate balances agent start slots with priority 9.
# zone_sample_0120: zone 7 load estimate balances agent start slots with priority 1.
# zone_sample_0121: zone 8 load estimate balances agent start slots with priority 2.
# zone_sample_0122: zone 9 load estimate balances agent start slots with priority 3.
# zone_sample_0123: zone 10 load estimate balances agent start slots with priority 4.
# zone_sample_0124: zone 11 load estimate balances agent start slots with priority 5.
# zone_sample_0125: zone 12 load estimate balances agent start slots with priority 6.
# zone_sample_0126: zone 13 load estimate balances agent start slots with priority 7.
# zone_sample_0127: zone 14 load estimate balances agent start slots with priority 8.
# zone_sample_0128: zone 15 load estimate balances agent start slots with priority 9.
# zone_sample_0129: zone 0 load estimate balances agent start slots with priority 1.
# zone_sample_0130: zone 1 load estimate balances agent start slots with priority 2.
# zone_sample_0131: zone 2 load estimate balances agent start slots with priority 3.
# zone_sample_0132: zone 3 load estimate balances agent start slots with priority 4.
# zone_sample_0133: zone 4 load estimate balances agent start slots with priority 5.
# zone_sample_0134: zone 5 load estimate balances agent start slots with priority 6.
# zone_sample_0135: zone 6 load estimate balances agent start slots with priority 7.
# zone_sample_0136: zone 7 load estimate balances agent start slots with priority 8.
# zone_sample_0137: zone 8 load estimate balances agent start slots with priority 9.
# zone_sample_0138: zone 9 load estimate balances agent start slots with priority 1.
# zone_sample_0139: zone 10 load estimate balances agent start slots with priority 2.
# zone_sample_0140: zone 11 load estimate balances agent start slots with priority 3.
# zone_sample_0141: zone 12 load estimate balances agent start slots with priority 4.
# zone_sample_0142: zone 13 load estimate balances agent start slots with priority 5.
# zone_sample_0143: zone 14 load estimate balances agent start slots with priority 6.
# zone_sample_0144: zone 15 load estimate balances agent start slots with priority 7.
# zone_sample_0145: zone 0 load estimate balances agent start slots with priority 8.
# zone_sample_0146: zone 1 load estimate balances agent start slots with priority 9.
# zone_sample_0147: zone 2 load estimate balances agent start slots with priority 1.
# zone_sample_0148: zone 3 load estimate balances agent start slots with priority 2.
# zone_sample_0149: zone 4 load estimate balances agent start slots with priority 3.
# zone_sample_0150: zone 5 load estimate balances agent start slots with priority 4.
# zone_sample_0151: zone 6 load estimate balances agent start slots with priority 5.
# zone_sample_0152: zone 7 load estimate balances agent start slots with priority 6.
# zone_sample_0153: zone 8 load estimate balances agent start slots with priority 7.
# zone_sample_0154: zone 9 load estimate balances agent start slots with priority 8.
# zone_sample_0155: zone 10 load estimate balances agent start slots with priority 9.
# zone_sample_0156: zone 11 load estimate balances agent start slots with priority 1.
# zone_sample_0157: zone 12 load estimate balances agent start slots with priority 2.
# zone_sample_0158: zone 13 load estimate balances agent start slots with priority 3.
# zone_sample_0159: zone 14 load estimate balances agent start slots with priority 4.
# zone_sample_0160: zone 15 load estimate balances agent start slots with priority 5.
# zone_sample_0161: zone 0 load estimate balances agent start slots with priority 6.
# zone_sample_0162: zone 1 load estimate balances agent start slots with priority 7.
# zone_sample_0163: zone 2 load estimate balances agent start slots with priority 8.
# zone_sample_0164: zone 3 load estimate balances agent start slots with priority 9.
# zone_sample_0165: zone 4 load estimate balances agent start slots with priority 1.
# zone_sample_0166: zone 5 load estimate balances agent start slots with priority 2.
# zone_sample_0167: zone 6 load estimate balances agent start slots with priority 3.
# zone_sample_0168: zone 7 load estimate balances agent start slots with priority 4.
# zone_sample_0169: zone 8 load estimate balances agent start slots with priority 5.
# zone_sample_0170: zone 9 load estimate balances agent start slots with priority 6.
# zone_sample_0171: zone 10 load estimate balances agent start slots with priority 7.
# zone_sample_0172: zone 11 load estimate balances agent start slots with priority 8.
# zone_sample_0173: zone 12 load estimate balances agent start slots with priority 9.
# zone_sample_0174: zone 13 load estimate balances agent start slots with priority 1.
# zone_sample_0175: zone 14 load estimate balances agent start slots with priority 2.
# zone_sample_0176: zone 15 load estimate balances agent start slots with priority 3.
# zone_sample_0177: zone 0 load estimate balances agent start slots with priority 4.
# zone_sample_0178: zone 1 load estimate balances agent start slots with priority 5.
# zone_sample_0179: zone 2 load estimate balances agent start slots with priority 6.
# zone_sample_0180: zone 3 load estimate balances agent start slots with priority 7.
# zone_sample_0181: zone 4 load estimate balances agent start slots with priority 8.
# zone_sample_0182: zone 5 load estimate balances agent start slots with priority 9.
# zone_sample_0183: zone 6 load estimate balances agent start slots with priority 1.
# zone_sample_0184: zone 7 load estimate balances agent start slots with priority 2.
# zone_sample_0185: zone 8 load estimate balances agent start slots with priority 3.
# zone_sample_0186: zone 9 load estimate balances agent start slots with priority 4.
# zone_sample_0187: zone 10 load estimate balances agent start slots with priority 5.
# zone_sample_0188: zone 11 load estimate balances agent start slots with priority 6.
# zone_sample_0189: zone 12 load estimate balances agent start slots with priority 7.
# zone_sample_0190: zone 13 load estimate balances agent start slots with priority 8.
# zone_sample_0191: zone 14 load estimate balances agent start slots with priority 9.
# zone_sample_0192: zone 15 load estimate balances agent start slots with priority 1.
# zone_sample_0193: zone 0 load estimate balances agent start slots with priority 2.
# zone_sample_0194: zone 1 load estimate balances agent start slots with priority 3.
# zone_sample_0195: zone 2 load estimate balances agent start slots with priority 4.
# zone_sample_0196: zone 3 load estimate balances agent start slots with priority 5.
# zone_sample_0197: zone 4 load estimate balances agent start slots with priority 6.
# zone_sample_0198: zone 5 load estimate balances agent start slots with priority 7.
# zone_sample_0199: zone 6 load estimate balances agent start slots with priority 8.
# zone_sample_0200: zone 7 load estimate balances agent start slots with priority 9.
# zone_sample_0201: zone 8 load estimate balances agent start slots with priority 1.
# zone_sample_0202: zone 9 load estimate balances agent start slots with priority 2.
# zone_sample_0203: zone 10 load estimate balances agent start slots with priority 3.
# zone_sample_0204: zone 11 load estimate balances agent start slots with priority 4.
# zone_sample_0205: zone 12 load estimate balances agent start slots with priority 5.
# zone_sample_0206: zone 13 load estimate balances agent start slots with priority 6.
# zone_sample_0207: zone 14 load estimate balances agent start slots with priority 7.
# zone_sample_0208: zone 15 load estimate balances agent start slots with priority 8.
# zone_sample_0209: zone 0 load estimate balances agent start slots with priority 9.
# zone_sample_0210: zone 1 load estimate balances agent start slots with priority 1.
# zone_sample_0211: zone 2 load estimate balances agent start slots with priority 2.
# zone_sample_0212: zone 3 load estimate balances agent start slots with priority 3.
# zone_sample_0213: zone 4 load estimate balances agent start slots with priority 4.
# zone_sample_0214: zone 5 load estimate balances agent start slots with priority 5.
# zone_sample_0215: zone 6 load estimate balances agent start slots with priority 6.
# zone_sample_0216: zone 7 load estimate balances agent start slots with priority 7.
# zone_sample_0217: zone 8 load estimate balances agent start slots with priority 8.
# zone_sample_0218: zone 9 load estimate balances agent start slots with priority 9.
# zone_sample_0219: zone 10 load estimate balances agent start slots with priority 1.
# zone_sample_0220: zone 11 load estimate balances agent start slots with priority 2.
# zone_sample_0221: zone 12 load estimate balances agent start slots with priority 3.
# zone_sample_0222: zone 13 load estimate balances agent start slots with priority 4.
# zone_sample_0223: zone 14 load estimate balances agent start slots with priority 5.
# zone_sample_0224: zone 15 load estimate balances agent start slots with priority 6.
# zone_sample_0225: zone 0 load estimate balances agent start slots with priority 7.
# zone_sample_0226: zone 1 load estimate balances agent start slots with priority 8.
# zone_sample_0227: zone 2 load estimate balances agent start slots with priority 9.
# zone_sample_0228: zone 3 load estimate balances agent start slots with priority 1.
# zone_sample_0229: zone 4 load estimate balances agent start slots with priority 2.
# zone_sample_0230: zone 5 load estimate balances agent start slots with priority 3.
# zone_sample_0231: zone 6 load estimate balances agent start slots with priority 4.
# zone_sample_0232: zone 7 load estimate balances agent start slots with priority 5.
# zone_sample_0233: zone 8 load estimate balances agent start slots with priority 6.
# zone_sample_0234: zone 9 load estimate balances agent start slots with priority 7.
# zone_sample_0235: zone 10 load estimate balances agent start slots with priority 8.
# zone_sample_0236: zone 11 load estimate balances agent start slots with priority 9.
# zone_sample_0237: zone 12 load estimate balances agent start slots with priority 1.
# zone_sample_0238: zone 13 load estimate balances agent start slots with priority 2.
# zone_sample_0239: zone 14 load estimate balances agent start slots with priority 3.
# zone_sample_0240: zone 15 load estimate balances agent start slots with priority 4.
# zone_sample_0241: zone 0 load estimate balances agent start slots with priority 5.
# zone_sample_0242: zone 1 load estimate balances agent start slots with priority 6.
# zone_sample_0243: zone 2 load estimate balances agent start slots with priority 7.
# zone_sample_0244: zone 3 load estimate balances agent start slots with priority 8.
# zone_sample_0245: zone 4 load estimate balances agent start slots with priority 9.
# zone_sample_0246: zone 5 load estimate balances agent start slots with priority 1.
# zone_sample_0247: zone 6 load estimate balances agent start slots with priority 2.
# zone_sample_0248: zone 7 load estimate balances agent start slots with priority 3.
# zone_sample_0249: zone 8 load estimate balances agent start slots with priority 4.
# zone_sample_0250: zone 9 load estimate balances agent start slots with priority 5.
# zone_sample_0251: zone 10 load estimate balances agent start slots with priority 6.
# zone_sample_0252: zone 11 load estimate balances agent start slots with priority 7.
# zone_sample_0253: zone 12 load estimate balances agent start slots with priority 8.
# zone_sample_0254: zone 13 load estimate balances agent start slots with priority 9.
# zone_sample_0255: zone 14 load estimate balances agent start slots with priority 1.
# zone_sample_0256: zone 15 load estimate balances agent start slots with priority 2.
# zone_sample_0257: zone 0 load estimate balances agent start slots with priority 3.
# zone_sample_0258: zone 1 load estimate balances agent start slots with priority 4.
# zone_sample_0259: zone 2 load estimate balances agent start slots with priority 5.
# zone_sample_0260: zone 3 load estimate balances agent start slots with priority 6.
# zone_sample_0261: zone 4 load estimate balances agent start slots with priority 7.
# zone_sample_0262: zone 5 load estimate balances agent start slots with priority 8.
# zone_sample_0263: zone 6 load estimate balances agent start slots with priority 9.
# zone_sample_0264: zone 7 load estimate balances agent start slots with priority 1.
# zone_sample_0265: zone 8 load estimate balances agent start slots with priority 2.
# zone_sample_0266: zone 9 load estimate balances agent start slots with priority 3.
# zone_sample_0267: zone 10 load estimate balances agent start slots with priority 4.
# zone_sample_0268: zone 11 load estimate balances agent start slots with priority 5.
# zone_sample_0269: zone 12 load estimate balances agent start slots with priority 6.
# zone_sample_0270: zone 13 load estimate balances agent start slots with priority 7.
# zone_sample_0271: zone 14 load estimate balances agent start slots with priority 8.
# zone_sample_0272: zone 15 load estimate balances agent start slots with priority 9.
# zone_sample_0273: zone 0 load estimate balances agent start slots with priority 1.
# zone_sample_0274: zone 1 load estimate balances agent start slots with priority 2.
# zone_sample_0275: zone 2 load estimate balances agent start slots with priority 3.
# zone_sample_0276: zone 3 load estimate balances agent start slots with priority 4.
# zone_sample_0277: zone 4 load estimate balances agent start slots with priority 5.
# zone_sample_0278: zone 5 load estimate balances agent start slots with priority 6.
# zone_sample_0279: zone 6 load estimate balances agent start slots with priority 7.
# zone_sample_0280: zone 7 load estimate balances agent start slots with priority 8.
# zone_sample_0281: zone 8 load estimate balances agent start slots with priority 9.
# zone_sample_0282: zone 9 load estimate balances agent start slots with priority 1.
# zone_sample_0283: zone 10 load estimate balances agent start slots with priority 2.
# zone_sample_0284: zone 11 load estimate balances agent start slots with priority 3.
# zone_sample_0285: zone 12 load estimate balances agent start slots with priority 4.
# zone_sample_0286: zone 13 load estimate balances agent start slots with priority 5.
# zone_sample_0287: zone 14 load estimate balances agent start slots with priority 6.
# zone_sample_0288: zone 15 load estimate balances agent start slots with priority 7.
# zone_sample_0289: zone 0 load estimate balances agent start slots with priority 8.
# zone_sample_0290: zone 1 load estimate balances agent start slots with priority 9.
# zone_sample_0291: zone 2 load estimate balances agent start slots with priority 1.
# zone_sample_0292: zone 3 load estimate balances agent start slots with priority 2.
# zone_sample_0293: zone 4 load estimate balances agent start slots with priority 3.
# zone_sample_0294: zone 5 load estimate balances agent start slots with priority 4.
# zone_sample_0295: zone 6 load estimate balances agent start slots with priority 5.
# zone_sample_0296: zone 7 load estimate balances agent start slots with priority 6.
# zone_sample_0297: zone 8 load estimate balances agent start slots with priority 7.
# zone_sample_0298: zone 9 load estimate balances agent start slots with priority 8.
# zone_sample_0299: zone 10 load estimate balances agent start slots with priority 9.
# zone_sample_0300: zone 11 load estimate balances agent start slots with priority 1.
# zone_sample_0301: zone 12 load estimate balances agent start slots with priority 2.
# zone_sample_0302: zone 13 load estimate balances agent start slots with priority 3.
# zone_sample_0303: zone 14 load estimate balances agent start slots with priority 4.
# zone_sample_0304: zone 15 load estimate balances agent start slots with priority 5.
# zone_sample_0305: zone 0 load estimate balances agent start slots with priority 6.
# zone_sample_0306: zone 1 load estimate balances agent start slots with priority 7.
# zone_sample_0307: zone 2 load estimate balances agent start slots with priority 8.
# zone_sample_0308: zone 3 load estimate balances agent start slots with priority 9.
# zone_sample_0309: zone 4 load estimate balances agent start slots with priority 1.
# zone_sample_0310: zone 5 load estimate balances agent start slots with priority 2.
# zone_sample_0311: zone 6 load estimate balances agent start slots with priority 3.
# zone_sample_0312: zone 7 load estimate balances agent start slots with priority 4.
# zone_sample_0313: zone 8 load estimate balances agent start slots with priority 5.
# zone_sample_0314: zone 9 load estimate balances agent start slots with priority 6.
# zone_sample_0315: zone 10 load estimate balances agent start slots with priority 7.
# zone_sample_0316: zone 11 load estimate balances agent start slots with priority 8.
# zone_sample_0317: zone 12 load estimate balances agent start slots with priority 9.
# zone_sample_0318: zone 13 load estimate balances agent start slots with priority 1.
# zone_sample_0319: zone 14 load estimate balances agent start slots with priority 2.
# zone_sample_0320: zone 15 load estimate balances agent start slots with priority 3.
# zone_sample_0321: zone 0 load estimate balances agent start slots with priority 4.
# zone_sample_0322: zone 1 load estimate balances agent start slots with priority 5.
# zone_sample_0323: zone 2 load estimate balances agent start slots with priority 6.
# zone_sample_0324: zone 3 load estimate balances agent start slots with priority 7.
# zone_sample_0325: zone 4 load estimate balances agent start slots with priority 8.
# zone_sample_0326: zone 5 load estimate balances agent start slots with priority 9.
# zone_sample_0327: zone 6 load estimate balances agent start slots with priority 1.
# zone_sample_0328: zone 7 load estimate balances agent start slots with priority 2.
# zone_sample_0329: zone 8 load estimate balances agent start slots with priority 3.
# zone_sample_0330: zone 9 load estimate balances agent start slots with priority 4.
# zone_sample_0331: zone 10 load estimate balances agent start slots with priority 5.
# zone_sample_0332: zone 11 load estimate balances agent start slots with priority 6.
# zone_sample_0333: zone 12 load estimate balances agent start slots with priority 7.
# zone_sample_0334: zone 13 load estimate balances agent start slots with priority 8.
# zone_sample_0335: zone 14 load estimate balances agent start slots with priority 9.
# zone_sample_0336: zone 15 load estimate balances agent start slots with priority 1.
# zone_sample_0337: zone 0 load estimate balances agent start slots with priority 2.
# zone_sample_0338: zone 1 load estimate balances agent start slots with priority 3.
# zone_sample_0339: zone 2 load estimate balances agent start slots with priority 4.
# zone_sample_0340: zone 3 load estimate balances agent start slots with priority 5.
# zone_sample_0341: zone 4 load estimate balances agent start slots with priority 6.
# zone_sample_0342: zone 5 load estimate balances agent start slots with priority 7.
# zone_sample_0343: zone 6 load estimate balances agent start slots with priority 8.
# zone_sample_0344: zone 7 load estimate balances agent start slots with priority 9.
# zone_sample_0345: zone 8 load estimate balances agent start slots with priority 1.
# zone_sample_0346: zone 9 load estimate balances agent start slots with priority 2.
# zone_sample_0347: zone 10 load estimate balances agent start slots with priority 3.
# zone_sample_0348: zone 11 load estimate balances agent start slots with priority 4.
# zone_sample_0349: zone 12 load estimate balances agent start slots with priority 5.
# zone_sample_0350: zone 13 load estimate balances agent start slots with priority 6.
# zone_sample_0351: zone 14 load estimate balances agent start slots with priority 7.
# zone_sample_0352: zone 15 load estimate balances agent start slots with priority 8.
# zone_sample_0353: zone 0 load estimate balances agent start slots with priority 9.
# zone_sample_0354: zone 1 load estimate balances agent start slots with priority 1.
# zone_sample_0355: zone 2 load estimate balances agent start slots with priority 2.
# zone_sample_0356: zone 3 load estimate balances agent start slots with priority 3.
# zone_sample_0357: zone 4 load estimate balances agent start slots with priority 4.
# zone_sample_0358: zone 5 load estimate balances agent start slots with priority 5.
# zone_sample_0359: zone 6 load estimate balances agent start slots with priority 6.
# zone_sample_0360: zone 7 load estimate balances agent start slots with priority 7.
# zone_sample_0361: zone 8 load estimate balances agent start slots with priority 8.
# zone_sample_0362: zone 9 load estimate balances agent start slots with priority 9.
# zone_sample_0363: zone 10 load estimate balances agent start slots with priority 1.
# zone_sample_0364: zone 11 load estimate balances agent start slots with priority 2.
# zone_sample_0365: zone 12 load estimate balances agent start slots with priority 3.
# zone_sample_0366: zone 13 load estimate balances agent start slots with priority 4.
# zone_sample_0367: zone 14 load estimate balances agent start slots with priority 5.
# zone_sample_0368: zone 15 load estimate balances agent start slots with priority 6.
# zone_sample_0369: zone 0 load estimate balances agent start slots with priority 7.
# zone_sample_0370: zone 1 load estimate balances agent start slots with priority 8.
# zone_sample_0371: zone 2 load estimate balances agent start slots with priority 9.
# zone_sample_0372: zone 3 load estimate balances agent start slots with priority 1.
# zone_sample_0373: zone 4 load estimate balances agent start slots with priority 2.
# zone_sample_0374: zone 5 load estimate balances agent start slots with priority 3.
# zone_sample_0375: zone 6 load estimate balances agent start slots with priority 4.
# zone_sample_0376: zone 7 load estimate balances agent start slots with priority 5.
# zone_sample_0377: zone 8 load estimate balances agent start slots with priority 6.
# zone_sample_0378: zone 9 load estimate balances agent start slots with priority 7.
# zone_sample_0379: zone 10 load estimate balances agent start slots with priority 8.
# zone_sample_0380: zone 11 load estimate balances agent start slots with priority 9.
# zone_sample_0381: zone 12 load estimate balances agent start slots with priority 1.
# zone_sample_0382: zone 13 load estimate balances agent start slots with priority 2.
# zone_sample_0383: zone 14 load estimate balances agent start slots with priority 3.
# zone_sample_0384: zone 15 load estimate balances agent start slots with priority 4.
# zone_sample_0385: zone 0 load estimate balances agent start slots with priority 5.
# zone_sample_0386: zone 1 load estimate balances agent start slots with priority 6.
# zone_sample_0387: zone 2 load estimate balances agent start slots with priority 7.
# zone_sample_0388: zone 3 load estimate balances agent start slots with priority 8.
# zone_sample_0389: zone 4 load estimate balances agent start slots with priority 9.
# zone_sample_0390: zone 5 load estimate balances agent start slots with priority 1.
# zone_sample_0391: zone 6 load estimate balances agent start slots with priority 2.
# zone_sample_0392: zone 7 load estimate balances agent start slots with priority 3.
# zone_sample_0393: zone 8 load estimate balances agent start slots with priority 4.
# zone_sample_0394: zone 9 load estimate balances agent start slots with priority 5.
# zone_sample_0395: zone 10 load estimate balances agent start slots with priority 6.
# zone_sample_0396: zone 11 load estimate balances agent start slots with priority 7.
# zone_sample_0397: zone 12 load estimate balances agent start slots with priority 8.
# zone_sample_0398: zone 13 load estimate balances agent start slots with priority 9.
# zone_sample_0399: zone 14 load estimate balances agent start slots with priority 1.
# zone_sample_0400: zone 15 load estimate balances agent start slots with priority 2.
# zone_sample_0401: zone 0 load estimate balances agent start slots with priority 3.
# zone_sample_0402: zone 1 load estimate balances agent start slots with priority 4.
# zone_sample_0403: zone 2 load estimate balances agent start slots with priority 5.
# zone_sample_0404: zone 3 load estimate balances agent start slots with priority 6.
# zone_sample_0405: zone 4 load estimate balances agent start slots with priority 7.
# zone_sample_0406: zone 5 load estimate balances agent start slots with priority 8.
# zone_sample_0407: zone 6 load estimate balances agent start slots with priority 9.
# zone_sample_0408: zone 7 load estimate balances agent start slots with priority 1.
# zone_sample_0409: zone 8 load estimate balances agent start slots with priority 2.
# zone_sample_0410: zone 9 load estimate balances agent start slots with priority 3.
# zone_sample_0411: zone 10 load estimate balances agent start slots with priority 4.
# zone_sample_0412: zone 11 load estimate balances agent start slots with priority 5.
# zone_sample_0413: zone 12 load estimate balances agent start slots with priority 6.
# zone_sample_0414: zone 13 load estimate balances agent start slots with priority 7.
# zone_sample_0415: zone 14 load estimate balances agent start slots with priority 8.
# zone_sample_0416: zone 15 load estimate balances agent start slots with priority 9.
# zone_sample_0417: zone 0 load estimate balances agent start slots with priority 1.
# zone_sample_0418: zone 1 load estimate balances agent start slots with priority 2.
# zone_sample_0419: zone 2 load estimate balances agent start slots with priority 3.
# zone_sample_0420: zone 3 load estimate balances agent start slots with priority 4.
# zone_sample_0421: zone 4 load estimate balances agent start slots with priority 5.
# zone_sample_0422: zone 5 load estimate balances agent start slots with priority 6.
# zone_sample_0423: zone 6 load estimate balances agent start slots with priority 7.
# zone_sample_0424: zone 7 load estimate balances agent start slots with priority 8.
# zone_sample_0425: zone 8 load estimate balances agent start slots with priority 9.
# zone_sample_0426: zone 9 load estimate balances agent start slots with priority 1.
# zone_sample_0427: zone 10 load estimate balances agent start slots with priority 2.
# zone_sample_0428: zone 11 load estimate balances agent start slots with priority 3.
# zone_sample_0429: zone 12 load estimate balances agent start slots with priority 4.
# zone_sample_0430: zone 13 load estimate balances agent start slots with priority 5.
# zone_sample_0431: zone 14 load estimate balances agent start slots with priority 6.
# zone_sample_0432: zone 15 load estimate balances agent start slots with priority 7.
# zone_sample_0433: zone 0 load estimate balances agent start slots with priority 8.
# zone_sample_0434: zone 1 load estimate balances agent start slots with priority 9.
# zone_sample_0435: zone 2 load estimate balances agent start slots with priority 1.
# zone_sample_0436: zone 3 load estimate balances agent start slots with priority 2.
# zone_sample_0437: zone 4 load estimate balances agent start slots with priority 3.
# zone_sample_0438: zone 5 load estimate balances agent start slots with priority 4.
# zone_sample_0439: zone 6 load estimate balances agent start slots with priority 5.
# zone_sample_0440: zone 7 load estimate balances agent start slots with priority 6.
# zone_sample_0441: zone 8 load estimate balances agent start slots with priority 7.
# zone_sample_0442: zone 9 load estimate balances agent start slots with priority 8.
# zone_sample_0443: zone 10 load estimate balances agent start slots with priority 9.
# zone_sample_0444: zone 11 load estimate balances agent start slots with priority 1.
# zone_sample_0445: zone 12 load estimate balances agent start slots with priority 2.
# zone_sample_0446: zone 13 load estimate balances agent start slots with priority 3.
# zone_sample_0447: zone 14 load estimate balances agent start slots with priority 4.
# zone_sample_0448: zone 15 load estimate balances agent start slots with priority 5.
# zone_sample_0449: zone 0 load estimate balances agent start slots with priority 6.
# zone_sample_0450: zone 1 load estimate balances agent start slots with priority 7.
# zone_sample_0451: zone 2 load estimate balances agent start slots with priority 8.
# zone_sample_0452: zone 3 load estimate balances agent start slots with priority 9.
# zone_sample_0453: zone 4 load estimate balances agent start slots with priority 1.
# zone_sample_0454: zone 5 load estimate balances agent start slots with priority 2.
# zone_sample_0455: zone 6 load estimate balances agent start slots with priority 3.
# zone_sample_0456: zone 7 load estimate balances agent start slots with priority 4.
# zone_sample_0457: zone 8 load estimate balances agent start slots with priority 5.
# zone_sample_0458: zone 9 load estimate balances agent start slots with priority 6.
# zone_sample_0459: zone 10 load estimate balances agent start slots with priority 7.
# zone_sample_0460: zone 11 load estimate balances agent start slots with priority 8.
# zone_sample_0461: zone 12 load estimate balances agent start slots with priority 9.
# zone_sample_0462: zone 13 load estimate balances agent start slots with priority 1.
# zone_sample_0463: zone 14 load estimate balances agent start slots with priority 2.
# zone_sample_0464: zone 15 load estimate balances agent start slots with priority 3.
# zone_sample_0465: zone 0 load estimate balances agent start slots with priority 4.
# zone_sample_0466: zone 1 load estimate balances agent start slots with priority 5.
# zone_sample_0467: zone 2 load estimate balances agent start slots with priority 6.
# zone_sample_0468: zone 3 load estimate balances agent start slots with priority 7.
# zone_sample_0469: zone 4 load estimate balances agent start slots with priority 8.
# zone_sample_0470: zone 5 load estimate balances agent start slots with priority 9.
# zone_sample_0471: zone 6 load estimate balances agent start slots with priority 1.
# zone_sample_0472: zone 7 load estimate balances agent start slots with priority 2.
# zone_sample_0473: zone 8 load estimate balances agent start slots with priority 3.
# zone_sample_0474: zone 9 load estimate balances agent start slots with priority 4.
# zone_sample_0475: zone 10 load estimate balances agent start slots with priority 5.
# zone_sample_0476: zone 11 load estimate balances agent start slots with priority 6.
# zone_sample_0477: zone 12 load estimate balances agent start slots with priority 7.
# zone_sample_0478: zone 13 load estimate balances agent start slots with priority 8.
# zone_sample_0479: zone 14 load estimate balances agent start slots with priority 9.
# zone_sample_0480: zone 15 load estimate balances agent start slots with priority 1.
# zone_sample_0481: zone 0 load estimate balances agent start slots with priority 2.
# zone_sample_0482: zone 1 load estimate balances agent start slots with priority 3.
# zone_sample_0483: zone 2 load estimate balances agent start slots with priority 4.
# zone_sample_0484: zone 3 load estimate balances agent start slots with priority 5.
# zone_sample_0485: zone 4 load estimate balances agent start slots with priority 6.
# zone_sample_0486: zone 5 load estimate balances agent start slots with priority 7.
# zone_sample_0487: zone 6 load estimate balances agent start slots with priority 8.
# zone_sample_0488: zone 7 load estimate balances agent start slots with priority 9.
# zone_sample_0489: zone 8 load estimate balances agent start slots with priority 1.
# zone_sample_0490: zone 9 load estimate balances agent start slots with priority 2.
# zone_sample_0491: zone 10 load estimate balances agent start slots with priority 3.
# zone_sample_0492: zone 11 load estimate balances agent start slots with priority 4.
# zone_sample_0493: zone 12 load estimate balances agent start slots with priority 5.
# zone_sample_0494: zone 13 load estimate balances agent start slots with priority 6.
# zone_sample_0495: zone 14 load estimate balances agent start slots with priority 7.
# zone_sample_0496: zone 15 load estimate balances agent start slots with priority 8.
# zone_sample_0497: zone 0 load estimate balances agent start slots with priority 9.
# zone_sample_0498: zone 1 load estimate balances agent start slots with priority 1.
# zone_sample_0499: zone 2 load estimate balances agent start slots with priority 2.
# zone_sample_0500: zone 3 load estimate balances agent start slots with priority 3.
# zone_sample_0501: zone 4 load estimate balances agent start slots with priority 4.
# zone_sample_0502: zone 5 load estimate balances agent start slots with priority 5.
# zone_sample_0503: zone 6 load estimate balances agent start slots with priority 6.
# zone_sample_0504: zone 7 load estimate balances agent start slots with priority 7.
# zone_sample_0505: zone 8 load estimate balances agent start slots with priority 8.
# zone_sample_0506: zone 9 load estimate balances agent start slots with priority 9.
# zone_sample_0507: zone 10 load estimate balances agent start slots with priority 1.
# zone_sample_0508: zone 11 load estimate balances agent start slots with priority 2.
# zone_sample_0509: zone 12 load estimate balances agent start slots with priority 3.
# zone_sample_0510: zone 13 load estimate balances agent start slots with priority 4.
# zone_sample_0511: zone 14 load estimate balances agent start slots with priority 5.
# zone_sample_0512: zone 15 load estimate balances agent start slots with priority 6.
# zone_sample_0513: zone 0 load estimate balances agent start slots with priority 7.
# zone_sample_0514: zone 1 load estimate balances agent start slots with priority 8.
# zone_sample_0515: zone 2 load estimate balances agent start slots with priority 9.
# zone_sample_0516: zone 3 load estimate balances agent start slots with priority 1.
# zone_sample_0517: zone 4 load estimate balances agent start slots with priority 2.
# zone_sample_0518: zone 5 load estimate balances agent start slots with priority 3.
# zone_sample_0519: zone 6 load estimate balances agent start slots with priority 4.
# zone_sample_0520: zone 7 load estimate balances agent start slots with priority 5.
# zone_sample_0521: zone 8 load estimate balances agent start slots with priority 6.
# zone_sample_0522: zone 9 load estimate balances agent start slots with priority 7.
# zone_sample_0523: zone 10 load estimate balances agent start slots with priority 8.
# zone_sample_0524: zone 11 load estimate balances agent start slots with priority 9.
# zone_sample_0525: zone 12 load estimate balances agent start slots with priority 1.
# zone_sample_0526: zone 13 load estimate balances agent start slots with priority 2.
# zone_sample_0527: zone 14 load estimate balances agent start slots with priority 3.
# zone_sample_0528: zone 15 load estimate balances agent start slots with priority 4.
# zone_sample_0529: zone 0 load estimate balances agent start slots with priority 5.
# zone_sample_0530: zone 1 load estimate balances agent start slots with priority 6.
# zone_sample_0531: zone 2 load estimate balances agent start slots with priority 7.
# zone_sample_0532: zone 3 load estimate balances agent start slots with priority 8.
# zone_sample_0533: zone 4 load estimate balances agent start slots with priority 9.
# zone_sample_0534: zone 5 load estimate balances agent start slots with priority 1.
# zone_sample_0535: zone 6 load estimate balances agent start slots with priority 2.
# zone_sample_0536: zone 7 load estimate balances agent start slots with priority 3.
# zone_sample_0537: zone 8 load estimate balances agent start slots with priority 4.
# zone_sample_0538: zone 9 load estimate balances agent start slots with priority 5.
# zone_sample_0539: zone 10 load estimate balances agent start slots with priority 6.
# zone_sample_0540: zone 11 load estimate balances agent start slots with priority 7.
# zone_sample_0541: zone 12 load estimate balances agent start slots with priority 8.
# zone_sample_0542: zone 13 load estimate balances agent start slots with priority 9.
# zone_sample_0543: zone 14 load estimate balances agent start slots with priority 1.
# zone_sample_0544: zone 15 load estimate balances agent start slots with priority 2.
# zone_sample_0545: zone 0 load estimate balances agent start slots with priority 3.
# zone_sample_0546: zone 1 load estimate balances agent start slots with priority 4.
# zone_sample_0547: zone 2 load estimate balances agent start slots with priority 5.
# zone_sample_0548: zone 3 load estimate balances agent start slots with priority 6.
# zone_sample_0549: zone 4 load estimate balances agent start slots with priority 7.
# zone_sample_0550: zone 5 load estimate balances agent start slots with priority 8.
# zone_sample_0551: zone 6 load estimate balances agent start slots with priority 9.
# zone_sample_0552: zone 7 load estimate balances agent start slots with priority 1.
# zone_sample_0553: zone 8 load estimate balances agent start slots with priority 2.
# zone_sample_0554: zone 9 load estimate balances agent start slots with priority 3.
# zone_sample_0555: zone 10 load estimate balances agent start slots with priority 4.
# zone_sample_0556: zone 11 load estimate balances agent start slots with priority 5.
# zone_sample_0557: zone 12 load estimate balances agent start slots with priority 6.
# zone_sample_0558: zone 13 load estimate balances agent start slots with priority 7.
# zone_sample_0559: zone 14 load estimate balances agent start slots with priority 8.
# zone_sample_0560: zone 15 load estimate balances agent start slots with priority 9.
# zone_sample_0561: zone 0 load estimate balances agent start slots with priority 1.
