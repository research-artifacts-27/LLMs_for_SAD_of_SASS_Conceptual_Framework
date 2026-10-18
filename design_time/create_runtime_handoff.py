import json
import os


# ============================================================
# PROJECT PATHS
# ============================================================

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

DECISION_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "architect_decision.json"
)

ADR_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "ADR-001.json"
)

CURRENT_RUNTIME_POLICY_FILE = os.path.join(
    PROJECT_DIR,
    "trusted_policies.json"
)

OUTPUT_FILE = os.path.join(
    PROJECT_DIR,
    "design_time",
    "outputs",
    "runtime_handoff.json"
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
# BUILD RUNTIME POLICY FROM APPROVED DESIGN
# ============================================================

def build_expected_runtime_policy(
    design_request
):

    constraints = design_request[
        "trusted_constraints"
    ]

    return {
        "max_servers":
            constraints[
                "maximum_servers"
            ],

        "min_servers":
            constraints[
                "minimum_servers"
            ],

        "response_time_target":
            constraints[
                "response_time_target_seconds"
            ],

        "dimmer_min":
            constraints[
                "dimmer_minimum"
            ],

        "dimmer_max":
            constraints[
                "dimmer_maximum"
            ],

        "dimmer_step":
            constraints[
                "dimmer_step"
            ],

        "allowed_actions":
            constraints[
                "allowed_runtime_actions"
            ]
    }


# ============================================================
# POLICY CONSISTENCY CHECK
# ============================================================

def compare_policies(
    expected,
    actual
):

    checks = []

    keys = [
        "max_servers",
        "min_servers",
        "response_time_target",
        "dimmer_min",
        "dimmer_max",
        "dimmer_step",
        "allowed_actions"
    ]


    for key in keys:

        expected_value = expected.get(
            key
        )

        actual_value = actual.get(
            key
        )

        status = (
            "PASS"
            if expected_value == actual_value
            else "FAIL"
        )


        checks.append(
            {
                "property":
                    key,

                "expected_from_approved_design":
                    expected_value,

                "actual_runtime_value":
                    actual_value,

                "status":
                    status
            }
        )


    overall = (
        "PASS"
        if all(
            item["status"] == "PASS"
            for item in checks
        )
        else "FAIL"
    )


    return {
        "overall_status":
            overall,

        "checks":
            checks
    }


# ============================================================
# CREATE HANDOFF
# ============================================================

def create_runtime_handoff():

    design_request = load_json(
        DESIGN_REQUEST_FILE
    )

    decision = load_json(
        DECISION_FILE
    )

    adr = load_json(
        ADR_FILE
    )

    runtime_policy = load_json(
        CURRENT_RUNTIME_POLICY_FILE
    )


    # ========================================================
    # GOVERNANCE CHECK
    # ========================================================

    if not decision.get(
        "approved",
        False
    ):

        raise RuntimeError(
            "Runtime handoff blocked because "
            "no architecture has been approved."
        )


    selected_architecture = decision[
        "selected_architecture"
    ]


    expected_policy = (
        build_expected_runtime_policy(
            design_request
        )
    )


    policy_consistency = (
        compare_policies(
            expected_policy,
            runtime_policy
        )
    )


    # ========================================================
    # IMPLEMENTATION TRACEABILITY
    # ========================================================

    implementation_mapping = {

        "monitoring": {
            "design_responsibility":
                "Observe real SWIM runtime state.",

            "implementation":
                "monitor.py"
        },

        "runtime_analysis": {
            "design_responsibility":
                "Interpret runtime state and diagnose adaptation need.",

            "implementation":
                "analyzer.py"
        },

        "runtime_rag": {
            "design_responsibility":
                "Retrieve relevant previous adaptation experience.",

            "implementation":
                "rag_retriever.py"
        },

        "planning": {
            "design_responsibility":
                "Generate candidate runtime adaptation plans.",

            "implementation":
                "planner.py"
        },

        "agentic_replanning": {
            "design_responsibility":
                "Recover from rejected adaptation candidates.",

            "implementation":
                "failure_router.py + agent_controller.py"
        },

        "deterministic_safety": {
            "design_responsibility":
                "Prevent unsafe or policy-violating plans from reaching effectors.",

            "implementation":
                "safety_checker.py"
        },

        "execution": {
            "design_responsibility":
                "Invoke only approved SWIM adaptation effectors.",

            "implementation":
                "executor.py + swim_client.py"
        },

        "post_execution_validation": {
            "design_responsibility":
                "Evaluate observed adaptation effects and QoS outcome.",

            "implementation":
                "outcome_evaluator.py"
        },

        "runtime_memory": {
            "design_responsibility":
                "Store states, decisions, safety verdicts, and observed outcomes.",

            "implementation":
                "runtime_kb.py + runtime_kb.json"
        },

        "bounded_recovery": {
            "design_responsibility":
                "Limit autonomous recovery attempts.",

            "implementation":
                "agent_controller.py"
        },

        "operator_escalation": {
            "design_responsibility":
                "Escalate when bounded autonomous recovery is exhausted.",

            "implementation":
                "agent_controller.py",

            "prototype_status":
                "simulated operator escalation only"
        }
    }


    # ========================================================
    # HANDOFF DOCUMENT
    # ========================================================

    handoff = {

        "handoff_status":
            (
                "READY"
                if policy_consistency[
                    "overall_status"
                ] == "PASS"
                else "REVIEW_REQUIRED"
            ),

        "design_case_id":
            design_request[
                "case_id"
            ],

        "approved_architecture": {
            "alternative_id":
                decision[
                    "selected_alternative_id"
                ],

            "name":
                decision[
                    "selected_alternative_name"
                ],

            "architectural_style":
                selected_architecture[
                    "architectural_style"
                ],

            "decision_authority":
                decision[
                    "decision_authority"
                ],

            "architect_rationale":
                decision[
                    "architect_rationale"
                ]
        },

        "architecture_decision_record": {
            "adr_id":
                adr[
                    "adr_id"
                ],

            "status":
                adr[
                    "status"
                ]
        },

        "runtime_control_style":
            selected_architecture[
                "runtime_structure"
            ][
                "control_style"
            ],

        "approved_runtime_structure":
            selected_architecture[
                "runtime_structure"
            ],

        "trusted_runtime_policy_from_design":
            expected_policy,

        "current_runtime_policy":
            runtime_policy,

        "policy_consistency":
            policy_consistency,

        "implementation_traceability":
            implementation_mapping,

        "runtime_governance": {
            "llm_direct_effector_access":
                False,

            "deterministic_safety_required":
                True,

            "post_execution_validation_required":
                True,

            "runtime_memory_enabled":
                True,

            "bounded_replanning_required":
                True,

            "human_escalation":
                "simulated in current prototype"
        },

        "design_to_runtime_traceability": {
            "design_request":
                "design_time/config/swim_design_request.json",

            "architect_decision":
                "design_time/outputs/architect_decision.json",

            "adr":
                "design_time/outputs/ADR-001.json",

            "runtime_policy":
                "trusted_policies.json"
        }
    }


    # ========================================================
    # SAVE
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
            handoff,
            file,
            indent=2
        )


    # ========================================================
    # SUMMARY
    # ========================================================

    print(
        "\n======================================"
    )

    print(
        " DESIGN → RUNTIME HANDOFF"
    )

    print(
        "======================================"
    )

    print(
        f"Approved architecture: "
        f"{decision['selected_alternative_id']} — "
        f"{decision['selected_alternative_name']}"
    )

    print(
        f"Runtime control style: "
        f"{handoff['runtime_control_style']}"
    )

    print(
        "\nTrusted-policy consistency:"
    )

    print(
        policy_consistency[
            "overall_status"
        ]
    )


    for check in policy_consistency[
        "checks"
    ]:

        print(
            f"  {check['property']}: "
            f"{check['status']}"
        )


    print(
        "\nHandoff status:"
    )

    print(
        handoff[
            "handoff_status"
        ]
    )

    print(
        "\nRuntime implementation mappings:"
    )


    for name, mapping in (
        implementation_mapping.items()
    ):

        print(
            f"  {name} -> "
            f"{mapping['implementation']}"
        )


    print(
        "\nHandoff saved to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":

    create_runtime_handoff()
