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
import evaluate_architecture_alternatives as architecture_evaluator
import validate_architecture_candidates as architecture_validator


# ============================================================
# FILES
# ============================================================

DESIGN_REQUEST_FILE = os.path.join(
    DESIGN_TIME_DIR,
    "config",
    "swim_design_request.json"
)

ALTERNATIVES_FILE = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "architecture_alternatives.json"
)

OUTPUT_FILE = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "design_recovery_run.json"
)

OUTPUT_MD = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "design_recovery_run.md"
)

RECOVERY_DIR = os.path.join(
    DESIGN_TIME_DIR,
    "outputs",
    "design_recovery"
)


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(path):

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
# LLM JSON HANDLING
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


# ============================================================
# CANDIDATE SELECTION
# ============================================================

def find_candidate(
    alternatives_data,
    candidate_id
):

    alternatives = alternatives_data.get(
        "alternatives",
        []
    )


    for candidate in alternatives:

        if candidate.get(
            "id"
        ) == candidate_id:

            return copy.deepcopy(
                candidate
            )


    raise RuntimeError(
        "Candidate not found: "
        + candidate_id
    )


# ============================================================
# CONTROLLED DESIGN-TIME FAULT INJECTION
# ============================================================

def inject_demo_failure(
    candidate
):

    faulty = copy.deepcopy(
        candidate
    )

    runtime = faulty.setdefault(
        "runtime_structure",
        {}
    )


    original_values = {
        "safety_mechanism":
            runtime.get(
                "safety_mechanism"
            ),

        "failure_recovery":
            runtime.get(
                "failure_recovery"
            )
    }


    runtime[
        "safety_mechanism"
    ] = ""

    runtime[
        "failure_recovery"
    ] = ""


    fault = {
        "type":
            "controlled_design_time_fault_injection",

        "target":
            candidate.get(
                "id"
            ),

        "changes": [
            {
                "field":
                    "runtime_structure.safety_mechanism",

                "fault":
                    "removed from isolated candidate copy"
            },

            {
                "field":
                    "runtime_structure.failure_recovery",

                "fault":
                    "removed from isolated candidate copy"
            }
        ],

        "original_values_preserved":
            original_values,

        "production_artifacts_modified":
            False
    }


    return faulty, fault


# ============================================================
# VALIDATION
# ============================================================

def run_validation(
    candidate,
    design_request
):

    deterministic = (
        architecture_validator
        .deterministic_checks(
            candidate,
            design_request
        )
    )


    try:

        llm_result = (
            architecture_validator
            .llm_validation(
                candidate,
                design_request
            )
        )

    except Exception as error:

        llm_result = {
            "status":
                "FAIL",

            "requirement_coverage":
                [],

            "major_strengths":
                [],

            "major_validation_concerns": [
                (
                    "LLM requirement validator "
                    "did not return a usable result: "
                    + str(
                        error
                    )
                )
            ],

            "validation_summary":
                (
                    "Validation could not be "
                    "completed successfully."
                )
        }


    final_status = (
        "PASS"
        if (
            deterministic.get(
                "status"
            ) == "PASS"
            and
            llm_result.get(
                "status"
            ) == "PASS"
        )
        else "FAIL"
    )


    return {
        "deterministic_validation":
            deterministic,

        "llm_requirement_validation":
            llm_result,

        "final_validation_status":
            final_status
    }


# ============================================================
# FAILURE CLASSIFICATION
# ============================================================

def classify_failure(
    validation
):

    deterministic = validation.get(
        "deterministic_validation",
        {}
    )

    llm_result = validation.get(
        "llm_requirement_validation",
        {}
    )


    deterministic_failures = []

    for check in deterministic.get(
        "checks",
        []
    ):

        if check.get(
            "status"
        ) == "FAIL":

            deterministic_failures.append(
                {
                    "check_id":
                        check.get(
                            "check_id"
                        ),

                    "description":
                        check.get(
                            "description"
                        ),

                    "evidence":
                        check.get(
                            "evidence"
                        )
                }
            )


    requirement_failures = []

    for item in llm_result.get(
        "requirement_coverage",
        []
    ):

        status = str(
            item.get(
                "status",
                ""
            )
        ).upper()


        if status in (
            "FAIL",
            "PARTIAL"
        ):

            requirement_failures.append(
                {
                    "item":
                        item.get(
                            "item"
                        ),

                    "status":
                        status,

                    "evidence":
                        item.get(
                            "evidence"
                        ),

                    "concern":
                        item.get(
                            "concern"
                        )
                }
            )


    major_concerns = (
        llm_result.get(
            "major_validation_concerns",
            []
        )
    )

    if not isinstance(
        major_concerns,
        list
    ):

        major_concerns = [
            str(
                major_concerns
            )
        ]


    return {
        "deterministic_failures":
            deterministic_failures,

        "requirement_failures":
            requirement_failures,

        "major_validation_concerns":
            major_concerns
    }


# ============================================================
# FAILURE-AWARE DESIGN REQUEST
# ============================================================

def build_recovery_request(
    design_request,
    failure,
    attempt_number
):

    request = copy.deepcopy(
        design_request
    )

    concerns = request.get(
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


    for item in failure.get(
        "deterministic_failures",
        []
    ):

        concerns.append(
            (
                "Design recovery attempt "
                + str(
                    attempt_number
                )
                + " deterministic validation failure "
                + str(
                    item.get(
                        "check_id"
                    )
                )
                + ": "
                + str(
                    item.get(
                        "description"
                    )
                )
                + ". Evidence: "
                + str(
                    item.get(
                        "evidence"
                    )
                )
            )
        )


    for item in failure.get(
        "requirement_failures",
        []
    ):

        concerns.append(
            (
                "Design recovery attempt "
                + str(
                    attempt_number
                )
                + " requirement validation "
                + str(
                    item.get(
                        "status"
                    )
                )
                + ": "
                + str(
                    item.get(
                        "item"
                    )
                )
                + ". Concern: "
                + str(
                    item.get(
                        "concern"
                    )
                )
            )
        )


    for concern in failure.get(
        "major_validation_concerns",
        []
    ):

        concerns.append(
            (
                "Design recovery validation concern: "
                + str(
                    concern
                )
            )
        )


    request[
        "architectural_concerns"
    ] = concerns


    request[
        "design_recovery_context"
    ] = {
        "attempt":
            attempt_number,

        "purpose":
            (
                "Repair a validation-failing "
                "candidate architecture."
            ),

        "automatic_architecture_approval":
            False,

        "architect_approval_required":
            True
    }


    return request


# ============================================================
# ARCHITECTURE RAG
# ============================================================

def retrieve_recovery_knowledge(
    recovery_request,
    attempt_number
):

    output_path = os.path.join(
        RECOVERY_DIR,
        (
            "attempt_"
            + str(
                attempt_number
            )
            + "_retrieved_knowledge.json"
        )
    )


    original_output = (
        architecture_rag.OUTPUT_FILE
    )


    try:

        architecture_rag.OUTPUT_FILE = (
            output_path
        )

        retrieved = (
            architecture_rag
            .retrieve_architecture_knowledge(
                recovery_request,
                semantic_top_k=8
            )
        )

    finally:

        architecture_rag.OUTPUT_FILE = (
            original_output
        )


    return retrieved, output_path


# ============================================================
# KNOWLEDGE CONTEXT
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
# CANDIDATE SHAPE CHECK
# ============================================================

def validate_candidate_shape(
    candidate,
    original_id,
    design_request
):

    if not isinstance(
        candidate,
        dict
    ):

        raise RuntimeError(
            "Repaired candidate must be "
            "a JSON object."
        )


    if candidate.get(
        "id"
    ) != original_id:

        raise RuntimeError(
            "Recovery changed the candidate ID. "
            "This is not allowed."
        )


    if not isinstance(
        candidate.get(
            "design_time_structure"
        ),
        dict
    ):

        raise RuntimeError(
            "Missing design_time_structure."
        )


    if not isinstance(
        candidate.get(
            "runtime_structure"
        ),
        dict
    ):

        raise RuntimeError(
            "Missing runtime_structure."
        )


    required_attributes = {
        item.get(
            "name"
        )
        for item in design_request.get(
            "quality_attributes",
            []
        )
    }


    actual_attributes = set(
        candidate.get(
            "quality_attribute_rationale",
            {}
        ).keys()
    )


    if (
        required_attributes
        != actual_attributes
    ):

        raise RuntimeError(
            "Recovered candidate does not "
            "preserve the exact required "
            "quality-attribute rationale set."
        )


# ============================================================
# LLM REPAIR
# ============================================================

def repair_candidate(
    candidate,
    failure,
    retrieved,
    design_request,
    attempt_number
):

    knowledge_context = (
        build_knowledge_context(
            retrieved
        )
    )


    prompt = f"""
You are acting as a software architect performing
BOUNDED DESIGN-TIME RECOVERY.

A candidate architecture for the SWIM self-adaptive
system has failed architecture validation.

Your task is to REPAIR the candidate architecture.

This is not architecture selection.

This is not architecture approval.

Make the smallest architecturally justified changes
needed to address the supplied validation failures.

Do not change the candidate ID.

Do not remove valid architectural capabilities merely
to simplify the design.

Do not invent new functional requirements.

Preserve the deterministic safety boundary.

The LLM must never receive direct effector authority.

Trusted runtime constraints must remain outside
generative LLM control.

Human architect approval remains mandatory.

The repaired architecture will be independently
re-evaluated and revalidated after this step.


==================================================
DESIGN REQUEST
==================================================

{json.dumps(
    design_request,
    indent=2
)}


==================================================
CURRENT VALIDATION-FAILING CANDIDATE
==================================================

{json.dumps(
    candidate,
    indent=2
)}


==================================================
VALIDATION FAILURE
==================================================

{json.dumps(
    failure,
    indent=2
)}


==================================================
RETRIEVED ARCHITECTURAL KNOWLEDGE
==================================================

{knowledge_context}


==================================================
RECOVERY ATTEMPT
==================================================

Attempt: {attempt_number}


==================================================
OUTPUT FORMAT
==================================================

Return ONLY valid JSON.

Return exactly:

{{
  "candidate": {{
    "id": "{candidate.get('id')}",
    "name": "candidate name",
    "architectural_style": "architectural style",
    "summary": "architecture summary",

    "design_time_structure": {{
      "components": [
        {{
          "name": "component name",
          "responsibility": "responsibility"
        }}
      ],
      "flow": [
        "step"
      ],
      "architect_role": "explicit human architect role"
    }},

    "runtime_structure": {{
      "control_style": "centralized/decentralized/hybrid",
      "components": [
        {{
          "name": "component name",
          "responsibility": "responsibility"
        }}
      ],
      "adaptation_flow": [
        "step"
      ],
      "safety_mechanism": "deterministic safety mechanism",
      "memory_strategy": "runtime adaptation memory strategy",
      "failure_recovery": "bounded recovery and escalation"
    }},

    "key_patterns_and_tactics": [
      "pattern or tactic"
    ],

    "quality_attribute_rationale": {{
      "performance": "rationale",
      "scalability": "rationale",
      "reliability": "rationale",
      "safety": "rationale",
      "resource_efficiency": "rationale",
      "explainability": "rationale"
    }},

    "advantages": [
      "advantage"
    ],

    "disadvantages": [
      "disadvantage"
    ],

    "risks": [
      "risk"
    ],

    "knowledge_used": [
      "AK identifier"
    ]
  }},

  "repair_summary": {{
    "attempt": {attempt_number},

    "changes": [
      "specific repair"
    ],

    "failures_addressed": [
      "validation failure addressed"
    ],

    "remaining_uncertainties": [
      "remaining uncertainty"
    ]
  }}
}}

Do not return markdown.

Do not approve the candidate.

Do not claim that the repaired candidate has passed
validation before independent validation occurs.
"""


    response = ask_llm(
        prompt
    )


    result = parse_json_response(
        response
    )


    repaired = result.get(
        "candidate"
    )


    validate_candidate_shape(
        repaired,
        candidate.get(
            "id"
        ),
        design_request
    )


    repair_summary = result.get(
        "repair_summary",
        {}
    )


    return repaired, repair_summary


# ============================================================
# SINGLE-CANDIDATE QA EVALUATION
# ============================================================

def evaluate_candidate(
    candidate,
    design_request
):

    quality_attributes = (
        architecture_evaluator
        .get_quality_attributes(
            design_request
        )
    )


    prompt = f"""
You are acting as a software architecture evaluator.

Evaluate ONE candidate architecture for the SWIM
self-adaptive system.

This candidate has undergone a design-time recovery
attempt.

Use ONLY the supplied design request and candidate
architecture.

You are not selecting or approving an architecture.

Score every required quality attribute using:

1 = very poor support
2 = poor support
3 = moderate support
4 = good support
5 = very good support

For every score provide:
- an architecture-specific rationale;
- an important trade-off or limitation.

Do NOT apply the numerical quality-attribute weights.

Python will calculate the weighted score
deterministically.


==================================================
DESIGN REQUEST
==================================================

{json.dumps(
    design_request,
    indent=2
)}


==================================================
CANDIDATE
==================================================

{json.dumps(
    candidate,
    indent=2
)}


==================================================
QUALITY ATTRIBUTES
==================================================

{json.dumps(
    list(
        quality_attributes.keys()
    ),
    indent=2
)}


==================================================
OUTPUT FORMAT
==================================================

Return ONLY valid JSON.

Return:

{{
  "evaluations": [
    {{
      "alternative_id": "{candidate.get('id')}",
      "alternative_name": "{candidate.get('name')}",

      "quality_attribute_scores": {{
        "performance": {{
          "score": 1,
          "rationale": "reason",
          "tradeoff": "trade-off"
        }},
        "scalability": {{
          "score": 1,
          "rationale": "reason",
          "tradeoff": "trade-off"
        }},
        "reliability": {{
          "score": 1,
          "rationale": "reason",
          "tradeoff": "trade-off"
        }},
        "safety": {{
          "score": 1,
          "rationale": "reason",
          "tradeoff": "trade-off"
        }},
        "resource_efficiency": {{
          "score": 1,
          "rationale": "reason",
          "tradeoff": "trade-off"
        }},
        "explainability": {{
          "score": 1,
          "rationale": "reason",
          "tradeoff": "trade-off"
        }}
      }},

      "overall_tradeoff_summary":
        "architecture-level trade-off summary"
    }}
  ]
}}

Do not select or approve the architecture.
"""


    response = ask_llm(
        prompt
    )


    result = parse_json_response(
        response
    )


    evaluation = result.get(
        "evaluations",
        []
    )


    architecture_evaluator.validate_evaluation(
        evaluation,
        [
            candidate
        ],
        quality_attributes
    )


    evaluation = (
        architecture_evaluator
        .calculate_weighted_scores(
            evaluation,
            quality_attributes
        )
    )


    ranked = (
        architecture_evaluator
        .add_ranking(
            evaluation
        )
    )


    return {
        "evaluation_method": {
            "score_minimum":
                1,

            "score_maximum":
                5,

            "weights_defined_by":
                "architect",

            "weighted_score_calculation":
                "deterministic",

            "automatic_architecture_approval":
                False
        },

        "quality_attribute_weights":
            quality_attributes,

        "evaluations":
            ranked
    }


# ============================================================
# MARKDOWN REPORT
# ============================================================

def write_markdown(
    result
):

    lines = []

    lines.append(
        "# Bounded Design-Time Recovery"
    )

    lines.append(
        ""
    )

    lines.append(
        "**Final status:** "
        + str(
            result.get(
                "final_status"
            )
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "**Automatic architecture approval:** No"
    )

    lines.append(
        ""
    )

    lines.append(
        "## Initial Validation"
    )

    lines.append(
        ""
    )

    lines.append(
        "Status: "
        + str(
            result.get(
                "initial_validation",
                {}
            ).get(
                "final_validation_status"
            )
        )
    )

    lines.append(
        ""
    )


    for attempt in result.get(
        "attempts",
        []
    ):

        lines.append(
            "## Recovery Attempt "
            + str(
                attempt.get(
                    "attempt"
                )
            )
        )

        lines.append(
            ""
        )

        lines.append(
            "Validation after repair: **"
            + str(
                attempt.get(
                    "validation",
                    {}
                ).get(
                    "final_validation_status"
                )
            )
            + "**"
        )

        lines.append(
            ""
        )


        evaluation = attempt.get(
            "evaluation",
            {}
        ).get(
            "evaluations",
            []
        )


        if evaluation:

            item = evaluation[0]

            lines.append(
                "Weighted QA score: "
                + str(
                    item.get(
                        "weighted_total"
                    )
                )
                + " / 5.0"
            )

            lines.append(
                ""
            )


        repair_summary = attempt.get(
            "repair_summary",
            {}
        )


        changes = repair_summary.get(
            "changes",
            []
        )


        if changes:

            lines.append(
                "### Repairs"
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


    lines.append(
        "## Authority Boundary"
    )

    lines.append(
        ""
    )

    lines.append(
        "Recovery operates only on an isolated candidate "
        "copy. Passing validation does not constitute "
        "architect approval. The approved architecture, "
        "ADR-001, trusted runtime policies, runtime "
        "controller, and SWIM configuration are unchanged."
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
# RECOVERY LOOP
# ============================================================

def run_recovery(
    candidate_id,
    max_retries,
    inject_failure
):

    design_request = load_json(
        DESIGN_REQUEST_FILE
    )

    alternatives_data = load_json(
        ALTERNATIVES_FILE
    )

    original_candidate = find_candidate(
        alternatives_data,
        candidate_id
    )


    fault_injection = None


    if inject_failure:

        working_candidate, fault_injection = (
            inject_demo_failure(
                original_candidate
            )
        )

    else:

        working_candidate = copy.deepcopy(
            original_candidate
        )


    os.makedirs(
        RECOVERY_DIR,
        exist_ok=True
    )


    save_json(
        os.path.join(
            RECOVERY_DIR,
            "initial_candidate.json"
        ),
        working_candidate
    )


    print()
    print(
        "=============================================="
    )
    print(
        " INITIAL ARCHITECTURE VALIDATION"
    )
    print(
        "=============================================="
    )


    initial_validation = run_validation(
        working_candidate,
        design_request
    )


    print(
        "Initial validation:",
        initial_validation[
            "final_validation_status"
        ]
    )


    attempts = []

    current_candidate = working_candidate

    current_validation = (
        initial_validation
    )


    final_status = None


    if (
        current_validation[
            "final_validation_status"
        ]
        == "PASS"
    ):

        final_status = (
            "INITIAL_CANDIDATE_PASS"
        )


    else:

        for attempt_number in range(
            1,
            max_retries + 1
        ):

            print()
            print(
                "=============================================="
            )
            print(
                " DESIGN RECOVERY ATTEMPT "
                + str(
                    attempt_number
                )
            )
            print(
                "=============================================="
            )


            failure = classify_failure(
                current_validation
            )


            failure_path = os.path.join(
                RECOVERY_DIR,
                (
                    "attempt_"
                    + str(
                        attempt_number
                    )
                    + "_failure.json"
                )
            )

            save_json(
                failure_path,
                failure
            )


            recovery_request = (
                build_recovery_request(
                    design_request,
                    failure,
                    attempt_number
                )
            )


            request_path = os.path.join(
                RECOVERY_DIR,
                (
                    "attempt_"
                    + str(
                        attempt_number
                    )
                    + "_request.json"
                )
            )

            save_json(
                request_path,
                recovery_request
            )


            print(
                "Retrieving architecture knowledge..."
            )


            retrieved, retrieval_path = (
                retrieve_recovery_knowledge(
                    recovery_request,
                    attempt_number
                )
            )


            print(
                "Retrieved entries:",
                len(
                    retrieved
                )
            )


            print(
                "Repairing candidate with LLM..."
            )


            repaired_candidate, repair_summary = (
                repair_candidate(
                    current_candidate,
                    failure,
                    retrieved,
                    design_request,
                    attempt_number
                )
            )


            candidate_path = os.path.join(
                RECOVERY_DIR,
                (
                    "attempt_"
                    + str(
                        attempt_number
                    )
                    + "_candidate.json"
                )
            )


            save_json(
                candidate_path,
                repaired_candidate
            )


            print(
                "Re-evaluating quality attributes..."
            )


            evaluation = evaluate_candidate(
                repaired_candidate,
                design_request
            )


            evaluation_path = os.path.join(
                RECOVERY_DIR,
                (
                    "attempt_"
                    + str(
                        attempt_number
                    )
                    + "_evaluation.json"
                )
            )


            save_json(
                evaluation_path,
                evaluation
            )


            print(
                "Revalidating repaired candidate..."
            )


            validation = run_validation(
                repaired_candidate,
                design_request
            )


            validation_path = os.path.join(
                RECOVERY_DIR,
                (
                    "attempt_"
                    + str(
                        attempt_number
                    )
                    + "_validation.json"
                )
            )


            save_json(
                validation_path,
                validation
            )


            evaluation_items = (
                evaluation.get(
                    "evaluations",
                    []
                )
            )


            weighted_total = None


            if evaluation_items:

                weighted_total = (
                    evaluation_items[0].get(
                        "weighted_total"
                    )
                )


            attempt_record = {
                "attempt":
                    attempt_number,

                "failure_input":
                    failure,

                "retrieved_knowledge_count":
                    len(
                        retrieved
                    ),

                "retrieved_knowledge_ids": [
                    item.get(
                        "knowledge",
                        {}
                    ).get(
                        "id"
                    )
                    for item in retrieved
                ],

                "repair_summary":
                    repair_summary,

                "evaluation":
                    evaluation,

                "weighted_total":
                    weighted_total,

                "validation":
                    validation,

                "artifacts": {
                    "failure":
                        os.path.relpath(
                            failure_path,
                            PROJECT_DIR
                        ),

                    "recovery_request":
                        os.path.relpath(
                            request_path,
                            PROJECT_DIR
                        ),

                    "retrieval":
                        os.path.relpath(
                            retrieval_path,
                            PROJECT_DIR
                        ),

                    "candidate":
                        os.path.relpath(
                            candidate_path,
                            PROJECT_DIR
                        ),

                    "evaluation":
                        os.path.relpath(
                            evaluation_path,
                            PROJECT_DIR
                        ),

                    "validation":
                        os.path.relpath(
                            validation_path,
                            PROJECT_DIR
                        )
                }
            }


            attempts.append(
                attempt_record
            )


            print(
                "Weighted QA score:",
                weighted_total
            )

            print(
                "Validation after repair:",
                validation[
                    "final_validation_status"
                ]
            )


            current_candidate = (
                repaired_candidate
            )

            current_validation = (
                validation
            )


            if (
                validation[
                    "final_validation_status"
                ]
                == "PASS"
            ):

                final_status = (
                    "RECOVERED_PASS"
                )

                break


        if final_status is None:

            final_status = (
                "RECOVERY_EXHAUSTED"
            )


    final_candidate_path = os.path.join(
        RECOVERY_DIR,
        "final_candidate.json"
    )


    save_json(
        final_candidate_path,
        current_candidate
    )


    result = {
        "run_type":
            (
                "controlled_design_time_fault_injection"
                if inject_failure
                else
                "design_time_validation_recovery"
            ),

        "schema_version":
            "1.0",

        "generated_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "candidate_id":
            candidate_id,

        "max_retries":
            max_retries,

        "fault_injection":
            fault_injection,

        "initial_validation":
            initial_validation,

        "attempts":
            attempts,

        "attempt_count":
            len(
                attempts
            ),

        "final_validation":
            current_validation,

        "final_status":
            final_status,

        "authority_boundary": {
            "automatic_architecture_approval":
                False,

            "approved_architecture_modified":
                False,

            "ADR_001_modified":
                False,

            "trusted_policy_modified":
                False,

            "runtime_controller_modified":
                False,

            "SWIM_modified":
                False,

            "human_architect_approval_required":
                True
        },

        "final_candidate_artifact":
            os.path.relpath(
                final_candidate_path,
                PROJECT_DIR
            )
    }


    save_json(
        OUTPUT_FILE,
        result
    )

    write_markdown(
        result
    )


    return result


# ============================================================
# COMMAND LINE
# ============================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Bounded design-time architecture "
            "recovery after validation failure."
        )
    )


    parser.add_argument(
        "--candidate",
        default="A1",
        help=(
            "Candidate architecture ID. "
            "Default: A1"
        )
    )


    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help=(
            "Maximum bounded recovery attempts. "
            "Default: 2"
        )
    )


    parser.add_argument(
        "--inject-demo-failure",
        action="store_true",
        help=(
            "Inject a controlled validation fault "
            "into an isolated candidate copy."
        )
    )


    parser.add_argument(
        "--confirm-run",
        action="store_true",
        help=(
            "Explicitly authorize API-backed "
            "design-time recovery execution."
        )
    )


    return parser.parse_args()


# ============================================================
# MAIN
# ============================================================

def main():

    args = parse_args()


    if args.max_retries < 1:

        raise RuntimeError(
            "--max-retries must be at least 1."
        )


    print(
        "=============================================="
    )
    print(
        " BOUNDED DESIGN-TIME ARCHITECTURE RECOVERY"
    )
    print(
        "=============================================="
    )
    print()
    print(
        "This component is DESIGN-TIME ONLY."
    )
    print(
        "It does NOT start or modify SWIM."
    )
    print(
        "It does NOT execute runtime adaptations."
    )
    print(
        "It does NOT modify trusted policies."
    )
    print(
        "It does NOT modify the approved A1 artifact."
    )
    print(
        "It does NOT supersede ADR-001."
    )
    print(
        "It does NOT automatically approve architecture."
    )
    print()


    if not args.confirm_run:

        print(
            "No recovery run started."
        )
        print()
        print(
            "An API-backed recovery run requires:"
        )
        print()
        print(
            "  --confirm-run"
        )
        print()
        print(
            "No LLM or embedding API call was performed."
        )

        return


    if args.inject_demo_failure:

        print(
            "CONTROLLED FAULT-INJECTION MODE:"
        )
        print(
            "Safety-mechanism and failure-recovery "
            "descriptions will be removed ONLY from "
            "an isolated in-memory copy of "
            + args.candidate
            + "."
        )
        print()


    result = run_recovery(
        candidate_id=args.candidate,
        max_retries=args.max_retries,
        inject_failure=args.inject_demo_failure
    )


    print()
    print(
        "=============================================="
    )
    print(
        " DESIGN RECOVERY COMPLETE"
    )
    print(
        "=============================================="
    )
    print()
    print(
        "Candidate:",
        result[
            "candidate_id"
        ]
    )
    print(
        "Initial validation:",
        result[
            "initial_validation"
        ][
            "final_validation_status"
        ]
    )
    print(
        "Recovery attempts:",
        result[
            "attempt_count"
        ]
    )
    print(
        "Final validation:",
        result[
            "final_validation"
        ][
            "final_validation_status"
        ]
    )
    print(
        "Final status:",
        result[
            "final_status"
        ]
    )
    print()
    print(
        "Automatic approval: False"
    )
    print(
        "Approved A1 modified: False"
    )
    print(
        "ADR-001 modified: False"
    )
    print(
        "Trusted policies modified: False"
    )
    print(
        "SWIM modified: False"
    )
    print()
    print(
        "Generated:"
    )
    print(
        " ",
        OUTPUT_FILE
    )
    print(
        " ",
        OUTPUT_MD
    )
    print(
        " ",
        RECOVERY_DIR
    )


if __name__ == "__main__":
    main()
