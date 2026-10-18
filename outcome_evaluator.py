import json


POLICY_FILE = "trusted_policies.json"


def load_policies():

    with open(POLICY_FILE, "r") as file:
        return json.load(file)


def evaluate_outcome(
    initial_state,
    final_state,
    executed_plan
):

    print("\n=== POST-EXECUTION VALIDATION ===")

    policies = load_policies()

    response_time_target = policies[
        "response_time_target"
    ]

    action = executed_plan.get(
        "action"
    )

    action_effect_observed = False

    # ========================================================
    # CHECK WHETHER THE ACTION TOOK EFFECT
    # ========================================================

    if action == "add_server":

        action_effect_observed = (
            final_state["servers"]
            > initial_state["servers"]
        )

    elif action == "remove_server":

        action_effect_observed = (
            final_state["servers"]
            < initial_state["servers"]
        )

    elif action == "set_dimmer":

        requested_value = float(
            executed_plan.get("value")
        )

        action_effect_observed = (
            abs(
                final_state["dimmer"]
                - requested_value
            )
            < 0.0001
        )

    elif action == "none":

        # No state-changing effector was expected.
        action_effect_observed = True

    # ========================================================
    # CHECK WHETHER THE RUNTIME GOAL IS SATISFIED
    # ========================================================

    goal_satisfied = (
        final_state["response_time"]
        <= response_time_target
    )

    # ========================================================
    # SPECIAL CASE — NO ADAPTATION REQUIRED
    # ========================================================

    if action == "none":

        if goal_satisfied:

            outcome = {
                "status": "PASS",
                "action_effect_observed": True,
                "goal_satisfied": True,
                "reason": (
                    "No adaptation action was required, "
                    "and the post-decision response-time "
                    "goal remains satisfied."
                )
            }

        else:

            outcome = {
                "status": "FAIL",
                "action_effect_observed": True,
                "goal_satisfied": False,
                "reason": (
                    "No adaptation action was executed, "
                    "but the response-time goal remains "
                    "violated."
                )
            }

    # ========================================================
    # ACTION EXECUTED + GOAL ACHIEVED
    # ========================================================

    elif (
        action_effect_observed
        and goal_satisfied
    ):

        outcome = {
            "status": "PASS",
            "action_effect_observed": True,
            "goal_satisfied": True,
            "reason": (
                "The approved adaptation took effect "
                "and the post-execution response-time "
                "goal is satisfied."
            )
        }

    # ========================================================
    # ACTION EXECUTED + MORE ADAPTATION NEEDED
    # ========================================================

    elif (
        action_effect_observed
        and not goal_satisfied
    ):

        outcome = {
            "status": "PARTIAL",
            "action_effect_observed": True,
            "goal_satisfied": False,
            "reason": (
                "The adaptation took effect successfully, "
                "but the response-time goal is still "
                "violated. Further adaptation may be needed."
            )
        }

    # ========================================================
    # ACTION ITSELF FAILED
    # ========================================================

    else:

        outcome = {
            "status": "FAIL",
            "action_effect_observed": False,
            "goal_satisfied": goal_satisfied,
            "reason": (
                "The approved adaptation did not produce "
                "the expected observable state change."
            )
        }

    # ========================================================
    # DISPLAY
    # ========================================================

    print(
        f"Action Effect Observed: "
        f"{outcome['action_effect_observed']}"
    )

    print(
        f"Goal Satisfied: "
        f"{outcome['goal_satisfied']}"
    )

    print(
        f"Actual Adaptation Outcome: "
        f"{outcome['status']}"
    )

    print(
        f"Reason: "
        f"{outcome['reason']}"
    )

    return outcome


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    initial_state = {
        "response_time": 0.0,
        "servers": 1,
        "active_servers": 1,
        "utilization": 0.0,
        "dimmer": 1.0
    }

    final_state = {
        "response_time": 0.0,
        "servers": 1,
        "active_servers": 1,
        "utilization": 0.0,
        "dimmer": 1.0
    }

    plan = {
        "action": "none"
    }

    evaluate_outcome(
        initial_state,
        final_state,
        plan
    )
