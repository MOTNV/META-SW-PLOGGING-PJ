from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
DEFAULT_SUMMARY = ROOT / "simulation" / "comparison_obstacle" / "summary.csv"
DEFAULT_OUTPUT = ROOT / "simulation" / "comparison_obstacle" / "figure_4_strategy_summary.png"
DEFAULT_LINE_OUTPUT = ROOT / "simulation" / "comparison_obstacle" / "figure_4_strategy_summary_line.png"
DEFAULT_TIMESERIES = ROOT / "simulation" / "comparison_obstacle" / "timeseries.csv"
DEFAULT_TIMESERIES_OUTPUT = ROOT / "simulation" / "comparison_obstacle" / "figure_4_timeseries_summary.png"

STRATEGY_LABELS = {
    "random": "무작위\n배치",
    "trash_priority": "쓰레기량\n우선 배치",
    "uniform": "균등\n배치",
}

STRATEGY_COLORS = {
    "random": "#64748b",
    "trash_priority": "#dc2626",
    "uniform": "#2563eb",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a paper-ready strategy summary figure.")
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--timeseries", type=Path, default=DEFAULT_TIMESERIES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--line-output", type=Path, default=DEFAULT_LINE_OUTPUT)
    parser.add_argument("--timeseries-output", type=Path, default=DEFAULT_TIMESERIES_OUTPUT)
    return parser.parse_args()


def read_summary(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_timeseries(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def aggregate_timeseries(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, float], dict[str, list[float]]] = {}
    metrics = ["collectionRate", "remainingTrashMass", "zoneImbalance"]
    for row in rows:
        key = (row["strategy"], float(row["timeSeconds"]))
        bucket = grouped.setdefault(key, {metric: [] for metric in metrics})
        for metric in metrics:
            bucket[metric].append(float(row[metric]))

    aggregated = []
    for (strategy, time_seconds), values_by_metric in grouped.items():
        output_row = {"strategy": strategy, "timeSeconds": time_seconds}
        for metric, values in values_by_metric.items():
            output_row[metric] = sum(values) / len(values)
        aggregated.append(output_row)

    return sorted(aggregated, key=lambda row: (row["strategy"], row["timeSeconds"]))


def generate_figure(rows: list[dict], output_path: Path) -> None:
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False

    strategies = ["random", "trash_priority", "uniform"]
    row_by_strategy = {row["strategy"]: row for row in rows}
    labels = [STRATEGY_LABELS[strategy] for strategy in strategies]
    colors = [STRATEGY_COLORS[strategy] for strategy in strategies]

    panels = [
        {
            "title": "수거율",
            "mean": "collectionRateMean",
            "std": "collectionRateStd",
            "ylabel": "수거율",
            "fmt": "{:.3f}",
        },
        {
            "title": "남은 쓰레기량",
            "mean": "remainingTrashMassMean",
            "std": "remainingTrashMassStd",
            "ylabel": "쓰레기량",
            "fmt": "{:.1f}",
        },
        {
            "title": "평균 구역 불균형",
            "mean": "averageZoneImbalanceMean",
            "std": "averageZoneImbalanceStd",
            "ylabel": "구역 부하 분산",
            "fmt": "{:.1f}",
        },
    ]

    fig, axes = plt.subplots(1, 3, figsize=(18, 6.5), dpi=200)
    fig.suptitle("그림 4. 배치 전략별 실험 결과 비교", fontsize=30, fontweight="bold", y=1.04)

    for ax, panel in zip(axes, panels):
        means = [float(row_by_strategy[strategy][panel["mean"]]) for strategy in strategies]
        stds = [float(row_by_strategy[strategy][panel["std"]]) for strategy in strategies]
        bars = ax.bar(labels, means, color=colors, alpha=0.88, yerr=stds, capsize=8)

        ax.set_title(panel["title"], fontsize=22, fontweight="bold", pad=16)
        ax.set_ylabel(panel["ylabel"], fontsize=18)
        ax.tick_params(axis="x", labelsize=16)
        ax.tick_params(axis="y", labelsize=14)
        ax.grid(True, axis="y", color="#e5e7eb", linewidth=1.0)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        y_max = max(mean + std for mean, std in zip(means, stds))
        ax.set_ylim(0, y_max * 1.25 if y_max > 0 else 1)
        for bar, mean in zip(bars, means):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                panel["fmt"].format(mean),
                ha="center",
                va="bottom",
                fontsize=14,
                fontweight="bold",
                color="#111827",
            )

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def generate_line_figure(rows: list[dict], output_path: Path) -> None:
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False

    strategies = ["random", "trash_priority", "uniform"]
    row_by_strategy = {row["strategy"]: row for row in rows}
    labels = [STRATEGY_LABELS[strategy].replace("\n", " ") for strategy in strategies]
    x_values = list(range(len(strategies)))

    panels = [
        {
            "title": "수거율",
            "mean": "collectionRateMean",
            "std": "collectionRateStd",
            "ylabel": "수거율",
            "color": "#16a34a",
            "fmt": "{:.3f}",
        },
        {
            "title": "남은 쓰레기량",
            "mean": "remainingTrashMassMean",
            "std": "remainingTrashMassStd",
            "ylabel": "쓰레기량",
            "color": "#dc2626",
            "fmt": "{:.1f}",
        },
        {
            "title": "평균 구역 불균형",
            "mean": "averageZoneImbalanceMean",
            "std": "averageZoneImbalanceStd",
            "ylabel": "구역 부하 분산",
            "color": "#2563eb",
            "fmt": "{:.1f}",
        },
    ]

    fig, axes = plt.subplots(1, 3, figsize=(18, 6.5), dpi=200)
    fig.suptitle("그림 4. 배치 전략별 실험 결과 비교", fontsize=30, fontweight="bold", y=1.04)

    for ax, panel in zip(axes, panels):
        means = [float(row_by_strategy[strategy][panel["mean"]]) for strategy in strategies]
        stds = [float(row_by_strategy[strategy][panel["std"]]) for strategy in strategies]
        ax.errorbar(
            x_values,
            means,
            yerr=stds,
            color=panel["color"],
            marker="o",
            markersize=12,
            linewidth=4,
            capsize=9,
            capthick=2.4,
        )

        ax.set_title(panel["title"], fontsize=22, fontweight="bold", pad=16)
        ax.set_ylabel(panel["ylabel"], fontsize=18)
        ax.set_xticks(x_values)
        ax.set_xticklabels(labels, fontsize=16)
        ax.tick_params(axis="y", labelsize=14)
        ax.grid(True, axis="both", color="#e5e7eb", linewidth=1.0)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        y_max = max(mean + std for mean, std in zip(means, stds))
        ax.set_ylim(0, y_max * 1.25 if y_max > 0 else 1)
        for x, mean in zip(x_values, means):
            ax.text(
                x,
                mean,
                panel["fmt"].format(mean),
                ha="center",
                va="bottom",
                fontsize=14,
                fontweight="bold",
                color="#111827",
            )

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def generate_timeseries_figure(rows: list[dict], output_path: Path) -> None:
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False

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
    panels = [
        ("collectionRate", "수거율 변화", "수거율"),
        ("remainingTrashMass", "남은 쓰레기량 변화", "쓰레기량"),
        ("zoneImbalance", "구역 불균형 변화", "구역 부하 분산"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(21, 6.8), dpi=200)
    fig.suptitle("그림 4. 배치 전략별 시간대별 변화", fontsize=30, fontweight="bold", y=1.04)

    for ax, (metric, title, ylabel) in zip(axes, panels):
        for strategy in strategies:
            strategy_rows = [row for row in rows if row["strategy"] == strategy]
            if not strategy_rows:
                continue
            x_values = [float(row["timeSeconds"]) for row in strategy_rows]
            y_values = [float(row[metric]) for row in strategy_rows]
            ax.plot(
                x_values,
                y_values,
                label=strategy_labels[strategy],
                color=colors[strategy],
                linewidth=3.4,
            )

        ax.set_title(title, fontsize=22, fontweight="bold", pad=16)
        ax.set_xlabel("시간(초)", fontsize=18)
        ax.set_ylabel(ylabel, fontsize=18)
        ax.tick_params(axis="both", labelsize=14)
        ax.grid(True, axis="both", color="#e5e7eb", linewidth=1.0)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].legend(title="배치 전략", frameon=False, fontsize=15, title_fontsize=15, loc="lower right")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    rows = read_summary(args.summary)
    timeseries_rows = aggregate_timeseries(read_timeseries(args.timeseries))
    generate_figure(rows, args.output)
    generate_line_figure(rows, args.line_output)
    generate_timeseries_figure(timeseries_rows, args.timeseries_output)
    print(f"figure_4\t{args.output}")
    print(f"figure_4_line\t{args.line_output}")
    print(f"figure_4_timeseries\t{args.timeseries_output}")


if __name__ == "__main__":
    main()
