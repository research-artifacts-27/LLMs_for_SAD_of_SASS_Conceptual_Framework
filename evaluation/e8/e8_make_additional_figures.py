#!/usr/bin/env python3

import csv
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
AGG = ROOT / "aggregate"
FIG = AGG / "figures"

RUN_METRICS = AGG / "run_level_metrics.csv"

VARIANTS = ["B0", "B1", "B2", "B3"]
LABELS = {
    "B0": "B0\nRule",
    "B1": "B1\nLLM",
    "B2": "B2\nLLM+RAG",
    "B3": "B3\nAgentic",
}


def read_run_metrics():
    with RUN_METRICS.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def make_controller_overhead(rows):
    values = {}

    for variant in VARIANTS:
        vals = [
            float(r["mean_controller_cycle_duration_seconds"])
            for r in rows
            if r["variant"] == variant
        ]

        if len(vals) != 5:
            raise RuntimeError(
                "{} has {} runs; expected 5".format(
                    variant,
                    len(vals),
                )
            )

        values[variant] = vals

    fig, ax = plt.subplots(
        figsize=(5.0, 3.15)
    )

    x = np.arange(len(VARIANTS))

    means = [
        np.mean(values[v])
        for v in VARIANTS
    ]

    sds = [
        np.std(values[v], ddof=1)
        for v in VARIANTS
    ]

    # Mean +/- SD
    ax.errorbar(
        x,
        means,
        yerr=sds,
        fmt="o",
        capsize=5,
        markersize=7,
        linewidth=1.4,
        label="Mean +/- SD",
    )

    # Individual paired repetitions.
    offsets = np.linspace(-0.10, 0.10, 5)

    for i, variant in enumerate(VARIANTS):
        for j, value in enumerate(values[variant]):
            ax.scatter(
                i + offsets[j],
                value,
                s=24,
                marker="x",
            )

    ax.set_xticks(x)
    ax.set_xticklabels(
        [LABELS[v] for v in VARIANTS]
    )

    ax.set_ylabel(
        "Controller-cycle duration (s)"
    )

    ax.set_title(
        "Runtime controller overhead"
    )

    ax.grid(
        axis="y",
        linestyle=":",
        alpha=0.35,
    )

    ax.text(
        0.02,
        0.97,
        "n = 5 paired repetitions",
        transform=ax.transAxes,
        va="top",
        fontsize=8,
    )

    fig.tight_layout()

    pdf = FIG / "fig_e8_controller_overhead.pdf"
    png = FIG / "fig_e8_controller_overhead.png"

    fig.savefig(
        pdf,
        bbox_inches="tight",
    )

    fig.savefig(
        png,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    return pdf, png


def make_fault_injection_figure():
    """
    Controlled fault-injection evidence previously validated
    independently from the nominal E8 campaign.

    EXP-D:
      Unsafe remove_server at minimum capacity.
      Safety rejection; executor not invoked.
      Recovery attempts = 0.

    EXP-E:
      Injected unsafe initial plan.
      Safety rejection -> LLM replanning -> revised safe plan.
      Recovery attempts = 1.
      Final result = PASS.

    EXP-F:
      Persistent unsafe candidates.
      Two bounded replanning attempts.
      Retry exhaustion -> fail-safe.
      Recovery attempts = 2.
    """

    scenarios = ["EXP-D", "EXP-E", "EXP-F"]
    recovery_attempts = [0, 1, 2]
    fail_safe = [0, 0, 1]

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(6.6, 2.8),
    )

    # Panel A: bounded recovery attempts
    ax = axes[0]

    bars = ax.bar(
        scenarios,
        recovery_attempts,
    )

    ax.set_ylabel(
        "Recovery attempts"
    )

    ax.set_ylim(
        0,
        2.6,
    )

    ax.set_yticks(
        [0, 1, 2]
    )

    ax.set_title(
        "(a) Bounded replanning"
    )

    ax.grid(
        axis="y",
        linestyle=":",
        alpha=0.35,
    )

    annotations = [
        "Safety reject\nNo execution",
        "Reject -> replan\nPASS",
        "Retry exhaustion\nFail-safe",
    ]

    for bar, text in zip(
        bars,
        annotations,
    ):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.10,
            text,
            ha="center",
            va="bottom",
            fontsize=7.2,
        )

    # Panel B: fail-safe activation
    ax = axes[1]

    bars = ax.bar(
        scenarios,
        fail_safe,
    )

    ax.set_ylabel(
        "Fail-safe triggered"
    )

    ax.set_ylim(
        0,
        1.25,
    )

    ax.set_yticks(
        [0, 1]
    )

    ax.set_yticklabels(
        ["No", "Yes"]
    )

    ax.set_title(
        "(b) Failure handling outcome"
    )

    ax.grid(
        axis="y",
        linestyle=":",
        alpha=0.35,
    )

    outcome_text = [
        "Rejected safely",
        "Recovered",
        "Fail-safe",
    ]

    for bar, text in zip(
        bars,
        outcome_text,
    ):
        y = (
            bar.get_height() + 0.05
            if bar.get_height() > 0
            else 0.06
        )

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            text,
            ha="center",
            va="bottom",
            fontsize=7.4,
        )

    fig.text(
        0.5,
        0.01,
        "Controlled fault-injection experiments; "
        "separate from the nominal E8 workload comparison.",
        ha="center",
        fontsize=7.5,
    )

    fig.tight_layout(
        rect=(0, 0.07, 1, 1)
    )

    pdf = FIG / "fig_fault_injection_recovery.pdf"
    png = FIG / "fig_fault_injection_recovery.png"

    fig.savefig(
        pdf,
        bbox_inches="tight",
    )

    fig.savefig(
        png,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    return pdf, png


def main():
    FIG.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = read_run_metrics()

    overhead_pdf, overhead_png = (
        make_controller_overhead(rows)
    )

    fault_pdf, fault_png = (
        make_fault_injection_figure()
    )

    print("=" * 72)
    print("ADDITIONAL PAPER FIGURES GENERATED")
    print("=" * 72)

    print()
    print("Controller overhead:")
    print(overhead_pdf)
    print(overhead_png)

    print()
    print("Controlled fault-injection:")
    print(fault_pdf)
    print(fault_png)

    print()
    print(
        "No SWIM execution or API calls were performed."
    )


if __name__ == "__main__":
    main()
