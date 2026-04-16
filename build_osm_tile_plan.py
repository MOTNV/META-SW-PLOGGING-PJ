from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MAP_CONFIG_PATH = ROOT / "unity" / "MetaSW" / "Assets" / "Data" / "map_config.json"
OUTPUT_DIR = ROOT / "unity" / "MetaSW" / "Assets" / "Data"
PLAN_PATH = OUTPUT_DIR / "osm_tile_plan.json"

# 주의:
# 아래 템플릿은 공용 OSM 타일 서버 형식입니다.
# 대량 다운로드나 반복 호출은 정책상 적절하지 않을 수 있으니,
# 실제 다운로드 전에 사용 가능한 타일 소스를 결정해서 교체하는 편이 좋습니다.
TILE_URL_TEMPLATE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

# 초기 Unity 배경맵용 권장 줌
ZOOM = 17
TILE_SIZE = 256


def latlon_to_tile(lat_deg: float, lon_deg: float, zoom: int) -> tuple[int, int]:
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def tile_to_latlon(x: int, y: int, zoom: int) -> tuple[float, float]:
    n = 2.0 ** zoom
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg


def build_plan() -> dict:
    config = json.loads(MAP_CONFIG_PATH.read_text(encoding="utf-8"))
    bounds = config["selectedBounds"]

    min_lat = float(bounds["minLatitude"])
    max_lat = float(bounds["maxLatitude"])
    min_lon = float(bounds["minLongitude"])
    max_lon = float(bounds["maxLongitude"])

    min_x, max_y = latlon_to_tile(min_lat, min_lon, ZOOM)
    max_x, min_y = latlon_to_tile(max_lat, max_lon, ZOOM)

    x_start = min(min_x, max_x)
    x_end = max(min_x, max_x)
    y_start = min(min_y, max_y)
    y_end = max(min_y, max_y)

    tiles = []
    for x in range(x_start, x_end + 1):
        for y in range(y_start, y_end + 1):
            tiles.append(
                {
                    "x": x,
                    "y": y,
                    "z": ZOOM,
                    "url": TILE_URL_TEMPLATE.format(z=ZOOM, x=x, y=y),
                    "filename": f"{ZOOM}_{x}_{y}.png",
                }
            )

    north, west = tile_to_latlon(x_start, y_start, ZOOM)
    south, east = tile_to_latlon(x_end + 1, y_end + 1, ZOOM)

    return {
        "sourceBounds": bounds,
        "zoom": ZOOM,
        "tileSize": TILE_SIZE,
        "tileRange": {
            "xStart": x_start,
            "xEnd": x_end,
            "yStart": y_start,
            "yEnd": y_end,
        },
        "tileCount": len(tiles),
        "mosaicSize": {
            "width": (x_end - x_start + 1) * TILE_SIZE,
            "height": (y_end - y_start + 1) * TILE_SIZE,
        },
        "coveredBounds": {
            "north": north,
            "south": south,
            "west": west,
            "east": east,
        },
        "tiles": tiles,
        "notes": [
            "이 파일은 다운로드 계획과 합성 범위를 계산하기 위한 dry-run 결과입니다.",
            "실제 다운로드 전에는 타일 소스 정책을 확인하세요.",
            "Unity 배경 합성 이미지의 실제 bbox는 coveredBounds를 사용하는 편이 안전합니다.",
        ],
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plan = build_plan()
    PLAN_PATH.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved\t{PLAN_PATH}")
    print(f"zoom\t{plan['zoom']}")
    print(f"tile_count\t{plan['tileCount']}")
    print(f"x_range\t{plan['tileRange']['xStart']}..{plan['tileRange']['xEnd']}")
    print(f"y_range\t{plan['tileRange']['yStart']}..{plan['tileRange']['yEnd']}")
    print(f"mosaic\t{plan['mosaicSize']['width']}x{plan['mosaicSize']['height']}")


if __name__ == "__main__":
    main()
