#!/usr/bin/env python3

import json
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve()
    .parents[2]
)

POLICY_FILE = (
    PROJECT_ROOT
    / "trusted_policies.json"
)


# ============================================================
# LOAD TRUSTED POLICIES
# ============================================================

def load_policies():

    with POLICY_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# B0 — DETERMINISTIC RULE-BASED PLANNER
# ============================================================

def plan_b0(state):

    """
    Deterministic B0 baseline.

    No LLM.
    No RAG.
    No runtime memory.
    No agentic failure routing.
    No bounded replanning.
    No E6 fallback.

    The returned candidate must still pass the common
    deterministic safety checker before execution.
    """

    policies = load_policies()

    target = float(
        policies[
            "response_time_target"
        ]
    )

    max_servers = int(
        policies[
            "max_servers"
        ]
    )

    min_servers = int(
        policies[
            "min_servers"
        ]
    )

    dimmer_min = float(
        policies[
            "dimmer_min"
        ]
    )

    dimmer_max = float(
        policies[
            "dimmer_max"
        ]
    )

    dimmer_step = float(
        policies[
            "dimmer_step"
        ]
    )


    response_time = float(
        state["response_time"]
    )

    total_servers = int(
        state["servers"]
    )

    active_servers = int(
        state["active_servers"]
    )

    utilization = float(
        state["utilization"]
    )

    current_dimmer = float(
        state["dimmer"]
    )

    server_booting = bool(
        state["server_booting"]
    )


    total_utilization = state.get(
        "total_utilization",
        utilization
        * active_servers
    )

    spare_capacity = (
        active_servers
        - total_utilization
    )


    # ========================================================
    # CASE 1 — RESPONSE TIME ABOVE TARGET
    # ========================================================

    if response_time > target:

        if (
            not server_booting
            and total_servers < max_servers
            and total_servers < state["max_servers"]
        ):

            return {
                "action":
                    "add_server",

                "decision_source":
                    "B0_rule_based",

                "decision_reason":
                    (
                        "Response time exceeds the target "
                        "and additional server capacity "
                        "is available."
                    )
            }


        if current_dimmer > dimmer_min:

            new_dimmer = max(
                dimmer_min,
                current_dimmer
                - dimmer_step
            )

            new_dimmer = round(
                new_dimmer,
                10
            )

            return {
                "action":
                    "set_dimmer",

                "value":
                    new_dimmer,

                "decision_source":
                    "B0_rule_based",

                "decision_reason":
                    (
                        "Response time exceeds the target "
                        "and additional server capacity "
                        "is unavailable, so optional "
                        "workload is reduced."
                    )
            }


        return {
            "action":
                "none",

            "decision_source":
                "B0_rule_based",

            "decision_reason":
                (
                    "Response time exceeds the target, "
                    "but no rule-based adaptation "
                    "candidate is available."
                )
        }


    # ========================================================
    # CASE 2 — RESPONSE TIME WITHIN TARGET
    # ========================================================

    if (
        spare_capacity > 1.0
        and current_dimmer < dimmer_max
    ):

        new_dimmer = min(
            dimmer_max,
            current_dimmer
            + dimmer_step
        )

        new_dimmer = round(
            new_dimmer,
            10
        )

        return {
            "action":
                "set_dimmer",

            "value":
                new_dimmer,

            "decision_source":
                "B0_rule_based",

            "decision_reason":
                (
                    "The system is within the response-time "
                    "target with spare capacity, so optional "
                    "functionality is restored first."
                )
        }


    if (
        spare_capacity > 1.0
        and current_dimmer >= dimmer_max
        and active_servers > min_servers
        and not server_booting
    ):

        return {
            "action":
                "remove_server",

            "decision_source":
                "B0_rule_based",

            "decision_reason":
                (
                    "The system is within the response-time "
                    "target, optional functionality is fully "
                    "restored, and spare capacity permits "
                    "scale-in."
                )
        }


    return {
        "action":
            "none",

        "decision_source":
            "B0_rule_based",

        "decision_reason":
            (
                "No rule-based adaptation is required "
                "under the current conditions."
            )
    }


# ============================================================
# INFORMATIONAL MODE
# ============================================================

if __name__ == "__main__":

    print(
        "B0 deterministic rule-based planner loaded."
    )

    print(
        "No SWIM interaction occurs in this module."
    )
