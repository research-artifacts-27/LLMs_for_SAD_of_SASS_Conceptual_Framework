#!/usr/bin/env python3
"""E8 live comparative-evaluation harness.

Dry-run is the default. A live SWIM run occurs only when --live is supplied.

One invocation runs one variant (B0/B1/B2/B3) for one paired repetition
(0..4). The harness keeps the validated E7 controllers unchanged.
"""

import argparse
import csv
import hashlib
import json
import os
import statistics
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path


THIS_FILE = Path(__file__).resolve()
E8_DIR = THIS_FILE.parent
PROJECT_ROOT = E8_DIR.parent.parent
E7_DIR = PROJECT_ROOT / "evaluation" / "e7"

LOCAL_E8_CONFIG = E8_DIR / "config" / "e8_swim.ini"
DOCKER_CONTAINER = "swim"
CONTAINER_SWIM_DIR = "/headless/seams-swim/swim/simulations/swim"
CONTAINER_E8_CONFIG = CONTAINER_SWIM_DIR + "/e8_swim.ini"
CONTAINER_TRACE = CONTAINER_SWIM_DIR + "/traces/wc_day53-highload-long.delta"

FROZEN_E8_CONFIG_SHA256 = (
    "107613df113772f24653bed5bf587bb1c0f488b6c7d557e9063cf5226adb30d3"
)

SUPPORTED_VARIANTS = ("B0", "B1", "B2", "B3")
SUPPORTED_REPETITIONS = tuple(range(5))

EVALUATION_WINDOW_SECONDS = 420.0
SWIM_SIM_LIMIT_SECONDS = 480.0
SAMPLE_INTERVAL_SECONDS = 2.0
CONTROL_TIMES_SECONDS = (60.0, 120.0, 180.0, 240.0, 300.0, 360.0)
RESPONSE_TIME_TARGET = 0.75
EXPECTED_INITIAL_SERVERS = 1
EXPECTED_MAX_SERVERS = 6
EXPECTED_INITIAL_DIMMER = 0.90

RESULTS_ROOT = E8_DIR / "results"

TIMESERIES_FIELDS = [
    "timestamp",
    "elapsed_s",
    "response_time",
    "response_time_target",
    "qos_satisfied",
    "arrival_rate",
    "servers",
    "active_servers",
    "max_servers",
    "server_booting",
    "utilization",
    "total_utilization",
    "dimmer",
    "basic_response_time",
    "optional_response_time",
    "basic_throughput",
    "optional_throughput",
]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def local_now():
    return datetime.now().astimezone().isoformat()


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def shell_quote(value):
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def run_command(args, cwd=None, check=True):
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd is not None else None,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def docker_exec_readonly(command):
    return run_command(
        ["docker", "exec", DOCKER_CONTAINER, "sh", "-lc", command]
    ).stdout


def container_sha256(path):
    out = docker_exec_readonly("sha256sum " + shell_quote(path)).strip()
    if not out:
        raise RuntimeError("Could not read container SHA256 for " + path)
    return out.split()[0]


def json_dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def jsonl_append(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def add_project_paths():
    for p in (PROJECT_ROOT, E7_DIR):
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)


def verify_required_files():
    required = [
        LOCAL_E8_CONFIG,
        E7_DIR / "b0_controller.py",
        E7_DIR / "b1_controller.py",
        E7_DIR / "b2_controller.py",
        E7_DIR / "b3_isolated_runner.py",
        E7_DIR / "e7_runtime_memory.py",
        E7_DIR / "e7_metric_extractor.py",
        PROJECT_ROOT / "agent_controller.py",
        PROJECT_ROOT / "trusted_policies.json",
        PROJECT_ROOT / "experiment_logger.py",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required files:\n- " + "\n- ".join(missing))


def verify_frozen_config():
    host_hash = sha256_file(LOCAL_E8_CONFIG)
    container_hash = container_sha256(CONTAINER_E8_CONFIG)
    if host_hash != FROZEN_E8_CONFIG_SHA256:
        raise RuntimeError(
            "Local e8_swim.ini differs from frozen protocol.\n"
            "Expected: {}\nObserved: {}".format(
                FROZEN_E8_CONFIG_SHA256, host_hash
            )
        )
    if container_hash != FROZEN_E8_CONFIG_SHA256:
        raise RuntimeError(
            "Container e8_swim.ini differs from frozen protocol.\n"
            "Expected: {}\nObserved: {}".format(
                FROZEN_E8_CONFIG_SHA256, container_hash
            )
        )
    return {
        "host_e8_config_sha256": host_hash,
        "container_e8_config_sha256": container_hash,
    }


def collect_code_hashes():
    files = {
        "e8_live_harness.py": THIS_FILE,
        "b0_controller.py": E7_DIR / "b0_controller.py",
        "b1_controller.py": E7_DIR / "b1_controller.py",
        "b2_controller.py": E7_DIR / "b2_controller.py",
        "b3_isolated_runner.py": E7_DIR / "b3_isolated_runner.py",
        "e7_runtime_memory.py": E7_DIR / "e7_runtime_memory.py",
        "e7_metric_extractor.py": E7_DIR / "e7_metric_extractor.py",
        "agent_controller.py": PROJECT_ROOT / "agent_controller.py",
        "trusted_policies.json": PROJECT_ROOT / "trusted_policies.json",
    }
    return {name: sha256_file(path) for name, path in files.items()}


def verify_no_swim_process():
    out = docker_exec_readonly(
        "ps aux | grep -E '[o]pp_run|[o]pp_runall|[/]src/swim|[s]wim -u' || true"
    ).strip()
    if out:
        raise RuntimeError(
            "A SWIM/OMNeT++ process appears to be running. "
            "Refusing to start a second one.\n\n" + out
        )


def canonical_run_id(variant, repetition):
    return "E8_{}_rep{:02d}".format(variant.upper(), int(repetition))


def result_dir_for(variant, repetition):
    return RESULTS_ROOT / variant.upper() / "rep{:02d}".format(int(repetition))


def require_fresh_result_dir(path):
    if path.exists():
        raise FileExistsError(
            "Result directory already exists; refusing to overwrite it:\n" + str(path)
        )
    path.mkdir(parents=True, exist_ok=False)


class RuntimeSampler:
    def __init__(self, output_csv, t0):
        self.output_csv = Path(output_csv)
        self.t0 = float(t0)
        self.stop_event = threading.Event()
        self.thread = None
        self.sample_count = 0
        self.errors = []

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=10)

    def _run(self):
        add_project_paths()
        from experiment_logger import get_runtime_state

        self.output_csv.parent.mkdir(parents=True, exist_ok=True)
        next_sample = self.t0

        with self.output_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=TIMESERIES_FIELDS)
            writer.writeheader()
            f.flush()

            while not self.stop_event.is_set():
                now = time.monotonic()
                if now < next_sample:
                    self.stop_event.wait(min(next_sample - now, 0.25))
                    continue

                try:
                    state = get_runtime_state()
                    elapsed = time.monotonic() - self.t0
                    rt = state.get("response_time")
                    qos = "" if rt is None else float(rt) <= RESPONSE_TIME_TARGET
                    row = {
                        "timestamp": local_now(),
                        "elapsed_s": round(elapsed, 3),
                        "response_time": rt,
                        "response_time_target": RESPONSE_TIME_TARGET,
                        "qos_satisfied": qos,
                        "arrival_rate": state.get("arrival_rate"),
                        "servers": state.get("servers"),
                        "active_servers": state.get("active_servers"),
                        "max_servers": state.get("max_servers"),
                        "server_booting": state.get("server_booting"),
                        "utilization": state.get("utilization"),
                        "total_utilization": state.get("total_utilization"),
                        "dimmer": state.get("dimmer"),
                        "basic_response_time": state.get("basic_response_time"),
                        "optional_response_time": state.get("optional_response_time"),
                        "basic_throughput": state.get("basic_throughput"),
                        "optional_throughput": state.get("optional_throughput"),
                    }
                    writer.writerow(row)
                    f.flush()
                    self.sample_count += 1
                except Exception as exc:
                    self.errors.append("{} | {!r}".format(local_now(), exc))

                next_sample += SAMPLE_INTERVAL_SECONDS
                now = time.monotonic()
                if next_sample < now - SAMPLE_INTERVAL_SECONDS:
                    missed = int((now - next_sample) // SAMPLE_INTERVAL_SECONDS) + 1
                    next_sample += missed * SAMPLE_INTERVAL_SECONDS


def start_swim(repetition, log_path):
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("w", encoding="utf-8")
    command = [
        "docker",
        "exec",
        DOCKER_CONTAINER,
        "sh",
        "-lc",
        "cd {} && ./run.sh e8 {} e8_swim.ini".format(
            shell_quote(CONTAINER_SWIM_DIR), int(repetition)
        ),
    ]
    proc = subprocess.Popen(
        command,
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc, handle, command


def wait_for_initial_state(timeout_seconds):
    add_project_paths()
    from experiment_logger import get_runtime_state

    deadline = time.monotonic() + float(timeout_seconds)
    last_state = None
    last_error = None

    while time.monotonic() < deadline:
        try:
            state = get_runtime_state()
            last_state = state
            active = state.get("active_servers")
            if active is None:
                active = state.get("servers")
            maximum = state.get("max_servers")
            dimmer = state.get("dimmer")

            servers_ok = active is not None and int(active) == EXPECTED_INITIAL_SERVERS
            max_ok = maximum is None or int(maximum) == EXPECTED_MAX_SERVERS
            dimmer_ok = dimmer is not None and abs(float(dimmer) - EXPECTED_INITIAL_DIMMER) <= 0.02

            if servers_ok and max_ok and dimmer_ok:
                return state
        except Exception as exc:
            last_error = exc
        time.sleep(0.5)

    raise RuntimeError(
        "Canonical E8 initial state was not observed within {:.1f}s.\n"
        "Expected active_servers={}, max_servers={}, dimmer≈{}.\n"
        "Last state: {}\nLast error: {!r}".format(
            timeout_seconds,
            EXPECTED_INITIAL_SERVERS,
            EXPECTED_MAX_SERVERS,
            EXPECTED_INITIAL_DIMMER,
            last_state,
            last_error,
        )
    )


class VariantAdapter:
    def __init__(self, variant, run_id):
        add_project_paths()
        self.variant = variant.upper()
        self.run_id = run_id

        from e7_metric_extractor import extract_episode_metrics
        self.extract_episode_metrics = extract_episode_metrics

        self.initialize_run_kb = None
        self.load_run_episodes = None

        if self.variant == "B0":
            from b0_controller import run_b0_cycle
            self.controller = run_b0_cycle
        elif self.variant == "B1":
            from b1_controller import run_b1_cycle
            self.controller = run_b1_cycle
        elif self.variant == "B2":
            from b2_controller import run_b2_cycle
            from e7_runtime_memory import initialize_run_kb, load_run_episodes
            self.controller = run_b2_cycle
            self.initialize_run_kb = initialize_run_kb
            self.load_run_episodes = load_run_episodes
        elif self.variant == "B3":
            from b3_isolated_runner import run_b3_controller
            from e7_runtime_memory import initialize_run_kb, load_run_episodes
            self.controller = run_b3_controller
            self.initialize_run_kb = initialize_run_kb
            self.load_run_episodes = load_run_episodes
        else:
            raise ValueError("Unsupported variant: " + self.variant)

    def initialize_memory(self):
        if self.variant in ("B2", "B3"):
            return self.initialize_run_kb(self.variant, self.run_id, overwrite=False)
        return None

    def run_cycle(self, cycle_index):
        before = None
        if self.variant in ("B2", "B3"):
            before = len(self.load_run_episodes(self.variant, self.run_id))

        if self.variant == "B0":
            episode = self.controller()
        elif self.variant == "B1":
            episode = self.controller()
        elif self.variant == "B2":
            episode = self.controller(self.run_id)
        else:
            self.controller(self.run_id)
            episodes = self.load_run_episodes("B3", self.run_id)
            if len(episodes) != before + 1:
                raise RuntimeError(
                    "B3 did not append exactly one normalized isolated-memory episode. "
                    "Before={}, after={}".format(before, len(episodes))
                )
            episode = episodes[-1]

        if not isinstance(episode, dict):
            raise TypeError("Controller episode is not a dict: " + type(episode).__name__)

        metrics = self.extract_episode_metrics(
            episode,
            run_id_override=self.run_id,
            cycle_index=cycle_index,
            response_time_target=RESPONSE_TIME_TARGET,
        )
        return episode, metrics


def numeric(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def summarize_timeseries(path):
    response_times = []
    violations = 0
    servers = []
    dimmers = []

    with Path(path).open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rt = numeric(row.get("response_time"))
            if rt is not None:
                response_times.append(rt)
                if rt > RESPONSE_TIME_TARGET:
                    violations += 1
            s = numeric(row.get("active_servers"))
            if s is not None:
                servers.append(s)
            d = numeric(row.get("dimmer"))
            if d is not None:
                dimmers.append(d)

    summary = {
        "response_time_target": RESPONSE_TIME_TARGET,
        "valid_response_time_samples": len(response_times),
        "qos_violation_samples": violations,
        "qos_violation_rate_percent": (
            100.0 * violations / len(response_times) if response_times else None
        ),
        "mean_response_time": statistics.mean(response_times) if response_times else None,
        "max_response_time": max(response_times) if response_times else None,
        "active_servers_start": servers[0] if servers else None,
        "active_servers_end": servers[-1] if servers else None,
        "dimmer_start": dimmers[0] if dimmers else None,
        "dimmer_end": dimmers[-1] if dimmers else None,
    }

    if response_times:
        ordered = sorted(response_times)
        idx = int(round(0.95 * (len(ordered) - 1)))
        summary["p95_response_time"] = ordered[idx]
    else:
        summary["p95_response_time"] = None

    return summary


def dry_run(args):
    verify_required_files()
    config_hashes = verify_frozen_config()
    code_hashes = collect_code_hashes()
    trace_hash = container_sha256(CONTAINER_TRACE)

    run_id = canonical_run_id(args.variant, args.repetition)
    result_dir = result_dir_for(args.variant, args.repetition)

    print("=" * 68)
    print("E8 DRY RUN — NO LIVE EXPERIMENT WILL BE STARTED")
    print("=" * 68)
    print("Variant:", args.variant)
    print("Repetition:", args.repetition)
    print("Run ID:", run_id)
    print("Result directory:", result_dir)
    print("Controller schedule (s):", CONTROL_TIMES_SECONDS)
    print("Observation window (s):", EVALUATION_WINDOW_SECONDS)
    print("Sampling interval (s):", SAMPLE_INTERVAL_SECONDS)
    print("SWIM sim-time limit (s):", SWIM_SIM_LIMIT_SECONDS)
    print("Frozen config SHA256:", config_hashes["host_e8_config_sha256"])
    print("High-load trace SHA256:", trace_hash)
    print("Controller/code hashes:")
    for name in sorted(code_hashes):
        print("  {}  {}".format(code_hashes[name], name))
    print()
    print("No SWIM process was started.")
    print("No controller was executed.")
    print("No LLM was called.")
    print("No runtime memory was created.")
    print("=" * 68)


def live_run(args):
    verify_required_files()
    verify_no_swim_process()
    config_hashes = verify_frozen_config()
    code_hashes = collect_code_hashes()
    trace_hash = container_sha256(CONTAINER_TRACE)

    variant = args.variant.upper()
    repetition = int(args.repetition)
    run_id = canonical_run_id(variant, repetition)
    result_dir = result_dir_for(variant, repetition)
    require_fresh_result_dir(result_dir)

    manifest_path = result_dir / "manifest.json"
    timeseries_path = result_dir / "runtime_timeseries.csv"
    episodes_path = result_dir / "episodes.jsonl"
    metrics_path = result_dir / "cycle_metrics.jsonl"
    summary_path = result_dir / "summary.json"
    simulator_log_path = result_dir / "swim_simulator.log"
    failure_path = result_dir / "failure.json"

    manifest = {
        "schema_version": "E8-RUN-1",
        "created_utc": utc_now(),
        "variant": variant,
        "repetition": repetition,
        "run_id": run_id,
        "protocol": {
            "evaluation_window_seconds": EVALUATION_WINDOW_SECONDS,
            "swim_sim_time_limit_seconds": SWIM_SIM_LIMIT_SECONDS,
            "sample_interval_seconds": SAMPLE_INTERVAL_SECONDS,
            "control_times_seconds": list(CONTROL_TIMES_SECONDS),
            "response_time_target": RESPONSE_TIME_TARGET,
            "expected_initial_servers": EXPECTED_INITIAL_SERVERS,
            "expected_max_servers": EXPECTED_MAX_SERVERS,
            "expected_initial_dimmer": EXPECTED_INITIAL_DIMMER,
            "runtime_memory_policy": (
                "fresh isolated per run" if variant in ("B2", "B3") else "not used"
            ),
        },
        "hashes": {
            **config_hashes,
            "container_trace_sha256": trace_hash,
            "code": code_hashes,
        },
        "status": "INITIALIZED",
    }
    json_dump(manifest_path, manifest)

    adapter = VariantAdapter(variant, run_id)
    memory_path = adapter.initialize_memory()
    if memory_path is not None:
        manifest["isolated_runtime_memory"] = str(memory_path)
        json_dump(manifest_path, manifest)

    sim_proc = None
    sim_log_handle = None
    sampler = None

    try:
        print("=" * 68)
        print("E8 LIVE RUN")
        print("=" * 68)
        print("Variant:", variant)
        print("Repetition:", repetition)
        print("Run ID:", run_id)
        print("Results:", result_dir)
        print("SWIM-AFFECTING EXECUTION IS ENABLED (--live).")
        print("=" * 68)

        sim_proc, sim_log_handle, launch_command = start_swim(
            repetition, simulator_log_path
        )
        manifest["swim_launch_command"] = launch_command
        manifest["status"] = "SWIM_STARTING"
        json_dump(manifest_path, manifest)

        initial_state = wait_for_initial_state(args.startup_timeout)
        t0 = time.monotonic()
        manifest["experiment_t0_local"] = local_now()
        manifest["initial_state"] = initial_state
        manifest["status"] = "RUNNING"
        json_dump(manifest_path, manifest)

        sampler = RuntimeSampler(timeseries_path, t0)
        sampler.start()

        for cycle_index, scheduled_time in enumerate(CONTROL_TIMES_SECONDS, start=1):
            while True:
                elapsed = time.monotonic() - t0
                remaining = scheduled_time - elapsed
                if remaining <= 0:
                    break
                time.sleep(min(remaining, 0.25))

            actual_start = time.monotonic() - t0
            print(
                "\n===== E8 {} CYCLE {} =====\nScheduled t={:.1f}s | actual t={:.3f}s".format(
                    variant, cycle_index, scheduled_time, actual_start
                )
            )

            cycle_start = time.monotonic()
            episode, metrics = adapter.run_cycle(cycle_index)
            cycle_end = time.monotonic()
            actual_end = cycle_end - t0

            jsonl_append(
                episodes_path,
                {
                    "variant": variant,
                    "repetition": repetition,
                    "run_id": run_id,
                    "cycle_index": cycle_index,
                    "scheduled_time_seconds": scheduled_time,
                    "actual_start_elapsed_seconds": actual_start,
                    "actual_end_elapsed_seconds": actual_end,
                    "harness_observed_cycle_duration_seconds": cycle_end - cycle_start,
                    "episode": episode,
                },
            )

            metrics = dict(metrics)
            metrics["scheduled_time_seconds"] = scheduled_time
            metrics["actual_start_elapsed_seconds"] = actual_start
            metrics["actual_end_elapsed_seconds"] = actual_end
            metrics["harness_observed_cycle_duration_seconds"] = cycle_end - cycle_start
            jsonl_append(metrics_path, metrics)

        while True:
            elapsed = time.monotonic() - t0
            if elapsed >= EVALUATION_WINDOW_SECONDS:
                break
            time.sleep(min(EVALUATION_WINDOW_SECONDS - elapsed, 0.25))

        sampler.stop()
        manifest["observation_end_local"] = local_now()
        manifest["sampler_sample_count"] = sampler.sample_count
        manifest["sampler_error_count"] = len(sampler.errors)
        manifest["sampler_errors"] = sampler.errors
        manifest["status"] = "OBSERVATION_COMPLETE"
        json_dump(manifest_path, manifest)

        print(
            "\n420 s observation complete; waiting for the configured "
            "480 s SWIM run to terminate naturally..."
        )
        try:
            exit_code = sim_proc.wait(timeout=args.simulator_exit_timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "SWIM did not exit within the post-observation timeout. "
                "The harness intentionally did not issue a broad kill command. "
                "Inspect the container before another run."
            )

        manifest["swim_exit_code"] = exit_code
        if exit_code != 0:
            raise RuntimeError("SWIM launcher exit code was {}".format(exit_code))

        summary = summarize_timeseries(timeseries_path)
        summary.update(
            {
                "variant": variant,
                "repetition": repetition,
                "run_id": run_id,
                "controller_cycles_expected": len(CONTROL_TIMES_SECONDS),
                "evaluation_window_seconds": EVALUATION_WINDOW_SECONDS,
                "sampling_interval_seconds": SAMPLE_INTERVAL_SECONDS,
                "sampler_sample_count": sampler.sample_count,
                "sampler_error_count": len(sampler.errors),
            }
        )
        json_dump(summary_path, summary)

        manifest["status"] = "COMPLETE"
        manifest["completed_utc"] = utc_now()
        manifest["summary_file"] = str(summary_path)
        json_dump(manifest_path, manifest)

        print("\n" + "=" * 68)
        print("E8 RUN COMPLETE")
        print("=" * 68)
        print("Variant:", variant)
        print("Repetition:", repetition)
        print("Results:", result_dir)
        print("Samples:", sampler.sample_count)
        print("QoS violation rate (%):", summary.get("qos_violation_rate_percent"))
        print("=" * 68)

    except Exception as exc:
        if sampler is not None:
            try:
                sampler.stop()
            except Exception:
                pass

        failure = {
            "timestamp_utc": utc_now(),
            "variant": variant,
            "repetition": repetition,
            "run_id": run_id,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        json_dump(failure_path, failure)
        manifest["status"] = "FAILED"
        manifest["failed_utc"] = utc_now()
        manifest["failure_file"] = str(failure_path)
        json_dump(manifest_path, manifest)
        raise

    finally:
        if sim_log_handle is not None:
            try:
                sim_log_handle.flush()
                sim_log_handle.close()
            except Exception:
                pass


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "E8 repeated-run harness for B0/B1/B2/B3. "
            "Dry-run by default."
        )
    )
    parser.add_argument("variant", choices=SUPPORTED_VARIANTS)
    parser.add_argument("repetition", type=int, choices=SUPPORTED_REPETITIONS)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually start SWIM and execute the selected controller.",
    )
    parser.add_argument("--startup-timeout", type=float, default=30.0)
    parser.add_argument("--simulator-exit-timeout", type=float, default=100.0)
    return parser.parse_args()


def main():
    args = parse_args()
    os.chdir(PROJECT_ROOT)
    if args.live:
        live_run(args)
    else:
        dry_run(args)


if __name__ == "__main__":
    main()
