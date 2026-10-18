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

from b2_rag_analyzer import analyze_b2
from b2_rag_planner import plan_b2

from e7_runtime_memory import (
    load_run_episodes,
    save_run_episode
)


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
# B2 — ONE CONTROL CYCLE
# ============================================================

def run_b2_cycle(
    run_id
):

    print()
    print(
        "======================================"
    )
    print(
        " E7 B2 — LLM + RUNTIME RAG"
    )
    print(
        "======================================"
    )

    print(
        "Run ID:",
        run_id
    )


    cycle_started = (
        time.perf_counter()
    )


    # ========================================================
    # MEMORY STATE BEFORE THIS CYCLE
    # ========================================================

    previous_episodes = (
        load_run_episodes(
            "B2",
            run_id
        )
    )

    memory_episode_count_before = (
        len(previous_episodes)
    )

    runtime_memory_available = (
        memory_episode_count_before > 0
    )


    print(
        "B2 Episodes Available Before Cycle:",
        memory_episode_count_before
    )


    # ========================================================
    # STEP 1 — MONITOR
    # ========================================================

    initial_state = monitor()

    current_state = (
        initial_state.copy()
    )


    # ========================================================
    # STEP 2 — B2 RAG-AUGMENTED ANALYSIS
    # ========================================================

    analysis_started = (
        time.perf_counter()
    )

    diagnosis = analyze_b2(
        current_state,
        run_id
    )

    analysis_finished = (
        time.perf_counter()
    )

    analysis_latency_seconds = (
        analysis_finished
        - analysis_started
    )


    # ========================================================
    # STEP 3 — B2 RAG-AUGMENTED PLANNING
    # ========================================================

    planning_started = (
        time.perf_counter()
    )

    candidate_plan = plan_b2(
        current_state,
        diagnosis,
        run_id
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
                "B2 selected validated no-action."
            )

            print(
                "No SWIM effector command is sent."
            )


        executed_plan = (
            candidate_plan.copy()
        )


        print()
        print(
            "=== MONITOR AFTER B2 DECISION ==="
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
    # B2 deliberately has:
    # - runtime RAG and memory
    # - NO failure router
    # - NO bounded replanning
    # - NO deterministic fallback
    #
    # The rejected proposal may inform later B2 cycles
    # after this episode is stored, but it is not repaired
    # within this control cycle.
    # ========================================================

    else:

        print()
        print(
            "=== B2 SAFETY REJECTION ==="
        )

        print(
            "The RAG-augmented LLM candidate "
            "was rejected."
        )

        print(
            "B2 performs no within-cycle recovery."
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
                    "The B2 RAG-augmented LLM candidate "
                    "was rejected by the common deterministic "
                    "safety checker. B2 has no within-cycle "
                    "failure routing, bounded replanning, or "
                    "deterministic fallback, so no adaptation "
                    "was executed."
                )
        }


    # ========================================================
    # STEP 6 — BUILD EXPERIMENT EPISODE
    # ========================================================

    cycle_finished = (
        time.perf_counter()
    )


    episode = {
        "variant":
            "B2",

        "variant_name":
            "LLM plus runtime RAG",

        "run_id":
            run_id,

        "timestamp_utc":
            utc_now(),

        "initial_state":
            initial_state,

        "diagnosis":
            diagnosis,

        "candidate_plan":
            candidate_plan,

        # Compatibility with the B3 retrieval representation.
        "final_plan":
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

        # Compatibility with older B3 episode readers.
        "final_verdict":
            actual_outcome,

        "memory_episode_count_before":
            memory_episode_count_before,

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

        "runtime_rag_enabled":
            True,

        "runtime_rag_used":
            runtime_memory_available,

        "runtime_memory_used_for_decisions":
            runtime_memory_available,

        "runtime_memory_scope":
            "isolated_B2_run",

        "agentic_recovery_used":
            False,

        "deterministic_fallback_used":
            False
    }


    # ========================================================
    # STEP 7 — SAVE ONLY TO THIS ISOLATED B2 RUN
    # ========================================================

    saved_path = save_run_episode(
        "B2",
        run_id,
        episode
    )


    memory_episode_count_after = (
        len(
            load_run_episodes(
                "B2",
                run_id
            )
        )
    )


    print()
    print(
        "B2 episode saved to isolated run memory:"
    )

    print(
        saved_path
    )


    # ========================================================
    # DISPLAY SUMMARY
    # ========================================================

    print()
    print(
        "======================================"
    )
    print(
        " E7 B2 CYCLE COMPLETE"
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
        "Runtime RAG Enabled:",
        True
    )

    print(
        "Runtime RAG Used This Cycle:",
        runtime_memory_available
    )

    print(
        "Memory Episodes Before:",
        memory_episode_count_before
    )

    print(
        "Memory Episodes After:",
        memory_episode_count_after
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

    if len(sys.argv) != 2:

        raise SystemExit(
            "Usage: "
            "python3 evaluation/e7/b2_controller.py "
            "<run_id>"
        )

    run_b2_cycle(
        sys.argv[1]
    )
