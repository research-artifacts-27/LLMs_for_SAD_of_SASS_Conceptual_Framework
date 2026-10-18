#!/usr/bin/env python3

import argparse
import csv
import json
import math
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS_ROOT = ROOT / "results"
POSTHOC_PATH = ROOT / "posthoc_actuation_validation.json"
OUTPUT_DIR = ROOT / "aggregate"

VARIANTS = ["B0", "B1", "B2", "B3"]
REPETITIONS = range(5)
EVALUATION_END_SECONDS = 420.0


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_timeseries(path):
    rows = []

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        for raw in reader:
            elapsed = float(raw["elapsed_s"])

            if elapsed > EVALUATION_END_SECONDS:
                continue

            rows.append({
                "elapsed_s": elapsed,
                "response_time": float(raw["response_time"]),
                "response_time_target":
                    float(raw["response_time_target"]),
                "qos_satisfied":
                    raw["qos_satisfied"].strip().lower() == "true",
                "active_servers": int(raw["active_servers"]),
                "servers": int(raw["servers"]),
                "dimmer": float(raw["dimmer"]),
                "arrival_rate": float(raw["arrival_rate"]),
                "utilization": float(raw["utilization"]),
            })

    rows.sort(key=lambda x: x["elapsed_s"])
    return rows


def mean_or_none(values):
    values = [
        float(v)
        for v in values
        if v is not None
    ]

    if not values:
        return None

    return statistics.mean(values)


def sd_or_none(values):
    values = [
        float(v)
        for v in values
        if v is not None
    ]

    if len(values) < 2:
        return None

    return statistics.stdev(values)


def median_or_none(values):
    values = [
        float(v)
        for v in values
        if v is not None
    ]

    if not values:
        return None

    return statistics.median(values)


def time_weighted_mean(rows, field):
    if not rows:
        return None

    points = [
        row
        for row in rows
        if 0.0 <= row["elapsed_s"] <= EVALUATION_END_SECONDS
    ]

    if not points:
        return None

    total = 0.0

    # Assume the first observed state also represents t=0
    first_t = max(0.0, points[0]["elapsed_s"])
    total += float(points[0][field]) * first_t

    for i, row in enumerate(points):
        start = max(0.0, row["elapsed_s"])

        if i + 1 < len(points):
            end = min(
                EVALUATION_END_SECONDS,
                points[i + 1]["elapsed_s"],
            )
        else:
            end = EVALUATION_END_SECONDS

        if end > start:
            total += float(row[field]) * (end - start)

    return total / EVALUATION_END_SECONDS


def sustained_compliance_metrics(rows):
    if not rows:
        return {
            "first_violation_elapsed_seconds": None,
            "last_violation_elapsed_seconds": None,
            "sustained_compliance_start_seconds": None,
            "recovery_span_seconds": None,
        }

    violating_indices = [
        i
        for i, row in enumerate(rows)
        if row["response_time"] > row["response_time_target"]
    ]

    if not violating_indices:
        return {
            "first_violation_elapsed_seconds": None,
            "last_violation_elapsed_seconds": None,
            "sustained_compliance_start_seconds": 0.0,
            "recovery_span_seconds": 0.0,
        }

    first_i = violating_indices[0]
    last_i = violating_indices[-1]

    first_t = rows[first_i]["elapsed_s"]
    last_t = rows[last_i]["elapsed_s"]

    if last_i + 1 < len(rows):
        sustained_t = rows[last_i + 1]["elapsed_s"]
        recovery_span = sustained_t - first_t
    else:
        sustained_t = None
        recovery_span = None

    return {
        "first_violation_elapsed_seconds": first_t,
        "last_violation_elapsed_seconds": last_t,
        "sustained_compliance_start_seconds": sustained_t,
        "recovery_span_seconds": recovery_span,
    }


def percentile(values, p):
    values = sorted(float(v) for v in values)

    if not values:
        return None

    if len(values) == 1:
        return values[0]

    k = (len(values) - 1) * p
    lower = math.floor(k)
    upper = math.ceil(k)

    if lower == upper:
        return values[int(k)]

    return (
        values[lower] * (upper - k)
        + values[upper] * (k - lower)
    )


def summarize_run(
    variant,
    repetition,
    summary,
    metrics,
    timeseries,
    posthoc_records,
):
    compliance = sustained_compliance_metrics(timeseries)

    harness_durations = [
        m.get("harness_observed_cycle_duration_seconds")
        for m in metrics
        if m.get("harness_observed_cycle_duration_seconds") is not None
    ]

    decision_latencies = [
        m.get("decision_latency_seconds")
        for m in metrics
        if m.get("decision_latency_seconds") is not None
    ]

    outcomes = Counter(
        str(m.get("outcome_status"))
        for m in metrics
    )

    actions = Counter(
        str(m.get("executed_action"))
        for m in metrics
    )

    posthoc_statuses = Counter(
        r["e8_actuation_status"]
        for r in posthoc_records
    )

    return {
        "variant": variant,
        "repetition": repetition,
        "run_id": summary["run_id"],

        "valid_response_time_samples":
            summary["valid_response_time_samples"],
        "qos_violation_rate_percent":
            summary["qos_violation_rate_percent"],
        "mean_response_time":
            summary["mean_response_time"],
        "p95_response_time":
            summary["p95_response_time"],
        "max_response_time":
            summary["max_response_time"],

        "active_servers_start":
            summary["active_servers_start"],
        "active_servers_end":
            summary["active_servers_end"],
        "dimmer_start":
            summary["dimmer_start"],
        "dimmer_end":
            summary["dimmer_end"],

        "mean_active_servers_time_weighted":
            time_weighted_mean(
                timeseries,
                "active_servers",
            ),
        "mean_dimmer_time_weighted":
            time_weighted_mean(
                timeseries,
                "dimmer",
            ),

        "first_violation_elapsed_seconds":
            compliance["first_violation_elapsed_seconds"],
        "last_violation_elapsed_seconds":
            compliance["last_violation_elapsed_seconds"],
        "sustained_compliance_start_seconds":
            compliance["sustained_compliance_start_seconds"],
        "recovery_span_seconds":
            compliance["recovery_span_seconds"],

        "mean_controller_cycle_duration_seconds":
            mean_or_none(harness_durations),
        "median_controller_cycle_duration_seconds":
            median_or_none(harness_durations),
        "p95_controller_cycle_duration_seconds":
            percentile(harness_durations, 0.95),

        # B3 deliberately has no fabricated common decision latency.
        "mean_reported_decision_latency_seconds":
            mean_or_none(decision_latencies),

        "runtime_rag_used_cycles":
            sum(
                1
                for m in metrics
                if m.get("runtime_rag_used") is True
            ),

        "safety_rejections":
            sum(
                1
                for m in metrics
                if m.get("safety_rejection") is True
            ),

        "recovery_attempts_total":
            sum(
                int(m.get("recovery_attempts") or 0)
                for m in metrics
            ),

        "agentic_recovery_cycles":
            sum(
                1
                for m in metrics
                if m.get("agentic_recovery_used") is True
            ),

        "deterministic_fallback_cycles":
            sum(
                1
                for m in metrics
                if m.get("deterministic_fallback_used") is True
            ),

        "fail_safe_cycles":
            sum(
                1
                for m in metrics
                if m.get("fail_safe_triggered") is True
            ),

        "controller_pass_cycles":
            outcomes.get("PASS", 0),
        "controller_partial_cycles":
            outcomes.get("PARTIAL", 0),
        "controller_fail_cycles":
            outcomes.get("FAIL", 0),

        "action_add_server_cycles":
            actions.get("add_server", 0),
        "action_remove_server_cycles":
            actions.get("remove_server", 0),
        "action_set_dimmer_cycles":
            actions.get("set_dimmer", 0),
        "action_none_cycles":
            actions.get("none", 0),

        "posthoc_immediate_success_cycles":
            posthoc_statuses.get("IMMEDIATE_SUCCESS", 0),
        "posthoc_delayed_success_cycles":
            posthoc_statuses.get("DELAYED_SUCCESS", 0),
        "posthoc_no_effect_cycles":
            posthoc_statuses.get("NO_EFFECT_WITHIN_10S", 0),
        "posthoc_not_applicable_cycles":
            posthoc_statuses.get("NOT_APPLICABLE", 0),
    }


def validate_run(variant, repetition):
    run_dir = (
        RESULTS_ROOT
        / variant
        / "rep{:02d}".format(repetition)
    )

    manifest = load_json(run_dir / "manifest.json")
    summary = load_json(run_dir / "summary.json")
    metrics = load_jsonl(run_dir / "cycle_metrics.jsonl")
    timeseries = load_timeseries(
        run_dir / "runtime_timeseries.csv"
    )

    if manifest.get("status") != "COMPLETE":
        raise RuntimeError(
            "{} is not COMPLETE".format(run_dir)
        )

    if manifest.get("swim_exit_code") != 0:
        raise RuntimeError(
            "{} has SWIM exit code {}".format(
                run_dir,
                manifest.get("swim_exit_code"),
            )
        )

    if len(metrics) != 6:
        raise RuntimeError(
            "{} has {} cycles, expected 6".format(
                run_dir,
                len(metrics),
            )
        )

    if not timeseries:
        raise RuntimeError(
            "{} has no time-series samples".format(run_dir)
        )

    return summary, metrics, timeseries


def build_variant_summary(run_rows):
    selected_metrics = [
        "qos_violation_rate_percent",
        "mean_response_time",
        "p95_response_time",
        "max_response_time",
        "mean_active_servers_time_weighted",
        "mean_dimmer_time_weighted",
        "sustained_compliance_start_seconds",
        "recovery_span_seconds",
        "mean_controller_cycle_duration_seconds",
    ]

    rows = []

    for variant in VARIANTS:
        subset = [
            r
            for r in run_rows
            if r["variant"] == variant
        ]

        row = {
            "variant": variant,
            "runs": len(subset),
        }

        for metric in selected_metrics:
            values = [
                r[metric]
                for r in subset
                if r[metric] is not None
            ]

            row[metric + "_mean"] = mean_or_none(values)
            row[metric + "_sd"] = sd_or_none(values)
            row[metric + "_median"] = median_or_none(values)

        row["controller_pass_cycles_total"] = sum(
            r["controller_pass_cycles"]
            for r in subset
        )

        row["controller_partial_cycles_total"] = sum(
            r["controller_partial_cycles"]
            for r in subset
        )

        row["controller_fail_cycles_total"] = sum(
            r["controller_fail_cycles"]
            for r in subset
        )

        row["posthoc_immediate_success_total"] = sum(
            r["posthoc_immediate_success_cycles"]
            for r in subset
        )

        row["posthoc_delayed_success_total"] = sum(
            r["posthoc_delayed_success_cycles"]
            for r in subset
        )

        row["posthoc_no_effect_total"] = sum(
            r["posthoc_no_effect_cycles"]
            for r in subset
        )

        row["runtime_rag_used_cycles_total"] = sum(
            r["runtime_rag_used_cycles"]
            for r in subset
        )

        row["safety_rejections_total"] = sum(
            r["safety_rejections"]
            for r in subset
        )

        row["recovery_attempts_total"] = sum(
            r["recovery_attempts_total"]
            for r in subset
        )

        row["fail_safe_cycles_total"] = sum(
            r["fail_safe_cycles"]
            for r in subset
        )

        rows.append(row)

    return rows


def build_paired_vs_b0(run_rows):
    metrics = [
        "qos_violation_rate_percent",
        "mean_response_time",
        "p95_response_time",
        "mean_active_servers_time_weighted",
        "sustained_compliance_start_seconds",
        "mean_controller_cycle_duration_seconds",
    ]

    lookup = {
        (r["variant"], r["repetition"]): r
        for r in run_rows
    }

    rows = []

    for variant in ["B1", "B2", "B3"]:
        for metric in metrics:
            differences = []
            pairs = []

            for rep in REPETITIONS:
                baseline = lookup[("B0", rep)][metric]
                candidate = lookup[(variant, rep)][metric]

                if baseline is None or candidate is None:
                    continue

                diff = float(candidate) - float(baseline)

                differences.append(diff)

                pairs.append({
                    "repetition": rep,
                    "b0": baseline,
                    "variant_value": candidate,
                    "difference_variant_minus_b0": diff,
                })

            rows.append({
                "variant": variant,
                "metric": metric,
                "paired_n": len(differences),
                "mean_difference_variant_minus_b0":
                    mean_or_none(differences),
                "sd_difference":
                    sd_or_none(differences),
                "median_difference":
                    median_or_none(differences),
                "pairs": pairs,
            })

    return rows


def write_csv(path, rows):
    if not rows:
        return

    fields = list(rows[0].keys())

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(rows)


def printable(value, digits=3):
    if value is None:
        return "NA"

    if isinstance(value, (int, str)):
        return str(value)

    return "{:.{}f}".format(
        float(value),
        digits,
    )


def print_summary(variant_rows, paired_rows):
    print()
    print("=" * 86)
    print("E8 AGGREGATE RESULTS - 5 PAIRED REPETITIONS")
    print("=" * 86)

    print()
    print("Primary run-level results")
    print(
        "{:<4} {:>10} {:>10} {:>10} {:>10} {:>12}".format(
            "Var",
            "QoS viol%",
            "Mean RT",
            "P95 RT",
            "Avg srv",
            "Sustain(s)",
        )
    )

    for row in variant_rows:
        print(
            "{:<4} {:>10} {:>10} {:>10} {:>10} {:>12}".format(
                row["variant"],
                printable(
                    row[
                        "qos_violation_rate_percent_mean"
                    ]
                ),
                printable(
                    row["mean_response_time_mean"]
                ),
                printable(
                    row["p95_response_time_mean"]
                ),
                printable(
                    row[
                        "mean_active_servers_time_weighted_mean"
                    ]
                ),
                printable(
                    row[
                        "sustained_compliance_start_seconds_mean"
                    ]
                ),
            )
        )

    print()
    print("Controller-cycle duration")
    print(
        "{:<4} {:>12} {:>12}".format(
            "Var",
            "Mean(s)",
            "SD(s)",
        )
    )

    for row in variant_rows:
        print(
            "{:<4} {:>12} {:>12}".format(
                row["variant"],
                printable(
                    row[
                        "mean_controller_cycle_duration_seconds_mean"
                    ]
                ),
                printable(
                    row[
                        "mean_controller_cycle_duration_seconds_sd"
                    ]
                ),
            )
        )

    print()
    print("Controller outcomes / post-hoc actuation")
    print(
        "{:<4} {:>6} {:>8} {:>6} {:>10} {:>9} {:>9}".format(
            "Var",
            "PASS",
            "PARTIAL",
            "FAIL",
            "Immediate",
            "Delayed",
            "NoEffect",
        )
    )

    for row in variant_rows:
        print(
            "{:<4} {:>6} {:>8} {:>6} {:>10} {:>9} {:>9}".format(
                row["variant"],
                row["controller_pass_cycles_total"],
                row["controller_partial_cycles_total"],
                row["controller_fail_cycles_total"],
                row["posthoc_immediate_success_total"],
                row["posthoc_delayed_success_total"],
                row["posthoc_no_effect_total"],
            )
        )

    print()
    print("Paired mean differences versus B0")
    print("(positive means variant value > B0)")
    print(
        "{:<4} {:<43} {:>12}".format(
            "Var",
            "Metric",
            "Mean diff",
        )
    )

    for row in paired_rows:
        print(
            "{:<4} {:<43} {:>12}".format(
                row["variant"],
                row["metric"],
                printable(
                    row[
                        "mean_difference_variant_minus_b0"
                    ]
                ),
            )
        )

    print()
    print(
        "NOTE: n=5 paired repetitions. These are descriptive "
        "comparisons; no significance claim is made."
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--write",
        action="store_true",
        help="Write aggregate artifacts.",
    )

    args = parser.parse_args()

    if not POSTHOC_PATH.is_file():
        raise RuntimeError(
            "Missing post-hoc file: {}".format(
                POSTHOC_PATH
            )
        )

    posthoc = load_json(POSTHOC_PATH)

    if len(posthoc) != 120:
        raise RuntimeError(
            "Expected 120 post-hoc cycle records, found {}".format(
                len(posthoc)
            )
        )

    posthoc_lookup = {}

    for record in posthoc:
        key = (
            record["variant"],
            int(record["repetition"]),
        )

        posthoc_lookup.setdefault(key, []).append(record)

    run_rows = []

    for variant in VARIANTS:
        for repetition in REPETITIONS:
            summary, metrics, timeseries = validate_run(
                variant,
                repetition,
            )

            ph = posthoc_lookup.get(
                (variant, repetition),
                [],
            )

            if len(ph) != 6:
                raise RuntimeError(
                    "{} rep{:02d} has {} post-hoc records, "
                    "expected 6".format(
                        variant,
                        repetition,
                        len(ph),
                    )
                )

            run_rows.append(
                summarize_run(
                    variant,
                    repetition,
                    summary,
                    metrics,
                    timeseries,
                    ph,
                )
            )

    if len(run_rows) != 20:
        raise RuntimeError(
            "Expected 20 valid runs, found {}".format(
                len(run_rows)
            )
        )

    variant_rows = build_variant_summary(run_rows)
    paired_rows = build_paired_vs_b0(run_rows)

    print_summary(
        variant_rows,
        paired_rows,
    )

    if not args.write:
        print()
        print(
            "DRY RUN ONLY: no aggregate result files were written."
        )
        return

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_csv = OUTPUT_DIR / "run_level_metrics.csv"
    variant_csv = OUTPUT_DIR / "variant_summary.csv"
    paired_json = OUTPUT_DIR / "paired_vs_b0.json"
    aggregate_json = OUTPUT_DIR / "aggregate_results.json"

    for path in [
        run_csv,
        variant_csv,
        paired_json,
        aggregate_json,
    ]:
        if path.exists():
            raise RuntimeError(
                "Refusing to overwrite existing aggregate artifact: "
                + str(path)
            )

    write_csv(
        run_csv,
        run_rows,
    )

    write_csv(
        variant_csv,
        variant_rows,
    )

    with paired_json.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            paired_rows,
            f,
            indent=2,
            sort_keys=True,
        )
        f.write("\n")

    with aggregate_json.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "protocol": {
                    "valid_runs": 20,
                    "variants": VARIANTS,
                    "repetitions_per_variant": 5,
                    "paired_by_repetition": True,
                    "evaluation_window_seconds":
                        EVALUATION_END_SECONDS,
                    "inference_policy":
                        "descriptive_preliminary_n5_no_significance_claim",
                },
                "run_level_metrics": run_rows,
                "variant_summary": variant_rows,
                "paired_vs_b0": paired_rows,
            },
            f,
            indent=2,
            sort_keys=True,
        )
        f.write("\n")

    print()
    print("AGGREGATE ARTIFACTS WRITTEN:")
    print(run_csv)
    print(variant_csv)
    print(paired_json)
    print(aggregate_json)


if __name__ == "__main__":
    main()
