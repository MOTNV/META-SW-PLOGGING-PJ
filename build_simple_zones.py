from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT_PATH = ROOT / "visualizations" / "merged_records.json"
DEFAULT_OUTPUT_PATH = ROOT / "simulation" / "simple_zones.json"

SIZE_WEIGHT = {
    "small": 1,
    "medium": 2,
    "large": 3,
}


@dataclass
class ZoneBounds:
    zone_id: str
    row: int
    col: int
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float

    @property
    def center_latitude(self) -> float:
        return (self.min_latitude + self.max_latitude) * 0.5

    @property
    def center_longitude(self) -> float:
        return (self.min_longitude + self.max_longitude) * 0.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build simple grid zones and assign trash records into zones."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--rows", type=int, default=4)
    parser.add_argument("--cols", type=int, default=4)
    return parser.parse_args()


def load_records(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Input JSON must be a list of records.")

    return data


def select_valid_records(records: list[dict]) -> list[dict]:
    valid_records = []
    for record in records:
        latitude = record.get("latitude")
        longitude = record.get("longitude")
        if latitude is None or longitude is None:
            continue

        items = record.get("items") or []
        if not items:
            continue

        valid_records.append(record)
    return valid_records


def compute_bounds(records: list[dict]) -> tuple[float, float, float, float]:
    latitudes = [float(record["latitude"]) for record in records]
    longitudes = [float(record["longitude"]) for record in records]
    return min(latitudes), max(latitudes), min(longitudes), max(longitudes)


def build_zone_grid(
    min_latitude: float,
    max_latitude: float,
    min_longitude: float,
    max_longitude: float,
    rows: int,
    cols: int,
) -> list[ZoneBounds]:
    zones: list[ZoneBounds] = []
    lat_step = (max_latitude - min_latitude) / rows
    lon_step = (max_longitude - min_longitude) / cols

    for row in range(rows):
        for col in range(cols):
            zone_min_lat = min_latitude + row * lat_step
            zone_max_lat = max_latitude if row == rows - 1 else zone_min_lat + lat_step
            zone_min_lon = min_longitude + col * lon_step
            zone_max_lon = max_longitude if col == cols - 1 else zone_min_lon + lon_step
            zone_id = f"Z{row:02d}{col:02d}"
            zones.append(
                ZoneBounds(
                    zone_id=zone_id,
                    row=row,
                    col=col,
                    min_latitude=zone_min_lat,
                    max_latitude=zone_max_lat,
                    min_longitude=zone_min_lon,
                    max_longitude=zone_max_lon,
                )
            )

    return zones


def find_zone_id(latitude: float, longitude: float, zones: list[ZoneBounds]) -> str:
    for zone in zones:
        inside_lat = zone.min_latitude <= latitude <= zone.max_latitude
        inside_lon = zone.min_longitude <= longitude <= zone.max_longitude
        if inside_lat and inside_lon:
            return zone.zone_id

    return zones[-1].zone_id


def calculate_record_metrics(record: dict) -> tuple[int, int]:
    total_quantity = 0
    total_mass = 0
    for item in record.get("items") or []:
        quantity = max(1, int(item.get("quantity", 1)))
        size = str(item.get("size", "small")).strip().lower()
        weight = SIZE_WEIGHT.get(size, 1)
        total_quantity += quantity
        total_mass += quantity * weight
    return total_quantity, total_mass


def initialize_zone_summary(zones: list[ZoneBounds]) -> dict[str, dict]:
    summary: dict[str, dict] = {}
    for zone in zones:
        summary[zone.zone_id] = {
            "zoneId": zone.zone_id,
            "row": zone.row,
            "col": zone.col,
            "minLatitude": zone.min_latitude,
            "maxLatitude": zone.max_latitude,
            "minLongitude": zone.min_longitude,
            "maxLongitude": zone.max_longitude,
            "centerLatitude": zone.center_latitude,
            "centerLongitude": zone.center_longitude,
            "recordCount": 0,
            "trashCount": 0,
            "trashMass": 0,
            "assignedAgentCount": 0,
        }
    return summary


def build_output(records: list[dict], rows: int, cols: int) -> dict:
    valid_records = select_valid_records(records)
    if not valid_records:
        raise ValueError("No valid labeled records with latitude/longitude were found.")

    min_lat, max_lat, min_lon, max_lon = compute_bounds(valid_records)
    zones = build_zone_grid(min_lat, max_lat, min_lon, max_lon, rows, cols)
    zone_summary = initialize_zone_summary(zones)

    mapped_records = []
    for index, record in enumerate(valid_records):
        latitude = float(record["latitude"])
        longitude = float(record["longitude"])
        zone_id = find_zone_id(latitude, longitude, zones)
        trash_count, trash_mass = calculate_record_metrics(record)

        zone_summary[zone_id]["recordCount"] += 1
        zone_summary[zone_id]["trashCount"] += trash_count
        zone_summary[zone_id]["trashMass"] += trash_mass

        mapped_records.append(
            {
                "recordIndex": index,
                "imagePath": record.get("imagePath", ""),
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": record.get("timestamp", ""),
                "source": record.get("source", ""),
                "zoneId": zone_id,
                "trashCount": trash_count,
                "trashMass": trash_mass,
                "items": record.get("items") or [],
            }
        )

    return {
        "metadata": {
            "rows": rows,
            "cols": cols,
            "zoneCount": rows * cols,
            "recordCount": len(mapped_records),
            "bounds": {
                "minLatitude": min_lat,
                "maxLatitude": max_lat,
                "minLongitude": min_lon,
                "maxLongitude": max_lon,
            },
        },
        "zones": list(zone_summary.values()),
        "trashRecords": mapped_records,
    }


def main() -> None:
    args = parse_args()
    records = load_records(args.input)
    payload = build_output(records, rows=args.rows, cols=args.cols)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"saved\t{args.output}")
    print(f"zones\t{payload['metadata']['zoneCount']}")
    print(f"records\t{payload['metadata']['recordCount']}")


if __name__ == "__main__":
    main()
