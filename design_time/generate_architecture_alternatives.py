import json
import os

from llm_client import ask_llm


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DESIGN_REQUEST_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "config",
    "swim_design_request.json"
)

RETRIEVED_KNOWLEDGE_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "retrieved_architecture_knowledge.json"
)

OUTPUT_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "architecture_alternatives.json"
)


# ============================================================
# LOAD JSON
# ============================================================

def load_json(path):

    with open(
        path,
        "r"
    ) as file:

        return json.load(file)


# ============================================================
# PREPARE RETRIEVED KNOWLEDGE
# ============================================================

def build_knowledge_context(
    retrieved
):

    parts = []


    for item in retrieved:

        knowledge = item[
            "knowledge"
        ]

        parts.append(
            "\n".join(
                [
                    (
                        f"ID: "
                        f"{knowledge.get('id')}"
                    ),

                    (
                        f"Name: "
                        f"{knowledge.get('name')}"
                    ),

                    (
                        f"Category: "
                        f"{knowledge.get('category')}"
                    ),

                    (
                        f"Description: "
                        f"{knowledge.get('description')}"
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
# GENERATE ARCHITECTURE ALTERNATIVES
# ============================================================

def generate_alternatives():

    design_request = load_json(
        DESIGN_REQUEST_FILE
    )

    retrieved = load_json(
        RETRIEVED_KNOWLEDGE_FILE
    )

    knowledge_context = (
        build_knowledge_context(
            retrieved
        )
    )


    print(
        "\n======================================"
    )

    print(
        " LLM ARCHITECTURE ALTERNATIVE GENERATION"
    )

    print(
        "======================================"
    )

    print(
        "Generating three candidate "
        "architectures..."
    )


    prompt = f"""
You are acting as a software architect.

Your task is to generate THREE distinct candidate
software architectures for a self-adaptive system.

The system is the SWIM self-adaptive web-system
case used in this research demonstrator.

You MUST reason from the supplied design request
and retrieved architectural knowledge.

Do not invent requirements that are not supported
by the design request.

Do not assume that LLM outputs are trusted.

The three alternatives must be meaningfully
different architectural choices, not cosmetic
variations of the same architecture.


==================================================
DESIGN REQUEST
==================================================

{json.dumps(
    design_request,
    indent=2
)}


==================================================
RETRIEVED ARCHITECTURAL KNOWLEDGE
==================================================

{knowledge_context}


==================================================
IMPORTANT DESIGN REQUIREMENTS
==================================================

The design must consider:

- design-time LLM-supported architecture reasoning
- architectural RAG
- multiple architectural alternatives
- quality-attribute trade-offs
- architecture rationale
- architect approval
- runtime self-adaptation
- runtime monitoring
- LLM-supported analysis and planning
- runtime RAG / adaptation memory
- deterministic safety validation
- approved effectors
- post-execution validation
- bounded replanning
- human escalation when autonomous recovery fails

Hard runtime constraints must remain outside the
generative LLM.

The LLM must not directly invoke effectors.


==================================================
OUTPUT FORMAT
==================================================

Return ONLY valid JSON.

Return an object with this exact structure:

{{
  "alternatives": [

    {{
      "id": "A1",

      "name": "Short architecture name",

      "architectural_style":
        "Main architectural style",

      "summary":
        "Short description of the architecture",

      "design_time_structure": {{
        "components": [
          {{
            "name": "component name",
            "responsibility":
              "what this component does"
          }}
        ],

        "flow": [
          "step 1",
          "step 2"
        ],

        "architect_role":
          "how the architect participates"
      }},

      "runtime_structure": {{
        "control_style":
          "centralized/decentralized/hybrid",

        "components": [
          {{
            "name": "component name",
            "responsibility":
              "what this component does"
          }}
        ],

        "adaptation_flow": [
          "step 1",
          "step 2"
        ],

        "safety_mechanism":
          "how deterministic safety is enforced",

        "memory_strategy":
          "how runtime experience is stored/reused",

        "failure_recovery":
          "how rejected or unsuccessful plans recover"
      }},

      "key_patterns_and_tactics": [
        "pattern or tactic"
      ],

      "quality_attribute_rationale": {{
        "performance":
          "expected impact",

        "scalability":
          "expected impact",

        "reliability":
          "expected impact",

        "safety":
          "expected impact",

        "resource_efficiency":
          "expected impact",

        "explainability":
          "expected impact"
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
        "AK1",
        "AK6"
      ]
    }}

  ]
}}


Generate exactly THREE alternatives:

A1
A2
A3

The alternatives must differ in meaningful
architectural structure.

At least one should use centralized runtime control.

At least one should explore decentralized or
distributed adaptation.

The third may use a hybrid architecture.

Do not choose the winner yet.

Do not score the alternatives yet.

Do not produce an ADR yet.

This stage only generates the architectural
design alternatives.
"""


    response = ask_llm(
        prompt
    )


    try:

        result = json.loads(
            response
        )

    except json.JSONDecodeError:

        print(
            "\nERROR:"
        )

        print(
            "The LLM did not return valid JSON."
        )

        print(
            "\nRaw response:"
        )

        print(
            response
        )

        raise


    alternatives = result.get(
        "alternatives",
        []
    )


    if len(
        alternatives
    ) != 3:

        raise RuntimeError(
            "Expected exactly 3 architecture "
            "alternatives."
        )


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
        "\nGenerated alternatives:"
    )


    for alternative in alternatives:

        print(
            f"\n{alternative.get('id')} — "
            f"{alternative.get('name')}"
        )

        print(
            "Style: "
            + str(
                alternative.get(
                    "architectural_style"
                )
            )
        )

        runtime = alternative.get(
            "runtime_structure",
            {}
        )

        print(
            "Runtime control: "
            + str(
                runtime.get(
                    "control_style"
                )
            )
        )


    print(
        "\nArchitecture alternatives saved to:"
    )

    print(
        OUTPUT_FILE
    )


    return result


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    generate_alternatives()
