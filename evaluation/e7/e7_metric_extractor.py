#!/usr/bin/env python3

import json
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = (
    Path(__file__).resolve()
    .parents[2]
)

POLICY_FILE = (
    PROJECT_ROOT
    / "trusted_policies.json"
)


# ============================================================
# HELPERS
# ============================================================

def load_response_time_target():

    with POLICY_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        policies = json.load(file)

    return float(
        policies[
            "response_time_target"
        ]
    )


def safe_get(
    mapping,
    key,
    default=None
):

    if not isinstance(
        mapping,
        dict
    ):

        return default

    return mapping.get(
        key,
        default
    )


def get_action(
    plan
):

    return safe_get(
        plan,
        "action"
    )


def get_action_value(
    plan
):

    if not isinstance(
        plan,
        dict
    ):

        return None

    if "value" in plan:

        return plan.get(
            "value"
        )

    if "target_servers" in plan:

        return plan.get(
            "target_servers"
        )

    return None


# ============================================================
# COMMON E7 METRIC EXTRACTION
# ============================================================

def extract_episode_metrics(
    episode,
    run_id_override=None,
    cycle_index=None,
    response_time_target=None
):

    """
    Convert one B0/B1/B2/B3 episode into one
    common E7 comparison row.

    This function is read-only.
    """

    if not isinstance(
        episode,
        dict
    ):

        raise TypeError(
            "episode must be a dictionary."
        )


    if response_time_target is None:

        response_time_target = (
            load_response_time_target()
        )


    variant = episode.get(
        "variant",
        "UNKNOWN"
    )

    variant_name = episode.get(
        "variant_name"
    )


    # ========================================================
    # RUN ID
    #
    # B2/B3 carry run_id directly.
    # B0/B1 can receive it from the future E8 harness.
    # ========================================================

    run_id = episode.get(
        "run_id"
    )

    if run_id_override is not None:

        run_id = run_id_override


    # ========================================================
    # STATES
    # ========================================================

    initial_state = episode.get(
        "initial_state",
        {}
    )

    final_state = episode.get(
        "final_state",
        {}
    )


    response_time_before = safe_get(
        initial_state,
        "response_time"
    )

    response_time_after = safe_get(
        final_state,
        "response_time"
    )


    # ========================================================
    # GOAL COMPLIANCE
    # ========================================================

    goal_violated_before = None

    if response_time_before is not None:

        goal_violated_before = (
            float(
                response_time_before
            )
            > response_time_target
        )


    goal_violated_after = None

    if response_time_after is not None:

        goal_violated_after = (
            float(
                response_time_after
            )
            > response_time_target
        )


    # ========================================================
    # CANDIDATE PLAN
    #
    # B3 normalization defines candidate_plan as the FIRST
    # agentic proposal.
    # ========================================================

    candidate_plan = episode.get(
        "candidate_plan",
        episode.get(
            "first_plan"
        )
    )


    candidate_action = get_action(
        candidate_plan
    )

    candidate_value = get_action_value(
        candidate_plan
    )


    # ========================================================
    # CANDIDATE SAFETY
    #
    # B3 uses candidate_safety_verdict for the FIRST proposal.
    # B0-B2 use safety_verdict directly.
    # ========================================================

    candidate_safety = episode.get(
        "candidate_safety_verdict"
    )

    if candidate_safety is None:

        candidate_safety = episode.get(
            "safety_verdict",
            {}
        )


    candidate_safety_status = safe_get(
        candidate_safety,
        "status"
    )


    safety_rejection = (
        candidate_safety_status
        == "FAIL"
    )


    # ========================================================
    # ACTUAL EXECUTION
    # ========================================================

    executed_plan = episode.get(
        "executed_plan"
    )

    execution_performed = bool(
        episode.get(
            "execution_performed",
            False
        )
    )


    # B3 normalized episodes derive this field.
    # This fallback supports older/raw B3 episodes.
    if (
        "execution_performed"
        not in episode
        and isinstance(
            executed_plan,
            dict
        )
    ):

        execution_performed = (
            executed_plan.get(
                "action"
            )
            not in {
                None,
                "none"
            }
        )


    executed_action = get_action(
        executed_plan
    )

    executed_value = get_action_value(
        executed_plan
    )


    executed_plan_source = episode.get(
        "executed_plan_source"
    )


    if executed_plan_source is None:

        if execution_performed:

            executed_plan_source = (
                "candidate_plan"
            )

        elif (
            isinstance(
                executed_plan,
                dict
            )
            and executed_plan.get(
                "action"
            )
            == "none"
        ):

            executed_plan_source = (
                "validated_no_action"
            )


    # ========================================================
    # OUTCOME
    # ========================================================

    execution_outcome = episode.get(
        "execution_outcome",
        episode.get(
            "final_verdict",
            {}
        )
    )


    outcome_status = safe_get(
        execution_outcome,
        "status"
    )

    action_effect_observed = safe_get(
        execution_outcome,
        "action_effect_observed"
    )

    goal_satisfied_reported = safe_get(
        execution_outcome,
        "goal_satisfied"
    )


    # ========================================================
    # RECOVERY / FALLBACK
    # ========================================================

    recovery_attempts = episode.get(
        "recovery_attempts",
        0
    )

    recovery_routes = episode.get(
        "recovery_routes",
        []
    )


    if recovery_routes is None:

        recovery_routes = []


    agentic_recovery_used = bool(
        episode.get(
            "agentic_recovery_used",
            False
        )
    )


    deterministic_fallback_used = bool(
        episode.get(
            "deterministic_fallback_used",
            episode.get(
                "fallback_invoked",
                False
            )
        )
    )


    fail_safe_triggered = bool(
        episode.get(
            "fail_safe_triggered",
            False
        )
    )


    operator_intervention = bool(
        episode.get(
            "operator_intervention",
            episode.get(
                "operator_escalation_requested",
                False
            )
        )
    )


    # ========================================================
    # MEMORY / RAG
    # ========================================================

    runtime_rag_enabled = episode.get(
        "runtime_rag_enabled"
    )


    if runtime_rag_enabled is None:

        runtime_rag_enabled = (
            variant in {
                "B2",
                "B3"
            }
        )


    runtime_rag_used = bool(
        episode.get(
            "runtime_rag_used",
            False
        )
    )


    memory_before = episode.get(
        "memory_episode_count_before"
    )

    memory_after = episode.get(
        "memory_episode_count_after"
    )


    # B2 currently stores count-before in the episode,
    # then appends the completed episode to memory.
    if (
        memory_after is None
        and variant == "B2"
        and isinstance(
            memory_before,
            int
        )
    ):

        memory_after = (
            memory_before
            + 1
        )


    # ========================================================
    # RESOURCE STATE
    # ========================================================

    servers_before = safe_get(
        initial_state,
        "servers"
    )

    servers_after = safe_get(
        final_state,
        "servers"
    )

    active_servers_before = safe_get(
        initial_state,
        "active_servers"
    )

    active_servers_after = safe_get(
        final_state,
        "active_servers"
    )

    dimmer_before = safe_get(
        initial_state,
        "dimmer"
    )

    dimmer_after = safe_get(
        final_state,
        "dimmer"
    )

    utilization_before = safe_get(
        initial_state,
        "utilization"
    )

    utilization_after = safe_get(
        final_state,
        "utilization"
    )

    arrival_rate_before = safe_get(
        initial_state,
        "arrival_rate"
    )

    arrival_rate_after = safe_get(
        final_state,
        "arrival_rate"
    )


    # ========================================================
    # LATENCIES
    #
    # Missing measurements remain None.
    # We do NOT fabricate B3 timing values.
    # ========================================================

    analysis_latency = episode.get(
        "analysis_latency_seconds"
    )

    planning_latency = episode.get(
        "planning_latency_seconds"
    )

    safety_latency = episode.get(
        "safety_latency_seconds"
    )

    decision_latency = episode.get(
        "decision_latency_seconds"
    )

    execution_latency = episode.get(
        "execution_latency_seconds"
    )

    cycle_latency = episode.get(
        "cycle_latency_seconds"
    )


    # ========================================================
    # COMMON COMPARISON ROW
    # ========================================================

    return {

        "metric_schema_version":
            "E7-METRICS-1",

        "variant":
            variant,

        "variant_name":
            variant_name,

        "run_id":
            run_id,

        "cycle_index":
            cycle_index,

        "timestamp_utc":
            episode.get(
                "timestamp_utc"
            ),

        "diagnosis":
            episode.get(
                "diagnosis"
            ),

        "response_time_target":
            response_time_target,

        "response_time_before":
            response_time_before,

        "response_time_after":
            response_time_after,

        "goal_violated_before":
            goal_violated_before,

        "goal_violated_after":
            goal_violated_after,

        "candidate_action":
            candidate_action,

        "candidate_value":
            candidate_value,

        "candidate_safety_status":
            candidate_safety_status,

        "safety_rejection":
            safety_rejection,

        "execution_performed":
            execution_performed,

        "executed_action":
            executed_action,

        "executed_value":
            executed_value,

        "executed_plan_source":
            executed_plan_source,

        "outcome_status":
            outcome_status,

        "action_effect_observed":
            action_effect_observed,

        "goal_satisfied_reported":
            goal_satisfied_reported,

        "servers_before":
            servers_before,

        "servers_after":
            servers_after,

        "active_servers_before":
            active_servers_before,

        "active_servers_after":
            active_servers_after,

        "dimmer_before":
            dimmer_before,

        "dimmer_after":
            dimmer_after,

        "utilization_before":
            utilization_before,

        "utilization_after":
            utilization_after,

        "arrival_rate_before":
            arrival_rate_before,

        "arrival_rate_after":
            arrival_rate_after,

        "llm_used":
            bool(
                episode.get(
                    "llm_used",
                    variant in {
                        "B1",
                        "B2",
                        "B3"
                    }
                )
            ),

        "runtime_rag_enabled":
            bool(
                runtime_rag_enabled
            ),

        "runtime_rag_used":
            runtime_rag_used,

        "runtime_memory_scope":
            episode.get(
                "runtime_memory_scope"
            ),

        "memory_episode_count_before":
            memory_before,

        "memory_episode_count_after":
            memory_after,

        "agentic_recovery_used":
            agentic_recovery_used,

        "recovery_attempts":
            recovery_attempts,

        "recovery_route_count":
            len(
                recovery_routes
            ),

        "deterministic_fallback_used":
            deterministic_fallback_used,

        "fail_safe_triggered":
            fail_safe_triggered,

        "operator_intervention":
            operator_intervention,

        "analysis_latency_seconds":
            analysis_latency,

        "planning_latency_seconds":
            planning_latency,

        "safety_latency_seconds":
            safety_latency,

        "decision_latency_seconds":
            decision_latency,

        "execution_latency_seconds":
            execution_latency,

        "cycle_latency_seconds":
            cycle_latency
    }


# ============================================================
# EXTRACT MULTIPLE EPISODES
# ============================================================

def extract_episode_list(
    episodes,
    run_id_override=None,
    response_time_target=None
):

    rows = []


    for index, episode in enumerate(
        episodes,
        start=1
    ):

        rows.append(
            extract_episode_metrics(
                episode,
                run_id_override=run_id_override,
                cycle_index=index,
                response_time_target=response_time_target
            )
        )


    return rows


# ============================================================
# INFORMATIONAL MODE
# ============================================================

if __name__ == "__main__":

    print(
        "E7 common metric extractor loaded."
    )

    print(
        "This module is read-only."
    )

    print(
        "It does not run SWIM, LLMs, embeddings, "
        "or adaptation actions."
    )
