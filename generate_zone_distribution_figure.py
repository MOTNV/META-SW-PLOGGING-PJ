from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "simulation" / "comparison" / "scenarios" / "simple_zones_run_000.json"
DEFAULT_OUTPUT = ROOT / "simulation" / "comparison" / "zone_distribution.svg"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate zone split and trash distribution SVG.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_payload(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def color_for_mass(mass: float, max_mass: float) -> str:
    if max_mass <= 0:
        return "#f8fafc"
    ratio = min(1.0, max(0.0, mass / max_mass))
    # Blue to red ramp with a light low end for print readability.
    r = int(239 + (185 - 239) * ratio)
    g = int(246 + (28 - 246) * ratio)
    b = int(255 + (28 - 255) * ratio)
    return f"#{r:02x}{g:02x}{b:02x}"


def generate_svg(payload: dict) -> str:
    width = 1100
    height = 900
    margin_left = 80
    margin_top = 80
    plot_w = 780
    plot_h = 700
    legend_x = 900
    legend_y = 140

    bounds = payload["metadata"]["bounds"]
    min_lat = float(bounds["minLatitude"])
    max_lat = float(bounds["maxLatitude"])
    min_lon = float(bounds["minLongitude"])
    max_lon = float(bounds["maxLongitude"])

    zones = payload["zones"]
    records = payload["trashRecords"]
    max_mass = max(float(zone.get("trashMass", 0)) for zone in zones) if zones else 1.0

    def sx(lon: float) -> float:
        return margin_left + ((lon - min_lon) / max(1e-12, max_lon - min_lon)) * plot_w

    def sy(lat: float) -> float:
        return margin_top + plot_h - ((lat - min_lat) / max(1e-12, max_lat - min_lat)) * plot_h

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="80" y="42" font-family="Arial" font-size="26" font-weight="700" fill="#111827">Plogging Area Zone Split and Trash Distribution</text>',
        '<text x="80" y="68" font-family="Arial" font-size="14" fill="#4b5563">4x4 zones, bootstrap scenario run 000, color = zone trash mass</text>',
    ]

    for zone in zones:
        x1 = sx(float(zone["minLongitude"]))
        x2 = sx(float(zone["maxLongitude"]))
        y1 = sy(float(zone["maxLatitude"]))
        y2 = sy(float(zone["minLatitude"]))
        mass = float(zone.get("trashMass", 0))
        fill = color_for_mass(mass, max_mass)
        lines.append(
            f'<rect x="{x1:.2f}" y="{y1:.2f}" width="{x2 - x1:.2f}" height="{y2 - y1:.2f}" fill="{fill}" stroke="#334155" stroke-width="1.3"/>'
        )
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        lines.append(
            f'<text x="{cx:.2f}" y="{cy - 6:.2f}" text-anchor="middle" font-family="Arial" font-size="14" font-weight="700" fill="#0f172a">{zone["zoneId"]}</text>'
        )
        lines.append(
            f'<text x="{cx:.2f}" y="{cy + 13:.2f}" text-anchor="middle" font-family="Arial" font-size="12" fill="#334155">mass {int(mass)}</text>'
        )

    for record in records:
        lat = float(record["latitude"])
        lon = float(record["longitude"])
        mass = max(1.0, float(record.get("trashMass", 1)))
        radius = min(5.0, 1.4 + math.sqrt(mass) * 0.45)
        lines.append(
            f'<circle cx="{sx(lon):.2f}" cy="{sy(lat):.2f}" r="{radius:.2f}" fill="#111827" fill-opacity="0.45" stroke="white" stroke-width="0.35"/>'
        )

    lines.extend(
        [
            f'<rect x="{margin_left}" y="{margin_top}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#111827" stroke-width="2"/>',
            f'<text x="{margin_left + plot_w / 2}" y="{height - 48}" text-anchor="middle" font-family="Arial" font-size="14" fill="#374151">longitude</text>',
            f'<text x="24" y="{margin_top + plot_h / 2}" transform="rotate(-90 24 {margin_top + plot_h / 2})" text-anchor="middle" font-family="Arial" font-size="14" fill="#374151">latitude</text>',
            f'<text x="{legend_x}" y="{legend_y}" font-family="Arial" font-size="16" font-weight="700" fill="#111827">Legend</text>',
            f'<circle cx="{legend_x + 8}" cy="{legend_y + 32}" r="4" fill="#111827" fill-opacity="0.45" stroke="white"/>',
            f'<text x="{legend_x + 24}" y="{legend_y + 37}" font-family="Arial" font-size="13" fill="#374151">trash record</text>',
            f'<text x="{legend_x}" y="{legend_y + 76}" font-family="Arial" font-size="13" fill="#374151">zone trash mass</text>',
        ]
    )

    for index in range(6):
        ratio = index / 5
        y = legend_y + 94 + index * 24
        mass = max_mass * ratio
        lines.append(
            f'<rect x="{legend_x}" y="{y}" width="38" height="18" fill="{color_for_mass(mass, max_mass)}" stroke="#cbd5e1"/>'
        )
        lines.append(
            f'<text x="{legend_x + 48}" y="{y + 13}" font-family="Arial" font-size="12" fill="#374151">{mass:.0f}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    payload = load_payload(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(generate_svg(payload), encoding="utf-8")
    print(f"saved\t{args.output}")


if __name__ == "__main__":
    main()
