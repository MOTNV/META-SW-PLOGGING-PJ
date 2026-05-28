from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
DEFAULT_SCENARIO = ROOT / "simulation" / "simple_zones.json"
DEFAULT_TIMESERIES = ROOT / "simulation" / "comparison" / "timeseries.csv"
DEFAULT_MAP = ROOT / "unity" / "MetaSW" / "Assets" / "Sprites" / "gunsan_campus_map.png"
DEFAULT_TILE_PLAN = ROOT / "unity" / "MetaSW" / "Assets" / "Data" / "osm_tile_plan.json"
DEFAULT_OUTPUT_DIR = ROOT / "simulation" / "comparison"

MAP_BOUNDS = {
    "minLatitude": 35.94056,
    "minLongitude": 126.67704,
    "maxLatitude": 35.95116,
    "maxLongitude": 126.68535,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate paper-ready figures as PNG files.")
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--timeseries", type=Path, default=DEFAULT_TIMESERIES)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--tile-plan", type=Path, default=DEFAULT_TILE_PLAN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--exclude-zones",
        nargs="*",
        default=["Z0000"],
        help="Zone IDs to hide from figure 1 zone overlay.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_map_bounds(tile_plan_path: Path) -> dict:
    if not tile_plan_path.exists():
        return MAP_BOUNDS

    plan = load_json(tile_plan_path)
    covered = plan.get("coveredBounds")
    if not covered:
        return MAP_BOUNDS

    return {
        "minLatitude": float(covered["south"]),
        "minLongitude": float(covered["west"]),
        "maxLatitude": float(covered["north"]),
        "maxLongitude": float(covered["east"]),
    }


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def latlon_to_xy(lat: float, lon: float, width: int, height: int, bounds: dict) -> tuple[float, float]:
    x = (lon - bounds["minLongitude"]) / (bounds["maxLongitude"] - bounds["minLongitude"]) * width
    y = height - (lat - bounds["minLatitude"]) / (bounds["maxLatitude"] - bounds["minLatitude"]) * height
    return x, y


def generate_zone_map(
    scenario: dict,
    map_path: Path,
    output_path: Path,
    map_bounds: dict,
    excluded_zone_ids: set[str],
) -> None:
    base = Image.open(map_path).convert("RGBA")
    base.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    width, height = base.size
    overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    font = load_font(26, bold=True)
    small_font = load_font(18)

    visible_zones = [
        zone for zone in scenario["zones"]
        if str(zone.get("zoneId")) not in excluded_zone_ids
    ]
    visible_records = [
        record for record in scenario["trashRecords"]
        if str(record.get("zoneId")) not in excluded_zone_ids
    ]

    max_mass = max(float(zone.get("trashMass", 0)) for zone in visible_zones)
    for zone in visible_zones:
        x1, y2 = latlon_to_xy(float(zone["minLatitude"]), float(zone["minLongitude"]), width, height, map_bounds)
        x2, y1 = latlon_to_xy(float(zone["maxLatitude"]), float(zone["maxLongitude"]), width, height, map_bounds)
        ratio = 0 if max_mass <= 0 else min(1.0, float(zone.get("trashMass", 0)) / max_mass)
        fill = (220, 38, 38, int(32 + ratio * 80))
        draw.rectangle((x1, y1, x2, y2), fill=fill, outline=(15, 23, 42, 230), width=4)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        label = f"{zone['zoneId']}\n{int(zone.get('trashMass', 0))}"
        draw.multiline_text((cx, cy), label, fill=(15, 23, 42, 255), font=small_font, anchor="mm", align="center")

    for record in visible_records:
        x, y = latlon_to_xy(float(record["latitude"]), float(record["longitude"]), width, height, map_bounds)
        mass = max(1.0, float(record.get("trashMass", 1)))
        radius = min(8, 2.5 + mass ** 0.5)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(17, 24, 39, 145), outline=(255, 255, 255, 210))

    title_h = 90
    canvas = Image.new("RGBA", (width, height + title_h), (255, 255, 255, 255))
    canvas.paste(base, (0, title_h))
    canvas.alpha_composite(overlay, (0, title_h))
    canvas_draw = ImageDraw.Draw(canvas)
    canvas_draw.text((28, 22), "그림 1. 대상 지역 구역 분할 및 쓰레기 분포", fill=(17, 24, 39), font=font)
    canvas_draw.text(
        (28, 58),
        "배경: 군산대학교 OSM 지도, 오버레이: 접근 가능 구역 및 bootstrap 쓰레기 위치",
        fill=(75, 85, 99),
        font=small_font,
    )
    canvas.convert("RGB").save(output_path)


def read_timeseries(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def aggregate_timeseries(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], dict[str, list[float]]] = {}
    metrics = ["collectionRate", "zoneImbalance", "idleAgentRate"]
    for row in rows:
        key = (row["strategy"], row["timeSeconds"])
        bucket = grouped.setdefault(key, {metric: [] for metric in metrics})
        for metric in metrics:
            bucket[metric].append(float(row[metric]))

    aggregated = []
    for (strategy, time_seconds), values in grouped.items():
        row = {"strategy": strategy, "timeSeconds": float(time_seconds)}
        for metric, metric_values in values.items():
            row[metric] = statistics.mean(metric_values)
        aggregated.append(row)
    return sorted(aggregated, key=lambda row: (row["strategy"], row["timeSeconds"]))


def generate_line_chart(rows: list[dict], output_path: Path, y_key: str, title: str, y_label: str) -> None:
    strategies = ["random", "trash_priority", "uniform"]
    strategy_labels = {
        "random": "무작위 배치",
        "trash_priority": "쓰레기량 우선 배치",
        "uniform": "균등 배치",
    }
    colors = {
        "random": "#64748b",
        "trash_priority": "#dc2626",
        "uniform": "#2563eb",
    }
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(11.0, 6.8), dpi=200)
    for strategy in strategies:
        strategy_rows = [row for row in rows if row["strategy"] == strategy]
        if not strategy_rows:
            continue
        x_values = [float(row["timeSeconds"]) for row in strategy_rows]
        y_values = [float(row[y_key]) for row in strategy_rows]
        ax.plot(x_values, y_values, label=strategy_labels[strategy], color=colors[strategy], linewidth=3.4)

    ax.set_title(title, fontsize=28, fontweight="bold", pad=22)
    ax.set_xlabel("시간(초)", fontsize=22)
    ax.set_ylabel(y_label, fontsize=22)
    ax.tick_params(axis="both", labelsize=18)
    ax.grid(True, axis="both", color="#e5e7eb", linewidth=1.0)
    ax.legend(title="배치 전략", frameon=False, fontsize=22, title_fontsize=22)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    scenario = load_json(args.scenario)
    map_bounds = load_map_bounds(args.tile_plan)
    excluded_zone_ids = {str(zone_id) for zone_id in args.exclude_zones}
    rows = aggregate_timeseries(read_timeseries(args.timeseries))

    figure_1 = args.output_dir / "figure_1_zone_map.png"
    figure_2 = args.output_dir / "figure_2_collection_rate.png"
    figure_3 = args.output_dir / "figure_3_zone_imbalance.png"

    generate_zone_map(scenario, args.map, figure_1, map_bounds, excluded_zone_ids)
    generate_line_chart(rows, figure_2, "collectionRate", "그림 2. 배치 전략별 수거율 변화", "수거율")
    generate_line_chart(rows, figure_3, "zoneImbalance", "그림 3. 배치 전략별 구역 불균형 변화", "구역 부하 분산")

    print(f"figure_1\t{figure_1}")
    print(f"figure_2\t{figure_2}")
    print(f"figure_3\t{figure_3}")


if __name__ == "__main__":
    main()
