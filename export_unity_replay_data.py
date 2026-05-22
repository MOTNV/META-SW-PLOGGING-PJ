import argparse
import json
from pathlib import Path


DEFAULT_STRATEGIES = ("random", "trash_priority", "uniform")


def compact_result(source_path: Path, sample_seconds: int) -> dict:
    with source_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    history = data.get("history", [])
    if not history:
        raise ValueError(f"No history in {source_path}")

    compact_history = []
    for index, step in enumerate(history):
        time_seconds = float(step.get("timeSeconds", 0.0))
        is_first = index == 0
        is_last = index == len(history) - 1
        is_sample = sample_seconds <= 1 or int(time_seconds) % sample_seconds == 0
        if not (is_first or is_last or is_sample):
            continue

        compact_history.append(
            {
                "timeSeconds": step.get("timeSeconds", 0.0),
                "remainingTrashMass": step.get("remainingTrashMass", 0),
                "remainingTrashCount": step.get("remainingTrashCount", 0),
                "idleAgentCount": step.get("idleAgentCount", 0),
                "zoneImbalance": step.get("zoneImbalance", 0.0),
                "agentSnapshots": [
                    {
                        "agentId": agent.get("agentId", ""),
                        "assignedZoneId": agent.get("assignedZoneId", ""),
                        "latitude": agent.get("latitude", 0.0),
                        "longitude": agent.get("longitude", 0.0),
                        "targetTrashIndex": agent.get("targetTrashIndex"),
                        "collectedMass": agent.get("collectedMass", 0),
                        "collectedCount": agent.get("collectedCount", 0),
                    }
                    for agent in step.get("agentSnapshots", [])
                ],
                "collectedTrashIndices": step.get("collectedTrashIndices", []),
            }
        )

    metadata = data.get("metadata", {})
    metadata["unitySampleSeconds"] = sample_seconds
    metadata["unitySourceFile"] = source_path.as_posix()
    return {
        "metadata": metadata,
        "summary": data.get("summary", {}),
        "activeTrashRecordIndices": data.get("activeTrashRecordIndices", []),
        "excludedTrashRecordIndices": data.get("excludedTrashRecordIndices", []),
        "agents": [
            {
                "agent_id": agent.get("agent_id", ""),
                "assigned_zone_id": agent.get("assigned_zone_id", ""),
                "latitude": agent.get("latitude", 0.0),
                "longitude": agent.get("longitude", 0.0),
                "collected_mass": agent.get("collected_mass", 0),
                "collected_count": agent.get("collected_count", 0),
                "travel_distance_m": agent.get("travel_distance_m", 0.0),
            }
            for agent in data.get("agents", [])
        ],
        "history": compact_history,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export compact Unity replay JSON files.")
    parser.add_argument("--source-dir", default="simulation/comparison_route/runs")
    parser.add_argument("--output-dir", default="unity/MetaSW/Assets/Data")
    parser.add_argument("--run", type=int, default=0)
    parser.add_argument("--sample-seconds", type=int, default=3)
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for strategy in DEFAULT_STRATEGIES:
        source_path = source_dir / f"greedy_{strategy}_run_{args.run:03d}_result.json"
        compact = compact_result(source_path, args.sample_seconds)
        output_path = output_dir / f"unity_replay_{strategy}.json"
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(compact, f, ensure_ascii=False, separators=(",", ":"))
        print(f"Wrote {output_path} ({len(compact['history'])} frames)")


if __name__ == "__main__":
    main()
