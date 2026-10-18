#!/usr/bin/env python3

import csv
import json
import os
import time
import urllib.request
from datetime import datetime

API_URL = "http://127.0.0.1:8081/api/state"
SAMPLE_INTERVAL_SECONDS = 2
RESPONSE_TIME_TARGET = 0.75

OUTPUT_FILE = "experiments/results/runtime_timeseries.csv"

FIELDS = [
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
    "optional_throughput"
]


def get_runtime_state():
    with urllib.request.urlopen(API_URL, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    file_exists = os.path.exists(OUTPUT_FILE)
    file_empty = (not file_exists) or os.path.getsize(OUTPUT_FILE) == 0

    start_time = time.time()

    print("=" * 50)
    print("SWIM EXPERIMENT LOGGER")
    print("=" * 50)
    print(f"Source: {API_URL}")
    print(f"Sampling interval: {SAMPLE_INTERVAL_SECONDS} seconds")
    print(f"Output: {OUTPUT_FILE}")
    print()
    print("READ-ONLY LOGGER")
    print("This program does NOT execute adaptation actions.")
    print()
    print("Press Control+C to stop recording.")
    print("=" * 50)

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as csvfile:

        writer = csv.DictWriter(csvfile, fieldnames=FIELDS)

        if file_empty:
            writer.writeheader()
            csvfile.flush()

        try:
            while True:
                cycle_start = time.time()

                try:
                    state = get_runtime_state()

                    elapsed = round(time.time() - start_time, 2)

                    response_time = state.get("response_time")

                    if response_time is not None:
                        qos_satisfied = response_time <= RESPONSE_TIME_TARGET
                    else:
                        qos_satisfied = ""

                    row = {
                        "timestamp": datetime.now().astimezone().isoformat(),
                        "elapsed_s": elapsed,
                        "response_time": response_time,
                        "response_time_target": RESPONSE_TIME_TARGET,
                        "qos_satisfied": qos_satisfied,
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
                        "optional_throughput": state.get("optional_throughput")
                    }

                    writer.writerow(row)
                    csvfile.flush()

                    print(
                        f"{elapsed:7.1f}s | "
                        f"RT={response_time:.4f}s | "
                        f"Arrival={state.get('arrival_rate')} | "
                        f"Servers={state.get('active_servers')} | "
                        f"Util={state.get('utilization', 0) * 100:.1f}% | "
                        f"Dimmer={state.get('dimmer')}"
                    )

                except Exception as exc:
                    print(f"LOGGER WARNING: {exc}")

                elapsed_cycle = time.time() - cycle_start
                sleep_time = max(0, SAMPLE_INTERVAL_SECONDS - elapsed_cycle)
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            print()
            print("=" * 50)
            print("Recording stopped.")
            print(f"Data saved to: {OUTPUT_FILE}")
            print("=" * 50)


if __name__ == "__main__":
    main()
