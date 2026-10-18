#!/usr/bin/env python3

import argparse
import runpy
import sys
from pathlib import Path


# ============================================================
# PATHS
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


import rag_retriever
import runtime_kb

from e7_runtime_memory import (
    get_run_kb_path,
    load_run_episodes,
    save_run_episode
)


# ============================================================
# NORMALIZE B3 EPISODE FOR E7 COMPARISON
# ============================================================

def normalize_b3_episode(
    episode,
    run_id,
    memory_episode_count_before
):

    normalized = dict(
        episode
    )


    first_plan = normalized.get(
        "first_plan"
    )

    first_verdict = normalized.get(
        "first_verdict"
    )

    executed_plan = normalized.get(
        "executed_plan"
    )

    recovery_attempts = normalized.get(
        "recovery_attempts",
        0
    )

    recovery_routes = normalized.get(
        "recovery_routes",
        []
    )

    fallback_invoked = bool(
        normalized.get(
            "fallback_invoked",
            False
        )
    )


    # ========================================================
    # COMMON E7 IDENTITY
    # ========================================================

    normalized[
        "variant"
    ] = "B3"

    normalized[
        "variant_name"
    ] = "Full agentic architecture"

    normalized[
        "run_id"
    ] = run_id

    normalized[
        "comparison_schema_version"
    ] = "E7-1"


    # ========================================================
    # COMMON CANDIDATE REPRESENTATION
    #
    # For cross-variant comparison, candidate_plan means the
    # FIRST proposed adaptation before B3 recovery.
    #
    # B3's existing final_plan remains untouched and continues
    # to represent the final agentic candidate.
    # ========================================================

    normalized[
        "candidate_plan"
    ] = first_plan

    normalized[
        "candidate_safety_verdict"
    ] = first_verdict


    # ========================================================
    # EXECUTION FLAG
    # ========================================================

    execution_performed = False

    if isinstance(
        executed_plan,
        dict
    ):

        if (
            executed_plan.get(
                "action"
            )
            not in {
                None,
                "none"
            }
        ):

            execution_performed = True


    normalized[
        "execution_performed"
    ] = execution_performed


    # ========================================================
    # ISOLATED MEMORY METADATA
    # ========================================================

    runtime_memory_available = (
        memory_episode_count_before
        > 0
    )


    normalized[
        "memory_episode_count_before"
    ] = memory_episode_count_before

    normalized[
        "memory_episode_count_after"
    ] = (
        memory_episode_count_before
        + 1
    )

    normalized[
        "runtime_rag_enabled"
    ] = True

    normalized[
        "runtime_rag_used"
    ] = runtime_memory_available

    normalized[
        "runtime_memory_used_for_decisions"
    ] = runtime_memory_available

    normalized[
        "runtime_memory_scope"
    ] = "isolated_B3_run"


    # ========================================================
    # B3 CAPABILITY METADATA
    # ========================================================

    normalized[
        "llm_used"
    ] = True

    normalized[
        "failure_router_enabled"
    ] = True

    normalized[
        "bounded_replanning_enabled"
    ] = True

    normalized[
        "deterministic_fallback_enabled"
    ] = True

    normalized[
        "operator_escalation_enabled"
    ] = True


    agentic_recovery_used = bool(
        recovery_attempts
    ) or bool(
        recovery_routes
    )


    normalized[
        "agentic_recovery_used"
    ] = agentic_recovery_used

    normalized[
        "deterministic_fallback_used"
    ] = fallback_invoked


    # ========================================================
    # INITIAL SAFETY-REJECTION INDICATOR
    # ========================================================

    initial_safety_rejection = False

    if isinstance(
        first_verdict,
        dict
    ):

        initial_safety_rejection = (
            first_verdict.get(
                "status"
            )
            == "FAIL"
        )


    normalized[
        "initial_safety_rejection"
    ] = initial_safety_rejection


    return normalized


# ============================================================
# INSTALL B3 MEMORY ISOLATION
# ============================================================

def install_b3_isolation(
    run_id
):

    """
    Redirect B3 runtime-memory reads and writes
    to one isolated E7 B3 run KB.

    The validated project files are not edited.
    """

    kb_path = get_run_kb_path(
        "B3",
        run_id
    )


    if not kb_path.exists():

        raise FileNotFoundError(
            "B3 E7 run KB does not exist.\n"
            "Initialize it explicitly before running B3:\n"
            + str(kb_path)
        )


    # ========================================================
    # ISOLATED RAG READ
    # ========================================================

    def isolated_load_runtime_episodes():

        episodes = load_run_episodes(
            "B3",
            run_id
        )

        print()
        print(
            "=== E7 B3 ISOLATED MEMORY READ ==="
        )

        print(
            "Run ID:",
            run_id
        )

        print(
            "Episodes available:",
            len(episodes)
        )

        print(
            "Memory source:",
            kb_path
        )

        return episodes


    # ========================================================
    # ISOLATED + NORMALIZED EPISODE WRITE
    # ========================================================

    def isolated_save_episode(
        episode
    ):

        memory_episode_count_before = len(
            load_run_episodes(
                "B3",
                run_id
            )
        )


        experimental_episode = (
            normalize_b3_episode(
                episode,
                run_id,
                memory_episode_count_before
            )
        )


        saved_path = save_run_episode(
            "B3",
            run_id,
            experimental_episode
        )


        print()
        print(
            "=== E7 B3 ISOLATED MEMORY WRITE ==="
        )

        print(
            "B3 episode stored in:"
        )

        print(
            saved_path
        )

        print(
            "Memory Episodes Before:",
            memory_episode_count_before
        )

        print(
            "Memory Episodes After:",
            memory_episode_count_before + 1
        )


    # ========================================================
    # PATCH READ BOUNDARY
    # ========================================================

    rag_retriever.load_runtime_episodes = (
        isolated_load_runtime_episodes
    )


    # ========================================================
    # PATCH WRITE BOUNDARY
    # ========================================================

    runtime_kb.save_episode = (
        isolated_save_episode
    )


    if "agent_controller" in sys.modules:

        sys.modules[
            "agent_controller"
        ].save_episode = (
            isolated_save_episode
        )


    return {
        "variant":
            "B3",

        "run_id":
            run_id,

        "kb_path":
            str(kb_path),

        "episode_count":
            len(
                load_run_episodes(
                    "B3",
                    run_id
                )
            )
    }


# ============================================================
# RUN VALIDATED B3 CONTROLLER
# ============================================================

def run_b3_controller(
    run_id
):

    info = install_b3_isolation(
        run_id
    )


    print()
    print(
        "======================================"
    )

    print(
        " E7 B3 EXPERIMENTAL RUN"
    )

    print(
        "======================================"
    )

    print(
        "Run ID:",
        info["run_id"]
    )

    print(
        "Isolated KB:",
        info["kb_path"]
    )

    print(
        "Episodes before run:",
        info["episode_count"]
    )

    print()
    print(
        "Starting validated B3 controller..."
    )


    runpy.run_path(
        str(
            PROJECT_ROOT
            / "agent_controller.py"
        ),
        run_name="__main__"
    )


# ============================================================
# COMMAND-LINE ENTRY POINT
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "E7 isolated-memory wrapper for "
            "the validated B3 controller."
        )
    )

    parser.add_argument(
        "run_id",
        help=(
            "Explicit B3 experimental run ID."
        )
    )

    parser.add_argument(
        "--run-controller",
        action="store_true",
        help=(
            "Actually execute the validated B3 "
            "controller. Without this flag the "
            "script performs isolation setup only."
        )
    )

    args = parser.parse_args()


    info = install_b3_isolation(
        args.run_id
    )


    print()
    print(
        "======================================"
    )

    print(
        " E7 B3 ISOLATION CHECK"
    )

    print(
        "======================================"
    )

    print(
        "Run ID:",
        info["run_id"]
    )

    print(
        "Isolated KB:",
        info["kb_path"]
    )

    print(
        "Episodes:",
        info["episode_count"]
    )

    print(
        "Project runtime_kb.json redirected:",
        True
    )


    if not args.run_controller:

        print()
        print(
            "CHECK-ONLY MODE."
        )

        print(
            "The B3 controller was NOT executed."
        )

        print(
            "No SWIM adaptation was started."
        )

        raise SystemExit(0)


    print()
    print(
        "LIVE CONTROLLER EXECUTION REQUESTED."
    )


    runpy.run_path(
        str(
            PROJECT_ROOT
            / "agent_controller.py"
        ),
        run_name="__main__"
    )
