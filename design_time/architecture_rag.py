import json
import math
import os
import urllib.request


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

KNOWLEDGE_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "knowledge",
    "architecture_knowledge.json"
)

CACHE_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "knowledge",
    "architecture_embedding_cache.json"
)

OUTPUT_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "retrieved_architecture_knowledge.json"
)

EMBEDDING_ENDPOINT = (
    "https://api.openai.com/v1/embeddings"
)

EMBEDDING_MODEL = (
    "text-embedding-3-small"
)


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(path):

    with open(
        path,
        "r"
    ) as file:

        return json.load(file)


# ============================================================
# EMBEDDINGS
# ============================================================

def get_embedding(text):

    api_key = os.environ.get(
        "OPENAI_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "OPENAI_API_KEY is not available."
        )

    payload = json.dumps(
        {
            "model":
                EMBEDDING_MODEL,

            "input":
                text
        }
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        EMBEDDING_ENDPOINT,
        data=payload,
        headers={
            "Authorization":
                f"Bearer {api_key}",

            "Content-Type":
                "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(
        request,
        timeout=60
    ) as response:

        result = json.loads(
            response.read().decode(
                "utf-8"
            )
        )

    return result[
        "data"
    ][0][
        "embedding"
    ]


# ============================================================
# COSINE SIMILARITY
# ============================================================

def cosine_similarity(
    vector_a,
    vector_b
):

    dot_product = sum(
        a * b
        for a, b in zip(
            vector_a,
            vector_b
        )
    )

    magnitude_a = math.sqrt(
        sum(
            value * value
            for value in vector_a
        )
    )

    magnitude_b = math.sqrt(
        sum(
            value * value
            for value in vector_b
        )
    )

    if (
        magnitude_a == 0
        or magnitude_b == 0
    ):

        return 0.0

    return (
        dot_product
        /
        (
            magnitude_a
            *
            magnitude_b
        )
    )


# ============================================================
# KNOWLEDGE ENTRY AS TEXT
# ============================================================

def knowledge_to_text(entry):

    return "\n".join(
        [
            f"ID: {entry.get('id')}",

            f"Name: "
            f"{entry.get('name')}",

            f"Category: "
            f"{entry.get('category')}",

            f"Description: "
            f"{entry.get('description')}",

            "Supports: "
            + ", ".join(
                entry.get(
                    "supports",
                    []
                )
            ),

            "Applicability: "
            + ", ".join(
                entry.get(
                    "applicability",
                    []
                )
            ),

            "Benefits: "
            + ", ".join(
                entry.get(
                    "benefits",
                    []
                )
            ),

            "Trade-offs: "
            + ", ".join(
                entry.get(
                    "tradeoffs",
                    []
                )
            ),

            "Constraints: "
            + ", ".join(
                entry.get(
                    "constraints",
                    []
                )
            )
        ]
    )


# ============================================================
# DESIGN REQUEST AS RETRIEVAL QUERY
# ============================================================

def design_request_to_query(
    design_request
):

    parts = []

    parts.append(
        "System: "
        + design_request.get(
            "system_name",
            ""
        )
    )

    parts.append(
        "Design objective: "
        + design_request.get(
            "design_objective",
            ""
        )
    )


    for requirement in design_request.get(
        "functional_requirements",
        []
    ):

        parts.append(
            "Functional requirement: "
            + requirement.get(
                "requirement",
                ""
            )
        )


    for goal in design_request.get(
        "adaptation_goals",
        []
    ):

        parts.append(
            "Adaptation goal: "
            + goal.get(
                "goal",
                ""
            )
        )


    for attribute in design_request.get(
        "quality_attributes",
        []
    ):

        parts.append(
            (
                "Quality attribute "
                + str(
                    attribute.get(
                        "name",
                        ""
                    )
                )
                + ": "
                + str(
                    attribute.get(
                        "goal",
                        ""
                    )
                )
            )
        )


    for uncertainty in design_request.get(
        "uncertainty_sources",
        []
    ):

        parts.append(
            (
                "Uncertainty: "
                + str(
                    uncertainty.get(
                        "source",
                        ""
                    )
                )
                + " - "
                + str(
                    uncertainty.get(
                        "description",
                        ""
                    )
                )
            )
        )


    for concern in design_request.get(
        "architectural_concerns",
        []
    ):

        parts.append(
            "Architectural concern: "
            + concern
        )


    constraints = design_request.get(
        "trusted_constraints",
        {}
    )

    for key, value in constraints.items():

        parts.append(
            f"Trusted constraint "
            f"{key}: {value}"
        )


    return "\n".join(
        parts
    )


# ============================================================
# EMBEDDING CACHE
# ============================================================

def load_cache():

    if not os.path.exists(
        CACHE_FILE
    ):

        return {}

    try:

        with open(
            CACHE_FILE,
            "r"
        ) as file:

            return json.load(file)

    except Exception:

        return {}


def save_cache(cache):

    with open(
        CACHE_FILE,
        "w"
    ) as file:

        json.dump(
            cache,
            file
        )


# ============================================================
# EXPLICIT REQUIREMENT COVERAGE
# ============================================================

def determine_mandatory_knowledge(
    design_request
):

    mandatory = {}

    scope = design_request.get(
        "candidate_architecture_scope",
        {}
    )

    constraints = design_request.get(
        "trusted_constraints",
        {}
    )


    if scope.get(
        "include_design_time_llm_support"
    ):

        mandatory[
            "AK5"
        ] = (
            "Design scope explicitly requires "
            "LLM-supported architecture reasoning."
        )


    if scope.get(
        "include_architectural_rag"
    ):

        mandatory[
            "AK4"
        ] = (
            "Design scope explicitly requires "
            "architectural RAG."
        )


    if constraints.get(
        "deterministic_safety_validation_required"
    ):

        mandatory[
            "AK6"
        ] = (
            "Trusted constraints require a "
            "deterministic safety validation layer."
        )


    if scope.get(
        "include_runtime_agentic_controller"
    ):

        mandatory[
            "AK1"
        ] = (
            "The requested system includes a "
            "runtime self-adaptation controller."
        )

        mandatory[
            "AK11"
        ] = (
            "Agentic control requires bounded "
            "replanning and recovery."
        )

        mandatory[
            "AK13"
        ] = (
            "Runtime adaptation requires "
            "post-execution validation."
        )


    if scope.get(
        "include_runtime_memory"
    ):

        mandatory[
            "AK10"
        ] = (
            "Runtime adaptation memory is "
            "explicitly required."
        )


    if (
        scope.get(
            "include_human_oversight"
        )
        or constraints.get(
            "architect_approval_required_at_design_time"
        )
    ):

        mandatory[
            "AK12"
        ] = (
            "Human oversight and architect "
            "approval are explicitly required."
        )

        mandatory[
            "AK14"
        ] = (
            "Architecture decisions require "
            "inspectable rationale and ADRs."
        )


    quality_attributes = (
        design_request.get(
            "quality_attributes",
            []
        )
    )

    if len(
        quality_attributes
    ) > 1:

        mandatory[
            "AK15"
        ] = (
            "Multiple weighted quality attributes "
            "require explicit trade-off analysis."
        )


    return mandatory


# ============================================================
# HYBRID ARCHITECTURAL RAG
# ============================================================

def retrieve_architecture_knowledge(
    design_request,
    semantic_top_k=8
):

    knowledge = load_json(
        KNOWLEDGE_FILE
    )

    knowledge_by_id = {
        entry[
            "id"
        ]:
            entry
        for entry in knowledge
    }

    query_text = (
        design_request_to_query(
            design_request
        )
    )


    print(
        "\n======================================"
    )

    print(
        " HYBRID DESIGN-TIME ARCHITECTURAL RAG"
    )

    print(
        "======================================"
    )

    print(
        f"Knowledge entries available: "
        f"{len(knowledge)}"
    )

    print(
        f"Semantic Top-K: "
        f"{semantic_top_k}"
    )


    query_embedding = get_embedding(
        query_text
    )

    cache = load_cache()

    scored_entries = []


    for entry in knowledge:

        entry_id = entry[
            "id"
        ]

        entry_text = knowledge_to_text(
            entry
        )

        cached = cache.get(
            entry_id
        )


        if (
            cached
            and cached.get(
                "text"
            ) == entry_text
        ):

            embedding = cached[
                "embedding"
            ]

        else:

            embedding = get_embedding(
                entry_text
            )

            cache[
                entry_id
            ] = {
                "text":
                    entry_text,

                "embedding":
                    embedding
            }


        similarity = cosine_similarity(
            query_embedding,
            embedding
        )

        scored_entries.append(
            {
                "knowledge":
                    entry,

                "similarity":
                    similarity
            }
        )


    save_cache(
        cache
    )


    scored_entries.sort(
        key=lambda item:
            item[
                "similarity"
            ],
        reverse=True
    )


    similarity_by_id = {
        item[
            "knowledge"
        ][
            "id"
        ]:
            item[
                "similarity"
            ]
        for item in scored_entries
    }


    # ========================================================
    # SEMANTIC TOP-K
    # ========================================================

    selected = {}

    semantic_selected = (
        scored_entries[
            :semantic_top_k
        ]
    )


    for semantic_rank, item in enumerate(
        semantic_selected,
        start=1
    ):

        entry = item[
            "knowledge"
        ]

        selected[
            entry[
                "id"
            ]
        ] = {
            "knowledge":
                entry,

            "similarity":
                item[
                    "similarity"
                ],

            "semantic_rank":
                semantic_rank,

            "selection_reasons": [
                "semantic_top_k"
            ],

            "requirement_reason":
                None
        }


    # ========================================================
    # MANDATORY COVERAGE
    # ========================================================

    mandatory = (
        determine_mandatory_knowledge(
            design_request
        )
    )


    for entry_id, reason in (
        mandatory.items()
    ):

        if entry_id not in (
            knowledge_by_id
        ):

            continue


        if entry_id in selected:

            selected[
                entry_id
            ][
                "selection_reasons"
            ].append(
                "mandatory_requirement"
            )

            selected[
                entry_id
            ][
                "requirement_reason"
            ] = reason

        else:

            selected[
                entry_id
            ] = {
                "knowledge":
                    knowledge_by_id[
                        entry_id
                    ],

                "similarity":
                    similarity_by_id.get(
                        entry_id,
                        0.0
                    ),

                "semantic_rank":
                    None,

                "selection_reasons": [
                    "mandatory_requirement"
                ],

                "requirement_reason":
                    reason
            }


    # ========================================================
    # FINAL ORDER
    # ========================================================

    final_items = list(
        selected.values()
    )

    final_items.sort(
        key=lambda item:
            item[
                "similarity"
            ],
        reverse=True
    )


    output = []


    print(
        "\nFinal retrieved architectural knowledge:"
    )


    for final_rank, item in enumerate(
        final_items,
        start=1
    ):

        entry = item[
            "knowledge"
        ]

        similarity = item[
            "similarity"
        ]


        result = {
            "final_rank":
                final_rank,

            "similarity":
                round(
                    similarity,
                    4
                ),

            "semantic_rank":
                item[
                    "semantic_rank"
                ],

            "selection_reasons":
                item[
                    "selection_reasons"
                ],

            "requirement_reason":
                item[
                    "requirement_reason"
                ],

            "knowledge":
                entry
        }


        output.append(
            result
        )


        print(
            f"\n{final_rank}. "
            f"{entry['id']} — "
            f"{entry['name']}"
        )

        print(
            f"   Category: "
            f"{entry['category']}"
        )

        print(
            f"   Similarity: "
            f"{similarity:.4f}"
        )

        print(
            "   Selection: "
            + ", ".join(
                item[
                    "selection_reasons"
                ]
            )
        )


        if item[
            "requirement_reason"
        ]:

            print(
                "   Required because: "
                + item[
                    "requirement_reason"
                ]
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
            output,
            file,
            indent=2
        )


    print(
        "\n======================================"
    )

    print(
        " RETRIEVAL SUMMARY"
    )

    print(
        "======================================"
    )

    print(
        f"Semantic selections: "
        f"{len(semantic_selected)}"
    )

    print(
        f"Mandatory knowledge rules: "
        f"{len(mandatory)}"
    )

    print(
        f"Final unique entries: "
        f"{len(output)}"
    )

    print(
        "\nRetrieved evidence saved to:"
    )

    print(
        OUTPUT_FILE
    )


    return output


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    design_request = load_json(
        DESIGN_REQUEST_FILE
    )

    results = (
        retrieve_architecture_knowledge(
            design_request,
            semantic_top_k=8
        )
    )

    print(
        "\n======================================"
    )

    print(
        " HYBRID ARCHITECTURAL RAG COMPLETE"
    )

    print(
        "======================================"
    )

    print(
        f"Final retrieved entries: "
        f"{len(results)}"
    )
