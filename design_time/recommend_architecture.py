import json
import os
import sys


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

VALIDATION_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "architecture_validation.json"
)

OUTPUT_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "architecture_recommendation.json"
)


def load_json(path):

    with open(
        path,
        "r"
    ) as file:

        return json.load(file)


def build_recommendation():

    alternatives = load_json(
        ALTERNATIVES_FILE
    )["alternatives"]

    evaluation = load_json(
        EVALUATION_FILE
    )["evaluations"]

    validation = load_json(
        VALIDATION_FILE
    )["validation_results"]


    valid_ids = {
        item["alternative_id"]
        for item in validation
        if item[
            "final_validation_status"
        ] == "PASS"
    }


    ranked_valid = [
        item
        for item in evaluation
        if item[
            "alternative_id"
        ] in valid_ids
    ]


    ranked_valid.sort(
        key=lambda item:
            item["weighted_rank"]
    )


    if not ranked_valid:

        raise RuntimeError(
            "No validated architecture "
            "is available for recommendation."
        )


    numerical_recommendation = (
        ranked_valid[0]
    )


    print(
        "\n======================================"
    )

    print(
        " ARCHITECTURE RECOMMENDATION"
    )

    print(
        "======================================"
    )

    print(
        "Highest-ranked validated alternative:"
    )

    print(
        f"{numerical_recommendation['alternative_id']} — "
        f"{numerical_recommendation['alternative_name']}"
    )

    print(
        f"Weighted score: "
        f"{numerical_recommendation['weighted_total']}"
    )


    prompt = f"""
You are preparing architecture decision support for
an architect.

This stage MUST NOT approve an architecture.

The numerical weighted ranking and validation evidence
are advisory.

A human architect retains final authority.

The research prototype already contains a real runtime
implementation with these characteristics:

- centralized runtime adaptation controller
- real SWIM monitoring
- runtime RAG
- LLM-supported diagnosis
- LLM-supported planning and replanning
- deterministic runtime safety gate
- approved SWIM effectors
- post-execution outcome validation
- PASS / PARTIAL / FAIL outcome semantics
- runtime adaptation memory
- bounded recovery attempts
- simulated operator escalation

Compare the validated architectural alternatives with
both:

1. the weighted quality-attribute evidence; and
2. the demonstrated runtime prototype structure.

Distinguish clearly between:

- numerically highest-ranked architecture;
- architecture most directly aligned with the
  implemented runtime prototype.

Do NOT approve or select the final architecture.

Return ONLY valid JSON.

==================================================
ARCHITECTURES
==================================================

{json.dumps(
    alternatives,
    indent=2
)}

==================================================
TRADE-OFF EVALUATION
==================================================

{json.dumps(
    evaluation,
    indent=2
)}

==================================================
VALIDATION
==================================================

{json.dumps(
    validation,
    indent=2
)}

==================================================
OUTPUT FORMAT
==================================================

{{
  "numerical_recommendation": {{
    "alternative_id": "A1",
    "reason": "reason"
  }},

  "prototype_alignment_recommendation": {{
    "alternative_id": "A1",
    "reason": "reason"
  }},

  "decision_tension": {{
    "exists": true,
    "explanation":
      "Explain any difference between weighted ranking and implementation alignment."
  }},

  "architect_review_points": [
    "point 1",
    "point 2",
    "point 3"
  ],

  "automatic_approval": false,

  "final_decision":
    "PENDING_ARCHITECT_APPROVAL"
}}
"""


    response = ask_llm(
        prompt
    )


    result = json.loads(
        response
    )


    # --------------------------------------------------------
    # Enforce architectural governance
    # --------------------------------------------------------

    result[
        "automatic_approval"
    ] = False

    result[
        "final_decision"
    ] = "PENDING_ARCHITECT_APPROVAL"


    result[
        "deterministic_highest_ranked"
    ] = {
        "alternative_id":
            numerical_recommendation[
                "alternative_id"
            ],

        "alternative_name":
            numerical_recommendation[
                "alternative_name"
            ],

        "weighted_total":
            numerical_recommendation[
                "weighted_total"
            ],

        "weighted_rank":
            numerical_recommendation[
                "weighted_rank"
            ]
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
            result,
            file,
            indent=2
        )


    print(
        "\nDecision-support recommendation:"
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )


    print(
        "\n======================================"
    )

    print(
        " ARCHITECT DECISION STILL REQUIRED"
    )

    print(
        "======================================"
    )

    print(
        "No architecture has been approved."
    )

    print(
        "\nRecommendation saved to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":

    build_recommendation()
