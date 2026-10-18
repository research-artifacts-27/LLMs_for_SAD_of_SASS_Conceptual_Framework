#!/usr/bin/env python3

import csv
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
RESULTS_ROOT = ROOT / "results"
AGG_ROOT = ROOT / "aggregate"
FIG_ROOT = AGG_ROOT / "figures"

VARIANTS = ["B0", "B1", "B2", "B3"]
LABELS = {
    "B0": "B0\nRule",
    "B1": "B1\nLLM",
    "B2": "B2\nLLM+RAG",
    "B3": "B3\nAgentic",
}

REPETITIONS = range(5)
GRID = np.arange(0.0, 420.0 + 0.001, 2.0)


def read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def as_float(value):
    if value in ("", None, "None", "NA"):
        return np.nan
    return float(value)


def load_variant_summary():
    path = AGG_ROOT / "variant_summary.csv"
    rows = read_csv(path)

    lookup = {
        row["variant"]: row
        for row in rows
    }

    missing = [
        variant
        for variant in VARIANTS
        if variant not in lookup
    ]

    if missing:
        raise RuntimeError(
            "Missing variants in variant_summary.csv: "
            + str(missing)
        )

    return lookup


def load_timeseries(variant, repetition):
    path = (
        RESULTS_ROOT
        / variant
        / "rep{:02d}".format(repetition)
        / "runtime_timeseries.csv"
    )

    rows = read_csv(path)

    elapsed = []
    response_time = []
    active_servers = []

    for row in rows:
        t = float(row["elapsed_s"])

        if t > 420.0:
            continue

        elapsed.append(t)
        response_time.append(float(row["response_time"]))
        active_servers.append(float(row["active_servers"]))

    if not elapsed:
        raise RuntimeError(
            "No usable samples in {}".format(path)
        )

    return (
        np.asarray(elapsed, dtype=float),
        np.asarray(response_time, dtype=float),
        np.asarray(active_servers, dtype=float),
    )


def nearest_sample_resample(times, values, grid):
    """
    Resample onto the common 2-second grid using the nearest
    actually observed sample rather than inventing interpolated
    measurements.
    """

    times = np.asarray(times)
    values = np.asarray(values)

    right = np.searchsorted(times, grid, side="left")
    right = np.clip(right, 0, len(times) - 1)
    left = np.clip(right - 1, 0, len(times) - 1)

    choose_right = (
        np.abs(times[right] - grid)
        < np.abs(times[left] - grid)
    )

    indices = np.where(
        choose_right,
        right,
        left,
    )

    return values[indices]


def prepare_longitudinal():
    result = {}

    for variant in VARIANTS:
        rt_runs = []
        server_runs = []

        for repetition in REPETITIONS:
            t, rt, servers = load_timeseries(
                variant,
                repetition,
            )

            rt_runs.append(
                nearest_sample_resample(
                    t,
                    rt,
                    GRID,
                )
            )

            server_runs.append(
                nearest_sample_resample(
                    t,
                    servers,
                    GRID,
                )
            )

        rt_runs = np.vstack(rt_runs)
        server_runs = np.vstack(server_runs)

        result[variant] = {
            "response_time_mean":
                np.mean(rt_runs, axis=0),
            "response_time_sd":
                np.std(rt_runs, axis=0, ddof=1),
            "active_servers_mean":
                np.mean(server_runs, axis=0),
            "active_servers_sd":
                np.std(server_runs, axis=0, ddof=1),
        }

    return result


def make_summary_figure(summary):
    fig, axes = plt.subplots(
        1,
        3,
        figsize=(7.15, 2.35),
    )

    x = np.arange(len(VARIANTS))

    specs = [
        (
            "qos_violation_rate_percent",
            "QoS violation rate (%)",
            "(a) QoS violations",
        ),
        (
            "sustained_compliance_start_seconds",
            "Time (s)",
            "(b) Sustained compliance",
        ),
        (
            "mean_controller_cycle_duration_seconds",
            "Duration (s)",
            "(c) Controller overhead",
        ),
    ]

    for ax, (metric, ylabel, title) in zip(axes, specs):
        means = [
            as_float(
                summary[v][metric + "_mean"]
            )
            for v in VARIANTS
        ]

        sds = [
            as_float(
                summary[v][metric + "_sd"]
            )
            for v in VARIANTS
        ]

        ax.bar(
            x,
            means,
            yerr=sds,
            capsize=3,
        )

        ax.set_xticks(x)
        ax.set_xticklabels(
            [LABELS[v] for v in VARIANTS],
            fontsize=7.5,
        )
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(
            axis="y",
            linestyle=":",
            alpha=0.35,
        )

    fig.text(
        0.5,
        0.01,
        "Bars show mean +/- SD across five paired repetitions.",
        ha="center",
        fontsize=7.5,
    )

    fig.tight_layout(
        rect=(0, 0.06, 1, 1)
    )

    pdf = FIG_ROOT / "fig_e8_comparative_summary.pdf"
    png = FIG_ROOT / "fig_e8_comparative_summary.png"

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


def make_trajectory_figure(longitudinal):
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(7.15, 4.25),
        sharex=True,
    )

    ax_rt = axes[0]
    ax_srv = axes[1]

    for variant in VARIANTS:
        data = longitudinal[variant]

        ax_rt.plot(
            GRID,
            data["response_time_mean"],
            linewidth=1.25,
            label=variant,
        )

        ax_srv.plot(
            GRID,
            data["active_servers_mean"],
            linewidth=1.25,
            label=variant,
        )

    ax_rt.axhline(
        0.75,
        linestyle="--",
        linewidth=1.0,
        label="QoS target",
    )

    for t in [60, 120, 180, 240, 300, 360]:
        ax_rt.axvline(
            t,
            linestyle=":",
            linewidth=0.6,
            alpha=0.35,
        )
        ax_srv.axvline(
            t,
            linestyle=":",
            linewidth=0.6,
            alpha=0.35,
        )

    ax_rt.set_ylabel(
        "Response time (s)"
    )
    ax_rt.set_title(
        "(a) Mean response-time trajectory"
    )
    ax_rt.grid(
        axis="y",
        linestyle=":",
        alpha=0.3,
    )

    ax_srv.set_ylabel(
        "Active servers"
    )
    ax_srv.set_xlabel(
        "Elapsed experiment time (s)"
    )
    ax_srv.set_title(
        "(b) Mean server-allocation trajectory"
    )
    ax_srv.set_ylim(
        0.8,
        6.2,
    )
    ax_srv.set_yticks(
        [1, 2, 3, 4, 5, 6]
    )
    ax_srv.grid(
        axis="y",
        linestyle=":",
        alpha=0.3,
    )

    handles, labels = ax_rt.get_legend_handles_labels()

    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=5,
        bbox_to_anchor=(0.5, 1.01),
        fontsize=7.5,
    )

    fig.text(
        0.5,
        0.01,
        "Lines show means across five paired repetitions; "
        "vertical markers indicate controller cycles.",
        ha="center",
        fontsize=7.5,
    )

    fig.tight_layout(
        rect=(0, 0.05, 1, 0.94)
    )

    pdf = FIG_ROOT / "fig_e8_longitudinal.pdf"
    png = FIG_ROOT / "fig_e8_longitudinal.png"

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
    FIG_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary = load_variant_summary()
    longitudinal = prepare_longitudinal()

    summary_pdf, summary_png = make_summary_figure(
        summary
    )

    trajectory_pdf, trajectory_png = (
        make_trajectory_figure(
            longitudinal
        )
    )

    print("=" * 72)
    print("E8 PAPER FIGURES GENERATED")
    print("=" * 72)

    print()
    print("Comparative summary:")
    print(summary_pdf)
    print(summary_png)

    print()
    print("Longitudinal behavior:")
    print(trajectory_pdf)
    print(trajectory_png)

    print()
    print("No SWIM execution or API calls were performed.")


if __name__ == "__main__":
    main()
