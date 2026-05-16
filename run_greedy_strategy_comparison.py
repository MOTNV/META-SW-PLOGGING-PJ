from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from copy import deepcopy
from pathlib import Path

from assign_agents_to_zones import (
    assign_random,
    assign_trash_priority,
    assign_uniform,
    load_zone_payload,
    save_assignment,
    summarize_assignment,
)
from simulate_greedy_plogging import load_json, run_simulation
from obstacle_aware_distance import ObstacleAwareDistance
from movement_rules import DEFAULT_MOVEMENT_RULES_PATH, MovementRules
from walkable_route_graph import DEFAULT_OSM_FEATURES_PATH, WalkableRouteGraph

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    tqdm = None

try:
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover
    plt = None


ROOT = Path(__file__).resolve().parent
DEFAULT_ZONE_PATH = ROOT / "simulation" / "simple_zones.json"
DEFAULT_OUTPUT_DIR = ROOT / "simulation" / "comparison"
DEFAULT_ASSIGNMENT_DIR = ROOT / "simulation" / "assignments"
SIZE_WEIGHT = {
    "small": 1,
    "medium": 2,
    "large": 3,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run A/B/C greedy plogging placement strategy comparison."
    )
    parser.add_argument("--zones", type=Path, default=DEFAULT_ZONE_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--assignment-dir", type=Path, default=DEFAULT_ASSIGNMENT_DIR)
    parser.add_argument("--agents", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument(
        "--trash-sampling",
        choices=["fixed", "bootstrap"],
        default="bootstrap",
        help="fixed uses the original trash records; bootstrap resamples records each run.",
    )
    parser.add_argument(
        "--trash-sample-size",
        type=int,
        default=0,
        help="Number of trash records sampled per run. 0 keeps the original record count.",
    )
    parser.add_argument("--step-seconds", type=float, default=1.0)
    parser.add_argument("--max-seconds", type=float, default=600.0)
    parser.add_argument("--agent-speed", type=float, default=1.2)
    parser.add_argument("--collect-seconds", type=float, default=3.0)
    parser.add_argument(
        "--distance-mode",
        choices=["straight", "route", "obstacle"],
        default="route",
        help="straight uses direct distance; route uses OSM walkable graph; obstacle uses straight movement with blocked-area detours.",
    )
    parser.add_argument("--osm-features", type=Path, default=DEFAULT_OSM_FEATURES_PATH)
    parser.add_argument("--movement-rules", type=Path, default=DEFAULT_MOVEMENT_RULES_PATH)
    parser.add_argument(
        "--local-cleanup-radius",
        type=float,
        default=0.0,
        help="If greater than zero, keep cleaning trash within this cluster radius before selecting a global route target.",
    )
    parser.add_argument(
        "--max-target-route-distance",
        type=float,
        default=0.0,
        help="Do not assign a new trash target if the route distance is longer than this many meters. 0 disables this limit.",
    )
    parser.add_argument(
        "--blocked-pickup-access-radius",
        type=float,
        default=80.0,
        help="Allow trash inside blocked areas to be collected from the nearest walkable graph node within this many meters.",
    )
    parser.add_argument(
        "--allow-duplicate-targets",
        dest="allow_duplicate_targets",
        action="store_true",
        default=True,
        help="Allow multiple agents to target the same trash record.",
    )
    parser.add_argument(
        "--prevent-duplicate-targets",
        dest="allow_duplicate_targets",
        action="store_false",
        help="Prevent multiple agents from targeting the same trash record.",
    )
    parser.add_argument("--no-progress", action="store_true", help="Disable tqdm progress bars.")
    parser.add_argument(
        "--exclude-zones",
        nargs="*",
        default=[],
        help="Zone IDs to exclude from assignment, simulation, and imbalance calculation.",
    )
    return parser.parse_args()


def calculate_record_metrics(record: dict) -> tuple[int, int]:
    total_count = 0
    total_mass = 0
    for item in record.get("items") or []:
        quantity = max(1, int(item.get("quantity", 1)))
        size = str(item.get("size", "small")).strip().lower()
        total_count += quantity
        total_mass += quantity * SIZE_WEIGHT.get(size, 1)
    return total_count, total_mass


def rebuild_zone_stats(zone_payload: dict) -> dict:
    zone_lookup = {zone["zoneId"]: zone for zone in zone_payload["zones"]}
    for zone in zone_lookup.values():
        zone["recordCount"] = 0
        zone["trashCount"] = 0
        zone["trashMass"] = 0
        zone["assignedAgentCount"] = 0

    for record in zone_payload["trashRecords"]:
        zone = zone_lookup.get(record["zoneId"])
        if zone is None:
            continue
        trash_count, trash_mass = calculate_record_metrics(record)
        record["trashCount"] = trash_count
        record["trashMass"] = trash_mass
        zone["recordCount"] += 1
        zone["trashCount"] += trash_count
        zone["trashMass"] += trash_mass

    return zone_payload


def filter_excluded_zones(zone_payload: dict, excluded_zone_ids: set[str]) -> dict:
    if not excluded_zone_ids:
        return zone_payload

    payload = deepcopy(zone_payload)
    payload["zones"] = [
        zone for zone in payload.get("zones", [])
        if str(zone.get("zoneId")) not in excluded_zone_ids
    ]
    payload["trashRecords"] = [
        record for record in payload.get("trashRecords", [])
        if str(record.get("zoneId")) not in excluded_zone_ids
    ]
    payload.setdefault("metadata", {})["excludedZones"] = sorted(excluded_zone_ids)
    return payload


def build_run_zone_payload(base_payload: dict, args: argparse.Namespace, run_index: int) -> dict:
    excluded_zone_ids = {str(zone_id) for zone_id in args.exclude_zones}
    if args.trash_sampling == "fixed":
        payload = filter_excluded_zones(base_payload, excluded_zone_ids)
        payload.setdefault("metadata", {})["trashSampling"] = "fixed"
        payload["metadata"]["run"] = run_index
        return rebuild_zone_stats(payload)

    filtered_base_payload = filter_excluded_zones(base_payload, excluded_zone_ids)
    original_records = filtered_base_payload.get("trashRecords", [])
    if not original_records:
        raise ValueError("No trash records are available after applying excluded zones.")
    sample_size = args.trash_sample_size if args.trash_sample_size > 0 else len(original_records)
    rng = random.Random(args.seed + run_index)
    sampled_records = []
    for new_index in range(sample_size):
        source_record = deepcopy(rng.choice(original_records))
        source_record["sourceRecordIndex"] = source_record.get("recordIndex", new_index)
        source_record["recordIndex"] = new_index
        sampled_records.append(source_record)

    payload = deepcopy(filtered_base_payload)
    payload["trashRecords"] = sampled_records
    payload.setdefault("metadata", {})["trashSampling"] = "bootstrap"
    payload["metadata"]["run"] = run_index
    payload["metadata"]["trashSampleSize"] = sample_size
    return rebuild_zone_stats(payload)


def save_run_zone_payload(output_dir: Path, run_index: int, zone_payload: dict) -> Path:
    scenario_dir = output_dir / "scenarios"
    scenario_dir.mkdir(parents=True, exist_ok=True)
    path = scenario_dir / f"simple_zones_run_{run_index:03d}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(zone_payload, f, ensure_ascii=False, indent=2)
    return path


def build_assignments(
    zone_payload: dict,
    agent_count: int,
    seed: int,
    assignment_dir: Path,
    run_index: int,
) -> dict[str, dict]:
    zones = zone_payload["zones"]
    rng = random.Random(seed)
    assigned_by_strategy = {
        "random": assign_random(zones, agent_count, rng),
        "trash_priority": assign_trash_priority(zones, agent_count),
        "uniform": assign_uniform(zones, agent_count),
    }

    payloads = {}
    for strategy, assigned_zones in assigned_by_strategy.items():
        payload = summarize_assignment(strategy, assigned_zones, agent_count)
        if run_index == 0:
            save_assignment(assignment_dir, payload)
        run_dir = assignment_dir / "runs"
        save_assignment(run_dir, {**payload, "strategy": f"{strategy}_run_{run_index:03d}"})
        payload["strategy"] = strategy
        payloads[strategy] = payload

    return payloads


def run_all_simulations(
    args: argparse.Namespace,
    zone_payload: dict,
    assignments: dict[str, dict],
    run_index: int,
    route_graph: WalkableRouteGraph | ObstacleAwareDistance | None,
    show_progress: bool,
) -> dict[str, dict]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    strategy_items = list(assignments.items())
    iterator = (
        tqdm(strategy_items, desc=f"run {run_index:03d} strategies", unit="strategy", leave=True)
        if show_progress and tqdm is not None
        else strategy_items
    )
    for strategy, assignment_payload in iterator:
        result = run_simulation(
            zone_payload=zone_payload,
            assignment_payload=assignment_payload,
            step_seconds=args.step_seconds,
            max_seconds=args.max_seconds,
            agent_speed=args.agent_speed,
            collect_seconds=args.collect_seconds,
            route_graph=route_graph,
            spawn_seed=args.seed + run_index,
            local_cleanup_radius_meters=args.local_cleanup_radius,
            max_target_route_distance_meters=args.max_target_route_distance,
            blocked_pickup_access_radius_meters=args.blocked_pickup_access_radius,
            allow_duplicate_targets=args.allow_duplicate_targets,
            show_progress=show_progress,
            progress_label=f"{strategy} run {run_index:03d}",
        )
        output_path = args.output_dir / "runs" / f"greedy_{strategy}_run_{run_index:03d}_result.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        results[strategy] = result
    return results


def calculate_midpoint_idle_rate(result: dict) -> float:
    history = result.get("history", [])
    max_seconds = float(result["metadata"]["maxSeconds"])
    midpoint = max_seconds * 0.5
    agent_count = max(1, int(result["metadata"]["agentCount"]))
    samples = [step for step in history if float(step["timeSeconds"]) >= midpoint]
    if not samples:
        return 0.0
    return sum(float(step["idleAgentCount"]) / agent_count for step in samples) / len(samples)


def calculate_average_zone_imbalance(result: dict) -> float:
    history = result.get("history", [])
    if not history:
        return 0.0
    return sum(float(step["zoneImbalance"]) for step in history) / len(history)


def summarize_result(strategy: str, run_index: int, result: dict) -> dict:
    summary = result["summary"]
    history = result.get("history", [])
    final_imbalance = float(history[-1]["zoneImbalance"]) if history else 0.0
    return {
        "strategy": strategy,
        "run": run_index,
        "agentCount": result["metadata"]["agentCount"],
        "elapsedTimeSeconds": summary["elapsedTimeSeconds"],
        "initialTrashMass": summary["initialTrashMass"],
        "collectedTrashMass": summary["collectedTrashMass"],
        "remainingTrashMass": summary["remainingTrashMass"],
        "collectionRate": summary["collectionRate"],
        "totalTravelDistanceMeters": summary["totalTravelDistanceMeters"],
        "totalIdleTimeSeconds": summary["totalIdleTimeSeconds"],
        "midpointIdleRate": calculate_midpoint_idle_rate(result),
        "averageZoneImbalance": calculate_average_zone_imbalance(result),
        "finalZoneImbalance": final_imbalance,
        "allTrashCollected": summary["allTrashCollected"],
    }


def write_run_summary_csv(output_dir: Path, rows: list[dict]) -> Path:
    path = output_dir / "summary_by_run.csv"
    fieldnames = [
        "strategy",
        "run",
        "agentCount",
        "elapsedTimeSeconds",
        "initialTrashMass",
        "collectedTrashMass",
        "remainingTrashMass",
        "collectionRate",
        "totalTravelDistanceMeters",
        "totalIdleTimeSeconds",
        "midpointIdleRate",
        "averageZoneImbalance",
        "finalZoneImbalance",
        "allTrashCollected",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_aggregate_summary_csv(output_dir: Path, rows: list[dict]) -> Path:
    path = output_dir / "summary.csv"
    metrics = [
        "collectionRate",
        "remainingTrashMass",
        "collectedTrashMass",
        "totalTravelDistanceMeters",
        "totalIdleTimeSeconds",
        "midpointIdleRate",
        "averageZoneImbalance",
        "finalZoneImbalance",
    ]
    fieldnames = ["strategy", "runs", "agentCount"]
    for metric in metrics:
        fieldnames.extend([f"{metric}Mean", f"{metric}Std"])

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for strategy in ["random", "trash_priority", "uniform"]:
            strategy_rows = [row for row in rows if row["strategy"] == strategy]
            if not strategy_rows:
                continue
            output_row = {
                "strategy": strategy,
                "runs": len(strategy_rows),
                "agentCount": strategy_rows[0]["agentCount"],
            }
            for metric in metrics:
                values = [float(row[metric]) for row in strategy_rows]
                output_row[f"{metric}Mean"] = statistics.mean(values)
                output_row[f"{metric}Std"] = statistics.stdev(values) if len(values) > 1 else 0.0
            writer.writerow(output_row)
    return path


def write_timeseries_csv(output_dir: Path, results_by_run: list[tuple[int, dict[str, dict]]]) -> Path:
    path = output_dir / "timeseries.csv"
    fieldnames = [
        "strategy",
        "run",
        "timeSeconds",
        "remainingTrashMass",
        "remainingTrashCount",
        "collectionRate",
        "idleAgentCount",
        "idleAgentRate",
        "zoneImbalance",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for run_index, results in results_by_run:
            for strategy, result in results.items():
                initial_mass = max(1, int(result["summary"]["initialTrashMass"]))
                agent_count = max(1, int(result["metadata"]["agentCount"]))
                for step in result.get("history", []):
                    remaining_mass = int(step["remainingTrashMass"])
                    writer.writerow(
                        {
                            "strategy": strategy,
                            "run": run_index,
                            "timeSeconds": step["timeSeconds"],
                            "remainingTrashMass": remaining_mass,
                            "remainingTrashCount": step["remainingTrashCount"],
                            "collectionRate": 1.0 - (remaining_mass / initial_mass),
                            "idleAgentCount": step["idleAgentCount"],
                            "idleAgentRate": float(step["idleAgentCount"]) / agent_count,
                            "zoneImbalance": step["zoneImbalance"],
                        }
                    )
    return path


def read_timeseries_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def aggregate_timeseries_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], dict[str, list[float]]] = {}
    for row in rows:
        key = (row["strategy"], row["timeSeconds"])
        bucket = grouped.setdefault(
            key,
            {
                "remainingTrashMass": [],
                "remainingTrashCount": [],
                "collectionRate": [],
                "idleAgentCount": [],
                "idleAgentRate": [],
                "zoneImbalance": [],
            },
        )
        for metric in bucket:
            bucket[metric].append(float(row[metric]))

    aggregated = []
    for (strategy, time_seconds), values_by_metric in grouped.items():
        row = {"strategy": strategy, "timeSeconds": time_seconds}
        for metric, values in values_by_metric.items():
            row[metric] = statistics.mean(values)
        aggregated.append(row)

    return sorted(aggregated, key=lambda row: (row["strategy"], float(row["timeSeconds"])))


def write_svg_line_chart(
    path: Path,
    rows: list[dict],
    y_key: str,
    title: str,
    y_label: str,
) -> None:
    width = 1000
    height = 560
    margin_left = 72
    margin_right = 28
    margin_top = 54
    margin_bottom = 60
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    strategies = ["random", "trash_priority", "uniform"]
    colors = {
        "random": "#64748b",
        "trash_priority": "#dc2626",
        "uniform": "#2563eb",
    }
    series = {
        strategy: [
            (float(row["timeSeconds"]), float(row[y_key]))
            for row in rows
            if row["strategy"] == strategy
        ]
        for strategy in strategies
    }

    all_points = [point for points in series.values() for point in points]
    if not all_points:
        return

    min_x = min(x for x, _ in all_points)
    max_x = max(x for x, _ in all_points)
    min_y = 0.0
    max_y = max(y for _, y in all_points)
    if max_y <= min_y:
        max_y = 1.0

    def sx(x: float) -> float:
        return margin_left + ((x - min_x) / max(1e-9, max_x - min_x)) * plot_w

    def sy(y: float) -> float:
        return margin_top + plot_h - ((y - min_y) / max(1e-9, max_y - min_y)) * plot_h

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{margin_left}" y="30" font-family="Arial" font-size="22" font-weight="700" fill="#111827">{title}</text>',
        f'<line x1="{margin_left}" y1="{margin_top + plot_h}" x2="{margin_left + plot_w}" y2="{margin_top + plot_h}" stroke="#111827" stroke-width="1"/>',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_h}" stroke="#111827" stroke-width="1"/>',
        f'<text x="{width / 2}" y="{height - 18}" text-anchor="middle" font-family="Arial" font-size="14" fill="#374151">time (seconds)</text>',
        f'<text x="18" y="{height / 2}" transform="rotate(-90 18 {height / 2})" text-anchor="middle" font-family="Arial" font-size="14" fill="#374151">{y_label}</text>',
    ]

    for tick in range(6):
        value = max_y * tick / 5
        y = sy(value)
        lines.append(f'<line x1="{margin_left}" y1="{y:.2f}" x2="{margin_left + plot_w}" y2="{y:.2f}" stroke="#e5e7eb"/>')
        lines.append(f'<text x="{margin_left - 10}" y="{y + 4:.2f}" text-anchor="end" font-family="Arial" font-size="12" fill="#6b7280">{value:.2f}</text>')

    for tick in range(6):
        value = min_x + (max_x - min_x) * tick / 5
        x = sx(value)
        lines.append(f'<text x="{x:.2f}" y="{margin_top + plot_h + 22}" text-anchor="middle" font-family="Arial" font-size="12" fill="#6b7280">{value:.0f}</text>')

    for strategy in strategies:
        points = series[strategy]
        if not points:
            continue
        polyline = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in points)
        lines.append(
            f'<polyline points="{polyline}" fill="none" stroke="{colors[strategy]}" stroke-width="2.2"/>'
        )

    legend_x = margin_left + plot_w - 170
    legend_y = margin_top + 8
    for index, strategy in enumerate(strategies):
        y = legend_y + index * 24
        lines.append(f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 28}" y2="{y}" stroke="{colors[strategy]}" stroke-width="3"/>')
        lines.append(f'<text x="{legend_x + 36}" y="{y + 4}" font-family="Arial" font-size="13" fill="#111827">{strategy}</text>')

    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_charts(output_dir: Path, timeseries_csv: Path) -> list[Path]:
    rows = aggregate_timeseries_rows(read_timeseries_rows(timeseries_csv))
    if plt is not None:
        return write_matplotlib_charts(output_dir, rows)

    charts = [
        (
            output_dir / "collection_rate.svg",
            "collectionRate",
            "Collection Rate Over Time",
            "collection rate",
        ),
        (
            output_dir / "zone_imbalance.svg",
            "zoneImbalance",
            "Zone Load Imbalance Over Time",
            "load variance",
        ),
        (
            output_dir / "idle_rate.svg",
            "idleAgentRate",
            "Idle Plogger Rate Over Time",
            "idle rate",
        ),
    ]
    written = []
    for path, y_key, title, y_label in charts:
        write_svg_line_chart(path, rows, y_key, title, y_label)
        written.append(path)
    return written


def write_matplotlib_charts(output_dir: Path, rows: list[dict]) -> list[Path]:
    strategies = ["random", "trash_priority", "uniform"]
    labels = {
        "random": "Random",
        "trash_priority": "Trash-priority",
        "uniform": "Uniform",
    }
    colors = {
        "random": "#64748b",
        "trash_priority": "#dc2626",
        "uniform": "#2563eb",
    }
    charts = [
        {
            "path": output_dir / "collection_rate.svg",
            "y_key": "collectionRate",
            "title": "Collection Rate Over Time",
            "y_label": "Collection rate",
            "ylim": (0.0, 1.0),
            "percent": True,
        },
        {
            "path": output_dir / "zone_imbalance.svg",
            "y_key": "zoneImbalance",
            "title": "Zone Load Imbalance Over Time",
            "y_label": "Load variance",
            "ylim": None,
            "percent": False,
        },
        {
            "path": output_dir / "idle_rate.svg",
            "y_key": "idleAgentRate",
            "title": "Idle Plogger Rate Over Time",
            "y_label": "Idle plogger rate",
            "ylim": (0.0, 1.0),
            "percent": True,
        },
    ]

    written = []
    for chart in charts:
        fig, ax = plt.subplots(figsize=(9.6, 5.4), dpi=160)
        for strategy in strategies:
            points = [
                (float(row["timeSeconds"]) / 60.0, float(row[chart["y_key"]]))
                for row in rows
                if row["strategy"] == strategy
            ]
            if not points:
                continue
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            ax.plot(xs, ys, label=labels[strategy], color=colors[strategy], linewidth=2.2)

        ax.set_title(chart["title"], fontsize=15, weight="bold", pad=12)
        ax.set_xlabel("Time (minutes)")
        ax.set_ylabel(chart["y_label"])
        if chart["ylim"] is not None:
            ax.set_ylim(*chart["ylim"])
        if chart["percent"]:
            ax.yaxis.set_major_formatter(lambda value, _: f"{value * 100:.0f}%")
        ax.grid(True, axis="both", color="#e5e7eb", linewidth=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(loc="best", frameon=False)
        fig.tight_layout()
        fig.savefig(chart["path"], format="svg")
        plt.close(fig)
        written.append(chart["path"])
    return written


def main() -> None:
    args = parse_args()
    base_zone_payload = load_zone_payload(args.zones)
    movement_rules = MovementRules.load(args.movement_rules)
    if args.distance_mode == "route":
        route_graph = WalkableRouteGraph.from_osm_features(args.osm_features, movement_rules=movement_rules)
    elif args.distance_mode == "obstacle":
        route_graph = ObstacleAwareDistance.from_osm_features(args.osm_features)
    else:
        route_graph = None
    all_summary_rows = []
    results_by_run = []

    run_indices = range(args.runs)
    run_iterator = (
        tqdm(run_indices, desc="experiment runs", unit="run", leave=True)
        if not args.no_progress and tqdm is not None
        else run_indices
    )

    for run_index in run_iterator:
        zone_payload = build_run_zone_payload(base_zone_payload, args, run_index)
        save_run_zone_payload(args.output_dir, run_index, zone_payload)
        assignments = build_assignments(
            zone_payload=zone_payload,
            agent_count=args.agents,
            seed=args.seed + run_index,
            assignment_dir=args.assignment_dir,
            run_index=run_index,
        )
        results = run_all_simulations(
            args,
            zone_payload,
            assignments,
            run_index,
            route_graph,
            show_progress=not args.no_progress,
        )
        results_by_run.append((run_index, results))
        for strategy, result in results.items():
            all_summary_rows.append(summarize_result(strategy, run_index, result))

    run_summary_csv = write_run_summary_csv(args.output_dir, all_summary_rows)
    summary_csv = write_aggregate_summary_csv(args.output_dir, all_summary_rows)
    timeseries_csv = write_timeseries_csv(args.output_dir, results_by_run)
    chart_paths = write_charts(args.output_dir, timeseries_csv)

    print(f"summary_by_run\t{run_summary_csv}")
    print(f"summary\t{summary_csv}")
    print(f"timeseries\t{timeseries_csv}")
    for chart_path in chart_paths:
        print(f"chart\t{chart_path}")


if __name__ == "__main__":
    main()
