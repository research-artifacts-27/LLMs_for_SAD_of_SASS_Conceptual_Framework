#!/usr/bin/env python3

import argparse
import copy
import json
import os
import sys
from datetime import datetime, timezone


# ============================================================
# PROJECT PATHS
# ============================================================

DESIGN_TIME_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_DIR = os.path.dirname(
    DESIGN_TIME_DIR
)

if PROJECT_DIR not in sys.path:
    sys.path.insert(
        0,
        PROJECT_DIR
    )

if DESIGN_TIME_DIR not in sys.path:
    sys.path.insert(
        0,
        DESIGN_TIME_DIR
    )


from llm_client import ask_llm
import architecture_rag


DESIGN_REQUEST_FILE = os.path.join(
    DESIGN_TIME_DIR,
    "config",
    "swim_design_request.json"
)

RUNTIME_FEEDBACK_FILE = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "runtime_design_feedback.json"
)

ARCHITECT_DECISION_FILE = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "architect_decision.json"
)

ALTERNATIVES_FILE = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "architecture_alternatives.json"
)

EVALUATION_FILE = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "architecture_evaluation.json"
)

RECOMMENDATION_FILE = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "architecture_recommendation.json"
)

VALIDATION_FILE = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "architecture_validation.json"
)

ADR_FILE = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "ADR-001.json"
)

AUGMENTED_REQUEST_FILE = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "architecture_reconsideration_request.json"
)

REVIEW_RETRIEVAL_FILE = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "architecture_reconsideration_retrieved_knowledge.json"
)

OUTPUT_JSON = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "architecture_reconsideration.json"
)

OUTPUT_MD = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "architecture_reconsideration.md"
)


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(
    path,
    required=True,
    default=None
):

    if not os.path.exists(
        path
    ):

        if required:

            raise FileNotFoundError(
                "Required file not found: "
                + path
            )

        return default


    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(
            file
        )


def save_json(
    path,
    data
):

    os.makedirs(
        os.path.dirname(
            path
        ),
        exist_ok=True
    )

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


# ============================================================
# RUNTIME FEEDBACK
# ============================================================

def get_review_triggers(
    feedback
):

    review = feedback.get(
        "architecture_review",
        {}
    )

    triggers = review.get(
        "triggers",
        []
    )

    if not isinstance(
        triggers,
        list
    ):

        return []

    return [
        item
        for item in triggers
        if isinstance(
            item,
            dict
        )
    ]


def build_runtime_feedback_context(
    feedback
):

    review = feedback.get(
        "architecture_review",
        {}
    )

    summary = feedback.get(
        "summary",
        {}
    )

    triggers = get_review_triggers(
        feedback
    )


    context = {
        "review_recommended":
            review.get(
                "review_recommended",
                False
            ),

        "trigger_count":
            len(
                triggers
            ),

        "triggers":
            triggers,

        "runtime_summary": {
            "episodes_with_final_qos_violation":
                summary.get(
                    "episodes_with_final_qos_violation"
                ),

            "episodes_with_qos_violation_at_max_capacity":
                summary.get(
                    "episodes_with_qos_violation_at_max_capacity"
                ),

            "episodes_with_safety_rejection":
                summary.get(
                    "episodes_with_safety_rejection"
                ),

            "episodes_with_recovery_attempts":
                summary.get(
                    "episodes_with_recovery_attempts"
                ),

            "episodes_with_fail_safe":
                summary.get(
                    "episodes_with_fail_safe"
                ),

            "execution_outcomes":
                summary.get(
                    "execution_outcomes",
                    {}
                )
        },

        "data_quality_notes":
            feedback.get(
                "data_quality_notes",
                []
            )
    }


    return context


# ============================================================
# AUGMENT DESIGN REQUEST FOR RAG
# ============================================================

def augment_design_request(
    design_request,
    runtime_feedback
):

    augmented = copy.deepcopy(
        design_request
    )

    triggers = get_review_triggers(
        runtime_feedback
    )


    concerns = augmented.get(
        "architectural_concerns",
        []
    )

    if not isinstance(
        concerns,
        list
    ):

        concerns = []


    concerns = list(
        concerns
    )


    for trigger in triggers:

        trigger_id = str(
            trigger.get(
                "id",
                "UNKNOWN"
            )
        )

        title = str(
            trigger.get(
                "title",
                ""
            )
        )

        interpretation = str(
            trigger.get(
                "interpretation",
                ""
            )
        )

        design_question = str(
            trigger.get(
                "design_review_question",
                ""
            )
        )


        concern = (
            "Runtime evidence "
            + trigger_id
            + ": "
            + title
            + ". "
            + interpretation
            + " Review question: "
            + design_question
        )

        concerns.append(
            concern
        )


    augmented[
        "architectural_concerns"
    ] = concerns


    augmented[
        "runtime_evidence_review"
    ] = {
        "source":
            "runtime_design_feedback.json",

        "review_recommended":
            runtime_feedback.get(
                "architecture_review",
                {}
            ).get(
                "review_recommended",
                False
            ),

        "trigger_ids": [
            trigger.get(
                "id"
            )
            for trigger in triggers
        ],

        "human_review_required":
            True,

        "automatic_redesign":
            False
    }


    return augmented


# ============================================================
# RETRIEVED KNOWLEDGE AS LLM CONTEXT
# ============================================================

def build_knowledge_context(
    retrieved
):

    parts = []


    for item in retrieved:

        knowledge = item.get(
            "knowledge",
            {}
        )


        parts.append(
            "\n".join(
                [
                    (
                        "ID: "
                        + str(
                            knowledge.get(
                                "id"
                            )
                        )
                    ),

                    (
                        "Name: "
                        + str(
                            knowledge.get(
                                "name"
                            )
                        )
                    ),

                    (
                        "Category: "
                        + str(
                            knowledge.get(
                                "category"
                            )
                        )
                    ),

                    (
                        "Description: "
                        + str(
                            knowledge.get(
                                "description"
                            )
                        )
                    ),

                    (
                        "Benefits: "
                        + "; ".join(
                            knowledge.get(
                                "benefits",
                                []
                            )
                        )
                    ),

                    (
                        "Trade-offs: "
                        + "; ".join(
                            knowledge.get(
                                "tradeoffs",
                                []
                            )
                        )
                    ),

                    (
                        "Constraints: "
                        + "; ".join(
                            knowledge.get(
                                "constraints",
                                []
                            )
                        )
                    ),

                    (
                        "Selection reasons: "
                        + ", ".join(
                            item.get(
                                "selection_reasons",
                                []
                            )
                        )
                    ),

                    (
                        "Requirement reason: "
                        + str(
                            item.get(
                                "requirement_reason"
                            )
                        )
                    ),

                    (
                        "Provenance class: "
                        + str(
                            knowledge.get(
                                "provenance_class",
                                "unclassified"
                            )
                        )
                    ),

                    (
                        "Provenance references: "
                        + ", ".join(
                            knowledge.get(
                                "provenance_refs",
                                []
                            )
                        )
                    ),

                    (
                        "Provenance note: "
                        + str(
                            knowledge.get(
                                "provenance_note",
                                ""
                            )
                        )
                    )
                ]
            )
        )


    return "\n\n---\n\n".join(
        parts
    )


# ============================================================
# LLM RESPONSE HANDLING
# ============================================================

def parse_json_response(
    response
):

    cleaned = response.strip()


    if cleaned.startswith(
        "```json"
    ):

        cleaned = cleaned[
            len(
                "```json"
            ):
        ].strip()


    elif cleaned.startswith(
        "```"
    ):

        cleaned = cleaned[
            3:
        ].strip()


    if cleaned.endswith(
        "```"
    ):

        cleaned = cleaned[
            :-3
        ].strip()


    return json.loads(
        cleaned
    )


def validate_llm_review(
    result
):

    if not isinstance(
        result,
        dict
    ):

        raise RuntimeError(
            "Architecture reconsideration "
            "must be a JSON object."
        )


    options = result.get(
        "review_options",
        []
    )


    if not isinstance(
        options,
        list
    ):

        raise RuntimeError(
            "review_options must be a list."
        )


    if len(
        options
    ) != 3:

        raise RuntimeError(
            "Expected exactly three "
            "architecture review options."
        )


    expected_ids = {
        "R1",
        "R2",
        "R3"
    }

    actual_ids = {
        str(
            option.get(
                "id"
            )
        )
        for option in options
    }


    if actual_ids != expected_ids:

        raise RuntimeError(
            "Review options must have IDs "
            "R1, R2, and R3."
        )


    expected_dispositions = {
        "retain_current",
        "revise_current",
        "reopen_selection"
    }

    actual_dispositions = {
        str(
            option.get(
                "disposition"
            )
        )
        for option in options
    }


    if actual_dispositions != (
        expected_dispositions
    ):

        raise RuntimeError(
            "The three review options must "
            "cover retain_current, "
            "revise_current, and "
            "reopen_selection exactly once."
        )


# ============================================================
# HUMAN-TRIGGERED LLM ARCHITECTURE REVIEW
# ============================================================

def run_reconsideration(
    human_reason
):

    design_request = load_json(
        DESIGN_REQUEST_FILE
    )

    runtime_feedback = load_json(
        RUNTIME_FEEDBACK_FILE
    )

    architect_decision = load_json(
        ARCHITECT_DECISION_FILE
    )

    alternatives = load_json(
        ALTERNATIVES_FILE
    )

    evaluation = load_json(
        EVALUATION_FILE,
        required=False,
        default={}
    )

    recommendation = load_json(
        RECOMMENDATION_FILE,
        required=False,
        default={}
    )

    validation = load_json(
        VALIDATION_FILE,
        required=False,
        default={}
    )

    adr = load_json(
        ADR_FILE,
        required=False,
        default={}
    )


    triggers = get_review_triggers(
        runtime_feedback
    )


    augmented_request = (
        augment_design_request(
            design_request,
            runtime_feedback
        )
    )


    save_json(
        AUGMENTED_REQUEST_FILE,
        augmented_request
    )


    print()
    print(
        "=============================================="
    )
    print(
        " HUMAN-TRIGGERED ARCHITECTURE RECONSIDERATION"
    )
    print(
        "=============================================="
    )
    print()
    print(
        "Human review initiation confirmed."
    )
    print(
        "Runtime review triggers:",
        len(
            triggers
        )
    )
    print()
    print(
        "Running Architecture RAG using the "
        "original design request plus runtime "
        "evidence concerns..."
    )


    original_rag_output = (
        architecture_rag.OUTPUT_FILE
    )


    try:

        architecture_rag.OUTPUT_FILE = (
            REVIEW_RETRIEVAL_FILE
        )

        retrieved = (
            architecture_rag
            .retrieve_architecture_knowledge(
                augmented_request,
                semantic_top_k=8
            )
        )

    finally:

        architecture_rag.OUTPUT_FILE = (
            original_rag_output
        )


    knowledge_context = (
        build_knowledge_context(
            retrieved
        )
    )

    runtime_context = (
        build_runtime_feedback_context(
            runtime_feedback
        )
    )


    print()
    print(
        "Architecture knowledge retrieved:",
        len(
            retrieved
        )
    )
    print()
    print(
        "Requesting LLM-supported "
        "architecture reconsideration..."
    )


    prompt = f"""
You are acting as a software architecture
decision-support assistant.

This is a HUMAN-TRIGGERED reconsideration of an
already approved software architecture for a
Self-Adaptive Software System.

The managed exemplar is SWIM.

You are NOT authorized to approve, deploy, or
enact a new architecture.

The human architect retains final decision
authority.

The existing approved design must be treated as
the current baseline unless the human architect
later approves a change.


==================================================
ORIGINAL DESIGN REQUEST
==================================================

{json.dumps(
    design_request,
    indent=2
)}


==================================================
CURRENT ARCHITECT DECISION
==================================================

{json.dumps(
    architect_decision,
    indent=2
)}


==================================================
CURRENT ARCHITECTURE ALTERNATIVES
==================================================

{json.dumps(
    alternatives,
    indent=2
)}


==================================================
ORIGINAL EVALUATION
==================================================

{json.dumps(
    evaluation,
    indent=2
)}


==================================================
ORIGINAL RECOMMENDATION
==================================================

{json.dumps(
    recommendation,
    indent=2
)}


==================================================
ORIGINAL VALIDATION
==================================================

{json.dumps(
    validation,
    indent=2
)}


==================================================
CURRENT ADR
==================================================

{json.dumps(
    adr,
    indent=2
)}


==================================================
ACCUMULATED RUNTIME EVIDENCE
==================================================

{json.dumps(
    runtime_context,
    indent=2
)}


==================================================
ARCHITECTURAL KNOWLEDGE RETRIEVED FOR REVIEW
==================================================

{knowledge_context}


==================================================
HUMAN REASON FOR INITIATING REVIEW
==================================================

{human_reason}


==================================================
REVIEW RULES
==================================================

The runtime evidence is evidence for review,
not proof that the current architecture is wrong.

Do not infer causality that is not supported by
the supplied evidence.

Some runtime evidence may originate from
controlled fault-injection experiments. If
provenance is not explicitly available, say so
instead of guessing.

Hard runtime constraints remain outside the
generative LLM.

Trusted runtime policies must not be changed by
the LLM.

The LLM must not directly invoke effectors.

The existing deterministic safety boundary must
be preserved.

Human architect approval remains mandatory.

A runtime symptom may justify:
1. retaining the current architecture,
2. revising the current architecture, or
3. reopening architectural selection.

For the observed repeated PARTIAL outcomes,
consider whether the evidence supports examining
multi-step planning, adaptation magnitude,
planning horizon, sequencing, or another
architectural response.

Do NOT claim that a proposed change has been
implemented or evaluated.

Do NOT overwrite the current architecture.

Do NOT make a final architecture decision.


==================================================
OUTPUT FORMAT
==================================================

Return ONLY valid JSON.

Return an object with this exact top-level
structure:

{{
  "current_architecture_assessment": {{
    "summary":
      "assessment of the current approved design",

    "runtime_evidence_interpretation":
      "what the evidence supports and does not support",

    "strengths_to_preserve": [
      "strength"
    ],

    "concerns_for_review": [
      "concern"
    ]
  }},

  "review_options": [

    {{
      "id": "R1",

      "disposition":
        "retain_current",

      "name":
        "short option name",

      "description":
        "what retaining the design means",

      "architectural_changes": [],

      "runtime_implications": [
        "implication"
      ],

      "quality_attribute_implications": {{
        "performance":
          "expected implication",

        "scalability":
          "expected implication",

        "reliability":
          "expected implication",

        "safety":
          "expected implication",

        "resource_efficiency":
          "expected implication",

        "explainability":
          "expected implication"
      }},

      "addresses_runtime_triggers": [
        "RTD-02"
      ],

      "knowledge_used": [
        "AK1"
      ],

      "advantages": [
        "advantage"
      ],

      "risks": [
        "risk"
      ],

      "validation_needed": [
        "future validation activity"
      ]
    }},

    {{
      "id": "R2",

      "disposition":
        "revise_current",

      "name":
        "short option name",

      "description":
        "bounded revision of the current architecture",

      "architectural_changes": [
        "specific proposed design change"
      ],

      "runtime_implications": [
        "implication"
      ],

      "quality_attribute_implications": {{
        "performance":
          "expected implication",

        "scalability":
          "expected implication",

        "reliability":
          "expected implication",

        "safety":
          "expected implication",

        "resource_efficiency":
          "expected implication",

        "explainability":
          "expected implication"
      }},

      "addresses_runtime_triggers": [
        "RTD-02"
      ],

      "knowledge_used": [
        "AK1"
      ],

      "advantages": [
        "advantage"
      ],

      "risks": [
        "risk"
      ],

      "validation_needed": [
        "future validation activity"
      ]
    }},

    {{
      "id": "R3",

      "disposition":
        "reopen_selection",

      "name":
        "short option name",

      "description":
        "alternative architecture or larger redesign",

      "architectural_changes": [
        "specific proposed design change"
      ],

      "runtime_implications": [
        "implication"
      ],

      "quality_attribute_implications": {{
        "performance":
          "expected implication",

        "scalability":
          "expected implication",

        "reliability":
          "expected implication",

        "safety":
          "expected implication",

        "resource_efficiency":
          "expected implication",

        "explainability":
          "expected implication"
      }},

      "addresses_runtime_triggers": [
        "RTD-02"
      ],

      "knowledge_used": [
        "AK1"
      ],

      "advantages": [
        "advantage"
      ],

      "risks": [
        "risk"
      ],

      "validation_needed": [
        "future validation activity"
      ]
    }}

  ],

  "llm_recommendation": {{
    "option_id":
      "R1 or R2 or R3",

    "reason":
      "advisory reasoning only",

    "confidence":
      "low, medium, or high",

    "limitations": [
      "limitation"
    ]
  }}
}}

Generate exactly THREE review options.

R1 must use disposition:
retain_current

R2 must use disposition:
revise_current

R3 must use disposition:
reopen_selection

The recommendation is advisory only.

Do not state that any option is approved.

Do not state that any option has been
implemented.

Do not state that the architecture has changed.
"""


    response = ask_llm(
        prompt
    )


    try:

        llm_result = (
            parse_json_response(
                response
            )
        )

    except json.JSONDecodeError:

        print()
        print(
            "ERROR:"
        )
        print(
            "The LLM did not return valid JSON."
        )
        print()
        print(
            "Raw response:"
        )
        print(
            response
        )

        raise


    validate_llm_review(
        llm_result
    )


    trigger_ids = [
        trigger.get(
            "id"
        )
        for trigger in triggers
    ]


    final_result = {
        "review_type":
            "human_triggered_architecture_reconsideration",

        "schema_version":
            "1.0",

        "generated_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "human_trigger": {
            "confirmed":
                True,

            "automatic":
                False,

            "reason":
                human_reason
        },

        "runtime_feedback": {
            "source":
                os.path.relpath(
                    RUNTIME_FEEDBACK_FILE,
                    PROJECT_DIR
                ),

            "review_recommended":
                runtime_feedback.get(
                    "architecture_review",
                    {}
                ).get(
                    "review_recommended",
                    False
                ),

            "trigger_ids":
                trigger_ids,

            "trigger_count":
                len(
                    trigger_ids
                )
        },

        "retrieval": {
            "method":
                "existing hybrid architecture RAG",

            "semantic_top_k":
                8,

            "retrieved_entry_count":
                len(
                    retrieved
                ),

            "output":
                os.path.relpath(
                    REVIEW_RETRIEVAL_FILE,
                    PROJECT_DIR
                )
        },

        "llm_review":
            llm_result,

        "authority_boundary": {
            "automatic_redesign":
                False,

            "automatic_architecture_approval":
                False,

            "automatic_policy_change":
                False,

            "automatic_runtime_deployment":
                False,

            "human_architect_approval_required":
                True
        },

        "architect_status":
            "PENDING_REVIEW"
    }


    save_json(
        OUTPUT_JSON,
        final_result
    )


    write_markdown(
        final_result
    )


    return final_result


# ============================================================
# HUMAN-READABLE REVIEW
# ============================================================

def write_markdown(
    result
):

    llm_review = result.get(
        "llm_review",
        {}
    )

    assessment = llm_review.get(
        "current_architecture_assessment",
        {}
    )

    options = llm_review.get(
        "review_options",
        []
    )

    recommendation = llm_review.get(
        "llm_recommendation",
        {}
    )


    lines = []

    lines.append(
        "# Human-Triggered Architecture Reconsideration"
    )

    lines.append(
        ""
    )

    lines.append(
        "Status: **PENDING HUMAN ARCHITECT REVIEW**"
    )

    lines.append(
        ""
    )

    lines.append(
        "No architecture has been changed or approved by this review."
    )

    lines.append(
        ""
    )

    lines.append(
        "## Runtime Evidence"
    )

    lines.append(
        ""
    )

    trigger_ids = result.get(
        "runtime_feedback",
        {}
    ).get(
        "trigger_ids",
        []
    )

    lines.append(
        "Triggers: "
        + (
            ", ".join(
                str(
                    item
                )
                for item in trigger_ids
            )
            if trigger_ids
            else "None"
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "## Current Architecture Assessment"
    )

    lines.append(
        ""
    )

    lines.append(
        str(
            assessment.get(
                "summary",
                ""
            )
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "### Runtime Evidence Interpretation"
    )

    lines.append(
        ""
    )

    lines.append(
        str(
            assessment.get(
                "runtime_evidence_interpretation",
                ""
            )
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "## Review Options"
    )

    lines.append(
        ""
    )


    for option in options:

        lines.append(
            "### "
            + str(
                option.get(
                    "id",
                    ""
                )
            )
            + " — "
            + str(
                option.get(
                    "name",
                    ""
                )
            )
        )

        lines.append(
            ""
        )

        lines.append(
            "**Disposition:** "
            + str(
                option.get(
                    "disposition",
                    ""
                )
            )
        )

        lines.append(
            ""
        )

        lines.append(
            str(
                option.get(
                    "description",
                    ""
                )
            )
        )

        lines.append(
            ""
        )

        changes = option.get(
            "architectural_changes",
            []
        )

        if changes:

            lines.append(
                "**Proposed architectural changes:**"
            )

            lines.append(
                ""
            )

            for change in changes:

                lines.append(
                    "- "
                    + str(
                        change
                    )
                )

            lines.append(
                ""
            )


        risks = option.get(
            "risks",
            []
        )

        if risks:

            lines.append(
                "**Risks:**"
            )

            lines.append(
                ""
            )

            for risk in risks:

                lines.append(
                    "- "
                    + str(
                        risk
                    )
                )

            lines.append(
                ""
            )


        validation = option.get(
            "validation_needed",
            []
        )

        if validation:

            lines.append(
                "**Validation needed before any approval:**"
            )

            lines.append(
                ""
            )

            for item in validation:

                lines.append(
                    "- "
                    + str(
                        item
                    )
                )

            lines.append(
                ""
            )


    lines.append(
        "## LLM Advisory Recommendation"
    )

    lines.append(
        ""
    )

    lines.append(
        "Option: "
        + str(
            recommendation.get(
                "option_id",
                ""
            )
        )
    )

    lines.append(
        ""
    )

    lines.append(
        str(
            recommendation.get(
                "reason",
                ""
            )
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "Confidence: "
        + str(
            recommendation.get(
                "confidence",
                ""
            )
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "## Authority Boundary"
    )

    lines.append(
        ""
    )

    lines.append(
        "This artifact is decision support only. "
        "The human architect must explicitly decide "
        "whether to retain, revise, or reopen the "
        "architecture. No trusted runtime policy, "
        "approved architecture, SWIM configuration, "
        "or runtime controller is modified."
    )

    lines.append(
        ""
    )


    with open(
        OUTPUT_MD,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(
                lines
            )
        )


# ============================================================
# COMMAND LINE
# ============================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Human-triggered architecture "
            "reconsideration using runtime "
            "evidence and Architecture RAG."
        )
    )

    parser.add_argument(
        "--confirm-review",
        action="store_true",
        help=(
            "Explicitly confirm that the "
            "human architect wants to initiate "
            "the architecture review."
        )
    )

    parser.add_argument(
        "--reason",
        default=(
            "Review accumulated runtime evidence "
            "and determine whether the approved "
            "architecture should be retained, "
            "revised, or reconsidered."
        ),
        help=(
            "Human-provided reason for initiating "
            "the architecture review."
        )
    )

    return parser.parse_args()


# ============================================================
# MAIN
# ============================================================

def main():

    args = parse_args()


    print(
        "=============================================="
    )
    print(
        " ARCHITECTURE RECONSIDERATION"
    )
    print(
        "=============================================="
    )
    print()
    print(
        "This component is design-time only."
    )
    print(
        "It does NOT start or modify SWIM."
    )
    print(
        "It does NOT execute runtime adaptations."
    )
    print(
        "It does NOT change trusted policies."
    )
    print(
        "It does NOT automatically approve "
        "or deploy an architecture."
    )
    print()


    if not args.confirm_review:

        print(
            "No review started."
        )
        print()
        print(
            "A human-triggered review requires "
            "the explicit flag:"
        )
        print()
        print(
            "  --confirm-review"
        )
        print()
        print(
            "No API call or architecture "
            "reconsideration was performed."
        )

        return


    result = run_reconsideration(
        args.reason
    )


    print()
    print(
        "=============================================="
    )
    print(
        " ARCHITECTURE RECONSIDERATION COMPLETE"
    )
    print(
        "=============================================="
    )

    print()
    print(
        "Runtime trigger IDs:",
        ", ".join(
            str(
                item
            )
            for item in result[
                "runtime_feedback"
            ][
                "trigger_ids"
            ]
        )
    )

    print(
        "Retrieved architecture entries:",
        result[
            "retrieval"
        ][
            "retrieved_entry_count"
        ]
    )


    review = result[
        "llm_review"
    ]

    print()
    print(
        "Generated review options:"
    )


    for option in review.get(
        "review_options",
        []
    ):

        print(
            "  "
            + str(
                option.get(
                    "id"
                )
            )
            + " | "
            + str(
                option.get(
                    "disposition"
                )
            )
            + " | "
            + str(
                option.get(
                    "name"
                )
            )
        )


    recommendation = review.get(
        "llm_recommendation",
        {}
    )

    print()
    print(
        "LLM advisory recommendation:",
        recommendation.get(
            "option_id"
        )
    )

    print(
        "Human architect status:",
        result[
            "architect_status"
        ]
    )

    print()
    print(
        "Generated:"
    )
    print(
        "  "
        + OUTPUT_JSON
    )
    print(
        "  "
        + OUTPUT_MD
    )
    print(
        "  "
        + REVIEW_RETRIEVAL_FILE
    )
    print(
        "  "
        + AUGMENTED_REQUEST_FILE
    )

    print()
    print(
        "No approved architecture, trusted "
        "policy, or SWIM configuration was changed."
    )


if __name__ == "__main__":
    main()
