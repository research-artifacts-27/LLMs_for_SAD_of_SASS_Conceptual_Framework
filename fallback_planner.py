#!/usr/bin/env python3

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

TRUSTED_POLICY_FILE = (
    PROJECT_ROOT
    / "trusted_policies.json"
)

FALLBACK_POLICY_FILE = (
    PROJECT_ROOT
    / "trusted_fallback_policy.json"
)


# ============================================================
# LOAD POLICIES
# ============================================================

def load_json(path):

    with path.open(
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# DETERMINISTIC FALLBACK CANDIDATE GENERATION
# ============================================================

def generate_fallback_candidates(
    state
):

    """
    Generate deterministic fallback candidates.

    IMPORTANT:
    - No LLM is used.
    - No SWIM command is executed.
    - Candidates still require the existing
      deterministic safety checker.
    """

    trusted = load_json(
        TRUSTED_POLICY_FILE
    )

    fallback = load_json(
        FALLBACK_POLICY_FILE
    )


    if not fallback.get(
        "enabled",
        False
    ):

        return []


    response_time = float(
        state["response_time"]
    )

    current_dimmer = float(
        state["dimmer"]
    )

    response_time_target = float(
        trusted[
            "response_time_target"
        ]
    )

    dimmer_min = float(
        trusted[
            "dimmer_min"
        ]
    )

    dimmer_step = float(
        trusted[
            "dimmer_step"
        ]
    )


    candidates = []


    # ========================================================
    # HEALTHY STATE
    # ========================================================

    if (
        response_time
        <= response_time_target
    ):

        healthy_candidate = fallback.get(
            "healthy_candidate",
            "none"
        )

        if healthy_candidate == "none":

            candidates.append(
                {
                    "action": "none",
                    "fallback_reason":
                        (
                            "Response time is already "
                            "within the trusted target."
                        ),
                    "fallback_source":
                        "deterministic_policy"
                }
            )

        return candidates


    # ========================================================
    # OVERLOAD STATE
    # ========================================================

    candidate_order = fallback.get(
        "overload_candidate_order",
        []
    )


    for candidate_type in candidate_order:

        # ----------------------------------------------------
        # CANDIDATE 1 — ADD SERVER
        # ----------------------------------------------------

        if candidate_type == "add_server":

            candidates.append(
                {
                    "action":
                        "add_server",

                    "fallback_reason":
                        (
                            "Response time exceeds the "
                            "trusted target; increasing "
                            "capacity is the first "
                            "deterministic fallback "
                            "candidate."
                        ),

                    "fallback_source":
                        "deterministic_policy"
                }
            )


        # ----------------------------------------------------
        # CANDIDATE 2 — REDUCE DIMMER
        # ----------------------------------------------------

        elif candidate_type == "reduce_dimmer":

            if (
                current_dimmer
                > dimmer_min
            ):

                new_dimmer = max(
                    dimmer_min,
                    current_dimmer
                    - dimmer_step
                )

                new_dimmer = round(
                    new_dimmer,
                    10
                )

                if (
                    new_dimmer
                    < current_dimmer
                ):

                    candidates.append(
                        {
                            "action":
                                "set_dimmer",

                            "value":
                                new_dimmer,

                            "fallback_reason":
                                (
                                    "Response time exceeds "
                                    "the trusted target; "
                                    "optional workload is "
                                    "reduced by one trusted "
                                    "dimmer step."
                                ),

                            "fallback_source":
                                "deterministic_policy"
                        }
                    )


    return candidates


# ============================================================
# STANDALONE INFORMATIONAL MODE
# ============================================================

if __name__ == "__main__":

    print(
        "Deterministic fallback planner loaded."
    )

    print(
        "No SWIM interaction occurs in this module."
    )

    print(
        "Use generate_fallback_candidates(state) "
        "to generate candidates."
    )
