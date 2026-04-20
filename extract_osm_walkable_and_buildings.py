from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MAP_OSM_PATH = ROOT / "map.osm"
OUTPUT_PATH = ROOT / "unity" / "MetaSW" / "Assets" / "Data" / "osm_features.json"

WALKABLE_HIGHWAYS = {
    "footway",
    "pedestrian",
    "steps",
    "living_street",
    "residential",
    "service",
    "crossing",
}

BLOCKED_FOOT_VALUES = {"no", "private"}
BLOCKED_ACCESS_VALUES = {"no", "private"}
DORMITORY_KEYWORD = "기숙사"
BLOCKED_NATURAL_VALUES = {"wood", "grassland", "water", "scrub"}
BLOCKED_LANDUSE_VALUES = {"farmland", "forest", "greenhouse_horticulture"}
ALLOWED_LEISURE_VALUES = {"pitch", "stadium"}


def parse_osm(path: Path):
    tree = ET.parse(path)
    root = tree.getroot()

    bounds_elem = root.find("bounds")
    bounds = {
        "minLatitude": float(bounds_elem.attrib["minlat"]),
        "minLongitude": float(bounds_elem.attrib["minlon"]),
        "maxLatitude": float(bounds_elem.attrib["maxlat"]),
        "maxLongitude": float(bounds_elem.attrib["maxlon"]),
    }

    nodes = {}
    ways = []

    for elem in root:
        if elem.tag == "node":
            nodes[elem.attrib["id"]] = {
                "lat": float(elem.attrib["lat"]),
                "lon": float(elem.attrib["lon"]),
            }
        elif elem.tag == "way":
            nd_refs = []
            tags = {}
            for child in elem:
                if child.tag == "nd":
                    nd_refs.append(child.attrib["ref"])
                elif child.tag == "tag":
                    tags[child.attrib["k"]] = child.attrib["v"]
            ways.append(
                {
                    "id": elem.attrib["id"],
                    "nd_refs": nd_refs,
                    "tags": tags,
                }
            )

    return bounds, nodes, ways


def refs_to_points(refs: list[str], nodes: dict) -> list[dict]:
    points = []
    for ref in refs:
        node = nodes.get(ref)
        if not node:
            continue
        points.append({"latitude": node["lat"], "longitude": node["lon"]})
    return points


def is_building(tags: dict) -> bool:
    if "building" in tags:
        return True

    name = (tags.get("name") or "") + " " + (tags.get("name:ko") or "")
    return "체육관" in name


def is_walkable_way(tags: dict) -> bool:
    highway = tags.get("highway")
    if highway not in WALKABLE_HIGHWAYS:
        return False

    if tags.get("foot") in BLOCKED_FOOT_VALUES:
        return False
    if tags.get("access") in BLOCKED_ACCESS_VALUES:
        return False

    return True


def is_dormitory_area(tags: dict) -> bool:
    name = (tags.get("name") or "") + " " + (tags.get("name:ko") or "")
    return DORMITORY_KEYWORD in name


def is_blocked_area(tags: dict) -> bool:
    if tags.get("natural") in BLOCKED_NATURAL_VALUES:
        return True
    if tags.get("landuse") in BLOCKED_LANDUSE_VALUES:
        return True
    return False


def is_allowed_area(tags: dict) -> bool:
    return tags.get("leisure") in ALLOWED_LEISURE_VALUES


def build_rectangle_from_points(
    points: list[dict],
    padding_lat: float = 0.00045,
    padding_lon: float = 0.00045,
) -> list[dict]:
    min_lat = min(point["latitude"] for point in points) - padding_lat
    max_lat = max(point["latitude"] for point in points) + padding_lat
    min_lon = min(point["longitude"] for point in points) - padding_lon
    max_lon = max(point["longitude"] for point in points) + padding_lon

    return [
        {"latitude": min_lat, "longitude": min_lon},
        {"latitude": min_lat, "longitude": max_lon},
        {"latitude": max_lat, "longitude": max_lon},
        {"latitude": max_lat, "longitude": min_lon},
        {"latitude": min_lat, "longitude": min_lon},
    ]


def build_output(bounds: dict, nodes: dict, ways: list[dict]) -> dict:
    walkable_ways = []
    buildings = []
    blocked_areas = []
    allowed_areas = []
    campus_boundary = None
    dormitory_points = []
    excluded_zones = []

    for way in ways:
        tags = way["tags"]
        points = refs_to_points(way["nd_refs"], nodes)
        if len(points) < 2:
            continue

        if tags.get("amenity") == "university":
            campus_boundary = {
                "id": way["id"],
                "name": tags.get("name", ""),
                "points": points,
            }

        if is_walkable_way(tags):
            walkable_ways.append(
                {
                    "id": way["id"],
                    "highway": tags.get("highway", ""),
                    "surface": tags.get("surface", ""),
                    "foot": tags.get("foot", ""),
                    "access": tags.get("access", ""),
                    "points": points,
                }
            )

        if len(points) >= 3 and is_building(tags):
            buildings.append(
                {
                    "id": way["id"],
                    "building": tags.get("building", ""),
                    "leisure": tags.get("leisure", ""),
                    "name": tags.get("name", ""),
                    "points": points,
                }
            )
            if is_dormitory_area(tags):
                dormitory_points.extend(points)

        if len(points) >= 3 and is_blocked_area(tags):
            blocked_areas.append(
                {
                    "id": way["id"],
                    "name": tags.get("name", "") or tags.get("name:ko", ""),
                    "natural": tags.get("natural", ""),
                    "landuse": tags.get("landuse", ""),
                    "points": points,
                }
            )

        if len(points) >= 3 and is_allowed_area(tags):
            allowed_areas.append(
                {
                    "id": way["id"],
                    "name": tags.get("name", "") or tags.get("name:ko", ""),
                    "leisure": tags.get("leisure", ""),
                    "sport": tags.get("sport", ""),
                    "points": points,
                }
            )

    if dormitory_points:
        excluded_zones.append(
            {
                "id": "dormitory_zone",
                "name": "Dormitory Exclusion Zone",
                "reason": "Exclude dormitory side from simulation area",
                "points": build_rectangle_from_points(dormitory_points),
            }
        )

    return {
        "bounds": bounds,
        "summary": {
            "walkableWayCount": len(walkable_ways),
            "buildingCount": len(buildings),
            "blockedAreaCount": len(blocked_areas),
            "allowedAreaCount": len(allowed_areas),
            "hasCampusBoundary": campus_boundary is not None,
            "excludedZoneCount": len(excluded_zones),
        },
        "campusBoundary": campus_boundary,
        "excludedZones": excluded_zones,
        "walkableWays": walkable_ways,
        "buildings": buildings,
        "blockedAreas": blocked_areas,
        "allowedAreas": allowed_areas,
    }


def main() -> None:
    bounds, nodes, ways = parse_osm(MAP_OSM_PATH)
    payload = build_output(bounds, nodes, ways)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"saved\t{OUTPUT_PATH}")
    print(f"walkable_ways\t{payload['summary']['walkableWayCount']}")
    print(f"buildings\t{payload['summary']['buildingCount']}")
    print(f"blocked_areas\t{payload['summary']['blockedAreaCount']}")
    print(f"allowed_areas\t{payload['summary']['allowedAreaCount']}")


if __name__ == "__main__":
    main()
