#!/usr/bin/env python3

import json
import os
from datetime import datetime, timezone


DESIGN_TIME_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_DIR = os.path.dirname(
    DESIGN_TIME_DIR
)

RECONSIDERATION_FILE = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "architecture_reconsideration.json"
)

OUTPUT_JSON = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "architecture_reconsideration_decision.json"
)

OUTPUT_MD = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "architecture_reconsideration_decision.md"
)


def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def save_json(
    path,
    data
):

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )


def main():

    review = load_json(
        RECONSIDERATION_FILE
    )

    if review.get(
        "architect_status"
    ) != "PENDING_REVIEW":

        raise RuntimeError(
            "Expected architecture reconsideration "
            "status PENDING_REVIEW."
        )


    options = review.get(
        "llm_review",
        {}
    ).get(
        "review_options",
        []
    )

    selected = None

    for option in options:

        if option.get(
            "id"
        ) == "R1":

            selected = option
            break


    if selected is None:

        raise RuntimeError(
            "R1 was not found in the "
            "architecture reconsideration."
        )


    decision = {
        "decision_type":
            "human_architect_reconsideration_decision",

        "schema_version":
            "1.0",

        "decided_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "selected_option": {
            "id":
                "R1",

            "disposition":
                selected.get(
                    "disposition"
                ),

            "name":
                selected.get(
                    "name"
                )
        },

        "decision":
            "RETAIN_CURRENT_ARCHITECTURE",

        "approved_architecture":
            "A1",

        "architect_rationale": (
            "RTD-02 identified repeated PARTIAL "
            "adaptation outcomes and therefore "
            "justified architectural review. "
            "Episode-level inspection showed that "
            "the PARTIAL outcomes represented "
            "successful incremental scale-out "
            "actions for which the response-time "
            "goal had not yet been restored within "
            "the same control cycle. Subsequent "
            "control cycles continued adaptation, "
            "and the inspected sequences included "
            "eventual goal restoration. The "
            "available evidence therefore does not "
            "demonstrate that the approved A1 "
            "architecture lacks the required "
            "architectural capability. A1 is "
            "retained without architectural or "
            "runtime-policy modification."
        ),

        "runtime_evidence_interpretation": {
            "review_trigger":
                "RTD-02",

            "partial_episode_count":
                8,

            "partial_episode_indices": [
                5,
                6,
                27,
                28,
                78,
                79,
                80,
                81
            ],

            "interpretation":
                (
                    "PARTIAL means the adaptation "
                    "action was successfully enacted "
                    "but the runtime goal remained "
                    "unsatisfied at evaluation time. "
                    "It is not equivalent to a "
                    "safety failure or failed "
                    "adaptation."
                ),

            "observed_recovery_example":
                (
                    "Episodes 78-82 show successive "
                    "scale-out from one to six active "
                    "servers, with episodes 78-81 "
                    "classified PARTIAL and episode "
                    "82 classified PASS with the "
                    "runtime goal satisfied."
                ),

            "causality_claimed":
                False
        },

        "llm_advisory_recommendation": {
            "recommended_option":
                review.get(
                    "llm_review",
                    {}
                ).get(
                    "llm_recommendation",
                    {}
                ).get(
                    "option_id"
                ),

            "accepted_by_architect":
                False,

            "note":
                (
                    "The LLM advisory recommendation "
                    "was considered but was not "
                    "accepted because the inspected "
                    "runtime evidence was insufficient "
                    "to justify architectural revision."
                )
        },

        "future_work": {
            "R2_status":
                "NOT_APPROVED",

            "R2_role":
                (
                    "Potential experimental refinement "
                    "for future comparative evaluation."
                ),

            "recommended_evidence_improvements": [
                "record experiment and scenario provenance",
                "record run identifiers",
                "record control-cycle timing",
                "record action and activation timing",
                "distinguish incremental progress from persistent unresolved adaptation",
                "link consecutive control cycles into recovery episodes"
            ]
        },

        "authority_boundary": {
            "human_architect_decision":
                True,

            "automatic_redesign":
                False,

            "architecture_changed":
                False,

            "trusted_policy_changed":
                False,

            "runtime_controller_changed":
                False,

            "swim_configuration_changed":
                False,

            "ADR_001_superseded":
                False
        },

        "status":
            "APPROVED_R1_RETAIN_A1"
    }


    save_json(
        OUTPUT_JSON,
        decision
    )


    markdown = f"""# Architecture Reconsideration Decision

**Status:** APPROVED — R1 / RETAIN A1

## Human Architect Decision

The human architect selected **R1 — {selected.get('name')}**.

The currently approved **A1 architecture remains unchanged**.

## Rationale

{decision['architect_rationale']}

## Interpretation of RTD-02

RTD-02 remains a valid architecture-review trigger. However, the inspected PARTIAL outcomes represent successful incremental adaptation actions for which the runtime goal had not yet been restored at the point of evaluation.

In particular, episodes 78–82 demonstrate successive scale-out from one to six active servers. Episodes 78–81 were PARTIAL, while episode 82 reached PASS with the goal satisfied.

This evidence does not establish that the architecture is defective, and no causal claim is made that server additions alone caused recovery because workload and system conditions also changed.

## LLM Recommendation

The LLM advisory review recommended **R2** with medium confidence.

The human architect did **not** approve R2.

R2 remains a possible future experimental refinement and may be evaluated comparatively before any future architectural reconsideration.

## Authority Boundary

- A1 remains the approved architecture.
- ADR-001 remains accepted and is not superseded.
- No trusted runtime policy is modified.
- No runtime controller is modified.
- No SWIM configuration is modified.
- No automatic redesign or deployment occurs.

"""

    with open(
        OUTPUT_MD,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            markdown
        )


    print("=" * 64)
    print(" HUMAN ARCHITECT REVIEW DECISION")
    print("=" * 64)
    print()
    print("Selected option: R1")
    print("Decision: RETAIN_CURRENT_ARCHITECTURE")
    print("Approved architecture: A1")
    print("LLM recommendation accepted: False")
    print("Architecture changed: False")
    print("Trusted policy changed: False")
    print("ADR-001 superseded: False")
    print()
    print("Status: APPROVED_R1_RETAIN_A1")
    print()
    print("Generated:")
    print(" ", OUTPUT_JSON)
    print(" ", OUTPUT_MD)
    print()
    print(
        "No SWIM, runtime controller, trusted policy, "
        "or approved architecture was modified."
    )
    print("=" * 64)


if __name__ == "__main__":
    main()
