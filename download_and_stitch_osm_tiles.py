from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from PIL import Image
import requests


ROOT = Path(__file__).resolve().parent
PLAN_PATH = ROOT / "unity" / "MetaSW" / "Assets" / "Data" / "osm_tile_plan.json"
SPRITES_DIR = ROOT / "unity" / "MetaSW" / "Assets" / "Sprites"
TEMP_TILE_DIR = ROOT / "unity" / "MetaSW" / "Assets" / "Data" / "osm_tiles"
OUTPUT_IMAGE_PATH = SPRITES_DIR / "gunsan_campus_map.png"

REQUEST_TIMEOUT = 20
USER_AGENT = "PloggingRL-Research/1.0 (local academic prototype)"


def load_plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def download_tile(session: requests.Session, url: str, destination: Path) -> None:
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content)).convert("RGBA")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)


def ensure_tiles(plan: dict) -> list[Path]:
    TEMP_TILE_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    tile_paths = []
    for tile in plan["tiles"]:
        destination = TEMP_TILE_DIR / tile["filename"]
        if not destination.exists():
            download_tile(session, tile["url"], destination)
        tile_paths.append(destination)
    return tile_paths


def stitch_tiles(plan: dict) -> Path:
    x_start = plan["tileRange"]["xStart"]
    y_start = plan["tileRange"]["yStart"]
    tile_size = plan["tileSize"]
    width = plan["mosaicSize"]["width"]
    height = plan["mosaicSize"]["height"]

    canvas = Image.new("RGBA", (width, height))

    for tile in plan["tiles"]:
        tile_path = TEMP_TILE_DIR / tile["filename"]
        image = Image.open(tile_path).convert("RGBA")
        x_offset = (tile["x"] - x_start) * tile_size
        y_offset = (tile["y"] - y_start) * tile_size
        canvas.paste(image, (x_offset, y_offset))

    SPRITES_DIR.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT_IMAGE_PATH)
    return OUTPUT_IMAGE_PATH


def main() -> None:
    plan = load_plan()
    ensure_tiles(plan)
    output = stitch_tiles(plan)
    print(f"saved\t{output}")
    print(f"tile_count\t{plan['tileCount']}")
    print(
        "covered_bounds\t"
        f"{plan['coveredBounds']['north']},"
        f"{plan['coveredBounds']['south']},"
        f"{plan['coveredBounds']['west']},"
        f"{plan['coveredBounds']['east']}"
    )


if __name__ == "__main__":
    main()
