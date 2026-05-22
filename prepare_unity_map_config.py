from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MAP_OSM_PATH = ROOT / "map.osm"
MERGED_RECORDS_PATH = ROOT / "visualizations" / "merged_records.json"
OUTPUT_PATH = ROOT / "unity" / "MetaSW" / "Assets" / "Data" / "map_config.json"

# OSM bounds가 없거나 너무 좁을 때 보정용 패딩
LAT_PADDING = 0.0005
LON_PADDING = 0.0005

# Unity에 넣을 배경맵 권장 크기
RECOMMENDED_WIDTH = 4096
RECOMMENDED_HEIGHT = 4096


def read_osm_bounds(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        bounds = root.find("bounds")
        if bounds is None:
            return None
        return {
            "minLatitude": float(bounds.attrib["minlat"]),
            "minLongitude": float(bounds.attrib["minlon"]),
            "maxLatitude": float(bounds.attrib["maxlat"]),
            "maxLongitude": float(bounds.attrib["maxlon"]),
            "sourceFile": str(path.resolve()),
        }
    except Exception:
        return None


def read_record_bounds(path: Path) -> dict | None:
    if not path.exists():
        return None
    records = json.loads(path.read_text(encoding="utf-8"))
    coords = [
        (float(record["latitude"]), float(record["longitude"]))
        for record in records
        if record.get("latitude") not in (None, "") and record.get("longitude") not in (None, "")
    ]
    if not coords:
        return None
    min_lat = min(lat for lat, _ in coords) - LAT_PADDING
    max_lat = max(lat for lat, _ in coords) + LAT_PADDING
    min_lon = min(lon for _, lon in coords) - LON_PADDING
    max_lon = max(lon for _, lon in coords) + LON_PADDING
    return {
        "minLatitude": min_lat,
        "minLongitude": min_lon,
        "maxLatitude": max_lat,
        "maxLongitude": max_lon,
        "sourceFile": str(path.resolve()),
    }


def choose_bounds() -> tuple[dict, dict | None]:
    osm_bounds = read_osm_bounds(MAP_OSM_PATH)
    if not osm_bounds:
        raise SystemExit("map.osm bounds를 읽지 못했습니다. map.osm 파일이 필요합니다.")
    osm_bounds["type"] = "osm"

    record_bounds = read_record_bounds(MERGED_RECORDS_PATH)
    if record_bounds:
        record_bounds["type"] = "records"

    return osm_bounds, record_bounds


def main() -> None:
    bounds, record_bounds = choose_bounds()
    center_lat = (bounds["minLatitude"] + bounds["maxLatitude"]) / 2.0
    center_lon = (bounds["minLongitude"] + bounds["maxLongitude"]) / 2.0

    payload = {
        "selectedBounds": bounds,
        "recordBoundsReference": record_bounds,
        "center": {
            "latitude": center_lat,
            "longitude": center_lon,
        },
        "recommendedImage": {
            "width": RECOMMENDED_WIDTH,
            "height": RECOMMENDED_HEIGHT,
            "outputPath": str((ROOT / "unity" / "MetaSW" / "Assets" / "Sprites" / "gunsan_campus_map.png").resolve()),
        },
        "instructions": {
            "summary": "map.osm bounds를 기준으로 Unity 배경맵을 준비할 때 쓰는 설정 파일입니다.",
            "steps": [
                "선택된 bounds와 같은 범위로 군산대 OSM 배경맵 이미지를 준비합니다.",
                "배경 이미지를 Unity Assets/Sprites/gunsan_campus_map.png 로 저장합니다.",
                "TrashMapLoader의 min/max latitude/longitude를 selectedBounds 값과 동일하게 맞춥니다.",
                "그 후 Play 해서 쓰레기 포인트 위치를 확인합니다.",
            ],
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"saved\t{OUTPUT_PATH}")
    print(f"source\t{bounds['sourceFile']}")
    print(f"min_lat\t{bounds['minLatitude']}")
    print(f"max_lat\t{bounds['maxLatitude']}")
    print(f"min_lon\t{bounds['minLongitude']}")
    print(f"max_lon\t{bounds['maxLongitude']}")
    print(f"center\t{center_lat}, {center_lon}")


if __name__ == "__main__":
    main()
