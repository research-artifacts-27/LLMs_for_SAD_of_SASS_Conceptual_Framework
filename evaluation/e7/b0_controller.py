#!/usr/bin/env python3

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# PROJECT IMPORTS
# ============================================================

PROJECT_ROOT = (
    Path(__file__).resolve()
    .parents[2]
)

E7_DIR = (
    PROJECT_ROOT
    / "evaluation"
    / "e7"
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )

if str(E7_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(E7_DIR)
    )


from monitor import monitor
from safety_checker import safety_check
from executor import execute
from outcome_evaluator import evaluate_outcome
from b0_rule_planner import plan_b0


POLICY_FILE = (
    PROJECT_ROOT
    / "trusted_policies.json"
)


# ============================================================
# HELPERS
# ============================================================

def utc_now():

    return datetime.now(
        timezone.utc
    ).isoformat()


def load_policies():

    with POLICY_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# B0 — ONE CONTROL CYCLE
# ============================================================

def run_b0_cycle():

    print()
    print(
        "======================================"
    )
    print(
        " E7 B0 — RULE-BASED BASELINE"
    )
    print(
        "======================================"
    )


    cycle_started = (
        time.perf_counter()
    )


    # ========================================================
    # STEP 1 — MONITOR
    # ========================================================

    initial_state = monitor()

    current_state = (
        initial_state.copy()
    )


    # ========================================================
    # STEP 2 — DETERMINISTIC B0 PLANNING
    # ========================================================

    decision_started = (
        time.perf_counter()
    )

    candidate_plan = plan_b0(
        current_state
    )


    print()
    print(
        "=== B0 RULE-BASED PLAN ==="
    )

    print(
        "Candidate:",
        candidate_plan
    )


    # ========================================================
    # STEP 3 — COMMON DETERMINISTIC SAFETY CHECK
    # ========================================================

    verdict = safety_check(
        candidate_plan,
        current_state
    )


    decision_finished = (
        time.perf_counter()
    )

    decision_latency_seconds = (
        decision_finished
        - decision_started
    )


    executed_plan = None

    execution_performed = False

    execution_latency_seconds = 0.0


    # ========================================================
    # STEP 4A — SAFETY PASS
    # ========================================================

    if verdict["status"] == "PASS":

        action = candidate_plan.get(
            "action"
        )


        if action != "none":

            execution_started = (
                time.perf_counter()
            )

            execute(
                candidate_plan
            )

            execution_finished = (
                time.perf_counter()
            )

            execution_latency_seconds = (
                execution_finished
                - execution_started
            )

            execution_performed = True


        else:

            print()
            print(
                "B0 selected validated no-action."
            )

            print(
                "No SWIM effector command is sent."
            )


        executed_plan = (
            candidate_plan.copy()
        )


        print()
        print(
            "=== MONITOR AFTER B0 DECISION ==="
        )

        final_state = monitor()


        actual_outcome = evaluate_outcome(
            current_state,
            final_state,
            candidate_plan
        )


    # ========================================================
    # STEP 4B — SAFETY FAIL
    #
    # B0 has:
    # - no LLM recovery
    # - no RAG recovery
    # - no agentic replanning
    # - no E6 deterministic fallback
    #
    # Therefore nothing is executed.
    # ========================================================

    else:

        print()
        print(
            "=== B0 SAFETY REJECTION ==="
        )

        print(
            "Candidate was rejected."
        )

        print(
            "B0 performs no recovery "
            "within this control cycle."
        )

        print(
            "No SWIM effector command is sent."
        )


        final_state = monitor()

        policies = load_policies()

        goal_satisfied = (
            final_state[
                "response_time"
            ]
            <= policies[
                "response_time_target"
            ]
        )


        actual_outcome = {
            "status":
                "FAIL",

            "action_effect_observed":
                False,

            "goal_satisfied":
                goal_satisfied,

            "reason":
                (
                    "The B0 rule-based candidate was "
                    "rejected by the common deterministic "
                    "safety checker. B0 has no within-cycle "
                    "replanning or fallback mechanism, so "
                    "no adaptation was executed."
                )
        }


    # ========================================================
    # STEP 5 — COMPLETE EXPERIMENT RECORD
    # ========================================================

    cycle_finished = (
        time.perf_counter()
    )


    episode = {
        "variant":
            "B0",

        "variant_name":
            "Rule-based baseline",

        "timestamp_utc":
            utc_now(),

        "initial_state":
            initial_state,

        "candidate_plan":
            candidate_plan,

        "safety_verdict":
            verdict,

        "executed_plan":
            executed_plan,

        "execution_performed":
            execution_performed,

        "final_state":
            final_state,

        "execution_outcome":
            actual_outcome,

        "decision_latency_seconds":
            decision_latency_seconds,

        "execution_latency_seconds":
            execution_latency_seconds,

        "cycle_latency_seconds":
            (
                cycle_finished
                - cycle_started
            ),

        "llm_used":
            False,

        "runtime_rag_used":
            False,

        "runtime_memory_used_for_decisions":
            False,

        "agentic_recovery_used":
            False,

        "deterministic_fallback_used":
            False
    }


    # ========================================================
    # DISPLAY SUMMARY
    # ========================================================

    print()
    print(
        "======================================"
    )
    print(
        " E7 B0 CYCLE COMPLETE"
    )
    print(
        "======================================"
    )

    print(
        "Safety Status:",
        verdict["status"]
    )

    print(
        "Execution Performed:",
        execution_performed
    )

    print(
        "Runtime Outcome:",
        actual_outcome["status"]
    )

    print(
        "Decision Latency:",
        f"{decision_latency_seconds:.6f}",
        "seconds"
    )


    return episode


# ============================================================
# REAL EXECUTION ENTRY POINT
# ============================================================

if __name__ == "__main__":

    run_b0_cycle()
