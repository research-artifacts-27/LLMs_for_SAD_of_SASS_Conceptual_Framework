#!/usr/bin/env python3

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS_ROOT = ROOT / "results"

VARIANTS = ["B0", "B1", "B2", "B3"]
REPETITIONS = range(5)

WINDOW_SECONDS = 10.0
DIMMER_TOLERANCE = 1e-6

PER_RUN_OUTPUT = "posthoc_actuation_validation.jsonl"
CAMPAIGN_CSV = ROOT / "posthoc_actuation_validation.csv"
CAMPAIGN_JSON = ROOT / "posthoc_actuation_validation.json"


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path):
    records = []

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except Exception as exc:
                raise RuntimeError(
                    "Invalid JSONL in {} line {}: {}".format(
                        path, line_no, exc
                    )
                )

    return records


def read_timeseries(path):
    rows = []

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        required = {
            "elapsed_s",
            "active_servers",
            "dimmer",
            "response_time",
            "response_time_target",
            "qos_satisfied",
        }

        missing = required.difference(reader.fieldnames or [])

        if missing:
            raise RuntimeError(
                "{} is missing columns: {}".format(
                    path, sorted(missing)
                )
            )

        for raw in reader:
            rows.append({
                "elapsed_s": float(raw["elapsed_s"]),
                "active_servers": int(raw["active_servers"]),
                "dimmer": float(raw["dimmer"]),
                "response_time": float(raw["response_time"]),
                "response_time_target": float(
                    raw["response_time_target"]
                ),
                "qos_satisfied": raw["qos_satisfied"].strip().lower()
                == "true",
            })

    rows.sort(key=lambda x: x["elapsed_s"])

    return rows


def normalize_action(action):
    if action is None:
        return "none"

    return str(action).strip().lower()


def immediate_effect(metric):
    """
    Deterministically recompute whether the action effect was already
    visible in the controller's immediate post-execution state.

    This does NOT use the controller's action_effect_observed boolean.
    """

    action = normalize_action(metric.get("executed_action"))

    if not metric.get("execution_performed", False):
        return None

    if action == "none":
        return None

    if action == "add_server":
        before = metric.get("active_servers_before")
        after = metric.get("active_servers_after")

        if before is None or after is None:
            raise RuntimeError(
                "Missing active-server values for add_server"
            )

        return int(after) > int(before)

    if action == "remove_server":
        before = metric.get("active_servers_before")
        after = metric.get("active_servers_after")

        if before is None or after is None:
            raise RuntimeError(
                "Missing active-server values for remove_server"
            )

        return int(after) < int(before)

    if action == "set_dimmer":
        target = metric.get("executed_value")
        after = metric.get("dimmer_after")

        if target is None:
            raise RuntimeError(
                "set_dimmer has no executed_value"
            )

        if after is None:
            raise RuntimeError(
                "set_dimmer has no dimmer_after"
            )

        return abs(float(after) - float(target)) <= DIMMER_TOLERANCE

    raise RuntimeError(
        "Unsupported executed action: {}".format(action)
    )


def row_shows_effect(metric, row):
    action = normalize_action(metric.get("executed_action"))

    if action == "add_server":
        before = metric.get("active_servers_before")

        if before is None:
            raise RuntimeError(
                "Missing active_servers_before for add_server"
            )

        return row["active_servers"] > int(before)

    if action == "remove_server":
        before = metric.get("active_servers_before")

        if before is None:
            raise RuntimeError(
                "Missing active_servers_before for remove_server"
            )

        return row["active_servers"] < int(before)

    if action == "set_dimmer":
        target = metric.get("executed_value")

        if target is None:
            raise RuntimeError(
                "Missing executed_value for set_dimmer"
            )

        return (
            abs(row["dimmer"] - float(target))
            <= DIMMER_TOLERANCE
        )

    if action == "none":
        return False

    raise RuntimeError(
        "Unsupported executed action: {}".format(action)
    )


def validate_cycle(variant, repetition, metric, timeseries):
    action = normalize_action(metric.get("executed_action"))

    cycle_index = int(metric["cycle_index"])
    cycle_end = float(metric["actual_end_elapsed_seconds"])
    window_end = cycle_end + WINDOW_SECONDS

    window_rows = [
        row
        for row in timeseries
        if cycle_end <= row["elapsed_s"] <= window_end
    ]

    execution_performed = bool(
        metric.get("execution_performed", False)
    )

    if not execution_performed or action == "none":
        status = "NOT_APPLICABLE"
        immediate = None
        first_effect = None
        delay = None
    else:
        immediate = immediate_effect(metric)

        first_effect = None

        for row in window_rows:
            if row_shows_effect(metric, row):
                first_effect = row
                break

        if immediate:
            status = "IMMEDIATE_SUCCESS"
            delay = 0.0

        elif first_effect is not None:
            status = "DELAYED_SUCCESS"
            delay = (
                first_effect["elapsed_s"] - cycle_end
            )

        else:
            status = "NO_EFFECT_WITHIN_10S"
            delay = None

    first_effect_elapsed = (
        None
        if first_effect is None
        else first_effect["elapsed_s"]
    )

    first_effect_response_time = (
        None
        if first_effect is None
        else first_effect["response_time"]
    )

    first_effect_active_servers = (
        None
        if first_effect is None
        else first_effect["active_servers"]
    )

    first_effect_dimmer = (
        None
        if first_effect is None
        else first_effect["dimmer"]
    )

    return {
        "posthoc_schema_version":
            "E8-POSTHOC-ACTUATION-1",
        "variant": variant,
        "repetition": repetition,
        "run_id": metric.get("run_id"),
        "cycle_index": cycle_index,

        # Original controller result: NEVER rewritten.
        "controller_outcome":
            metric.get("outcome_status"),
        "controller_action_effect_observed":
            metric.get("action_effect_observed"),

        "execution_performed": execution_performed,
        "executed_action": action,
        "executed_value":
            metric.get("executed_value"),

        "active_servers_before":
            metric.get("active_servers_before"),
        "active_servers_after":
            metric.get("active_servers_after"),
        "dimmer_before":
            metric.get("dimmer_before"),
        "dimmer_after":
            metric.get("dimmer_after"),

        "cycle_end_elapsed_seconds":
            cycle_end,
        "posthoc_window_seconds":
            WINDOW_SECONDS,
        "posthoc_window_end_elapsed_seconds":
            window_end,
        "window_sample_count":
            len(window_rows),

        # Independently recomputed immediate state.
        "immediate_effect_recomputed":
            immediate,

        # Independent continuous-timeseries check.
        "timeseries_effect_observed_within_window":
            first_effect is not None,
        "first_timeseries_effect_elapsed_seconds":
            first_effect_elapsed,
        "first_timeseries_effect_delay_seconds":
            (
                None
                if first_effect is None
                else first_effect_elapsed - cycle_end
            ),
        "first_timeseries_effect_active_servers":
            first_effect_active_servers,
        "first_timeseries_effect_dimmer":
            first_effect_dimmer,
        "first_timeseries_effect_response_time":
            first_effect_response_time,

        # Frozen E8 post-hoc classification.
        "e8_actuation_status": status,
        "e8_actuation_delay_seconds": delay,

        # Explicit reminder: QoS is NOT used to classify actuation.
        "actuation_classification_uses_qos": False,
    }


def validate_run(variant, repetition):
    rep_name = "rep{:02d}".format(repetition)
    run_dir = RESULTS_ROOT / variant / rep_name

    if not run_dir.is_dir():
        raise RuntimeError(
            "Missing valid run directory: {}".format(run_dir)
        )

    manifest_path = run_dir / "manifest.json"
    metrics_path = run_dir / "cycle_metrics.jsonl"
    timeseries_path = run_dir / "runtime_timeseries.csv"

    for required in [
        manifest_path,
        metrics_path,
        timeseries_path,
    ]:
        if not required.is_file():
            raise RuntimeError(
                "Missing required artifact: {}".format(required)
            )

    manifest = read_json(manifest_path)

    if manifest.get("status") != "COMPLETE":
        raise RuntimeError(
            "{} manifest status is {!r}, expected COMPLETE".format(
                run_dir, manifest.get("status")
            )
        )

    if manifest.get("swim_exit_code") != 0:
        raise RuntimeError(
            "{} SWIM exit code is {!r}, expected 0".format(
                run_dir,
                manifest.get("swim_exit_code"),
            )
        )

    metrics = read_jsonl(metrics_path)
    timeseries = read_timeseries(timeseries_path)

    if len(metrics) != 6:
        raise RuntimeError(
            "{} has {} controller cycles, expected 6".format(
                run_dir, len(metrics)
            )
        )

    indices = [
        int(metric["cycle_index"])
        for metric in metrics
    ]

    if indices != [1, 2, 3, 4, 5, 6]:
        raise RuntimeError(
            "{} has unexpected cycle indices: {}".format(
                run_dir, indices
            )
        )

    records = []

    for metric in metrics:
        if metric.get("variant") != variant:
            raise RuntimeError(
                "{} cycle {} variant mismatch".format(
                    run_dir,
                    metric.get("cycle_index"),
                )
            )

        records.append(
            validate_cycle(
                variant,
                repetition,
                metric,
                timeseries,
            )
        )

    return run_dir, records


def write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(
                json.dumps(
                    record,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )


def write_campaign_csv(path, records):
    fields = [
        "variant",
        "repetition",
        "run_id",
        "cycle_index",
        "controller_outcome",
        "controller_action_effect_observed",
        "execution_performed",
        "executed_action",
        "executed_value",
        "active_servers_before",
        "active_servers_after",
        "dimmer_before",
        "dimmer_after",
        "cycle_end_elapsed_seconds",
        "posthoc_window_seconds",
        "window_sample_count",
        "immediate_effect_recomputed",
        "timeseries_effect_observed_within_window",
        "first_timeseries_effect_elapsed_seconds",
        "first_timeseries_effect_delay_seconds",
        "first_timeseries_effect_active_servers",
        "first_timeseries_effect_dimmer",
        "first_timeseries_effect_response_time",
        "e8_actuation_status",
        "e8_actuation_delay_seconds",
        "actuation_classification_uses_qos",
    ]

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

        for record in records:
            writer.writerow({
                field: record.get(field)
                for field in fields
            })


def print_summary(records):
    print()
    print("=" * 72)
    print("E8 FROZEN POST-HOC ACTUATION VALIDATION")
    print("=" * 72)
    print("Valid runs processed: 20 / 20")
    print("Controller cycles processed:", len(records))
    print("Window: cycle end through cycle end + 10.0 s")
    print("QoS used for actuation classification: NO")

    print()
    print("===== ACTUATION STATUS COUNTS =====")

    status_counts = Counter(
        record["e8_actuation_status"]
        for record in records
    )

    for status in [
        "IMMEDIATE_SUCCESS",
        "DELAYED_SUCCESS",
        "NO_EFFECT_WITHIN_10S",
        "NOT_APPLICABLE",
    ]:
        print(
            "{:<24} {}".format(
                status + ":",
                status_counts.get(status, 0),
            )
        )

    print()
    print("===== BY VARIANT =====")

    by_variant = defaultdict(Counter)

    for record in records:
        by_variant[record["variant"]][
            record["e8_actuation_status"]
        ] += 1

    for variant in VARIANTS:
        counts = by_variant[variant]

        print(
            "{}  immediate={}  delayed={}  no_effect={}  n/a={}".format(
                variant,
                counts.get("IMMEDIATE_SUCCESS", 0),
                counts.get("DELAYED_SUCCESS", 0),
                counts.get("NO_EFFECT_WITHIN_10S", 0),
                counts.get("NOT_APPLICABLE", 0),
            )
        )

    print()
    print("===== DELAYED / NO-EFFECT DETAILS =====")

    special = [
        record
        for record in records
        if record["e8_actuation_status"]
        in {
            "DELAYED_SUCCESS",
            "NO_EFFECT_WITHIN_10S",
        }
    ]

    if not special:
        print("None.")
    else:
        for record in special:
            delay = record["e8_actuation_delay_seconds"]

            if delay is None:
                delay_text = "n/a"
            else:
                delay_text = "{:.6f}s".format(delay)

            print(
                "{} rep{:02d} cycle{} | action={} | "
                "controller={} | posthoc={} | delay={}".format(
                    record["variant"],
                    record["repetition"],
                    record["cycle_index"],
                    record["executed_action"],
                    record["controller_outcome"],
                    record["e8_actuation_status"],
                    delay_text,
                )
            )

    print()
    print("===== CONTROLLER OUTCOME x POST-HOC STATUS =====")

    cross = Counter(
        (
            record["controller_outcome"],
            record["e8_actuation_status"],
        )
        for record in records
    )

    for key in sorted(
        cross,
        key=lambda x: (str(x[0]), str(x[1])),
    ):
        print(
            "{:<10} {:<24} {}".format(
                str(key[0]),
                key[1],
                cross[key],
            )
        )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Frozen E8 post-hoc actuation validation. "
            "Offline only; never modifies controller outcomes."
        )
    )

    parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "Write additive per-run JSONL and campaign CSV/JSON "
            "artifacts. Without this flag the script is read-only."
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Allow replacement of previously generated post-hoc "
            "artifacts. Only meaningful with --write."
        ),
    )

    args = parser.parse_args()

    all_records = []
    per_run_records = {}

    for variant in VARIANTS:
        for repetition in REPETITIONS:
            run_dir, records = validate_run(
                variant,
                repetition,
            )

            all_records.extend(records)
            per_run_records[run_dir] = records

    if len(all_records) != 120:
        raise RuntimeError(
            "Expected 120 cycle records from 20 runs, found {}".format(
                len(all_records)
            )
        )

    print_summary(all_records)

    if not args.write:
        print()
        print("DRY RUN ONLY: no post-hoc result files were written.")
        return

    output_paths = [
        CAMPAIGN_CSV,
        CAMPAIGN_JSON,
    ]

    for run_dir in per_run_records:
        output_paths.append(
            run_dir / PER_RUN_OUTPUT
        )

    if not args.overwrite:
        existing = [
            path
            for path in output_paths
            if path.exists()
        ]

        if existing:
            raise RuntimeError(
                "Refusing to overwrite existing post-hoc artifacts:\n"
                + "\n".join(
                    str(path)
                    for path in existing
                )
            )

    for run_dir, records in per_run_records.items():
        write_jsonl(
            run_dir / PER_RUN_OUTPUT,
            records,
        )

    write_campaign_csv(
        CAMPAIGN_CSV,
        all_records,
    )

    with CAMPAIGN_JSON.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            all_records,
            f,
            indent=2,
            sort_keys=True,
        )
        f.write("\n")

    print()
    print("POST-HOC ARTIFACTS WRITTEN.")
    print("Campaign CSV:", CAMPAIGN_CSV)
    print("Campaign JSON:", CAMPAIGN_JSON)
    print(
        "Per-run file:",
        PER_RUN_OUTPUT,
        "inside each of the 20 valid run directories.",
    )


if __name__ == "__main__":
    main()
