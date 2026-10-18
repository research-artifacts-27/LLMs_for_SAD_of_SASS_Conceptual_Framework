import json
import os
import sys


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if PROJECT_DIR not in sys.path:
    sys.path.insert(
        0,
        PROJECT_DIR
    )


from llm_client import ask_llm


# ============================================================
# FILES
# ============================================================

DESIGN_REQUEST_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "config",
    "swim_design_request.json"
)

ALTERNATIVES_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "architecture_alternatives.json"
)

EVALUATION_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "architecture_evaluation.json"
)

OUTPUT_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "architecture_validation.json"
)


# ============================================================
# HELPERS
# ============================================================

def load_json(path):

    with open(
        path,
        "r"
    ) as file:

        return json.load(file)


# ============================================================
# DETERMINISTIC STRUCTURAL CHECKS
# ============================================================

def deterministic_checks(
    alternative,
    design_request
):

    runtime = alternative.get(
        "runtime_structure",
        {}
    )

    design_time = alternative.get(
        "design_time_structure",
        {}
    )

    runtime_components = runtime.get(
        "components",
        []
    )

    design_components = design_time.get(
        "components",
        []
    )

    runtime_text = json.dumps(
        runtime,
        default=str
    ).lower()

    design_text = json.dumps(
        design_time,
        default=str
    ).lower()

    full_text = (
        runtime_text
        + " "
        + design_text
        + " "
        + json.dumps(
            alternative,
            default=str
        ).lower()
    )


    checks = []


    def add_check(
        check_id,
        description,
        passed,
        evidence
    ):

        checks.append(
            {
                "check_id":
                    check_id,

                "description":
                    description,

                "status":
                    (
                        "PASS"
                        if passed
                        else "FAIL"
                    ),

                "evidence":
                    evidence
            }
        )


    # --------------------------------------------------------
    # CHECK 1 — DESIGN-TIME COMPONENTS
    # --------------------------------------------------------

    add_check(
        "C1",
        "Architecture contains explicit design-time structure.",
        len(design_components) > 0,
        (
            f"Design-time components found: "
            f"{len(design_components)}"
        )
    )


    # --------------------------------------------------------
    # CHECK 2 — RUNTIME CONTROLLER
    # --------------------------------------------------------

    add_check(
        "C2",
        "Architecture contains explicit runtime adaptation structure.",
        len(runtime_components) > 0,
        (
            f"Runtime components found: "
            f"{len(runtime_components)}"
        )
    )


    # --------------------------------------------------------
    # CHECK 3 — SAFETY
    # --------------------------------------------------------

    safety_present = (
        runtime.get(
            "safety_mechanism"
        )
        is not None
        and str(
            runtime.get(
                "safety_mechanism"
            )
        ).strip()
        != ""
    )

    add_check(
        "C3",
        "Architecture defines a runtime safety mechanism.",
        safety_present,
        str(
            runtime.get(
                "safety_mechanism"
            )
        )
    )


    # --------------------------------------------------------
    # CHECK 4 — LLM MUST NOT DIRECTLY CONTROL EFFECTORS
    # --------------------------------------------------------

    direct_llm_effector_risk = (
        "llm directly executes"
        in full_text
        or
        "llm directly invokes"
        in full_text
        or
        "llm directly controls effectors"
        in full_text
    )

    add_check(
        "C4",
        "Architecture does not explicitly give the LLM direct effector authority.",
        not direct_llm_effector_risk,
        (
            "No explicit direct-LLM-effector "
            "authority detected."
            if not direct_llm_effector_risk
            else
            "Potential direct LLM effector authority detected."
        )
    )


    # --------------------------------------------------------
    # CHECK 5 — MEMORY
    # --------------------------------------------------------

    memory_present = (
        runtime.get(
            "memory_strategy"
        )
        is not None
        and str(
            runtime.get(
                "memory_strategy"
            )
        ).strip()
        != ""
    )

    add_check(
        "C5",
        "Architecture defines runtime adaptation memory.",
        memory_present,
        str(
            runtime.get(
                "memory_strategy"
            )
        )
    )


    # --------------------------------------------------------
    # CHECK 6 — FAILURE RECOVERY
    # --------------------------------------------------------

    recovery_present = (
        runtime.get(
            "failure_recovery"
        )
        is not None
        and str(
            runtime.get(
                "failure_recovery"
            )
        ).strip()
        != ""
    )

    add_check(
        "C6",
        "Architecture defines failure recovery.",
        recovery_present,
        str(
            runtime.get(
                "failure_recovery"
            )
        )
    )


    # --------------------------------------------------------
    # CHECK 7 — ARCHITECT ROLE
    # --------------------------------------------------------

    architect_role_present = (
        design_time.get(
            "architect_role"
        )
        is not None
        and str(
            design_time.get(
                "architect_role"
            )
        ).strip()
        != ""
    )

    add_check(
        "C7",
        "Architecture keeps an explicit architect role at design time.",
        architect_role_present,
        str(
            design_time.get(
                "architect_role"
            )
        )
    )


    # --------------------------------------------------------
    # CHECK 8 — QUALITY-ATTRIBUTE COVERAGE
    # --------------------------------------------------------

    required_quality_attributes = {
        item[
            "name"
        ]
        for item in design_request.get(
            "quality_attributes",
            []
        )
    }

    actual_quality_attributes = set(
        alternative.get(
            "quality_attribute_rationale",
            {}
        ).keys()
    )

    qa_complete = (
        required_quality_attributes
        == actual_quality_attributes
    )

    add_check(
        "C8",
        "Architecture provides rationale for every required quality attribute.",
        qa_complete,
        (
            "Required: "
            + str(
                sorted(
                    required_quality_attributes
                )
            )
            + "; Actual: "
            + str(
                sorted(
                    actual_quality_attributes
                )
            )
        )
    )


    # --------------------------------------------------------
    # OVERALL DETERMINISTIC STATUS
    # --------------------------------------------------------

    all_pass = all(
        check[
            "status"
        ] == "PASS"
        for check in checks
    )


    return {
        "status":
            (
                "PASS"
                if all_pass
                else "FAIL"
            ),

        "checks":
            checks
    }


# ============================================================
# LLM REQUIREMENT VALIDATION
# ============================================================

def llm_validation(
    alternative,
    design_request
):

    prompt = f"""
You are validating a candidate software architecture
for the SWIM self-adaptive system.

This is architecture validation, NOT architecture
selection.

Evaluate whether the candidate architecture adequately
addresses the supplied requirements, adaptation goals,
uncertainties, architectural concerns, and trusted
constraints.

Do not assume that a high trade-off score means that
the architecture is valid.

Pay particular attention to:

- design-time LLM support
- architectural RAG
- multiple design alternatives
- architect oversight
- runtime monitoring
- analysis and planning
- deterministic safety validation
- prohibition of direct LLM-to-effector authority
- bounded recovery
- post-execution validation
- runtime adaptation memory
- human escalation
- response-time adaptation
- resource scaling
- dimmer adaptation

==================================================
DESIGN REQUEST
==================================================

{json.dumps(
    design_request,
    indent=2
)}

==================================================
CANDIDATE ARCHITECTURE
==================================================

{json.dumps(
    alternative,
    indent=2
)}

==================================================
OUTPUT
==================================================

Return ONLY valid JSON:

{{
  "status": "PASS",

  "requirement_coverage": [
    {{
      "item":
        "requirement or concern",

      "status":
        "PASS or PARTIAL or FAIL",

      "evidence":
        "architecture-specific evidence",

      "concern":
        "remaining issue or none"
    }}
  ],

  "major_strengths": [
    "strength"
  ],

  "major_validation_concerns": [
    "concern"
  ],

  "validation_summary":
    "overall architecture validation summary"
}}

Use overall status PASS only when there is no
architecture-breaking violation of the trusted
requirements.

Use FAIL when a hard requirement or trusted boundary
is violated.
"""

    response = ask_llm(
        prompt
    )

    return json.loads(
        response
    )


# ============================================================
# FULL VALIDATION
# ============================================================

def validate_candidates():

    design_request = load_json(
        DESIGN_REQUEST_FILE
    )

    alternatives_data = load_json(
        ALTERNATIVES_FILE
    )

    evaluation_data = load_json(
        EVALUATION_FILE
    )


    alternatives = alternatives_data[
        "alternatives"
    ]


    ranking = {
        item[
            "alternative_id"
        ]:
            {
                "weighted_total":
                    item[
                        "weighted_total"
                    ],

                "weighted_rank":
                    item[
                        "weighted_rank"
                    ]
            }

        for item in evaluation_data[
            "evaluations"
        ]
    }


    results = []


    print(
        "\n======================================"
    )

    print(
        " ARCHITECTURE VALIDATION"
    )

    print(
        "======================================"
    )


    for alternative in alternatives:

        alternative_id = alternative[
            "id"
        ]

        print(
            f"\nValidating "
            f"{alternative_id} — "
            f"{alternative['name']}"
        )


        deterministic = (
            deterministic_checks(
                alternative,
                design_request
            )
        )


        llm_result = (
            llm_validation(
                alternative,
                design_request
            )
        )


        final_status = (
            "PASS"
            if (
                deterministic[
                    "status"
                ]
                == "PASS"
                and
                llm_result.get(
                    "status"
                )
                == "PASS"
            )
            else "FAIL"
        )


        result = {
            "alternative_id":
                alternative_id,

            "alternative_name":
                alternative[
                    "name"
                ],

            "weighted_rank":
                ranking[
                    alternative_id
                ][
                    "weighted_rank"
                ],

            "weighted_total":
                ranking[
                    alternative_id
                ][
                    "weighted_total"
                ],

            "deterministic_validation":
                deterministic,

            "llm_requirement_validation":
                llm_result,

            "final_validation_status":
                final_status
        }


        results.append(
            result
        )


        print(
            f"  Deterministic: "
            f"{deterministic['status']}"
        )

        print(
            f"  LLM requirement validation: "
            f"{llm_result.get('status')}"
        )

        print(
            f"  Final validation: "
            f"{final_status}"
        )


    result_document = {
        "automatic_approval":
            False,

        "validation_results":
            results
    }


    os.makedirs(
        os.path.dirname(
            OUTPUT_FILE
        ),
        exist_ok=True
    )


    with open(
        OUTPUT_FILE,
        "w"
    ) as file:

        json.dump(
            result_document,
            file,
            indent=2
        )


    print(
        "\n======================================"
    )

    print(
        " VALIDATION COMPLETE"
    )

    print(
        "======================================"
    )


    for result in sorted(
        results,
        key=lambda item:
            item[
                "weighted_rank"
            ]
    ):

        print(
            f"\nRank "
            f"{result['weighted_rank']}: "
            f"{result['alternative_id']}"
        )

        print(
            f"Weighted score: "
            f"{result['weighted_total']}"
        )

        print(
            f"Validation: "
            f"{result['final_validation_status']}"
        )


    print(
        "\nIMPORTANT:"
    )

    print(
        "Validation does not constitute "
        "architect approval."
    )

    print(
        "\nValidation saved to:"
    )

    print(
        OUTPUT_FILE
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    validate_candidates()
