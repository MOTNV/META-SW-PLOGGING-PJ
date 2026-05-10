from __future__ import annotations

import argparse
import json
import random
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT_PATH = ROOT / "simulation" / "simple_zones.json"
DEFAULT_OUTPUT_DIR = ROOT / "simulation" / "assignments"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assign agents to zones using simple placement strategies."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--agents", type=int, default=20)
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=["random", "trash_priority", "uniform"],
        choices=["random", "trash_priority", "uniform"],
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def load_zone_payload(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if "zones" not in payload or not isinstance(payload["zones"], list):
        raise ValueError("Input JSON must contain a 'zones' list.")

    return payload


def reset_assigned_counts(zones: list[dict]) -> list[dict]:
    copied = deepcopy(zones)
    for zone in copied:
        zone["assignedAgentCount"] = 0
    return copied


def assign_random(zones: list[dict], agent_count: int, rng: random.Random) -> list[dict]:
    assigned = reset_assigned_counts(zones)
    if not assigned:
        return assigned

    for _ in range(agent_count):
        zone = rng.choice(assigned)
        zone["assignedAgentCount"] += 1
    return assigned


def assign_trash_priority(zones: list[dict], agent_count: int) -> list[dict]:
    assigned = reset_assigned_counts(zones)
    if not assigned:
        return assigned

    weighted_zones = sorted(
        assigned,
        key=lambda zone: (zone.get("trashMass", 0), zone.get("trashCount", 0)),
        reverse=True,
    )

    total_trash_mass = sum(max(0, zone.get("trashMass", 0)) for zone in weighted_zones)
    if total_trash_mass <= 0:
        return assign_uniform(assigned, agent_count)

    allocated = 0
    for zone in weighted_zones:
        share = zone.get("trashMass", 0) / total_trash_mass
        count = int(agent_count * share)
        zone["assignedAgentCount"] += count
        allocated += count

    while allocated < agent_count:
        best_zone = max(
            weighted_zones,
            key=lambda zone: (
                zone.get("trashMass", 0) / max(1, zone.get("assignedAgentCount", 0)),
                zone.get("trashCount", 0),
            ),
        )
        best_zone["assignedAgentCount"] += 1
        allocated += 1

    return assigned


def assign_uniform(zones: list[dict], agent_count: int) -> list[dict]:
    assigned = reset_assigned_counts(zones)
    if not assigned:
        return assigned

    zone_count = len(assigned)
    base = agent_count // zone_count
    remainder = agent_count % zone_count

    for zone in assigned:
        zone["assignedAgentCount"] = base

    for index in range(remainder):
        assigned[index]["assignedAgentCount"] += 1

    return assigned


def summarize_assignment(strategy: str, zones: list[dict], agent_count: int) -> dict:
    return {
        "strategy": strategy,
        "agentCount": agent_count,
        "zoneCount": len(zones),
        "totalAssignedAgents": sum(zone.get("assignedAgentCount", 0) for zone in zones),
        "zones": zones,
    }


def save_assignment(output_dir: Path, summary: dict) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{summary['strategy']}_assignment.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return output_path


def main() -> None:
    args = parse_args()
    payload = load_zone_payload(args.input)
    zones = payload["zones"]
    rng = random.Random(args.seed)

    strategy_to_function = {
        "random": lambda current_zones: assign_random(current_zones, args.agents, rng),
        "trash_priority": lambda current_zones: assign_trash_priority(current_zones, args.agents),
        "uniform": lambda current_zones: assign_uniform(current_zones, args.agents),
    }

    for strategy in args.strategies:
        assigned_zones = strategy_to_function[strategy](zones)
        summary = summarize_assignment(strategy, assigned_zones, args.agents)
        output_path = save_assignment(args.output_dir, summary)
        print(f"saved\t{output_path}")
        print(f"strategy\t{strategy}")
        print(f"agents\t{summary['totalAssignedAgents']}")


if __name__ == "__main__":
    main()
