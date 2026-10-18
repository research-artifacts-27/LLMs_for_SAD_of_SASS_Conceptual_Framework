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

OUTPUT_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "architecture_evaluation.json"
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
# QUALITY ATTRIBUTE WEIGHTS
# ============================================================

def get_quality_attributes(
    design_request
):

    result = {}

    for attribute in design_request.get(
        "quality_attributes",
        []
    ):

        name = attribute[
            "name"
        ]

        result[
            name
        ] = {
            "weight":
                float(
                    attribute[
                        "weight"
                    ]
                ),

            "priority":
                attribute.get(
                    "priority"
                ),

            "goal":
                attribute.get(
                    "goal"
                )
        }

    return result


# ============================================================
# VALIDATE LLM SCORES
# ============================================================

def validate_evaluation(
    evaluation,
    alternatives,
    quality_attributes
):

    expected_ids = {
        alternative[
            "id"
        ]
        for alternative in alternatives
    }

    received_ids = {
        item[
            "alternative_id"
        ]
        for item in evaluation
    }


    if received_ids != expected_ids:

        raise RuntimeError(
            "Evaluation does not contain "
            "exactly A1, A2, and A3."
        )


    expected_attributes = set(
        quality_attributes.keys()
    )


    for item in evaluation:

        scores = item.get(
            "quality_attribute_scores",
            {}
        )

        received_attributes = set(
            scores.keys()
        )


        if (
            received_attributes
            != expected_attributes
        ):

            raise RuntimeError(
                "Quality-attribute coverage "
                "is incomplete for "
                + item[
                    "alternative_id"
                ]
            )


        for attribute_name, score_info in (
            scores.items()
        ):

            score = score_info.get(
                "score"
            )


            if not isinstance(
                score,
                (int, float)
            ):

                raise RuntimeError(
                    "Non-numeric score found "
                    "for "
                    + attribute_name
                )


            if (
                score < 1
                or score > 5
            ):

                raise RuntimeError(
                    "Score outside allowed "
                    "1–5 range for "
                    + attribute_name
                )


# ============================================================
# DETERMINISTIC WEIGHTED SCORE
# ============================================================

def calculate_weighted_scores(
    evaluation,
    quality_attributes
):

    for item in evaluation:

        weighted_total = 0.0

        weighted_breakdown = {}


        for attribute_name, attribute_info in (
            quality_attributes.items()
        ):

            weight = attribute_info[
                "weight"
            ]

            score = float(
                item[
                    "quality_attribute_scores"
                ][
                    attribute_name
                ][
                    "score"
                ]
            )


            weighted_value = (
                score * weight
            )


            weighted_breakdown[
                attribute_name
            ] = {
                "score":
                    score,

                "weight":
                    weight,

                "weighted_value":
                    round(
                        weighted_value,
                        4
                    )
            }


            weighted_total += (
                weighted_value
            )


        item[
            "weighted_breakdown"
        ] = weighted_breakdown


        item[
            "weighted_total"
        ] = round(
            weighted_total,
            4
        )


    return evaluation


# ============================================================
# RANK ALTERNATIVES
# ============================================================

def add_ranking(
    evaluation
):

    ordered = sorted(
        evaluation,
        key=lambda item:
            item[
                "weighted_total"
            ],
        reverse=True
    )


    for rank, item in enumerate(
        ordered,
        start=1
    ):

        item[
            "weighted_rank"
        ] = rank


    return ordered


# ============================================================
# LLM TRADE-OFF ANALYSIS
# ============================================================

def evaluate_alternatives():

    design_request = load_json(
        DESIGN_REQUEST_FILE
    )


    alternatives_data = load_json(
        ALTERNATIVES_FILE
    )


    alternatives = alternatives_data[
        "alternatives"
    ]


    quality_attributes = (
        get_quality_attributes(
            design_request
        )
    )


    print(
        "\n======================================"
    )

    print(
        " ARCHITECTURE TRADE-OFF ANALYSIS"
    )

    print(
        "======================================"
    )

    print(
        "Evaluating A1, A2, and A3 against "
        "the architect-defined quality attributes..."
    )


    prompt = f"""
You are acting as a software architecture evaluator.

Evaluate THREE candidate architectures for the
SWIM self-adaptive system.

Use ONLY the supplied design request and candidate
architecture descriptions.

You are NOT selecting the final architecture.

You are providing structured architecture trade-off
evidence for architect review.

==================================================
DESIGN REQUEST
==================================================

{json.dumps(
    design_request,
    indent=2
)}

==================================================
CANDIDATE ARCHITECTURES
==================================================

{json.dumps(
    alternatives,
    indent=2
)}

==================================================
EVALUATION METHOD
==================================================

Score every architecture against every listed
quality attribute.

Use this scale:

1 = very poor support
2 = poor support
3 = moderate support
4 = good support
5 = very good support

Evaluate these exact quality attributes:

{json.dumps(
    list(
        quality_attributes.keys()
    ),
    indent=2
)}

For EACH score:

- provide a concise architecture-specific rationale;
- identify an important trade-off or limitation;
- base the judgment on the actual architecture structure;
- do not favor an architecture merely because it uses an LLM;
- distinguish centralized, decentralized, and hybrid consequences.

Do NOT apply the numerical weights yourself.

The Python program will calculate weighted totals
deterministically after your evaluation.

Do NOT select or approve a winner.

==================================================
OUTPUT FORMAT
==================================================

Return ONLY valid JSON.

Use exactly this structure:

{{
  "evaluations": [

    {{
      "alternative_id": "A1",

      "alternative_name": "name",

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
        "Concise architecture-level trade-off summary."
    }}

  ]
}}

Include exactly A1, A2, and A3.
"""


    response = ask_llm(
        prompt
    )


    try:

        llm_result = json.loads(
            response
        )

    except json.JSONDecodeError:

        print(
            "\nERROR: LLM returned "
            "invalid JSON."
        )

        print(
            "\nRaw response:"
        )

        print(
            response
        )

        raise


    evaluation = llm_result.get(
        "evaluations",
        []
    )


    validate_evaluation(
        evaluation,
        alternatives,
        quality_attributes
    )


    evaluation = (
        calculate_weighted_scores(
            evaluation,
            quality_attributes
        )
    )


    ranked = add_ranking(
        evaluation
    )


    result = {

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
        "\n======================================"
    )

    print(
        " WEIGHTED TRADE-OFF RESULTS"
    )

    print(
        "======================================"
    )


    for item in ranked:

        print(
            f"\nRank {item['weighted_rank']}: "
            f"{item['alternative_id']} — "
            f"{item['alternative_name']}"
        )

        print(
            f"Weighted score: "
            f"{item['weighted_total']:.4f} / 5.0000"
        )


        for attribute_name in (
            quality_attributes.keys()
        ):

            score = item[
                "quality_attribute_scores"
            ][
                attribute_name
            ][
                "score"
            ]

            print(
                f"  {attribute_name}: "
                f"{score}/5"
            )


    print(
        "\nIMPORTANT:"
    )

    print(
        "The numerical ranking is decision support only."
    )

    print(
        "No architecture has been automatically approved."
    )

    print(
        "\nEvaluation saved to:"
    )

    print(
        OUTPUT_FILE
    )


    return result


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    evaluate_alternatives()
