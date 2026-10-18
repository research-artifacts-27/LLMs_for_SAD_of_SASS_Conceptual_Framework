#!/usr/bin/env python3

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

RUNTIME_KB = PROJECT_ROOT / "runtime_kb.json"
TRUSTED_POLICIES = PROJECT_ROOT / "trusted_policies.json"
DESIGN_REQUEST = (
    PROJECT_ROOT
    / "design_time"
    / "config"
    / "swim_design_request.json"
)

OUTPUT_JSON = (
    PROJECT_ROOT
    / "design_time"
    / "outputs"
    / "runtime_design_feedback.json"
)

OUTPUT_MD = (
    PROJECT_ROOT
    / "design_time"
    / "outputs"
    / "runtime_design_feedback.md"
)


def load_json(path, default=None):
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def as_dict(value):
    if isinstance(value, dict):
        return value
    return {}


def get_status(value):
    """
    Extract a status from either:
      - {"status": "PASS"}
      - "PASS"
      - None
    """
    if isinstance(value, dict):
        status = value.get("status")
        if status is not None:
            return str(status).upper()

    if isinstance(value, str):
        return value.upper()

    return None


def get_action(plan):
    if isinstance(plan, dict):
        action = plan.get("action")
        if action is not None:
            return str(action)

    if isinstance(plan, str):
        return plan

    return "unknown"


def get_number(mapping, key):
    if not isinstance(mapping, dict):
        return None

    value = mapping.get(key)

    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def get_bool(mapping, key):
    if not isinstance(mapping, dict):
        return None

    value = mapping.get(key)

    if isinstance(value, bool):
        return value

    return None


def pct(part, total):
    if total == 0:
        return 0.0
    return round((part / total) * 100.0, 2)


def compact_counter(counter):
    return {
        str(k): int(v)
        for k, v in sorted(
            counter.items(),
            key=lambda item: (-item[1], str(item[0]))
        )
    }


def episode_evidence(
    index,
    episode,
    response_time_target,
    max_servers
):
    initial_state = as_dict(episode.get("initial_state"))
    final_state = as_dict(episode.get("final_state"))

    execution_outcome_raw = episode.get("execution_outcome")
    execution_outcome = as_dict(execution_outcome_raw)

    final_verdict = episode.get("final_verdict")
    first_verdict = episode.get("first_verdict")
    safety_verdict = episode.get("safety_verdict")

    diagnosis = episode.get("diagnosis", "unknown")
    final_plan = episode.get("final_plan")
    first_plan = episode.get("first_plan")

    final_action = get_action(final_plan)
    first_action = get_action(first_plan)

    final_safety_status = (
        get_status(safety_verdict)
        or get_status(final_verdict)
    )

    first_safety_status = get_status(first_verdict)

    execution_status = get_status(execution_outcome_raw)

    final_rt = get_number(final_state, "response_time")
    initial_rt = get_number(initial_state, "response_time")

    final_servers = (
        get_number(final_state, "active_servers")
        or get_number(final_state, "servers")
    )

    initial_servers = (
        get_number(initial_state, "active_servers")
        or get_number(initial_state, "servers")
    )

    fail_safe = episode.get("fail_safe_triggered")
    if not isinstance(fail_safe, bool):
        fail_safe = False

    operator_intervention = episode.get("operator_intervention")
    operator_requested = bool(operator_intervention)

    recovery_attempts = episode.get("recovery_attempts", 0)
    try:
        recovery_attempts = int(recovery_attempts or 0)
    except (TypeError, ValueError):
        recovery_attempts = 0

    routes = episode.get("recovery_routes", [])
    if not isinstance(routes, list):
        routes = []

    goal_satisfied = None

    if execution_outcome:
        goal_satisfied = get_bool(
            execution_outcome,
            "goal_satisfied"
        )

    if goal_satisfied is None and final_rt is not None:
        goal_satisfied = final_rt <= response_time_target

    final_qos_violation = (
        final_rt is not None
        and final_rt > response_time_target
    )

    at_max_servers = (
        final_servers is not None
        and max_servers is not None
        and int(final_servers) >= int(max_servers)
    )

    return {
        "episode_index": index,
        "diagnosis": diagnosis,
        "first_action": first_action,
        "final_action": final_action,
        "first_safety_status": first_safety_status,
        "final_safety_status": final_safety_status,
        "execution_status": execution_status,
        "initial_response_time": initial_rt,
        "final_response_time": final_rt,
        "response_time_target": response_time_target,
        "initial_servers": initial_servers,
        "final_servers": final_servers,
        "max_servers": max_servers,
        "goal_satisfied": goal_satisfied,
        "final_qos_violation": final_qos_violation,
        "at_max_servers": at_max_servers,
        "fail_safe_triggered": fail_safe,
        "operator_intervention": operator_requested,
        "recovery_attempts": recovery_attempts,
        "recovery_routes": routes,
    }


def make_trigger(
    trigger_id,
    title,
    severity,
    condition,
    count,
    episode_indices,
    interpretation,
    design_question,
):
    return {
        "id": trigger_id,
        "title": title,
        "severity": severity,
        "condition": condition,
        "evidence_count": int(count),
        "episode_indices": episode_indices[:20],
        "interpretation": interpretation,
        "design_review_question": design_question,
    }


def analyze():
    runtime_kb = load_json(RUNTIME_KB, [])

    if not isinstance(runtime_kb, list):
        raise ValueError(
            "runtime_kb.json must contain a JSON list."
        )

    policies = load_json(TRUSTED_POLICIES, {})
    if not isinstance(policies, dict):
        policies = {}

    design_request = load_json(DESIGN_REQUEST, {})
    if not isinstance(design_request, dict):
        design_request = {}

    response_time_target = float(
        policies.get("response_time_target", 0.75)
    )

    max_servers = policies.get("max_servers", 6)
    try:
        max_servers = int(max_servers)
    except (TypeError, ValueError):
        max_servers = 6

    evidence = []

    for index, episode in enumerate(runtime_kb, start=1):
        if not isinstance(episode, dict):
            continue

        evidence.append(
            episode_evidence(
                index,
                episode,
                response_time_target,
                max_servers,
            )
        )

    total = len(evidence)

    diagnoses = Counter()
    first_actions = Counter()
    final_actions = Counter()
    first_safety = Counter()
    final_safety = Counter()
    execution_outcomes = Counter()
    recovery_routes = Counter()

    recovery_attempt_total = 0

    modern_execution_count = 0
    modern_safety_count = 0
    fail_safe_field_count = 0

    qos_violation_indices = []
    max_capacity_violation_indices = []
    fail_safe_indices = []
    operator_indices = []
    recovery_indices = []
    safety_rejection_indices = []
    partial_indices = []
    failed_execution_indices = []
    unknown_diagnosis_indices = []

    for item in evidence:
        diagnoses[item["diagnosis"]] += 1
        first_actions[item["first_action"]] += 1
        final_actions[item["final_action"]] += 1

        if item["first_safety_status"]:
            first_safety[item["first_safety_status"]] += 1

        if item["final_safety_status"]:
            final_safety[item["final_safety_status"]] += 1

        if item["execution_status"]:
            execution_outcomes[item["execution_status"]] += 1
            modern_execution_count += 1

        if (
            item["first_safety_status"] is not None
            or item["final_safety_status"] is not None
        ):
            modern_safety_count += 1

        original_episode = runtime_kb[item["episode_index"] - 1]

        if "fail_safe_triggered" in original_episode:
            fail_safe_field_count += 1

        for route in item["recovery_routes"]:
            recovery_routes[str(route).lower()] += 1

        recovery_attempt_total += item["recovery_attempts"]

        if item["final_qos_violation"]:
            qos_violation_indices.append(item["episode_index"])

        if (
            item["final_qos_violation"]
            and item["at_max_servers"]
        ):
            max_capacity_violation_indices.append(
                item["episode_index"]
            )

        if item["fail_safe_triggered"]:
            fail_safe_indices.append(item["episode_index"])

        if item["operator_intervention"]:
            operator_indices.append(item["episode_index"])

        if item["recovery_attempts"] > 0:
            recovery_indices.append(item["episode_index"])

        if (
            item["first_safety_status"] == "FAIL"
            or item["final_safety_status"] == "FAIL"
        ):
            safety_rejection_indices.append(
                item["episode_index"]
            )

        if item["execution_status"] == "PARTIAL":
            partial_indices.append(item["episode_index"])

        if item["execution_status"] == "FAIL":
            failed_execution_indices.append(
                item["episode_index"]
            )

        diagnosis_text = str(item["diagnosis"]).lower()
        if diagnosis_text in (
            "unknown",
            "none",
            "",
        ):
            unknown_diagnosis_indices.append(
                item["episode_index"]
            )

    triggers = []

    if max_capacity_violation_indices:
        triggers.append(
            make_trigger(
                "RTD-01",
                "QoS violation at maximum configured capacity",
                "high",
                (
                    "Final response time exceeded the trusted target "
                    "while the system was already at max_servers."
                ),
                len(max_capacity_violation_indices),
                max_capacity_violation_indices,
                (
                    "The approved resource envelope may be insufficient "
                    "for some observed workloads, or an alternative "
                    "adaptation tactic may be required."
                ),
                (
                    "Should the architecture provide additional capacity, "
                    "a stronger degradation tactic, or another adaptation "
                    "mechanism for workloads that exceed the current "
                    "resource envelope?"
                ),
            )
        )

    if len(partial_indices) >= 2:
        triggers.append(
            make_trigger(
                "RTD-02",
                "Repeated partial adaptation outcomes",
                "medium",
                (
                    "An adaptation action took effect, but the runtime "
                    "goal remained unsatisfied in multiple episodes."
                ),
                len(partial_indices),
                partial_indices,
                (
                    "Individual adaptations may be too incremental for "
                    "some operating conditions, requiring multiple "
                    "control cycles before the goal is restored."
                ),
                (
                    "Should the architecture support stronger multi-step "
                    "plans, adaptive planning horizons, or explicit "
                    "reasoning about expected adaptation magnitude?"
                ),
            )
        )

    if safety_rejection_indices:
        triggers.append(
            make_trigger(
                "RTD-03",
                "Safety-rejected candidate adaptations",
                "medium",
                (
                    "One or more generated candidate plans violated "
                    "trusted runtime constraints."
                ),
                len(safety_rejection_indices),
                safety_rejection_indices,
                (
                    "The deterministic safety boundary is functioning, "
                    "but repeated rejection may reveal a mismatch between "
                    "planning knowledge and authoritative runtime policy."
                ),
                (
                    "Should trusted constraints or feasibility knowledge "
                    "be exposed more explicitly to the planner while "
                    "remaining outside LLM control?"
                ),
            )
        )

    if fail_safe_indices:
        triggers.append(
            make_trigger(
                "RTD-04",
                "Bounded recovery exhausted",
                "high",
                (
                    "The configured recovery bound was exhausted and "
                    "fail-safe handling was activated."
                ),
                len(fail_safe_indices),
                fail_safe_indices,
                (
                    "The runtime architecture correctly prevented "
                    "unbounded recovery, but the episode warrants "
                    "architectural review of available fallback options."
                ),
                (
                    "Should the architecture provide an additional "
                    "fallback tactic, safe-state transition, or richer "
                    "recovery strategy for this class of failure?"
                ),
            )
        )

    if failed_execution_indices:
        triggers.append(
            make_trigger(
                "RTD-05",
                "Failed adaptation effects",
                "high",
                (
                    "The intended runtime adaptation effect was not "
                    "observed after execution."
                ),
                len(failed_execution_indices),
                failed_execution_indices,
                (
                    "This may indicate an execution, timing, actuation, "
                    "or model synchronization concern."
                ),
                (
                    "Should execution verification, rollback, or "
                    "effect-confirmation mechanisms be strengthened?"
                ),
            )
        )

    if unknown_diagnosis_indices:
        triggers.append(
            make_trigger(
                "RTD-06",
                "Unresolved runtime diagnoses",
                "medium",
                (
                    "One or more runtime episodes could not be assigned "
                    "a recognized diagnosis."
                ),
                len(unknown_diagnosis_indices),
                unknown_diagnosis_indices,
                (
                    "The analysis knowledge may not cover all encountered "
                    "runtime states."
                ),
                (
                    "Should the architecture knowledge or diagnostic "
                    "taxonomy be extended to cover these states?"
                ),
            )
        )

    severity_order = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }

    triggers.sort(
        key=lambda x: (
            severity_order.get(x["severity"], 99),
            -x["evidence_count"],
            x["id"],
        )
    )

    report = {
        "report_type": "runtime_to_design_feedback",
        "schema_version": "1.0",
        "generated_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "purpose": (
            "Deterministically summarize accumulated runtime "
            "adaptation evidence and identify evidence that may "
            "justify human-initiated architecture review."
        ),
        "authority_boundary": {
            "automatic_redesign": False,
            "automatic_architecture_approval": False,
            "automatic_runtime_policy_change": False,
            "human_architect_review_required": True,
        },
        "sources": {
            "runtime_kb": str(
                RUNTIME_KB.relative_to(PROJECT_ROOT)
            ),
            "trusted_policies": str(
                TRUSTED_POLICIES.relative_to(PROJECT_ROOT)
            ),
            "design_request": str(
                DESIGN_REQUEST.relative_to(PROJECT_ROOT)
            ),
        },
        "trusted_runtime_context": {
            "response_time_target_seconds": response_time_target,
            "max_servers": max_servers,
            "allowed_actions": policies.get(
                "allowed_actions",
                [],
            ),
        },
        "design_context_available": bool(design_request),
        "coverage": {
            "total_runtime_episodes": total,
            "episodes_with_explicit_execution_outcome": (
                modern_execution_count
            ),
            "episodes_with_safety_information": (
                modern_safety_count
            ),
            "episodes_with_fail_safe_field": (
                fail_safe_field_count
            ),
            "note": (
                "The runtime knowledge base contains episodes "
                "created under evolving schemas. Missing fields "
                "are treated as unavailable rather than fabricated."
            ),
        },
        "summary": {
            "diagnoses": compact_counter(diagnoses),
            "first_actions": compact_counter(first_actions),
            "final_actions": compact_counter(final_actions),
            "first_safety_statuses": compact_counter(
                first_safety
            ),
            "final_safety_statuses": compact_counter(
                final_safety
            ),
            "execution_outcomes": compact_counter(
                execution_outcomes
            ),
            "recovery_routes": compact_counter(
                recovery_routes
            ),
            "episodes_with_final_qos_violation": len(
                qos_violation_indices
            ),
            "episodes_with_qos_violation_at_max_capacity": len(
                max_capacity_violation_indices
            ),
            "episodes_with_safety_rejection": len(
                safety_rejection_indices
            ),
            "episodes_with_recovery_attempts": len(
                recovery_indices
            ),
            "total_recovery_attempts": (
                recovery_attempt_total
            ),
            "episodes_with_fail_safe": len(
                fail_safe_indices
            ),
            "episodes_with_operator_intervention": len(
                operator_indices
            ),
        },
        "architecture_review": {
            "review_recommended": bool(triggers),
            "trigger_count": len(triggers),
            "triggers": triggers,
            "decision": (
                "Evidence package only. Any architecture "
                "reconsideration requires explicit human "
                "architect initiation and approval."
            ),
        },
        "data_quality_notes": [
            (
                "The runtime knowledge base may contain both "
                "ordinary runtime episodes and controlled "
                "fault-injection episodes."
            ),
            (
                "Where experiment provenance is not explicitly "
                "stored in an episode, this analyzer does not "
                "guess whether the evidence came from natural "
                "operation or fault injection."
            ),
            (
                "A review trigger indicates evidence worth "
                "examining; it does not by itself prove that "
                "the approved architecture is defective."
            ),
        ],
    }

    return report


def write_markdown(report):
    summary = report["summary"]
    review = report["architecture_review"]
    coverage = report["coverage"]

    lines = []

    lines.append("# Runtime-to-Design Feedback Report")
    lines.append("")
    lines.append(
        f"Generated: {report['generated_utc']}"
    )
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(report["purpose"])
    lines.append("")
    lines.append("## Evidence Coverage")
    lines.append("")
    lines.append(
        f"- Runtime episodes: "
        f"{coverage['total_runtime_episodes']}"
    )
    lines.append(
        f"- Explicit execution outcomes: "
        f"{coverage['episodes_with_explicit_execution_outcome']}"
    )
    lines.append(
        f"- Episodes with safety information: "
        f"{coverage['episodes_with_safety_information']}"
    )
    lines.append(
        f"- Episodes with fail-safe field: "
        f"{coverage['episodes_with_fail_safe_field']}"
    )
    lines.append("")
    lines.append("## Runtime Summary")
    lines.append("")
    lines.append(
        f"- Final QoS violations: "
        f"{summary['episodes_with_final_qos_violation']}"
    )
    lines.append(
        f"- QoS violations at maximum capacity: "
        f"{summary['episodes_with_qos_violation_at_max_capacity']}"
    )
    lines.append(
        f"- Safety rejections: "
        f"{summary['episodes_with_safety_rejection']}"
    )
    lines.append(
        f"- Episodes with recovery attempts: "
        f"{summary['episodes_with_recovery_attempts']}"
    )
    lines.append(
        f"- Total recovery attempts: "
        f"{summary['total_recovery_attempts']}"
    )
    lines.append(
        f"- Fail-safe episodes: "
        f"{summary['episodes_with_fail_safe']}"
    )
    lines.append(
        f"- Operator-intervention episodes: "
        f"{summary['episodes_with_operator_intervention']}"
    )
    lines.append("")
    lines.append("## Architecture Review Triggers")
    lines.append("")

    if not review["triggers"]:
        lines.append(
            "No deterministic architecture-review trigger "
            "was identified."
        )
    else:
        for trigger in review["triggers"]:
            lines.append(
                f"### {trigger['id']} — "
                f"{trigger['title']}"
            )
            lines.append("")
            lines.append(
                f"- Severity: {trigger['severity']}"
            )
            lines.append(
                f"- Evidence count: "
                f"{trigger['evidence_count']}"
            )
            lines.append(
                f"- Episode indices: "
                f"{trigger['episode_indices']}"
            )
            lines.append(
                f"- Interpretation: "
                f"{trigger['interpretation']}"
            )
            lines.append(
                f"- Design-review question: "
                f"{trigger['design_review_question']}"
            )
            lines.append("")

    lines.append("## Authority Boundary")
    lines.append("")
    lines.append(
        "This report does not redesign the architecture, "
        "approve an architecture, or modify trusted runtime "
        "policies. It provides evidence for human architect "
        "review."
    )
    lines.append("")

    OUTPUT_MD.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_MD.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main():
    print("=" * 62)
    print(" RUNTIME-TO-DESIGN FEEDBACK ANALYZER")
    print("=" * 62)
    print()
    print("OFFLINE ANALYSIS")
    print("This program does NOT start or modify SWIM.")
    print("This program does NOT execute adaptation actions.")
    print("This program does NOT call the LLM.")
    print("This program does NOT modify runtime_kb.json.")
    print()

    report = analyze()

    OUTPUT_JSON.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_JSON.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    write_markdown(report)

    coverage = report["coverage"]
    summary = report["summary"]
    review = report["architecture_review"]

    print(
        "Runtime episodes analyzed:",
        coverage["total_runtime_episodes"],
    )
    print(
        "Explicit execution outcomes:",
        coverage[
            "episodes_with_explicit_execution_outcome"
        ],
    )
    print(
        "Safety-rejected episodes:",
        summary["episodes_with_safety_rejection"],
    )
    print(
        "Final QoS violations:",
        summary["episodes_with_final_qos_violation"],
    )
    print(
        "QoS violations at max capacity:",
        summary[
            "episodes_with_qos_violation_at_max_capacity"
        ],
    )
    print(
        "Episodes with recovery:",
        summary["episodes_with_recovery_attempts"],
    )
    print(
        "Fail-safe episodes:",
        summary["episodes_with_fail_safe"],
    )
    print()
    print(
        "Architecture review recommended:",
        review["review_recommended"],
    )
    print(
        "Review triggers:",
        review["trigger_count"],
    )

    for trigger in review["triggers"]:
        print(
            f"  {trigger['id']} | "
            f"{trigger['severity'].upper()} | "
            f"{trigger['title']} | "
            f"evidence={trigger['evidence_count']}"
        )

    print()
    print("Generated:")
    print(f"  {OUTPUT_JSON}")
    print(f"  {OUTPUT_MD}")
    print()
    print(
        "No architecture or runtime policy was changed."
    )
    print("=" * 62)


if __name__ == "__main__":
    main()
