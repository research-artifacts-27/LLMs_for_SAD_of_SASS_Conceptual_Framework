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

from b1_llm_analyzer import analyze_b1
from b1_llm_planner import plan_b1


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
# B1 — ONE CONTROL CYCLE
# ============================================================

def run_b1_cycle():

    print()
    print(
        "======================================"
    )
    print(
        " E7 B1 — LLM-ONLY"
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
    # STEP 2 — LLM-ONLY ANALYSIS
    # ========================================================

    analysis_started = (
        time.perf_counter()
    )

    diagnosis = analyze_b1(
        current_state
    )

    analysis_finished = (
        time.perf_counter()
    )

    analysis_latency_seconds = (
        analysis_finished
        - analysis_started
    )


    # ========================================================
    # STEP 3 — LLM-ONLY PLANNING
    # ========================================================

    planning_started = (
        time.perf_counter()
    )

    candidate_plan = plan_b1(
        current_state,
        diagnosis
    )

    planning_finished = (
        time.perf_counter()
    )

    planning_latency_seconds = (
        planning_finished
        - planning_started
    )


    # ========================================================
    # STEP 4 — COMMON DETERMINISTIC SAFETY CHECK
    # ========================================================

    safety_started = (
        time.perf_counter()
    )

    verdict = safety_check(
        candidate_plan,
        current_state
    )

    safety_finished = (
        time.perf_counter()
    )

    safety_latency_seconds = (
        safety_finished
        - safety_started
    )


    decision_latency_seconds = (
        analysis_latency_seconds
        + planning_latency_seconds
        + safety_latency_seconds
    )


    executed_plan = None

    execution_performed = False

    execution_latency_seconds = 0.0


    # ========================================================
    # STEP 5A — SAFETY PASS
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
                "B1 selected validated no-action."
            )

            print(
                "No SWIM effector command is sent."
            )


        executed_plan = (
            candidate_plan.copy()
        )


        print()
        print(
            "=== MONITOR AFTER B1 DECISION ==="
        )

        final_state = monitor()


        actual_outcome = evaluate_outcome(
            current_state,
            final_state,
            candidate_plan
        )


    # ========================================================
    # STEP 5B — SAFETY FAIL
    #
    # B1 deliberately has:
    # - no runtime RAG
    # - no runtime-memory retrieval
    # - no agentic failure routing
    # - no bounded replanning
    # - no deterministic fallback
    #
    # Therefore the rejected LLM plan is not executed.
    # ========================================================

    else:

        print()
        print(
            "=== B1 SAFETY REJECTION ==="
        )

        print(
            "The LLM-generated candidate was rejected."
        )

        print(
            "B1 performs no within-cycle recovery."
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
                    "The B1 LLM-generated candidate was "
                    "rejected by the common deterministic "
                    "safety checker. B1 has no within-cycle "
                    "failure routing, replanning, or "
                    "deterministic fallback, so no "
                    "adaptation was executed."
                )
        }


    # ========================================================
    # STEP 6 — COMPLETE EXPERIMENT RECORD
    # ========================================================

    cycle_finished = (
        time.perf_counter()
    )


    episode = {
        "variant":
            "B1",

        "variant_name":
            "LLM-only",

        "timestamp_utc":
            utc_now(),

        "initial_state":
            initial_state,

        "diagnosis":
            diagnosis,

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

        "analysis_latency_seconds":
            analysis_latency_seconds,

        "planning_latency_seconds":
            planning_latency_seconds,

        "safety_latency_seconds":
            safety_latency_seconds,

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
            True,

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
        " E7 B1 CYCLE COMPLETE"
    )
    print(
        "======================================"
    )

    print(
        "Diagnosis:",
        diagnosis
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
        "Analysis Latency:",
        f"{analysis_latency_seconds:.6f}",
        "seconds"
    )

    print(
        "Planning Latency:",
        f"{planning_latency_seconds:.6f}",
        "seconds"
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

    run_b1_cycle()
