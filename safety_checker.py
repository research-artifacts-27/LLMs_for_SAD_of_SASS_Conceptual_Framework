import json

from monitor import monitor
from analyzer import analyze
from planner import plan


POLICY_FILE = "trusted_policies.json"


def load_policies():

    with open(POLICY_FILE, "r") as file:
        return json.load(file)


def safety_check(candidate_plan, state):

    print("\n=== SAFETY CHECK — REAL SWIM ===")

    policies = load_policies()

    max_servers = policies["max_servers"]
    min_servers = policies["min_servers"]
    response_time_target = policies[
        "response_time_target"
    ]

    dimmer_min = policies["dimmer_min"]
    dimmer_max = policies["dimmer_max"]
    allowed_actions = policies[
        "allowed_actions"
    ]

    action = candidate_plan.get("action")

    # ========================================================
    # CAPACITY INFORMATION
    # ========================================================

    total_utilization = (
        state["utilization"]
        * state["active_servers"]
    )

    spare_capacity = (
        state["active_servers"]
        - total_utilization
    )

    total_servers = state["servers"]
    active_servers = state["active_servers"]
    server_booting = state["server_booting"]

    # ========================================================
    # RULE 1 — ACTION MUST BE TRUSTED
    # ========================================================

    if action not in allowed_actions:

        verdict = {
            "status": "FAIL",
            "reason": (
                f"Action '{action}' is not allowed "
                "by trusted SWIM policies."
            )
        }

        print("Result: FAIL")
        print(f"Reason: {verdict['reason']}")

        return verdict

    # ========================================================
    # RULE 2 — ADD SERVER
    # ========================================================

    if action == "add_server":

        # Do not request another server while
        # a previously requested server is booting.
        if server_booting:

            verdict = {
                "status": "FAIL",
                "reason": (
                    "Cannot add another server because "
                    "a server is already booting."
                )
            }

            print("Result: FAIL")
            print(f"Reason: {verdict['reason']}")

            return verdict

        # Use TOTAL servers here because a server may
        # exist but not yet be active.
        if total_servers >= max_servers:

            verdict = {
                "status": "FAIL",
                "reason": (
                    f"Cannot add a server because "
                    f"{total_servers} servers already exist "
                    f"and the trusted maximum is "
                    f"{max_servers}."
                )
            }

            print("Result: FAIL")
            print(f"Reason: {verdict['reason']}")

            return verdict

        if total_servers >= state["max_servers"]:

            verdict = {
                "status": "FAIL",
                "reason": (
                    "Cannot add a server because the "
                    "real SWIM maximum has been reached."
                )
            }

            print("Result: FAIL")
            print(f"Reason: {verdict['reason']}")

            return verdict

        if (
            state["response_time"]
            <= response_time_target
        ):

            verdict = {
                "status": "FAIL",
                "reason": (
                    "Adding a server is not justified "
                    "because response time "
                    f"{state['response_time']:.4f} seconds "
                    "is within the trusted target of "
                    f"{response_time_target} seconds."
                )
            }

            print("Result: FAIL")
            print(f"Reason: {verdict['reason']}")

            return verdict

        verdict = {
            "status": "PASS",
            "reason": (
                "add_server satisfies trusted "
                "SWIM adaptation policies."
            )
        }

        print("Result: PASS")
        print(f"Reason: {verdict['reason']}")

        return verdict

    # ========================================================
    # RULE 3 — REMOVE SERVER
    # ========================================================

    if action == "remove_server":

        # SWIM's reference manager also avoids
        # removal while a server is booting.
        if server_booting:

            verdict = {
                "status": "FAIL",
                "reason": (
                    "Cannot remove a server while "
                    "another server is booting."
                )
            }

            print("Result: FAIL")
            print(f"Reason: {verdict['reason']}")

            return verdict

        if active_servers <= min_servers:

            verdict = {
                "status": "FAIL",
                "reason": (
                    "Cannot remove a server because "
                    f"{active_servers} active server(s) "
                    f"equals the trusted minimum of "
                    f"{min_servers}."
                )
            }

            print("Result: FAIL")
            print(f"Reason: {verdict['reason']}")

            return verdict

        if (
            state["response_time"]
            >= response_time_target
        ):

            verdict = {
                "status": "FAIL",
                "reason": (
                    "Cannot remove a server while "
                    "response time is at or above "
                    "the trusted target."
                )
            }

            print("Result: FAIL")
            print(f"Reason: {verdict['reason']}")

            return verdict

        if spare_capacity <= 1.0:

            verdict = {
                "status": "FAIL",
                "reason": (
                    "Cannot remove a server because "
                    f"spare capacity is only "
                    f"{spare_capacity:.3f} "
                    "equivalent servers."
                )
            }

            print("Result: FAIL")
            print(f"Reason: {verdict['reason']}")

            return verdict

        if state["dimmer"] < dimmer_max:

            verdict = {
                "status": "FAIL",
                "reason": (
                    "Optional functionality should be "
                    "restored before removing a server. "
                    f"Current dimmer is "
                    f"{state['dimmer']} but maximum "
                    f"dimmer is {dimmer_max}."
                )
            }

            print("Result: FAIL")
            print(f"Reason: {verdict['reason']}")

            return verdict

        verdict = {
            "status": "PASS",
            "reason": (
                "remove_server satisfies trusted "
                "SWIM adaptation policies."
            )
        }

        print("Result: PASS")
        print(f"Reason: {verdict['reason']}")

        return verdict

    # ========================================================
    # RULE 4 — SET DIMMER
    # ========================================================

    if action == "set_dimmer":

        value = candidate_plan.get("value")

        if not isinstance(
            value,
            (int, float)
        ):

            verdict = {
                "status": "FAIL",
                "reason": (
                    "set_dimmer requires a numeric value."
                )
            }

            print("Result: FAIL")
            print(f"Reason: {verdict['reason']}")

            return verdict

        value = float(value)

        if (
            value < dimmer_min
            or value > dimmer_max
        ):

            verdict = {
                "status": "FAIL",
                "reason": (
                    f"Dimmer value {value} is outside "
                    f"the trusted range "
                    f"[{dimmer_min}, {dimmer_max}]."
                )
            }

            print("Result: FAIL")
            print(f"Reason: {verdict['reason']}")

            return verdict

        if abs(
            value - state["dimmer"]
        ) < 0.000001:

            verdict = {
                "status": "FAIL",
                "reason": (
                    "The proposed dimmer value is "
                    "already the current dimmer value."
                )
            }

            print("Result: FAIL")
            print(f"Reason: {verdict['reason']}")

            return verdict

        # If overloaded, do not INCREASE
        # optional workload.
        if (
            state["response_time"]
            > response_time_target
            and value > state["dimmer"]
        ):

            verdict = {
                "status": "FAIL",
                "reason": (
                    "Cannot increase optional workload "
                    "while response time exceeds "
                    "the trusted target."
                )
            }

            print("Result: FAIL")
            print(f"Reason: {verdict['reason']}")

            return verdict

        # If healthy and spare capacity exists,
        # do not REDUCE optional functionality.
        if (
            state["response_time"]
            < response_time_target
            and spare_capacity > 1.0
            and value < state["dimmer"]
        ):

            verdict = {
                "status": "FAIL",
                "reason": (
                    "The system has spare capacity, "
                    "so reducing the dimmer is not "
                    "consistent with the trusted "
                    "SWIM adaptation policy."
                )
            }

            print("Result: FAIL")
            print(f"Reason: {verdict['reason']}")

            return verdict

        verdict = {
            "status": "PASS",
            "reason": (
                "set_dimmer satisfies trusted "
                "SWIM adaptation policies."
            )
        }

        print("Result: PASS")
        print(f"Reason: {verdict['reason']}")

        return verdict

    # ========================================================
    # RULE 5 — NONE
    # ========================================================

    if action == "none":

        if (
            state["response_time"]
            > response_time_target
        ):

            verdict = {
                "status": "FAIL",
                "reason": (
                    "No adaptation was proposed while "
                    f"response time "
                    f"{state['response_time']:.4f} seconds "
                    f"exceeds the target of "
                    f"{response_time_target} seconds."
                )
            }

            print("Result: FAIL")
            print(f"Reason: {verdict['reason']}")

            return verdict

        verdict = {
            "status": "PASS",
            "reason": (
                "No adaptation is required under "
                "the current trusted SWIM conditions."
            )
        }

        print("Result: PASS")
        print(f"Reason: {verdict['reason']}")

        return verdict

    # ========================================================
    # FALLBACK
    # ========================================================

    verdict = {
        "status": "FAIL",
        "reason": (
            "Unknown SWIM safety-check condition."
        )
    }

    print("Result: FAIL")
    print(f"Reason: {verdict['reason']}")

    return verdict


if __name__ == "__main__":

    current_state = monitor()

    diagnosis = analyze(
        current_state
    )

    candidate_plan = plan(
        current_state,
        diagnosis
    )

    safety_check(
        candidate_plan,
        current_state
    )
