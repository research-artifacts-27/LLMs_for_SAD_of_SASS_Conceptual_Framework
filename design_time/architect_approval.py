import json
import os


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
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

OUTPUT_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "architect_decision.json"
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
# MAIN APPROVAL GATE
# ============================================================

def run_architect_approval():

    alternatives = load_json(
        ALTERNATIVES_FILE
    )[
        "alternatives"
    ]

    evaluation = load_json(
        EVALUATION_FILE
    )[
        "evaluations"
    ]

    validation = load_json(
        VALIDATION_FILE
    )[
        "validation_results"
    ]

    recommendation = load_json(
        RECOMMENDATION_FILE
    )


    alternative_by_id = {
        item["id"]: item
        for item in alternatives
    }


    evaluation_by_id = {
        item["alternative_id"]: item
        for item in evaluation
    }


    validation_by_id = {
        item["alternative_id"]: item
        for item in validation
    }


    print(
        "\n======================================"
    )

    print(
        " ARCHITECT APPROVAL GATE"
    )

    print(
        "======================================"
    )

    print(
        "\nDecision-support summary:"
    )


    for alternative_id in [
        "A1",
        "A2",
        "A3"
    ]:

        alternative = (
            alternative_by_id[
                alternative_id
            ]
        )

        evaluation_item = (
            evaluation_by_id[
                alternative_id
            ]
        )

        validation_item = (
            validation_by_id[
                alternative_id
            ]
        )


        print(
            f"\n{alternative_id} — "
            f"{alternative['name']}"
        )

        print(
            f"  Style: "
            f"{alternative['architectural_style']}"
        )

        print(
            f"  Weighted score: "
            f"{evaluation_item['weighted_total']}"
        )

        print(
            f"  Weighted rank: "
            f"{evaluation_item['weighted_rank']}"
        )

        print(
            f"  Validation: "
            f"{validation_item['final_validation_status']}"
        )


    print(
        "\n--------------------------------------"
    )

    print(
        "Numerically highest-ranked:"
    )

    highest = recommendation.get(
        "deterministic_highest_ranked",
        {}
    )

    print(
        f"{highest.get('alternative_id')} — "
        f"{highest.get('alternative_name')}"
    )


    print(
        "\nPrototype-alignment recommendation:"
    )

    prototype_alignment = recommendation.get(
        "prototype_alignment_recommendation",
        {}
    )

    print(
        f"{prototype_alignment.get('alternative_id')}"
    )

    print(
        prototype_alignment.get(
            "reason"
        )
    )


    print(
        "\n======================================"
    )

    print(
        " HUMAN ARCHITECT DECISION REQUIRED"
    )

    print(
        "======================================"
    )

    print(
        "\nChoose one of:"
    )

    print(
        "A1, A2, A3, or REJECT"
    )


    while True:

        decision = input(
            "\nArchitect decision: "
        ).strip().upper()


        if decision in {
            "A1",
            "A2",
            "A3",
            "REJECT"
        }:

            break


        print(
            "Invalid choice. "
            "Enter A1, A2, A3, or REJECT."
        )


    # ========================================================
    # REJECTION PATH
    # ========================================================

    if decision == "REJECT":

        while True:

            rationale = input(
                "\nReason for rejecting all "
                "candidate architectures: "
            ).strip()


            if rationale:

                break


            print(
                "A rationale is required."
            )


        print(
            "\nYou are about to reject all "
            "candidate architectures."
        )

        confirmation = input(
            "Type YES to confirm: "
        ).strip().upper()


        if confirmation != "YES":

            print(
                "\nDecision cancelled."
            )

            return


        decision_record = {

            "architect_decision":
                "REJECTED",

            "approved":
                False,

            "selected_alternative_id":
                None,

            "selected_alternative_name":
                None,

            "architect_rationale":
                rationale,

            "automatic_approval":
                False,

            "decision_authority":
                "human_architect",

            "next_step":
                "REVISE_ARCHITECTURE_ALTERNATIVES"
        }


    # ========================================================
    # APPROVAL PATH
    # ========================================================

    else:

        selected = (
            alternative_by_id[
                decision
            ]
        )

        selected_validation = (
            validation_by_id[
                decision
            ]
        )


        if (
            selected_validation[
                "final_validation_status"
            ]
            != "PASS"
        ):

            print(
                "\nERROR:"
            )

            print(
                "The selected architecture "
                "did not pass validation."
            )

            print(
                "Approval is blocked."
            )

            return


        print(
            "\nSelected architecture:"
        )

        print(
            f"{decision} — "
            f"{selected['name']}"
        )


        while True:

            rationale = input(
                "\nArchitect rationale for "
                "this selection: "
            ).strip()


            if rationale:

                break


            print(
                "A rationale is required."
            )


        print(
            "\n--------------------------------------"
        )

        print(
            "FINAL CONFIRMATION"
        )

        print(
            "--------------------------------------"
        )

        print(
            f"You are approving "
            f"{decision} — "
            f"{selected['name']}"
        )

        print(
            "\nThis decision will be recorded "
            "as the HUMAN architect decision."
        )


        confirmation = input(
            "\nType YES to approve: "
        ).strip().upper()


        if confirmation != "YES":

            print(
                "\nApproval cancelled."
            )

            return


        evaluation_item = (
            evaluation_by_id[
                decision
            ]
        )


        decision_record = {

            "architect_decision":
                "APPROVED",

            "approved":
                True,

            "selected_alternative_id":
                decision,

            "selected_alternative_name":
                selected[
                    "name"
                ],

            "selected_architecture":
                selected,

            "weighted_score":
                evaluation_item[
                    "weighted_total"
                ],

            "weighted_rank":
                evaluation_item[
                    "weighted_rank"
                ],

            "validation_status":
                selected_validation[
                    "final_validation_status"
                ],

            "architect_rationale":
                rationale,

            "automatic_approval":
                False,

            "decision_authority":
                "human_architect",

            "numerically_highest_ranked":
                highest,

            "prototype_alignment_recommendation":
                prototype_alignment,

            "next_step":
                "GENERATE_ADR_AND_RUNTIME_CONFIGURATION"
        }


    # ========================================================
    # SAVE DECISION
    # ========================================================

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
            decision_record,
            file,
            indent=2
        )


    print(
        "\n======================================"
    )

    print(
        " ARCHITECT DECISION RECORDED"
    )

    print(
        "======================================"
    )

    print(
        f"Decision: "
        f"{decision_record['architect_decision']}"
    )

    print(
        f"Approved: "
        f"{decision_record['approved']}"
    )


    if decision_record[
        "approved"
    ]:

        print(
            f"Selected architecture: "
            f"{decision_record['selected_alternative_id']} — "
            f"{decision_record['selected_alternative_name']}"
        )


    print(
        "\nDecision authority:"
    )

    print(
        "Human architect"
    )


    print(
        "\nDecision saved to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":

    run_architect_approval()
