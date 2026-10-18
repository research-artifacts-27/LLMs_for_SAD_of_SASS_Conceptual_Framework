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
# INPUT / OUTPUT FILES
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

VALIDATION_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "architecture_validation.json"
)

RECOMMENDATION_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "architecture_recommendation.json"
)

DECISION_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "architect_decision.json"
)

ADR_JSON_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "ADR-001.json"
)

ADR_MD_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "ADR-001.md"
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
# GENERATE ADR
# ============================================================

def generate_adr():

    design_request = load_json(
        DESIGN_REQUEST_FILE
    )

    alternatives = load_json(
        ALTERNATIVES_FILE
    )

    evaluation = load_json(
        EVALUATION_FILE
    )

    validation = load_json(
        VALIDATION_FILE
    )

    recommendation = load_json(
        RECOMMENDATION_FILE
    )

    decision = load_json(
        DECISION_FILE
    )


    # ========================================================
    # GOVERNANCE CHECK
    # ========================================================

    if not decision.get(
        "approved",
        False
    ):

        raise RuntimeError(
            "No architecture has been approved "
            "by the human architect."
        )


    selected_id = decision[
        "selected_alternative_id"
    ]

    selected_name = decision[
        "selected_alternative_name"
    ]


    print(
        "\n======================================"
    )

    print(
        " ARCHITECTURE DECISION RECORD"
    )

    print(
        "======================================"
    )

    print(
        f"Approved architecture: "
        f"{selected_id} — {selected_name}"
    )


    prompt = f"""
You are documenting an Architecture Decision Record
for a research demonstrator involving LLM-supported
software architecture design and Agentic-AI-supported
runtime adaptation of a self-adaptive software system.

The HUMAN architect has already made the final
architecture decision.

You must NOT change, override, or reinterpret that
decision.

The ADR must faithfully explain:

- the architecture decision context;
- the requirements and quality attributes;
- the alternatives considered;
- the trade-off analysis;
- validation results;
- numerical recommendation;
- prototype-alignment recommendation;
- the human architect's final choice;
- the rationale for choosing the approved design;
- positive and negative consequences;
- risks and remaining validation needs;
- how the approved design connects to runtime SWIM.

==================================================
DESIGN REQUEST
==================================================

{json.dumps(
    design_request,
    indent=2
)}

==================================================
ARCHITECTURE ALTERNATIVES
==================================================

{json.dumps(
    alternatives,
    indent=2
)}

==================================================
QUALITY-ATTRIBUTE EVALUATION
==================================================

{json.dumps(
    evaluation,
    indent=2
)}

==================================================
ARCHITECTURE VALIDATION
==================================================

{json.dumps(
    validation,
    indent=2
)}

==================================================
DECISION-SUPPORT RECOMMENDATION
==================================================

{json.dumps(
    recommendation,
    indent=2
)}

==================================================
HUMAN ARCHITECT DECISION
==================================================

{json.dumps(
    decision,
    indent=2
)}

==================================================
OUTPUT FORMAT
==================================================

Return ONLY valid JSON with this exact structure:

{{
  "adr_id": "ADR-001",

  "title":
    "Short architecture decision title",

  "status":
    "Accepted",

  "decision_authority":
    "Human Architect",

  "context":
    "Architecture decision context.",

  "decision_drivers": [
    "driver"
  ],

  "alternatives_considered": [
    {{
      "alternative_id": "A1",
      "name": "name",
      "weighted_score": 0.0,
      "validation_status": "PASS",
      "key_strengths": [
        "strength"
      ],
      "key_weaknesses": [
        "weakness"
      ]
    }}
  ],

  "decision": {{
    "selected_alternative_id":
      "A1",

    "selected_alternative_name":
      "name",

    "architect_rationale":
      "Explain the human architect's rationale.",

    "why_not_highest_ranked_if_applicable":
      "Explain if the selected design differs from the numerical winner."
  }},

  "approved_architecture_summary":
    "Concise structural summary.",

  "design_time_architecture": [
    "component / responsibility"
  ],

  "runtime_architecture": [
    "component / responsibility"
  ],

  "runtime_control_flow": [
    "step"
  ],

  "safety_boundaries": [
    "boundary"
  ],

  "positive_consequences": [
    "consequence"
  ],

  "negative_consequences": [
    "consequence"
  ],

  "risks": [
    "risk"
  ],

  "remaining_validation_needs": [
    "validation need"
  ],

  "traceability": {{
    "design_request":
      "swim_design_request.json",

    "architecture_alternatives":
      "architecture_alternatives.json",

    "tradeoff_evaluation":
      "architecture_evaluation.json",

    "architecture_validation":
      "architecture_validation.json",

    "architect_decision":
      "architect_decision.json"
  }}
}}

The selected architecture MUST exactly match:

Selected ID:
{selected_id}

Selected name:
{selected_name}

The ADR must explicitly state that numerical ranking
was decision support only and that final authority
remained with the human architect.

Do not claim that simulated operator escalation is a
real production notification mechanism.

Do not claim experimental evidence that has not been
demonstrated.
"""


    response = ask_llm(
        prompt
    )


    try:

        adr = json.loads(
            response
        )

    except json.JSONDecodeError:

        print(
            "\nERROR:"
        )

        print(
            "LLM returned invalid ADR JSON."
        )

        print(
            response
        )

        raise


    # ========================================================
    # DETERMINISTIC GOVERNANCE ENFORCEMENT
    # ========================================================

    adr[
        "adr_id"
    ] = "ADR-001"

    adr[
        "status"
    ] = "Accepted"

    adr[
        "decision_authority"
    ] = "Human Architect"


    adr.setdefault(
        "decision",
        {}
    )


    adr[
        "decision"
    ][
        "selected_alternative_id"
    ] = selected_id


    adr[
        "decision"
    ][
        "selected_alternative_name"
    ] = selected_name


    adr[
        "decision"
    ][
        "architect_rationale"
    ] = decision[
        "architect_rationale"
    ]


    # ========================================================
    # SAVE JSON ADR
    # ========================================================

    os.makedirs(
        os.path.dirname(
            ADR_JSON_FILE
        ),
        exist_ok=True
    )


    with open(
        ADR_JSON_FILE,
        "w"
    ) as file:

        json.dump(
            adr,
            file,
            indent=2
        )


    # ========================================================
    # GENERATE MARKDOWN ADR
    # ========================================================

    lines = []

    lines.append(
        "# ADR-001: "
        + adr.get(
            "title",
            "Approved SASS Architecture"
        )
    )

    lines.append("")

    lines.append(
        "**Status:** Accepted"
    )

    lines.append(
        "**Decision Authority:** Human Architect"
    )

    lines.append("")

    lines.append(
        "## Context"
    )

    lines.append("")

    lines.append(
        adr.get(
            "context",
            ""
        )
    )

    lines.append("")

    lines.append(
        "## Decision Drivers"
    )

    lines.append("")

    for item in adr.get(
        "decision_drivers",
        []
    ):

        lines.append(
            "- " + item
        )

    lines.append("")

    lines.append(
        "## Alternatives Considered"
    )

    lines.append("")


    for alternative in adr.get(
        "alternatives_considered",
        []
    ):

        lines.append(
            "### "
            + str(
                alternative.get(
                    "alternative_id",
                    ""
                )
            )
            + " — "
            + str(
                alternative.get(
                    "name",
                    ""
                )
            )
        )

        lines.append("")

        lines.append(
            "**Weighted score:** "
            + str(
                alternative.get(
                    "weighted_score",
                    ""
                )
            )
        )

        lines.append(
            "**Validation:** "
            + str(
                alternative.get(
                    "validation_status",
                    ""
                )
            )
        )

        lines.append("")

        lines.append(
            "**Strengths:**"
        )

        for item in alternative.get(
            "key_strengths",
            []
        ):

            lines.append(
                "- " + item
            )

        lines.append("")

        lines.append(
            "**Weaknesses:**"
        )

        for item in alternative.get(
            "key_weaknesses",
            []
        ):

            lines.append(
                "- " + item
            )

        lines.append("")


    decision_section = adr.get(
        "decision",
        {}
    )


    lines.append(
        "## Decision"
    )

    lines.append("")

    lines.append(
        "**Selected architecture:** "
        + str(
            decision_section.get(
                "selected_alternative_id",
                ""
            )
        )
        + " — "
        + str(
            decision_section.get(
                "selected_alternative_name",
                ""
            )
        )
    )

    lines.append("")

    lines.append(
        "**Architect rationale:**"
    )

    lines.append("")

    lines.append(
        decision_section.get(
            "architect_rationale",
            ""
        )
    )

    lines.append("")

    lines.append(
        "**Difference from numerical ranking:**"
    )

    lines.append("")

    lines.append(
        decision_section.get(
            "why_not_highest_ranked_if_applicable",
            ""
        )
    )

    lines.append("")

    lines.append(
        "## Approved Architecture Summary"
    )

    lines.append("")

    lines.append(
        adr.get(
            "approved_architecture_summary",
            ""
        )
    )

    lines.append("")

    lines.append(
        "## Design-Time Architecture"
    )

    lines.append("")

    for item in adr.get(
        "design_time_architecture",
        []
    ):

        lines.append(
            "- " + item
        )

    lines.append("")

    lines.append(
        "## Runtime Architecture"
    )

    lines.append("")

    for item in adr.get(
        "runtime_architecture",
        []
    ):

        lines.append(
            "- " + item
        )

    lines.append("")

    lines.append(
        "## Runtime Control Flow"
    )

    lines.append("")

    for index, item in enumerate(
        adr.get(
            "runtime_control_flow",
            []
        ),
        start=1
    ):

        lines.append(
            f"{index}. {item}"
        )

    lines.append("")

    lines.append(
        "## Safety Boundaries"
    )

    lines.append("")

    for item in adr.get(
        "safety_boundaries",
        []
    ):

        lines.append(
            "- " + item
        )

    lines.append("")

    lines.append(
        "## Positive Consequences"
    )

    lines.append("")

    for item in adr.get(
        "positive_consequences",
        []
    ):

        lines.append(
            "- " + item
        )

    lines.append("")

    lines.append(
        "## Negative Consequences"
    )

    lines.append("")

    for item in adr.get(
        "negative_consequences",
        []
    ):

        lines.append(
            "- " + item
        )

    lines.append("")

    lines.append(
        "## Risks"
    )

    lines.append("")

    for item in adr.get(
        "risks",
        []
    ):

        lines.append(
            "- " + item
        )

    lines.append("")

    lines.append(
        "## Remaining Validation Needs"
    )

    lines.append("")

    for item in adr.get(
        "remaining_validation_needs",
        []
    ):

        lines.append(
            "- " + item
        )

    lines.append("")

    lines.append(
        "## Governance Note"
    )

    lines.append("")

    lines.append(
        "The numerical architecture ranking was used "
        "as decision support only. Final architectural "
        "authority remained with the human architect."
    )


    with open(
        ADR_MD_FILE,
        "w"
    ) as file:

        file.write(
            "\n".join(
                lines
            )
        )


    # ========================================================
    # SUMMARY
    # ========================================================

    print(
        "\n======================================"
    )

    print(
        " ADR GENERATED"
    )

    print(
        "======================================"
    )

    print(
        f"ADR ID: "
        f"{adr['adr_id']}"
    )

    print(
        f"Status: "
        f"{adr['status']}"
    )

    print(
        f"Selected architecture: "
        f"{selected_id} — {selected_name}"
    )

    print(
        "Decision authority: "
        "Human Architect"
    )

    print(
        "\nJSON ADR:"
    )

    print(
        ADR_JSON_FILE
    )

    print(
        "\nMarkdown ADR:"
    )

    print(
        ADR_MD_FILE
    )


if __name__ == "__main__":

    generate_adr()
