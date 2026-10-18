from llm_client import ask_llm


def route_failure(state, diagnosis, verdict):
    print("\n=== FAILURE ROUTING ===")
    print(f"Failure reason: {verdict['reason']}")

    prompt = f"""
You are controlling a self-adaptive web system.

Current runtime state:
- Response time: {state['response_time']} seconds
- Active servers: {state['active_servers']}
- CPU utilization: {state['utilization'] * 100:.0f}%
- Dimmer: {state['dimmer']}

Current diagnosis:
{diagnosis}

A candidate adaptation plan was rejected.

Failure reason:
{verdict['reason']}

Choose where the Agentic Adaptation Controller should return:

MONITOR
Use this if the runtime observations are missing, stale, or insufficient.

ANALYZE
Use this if the diagnosis or assumptions may be wrong and should be reconsidered.

REPLAN
Use this if the diagnosis is still reasonable but the candidate plan itself violates a constraint or needs modification.

Return ONLY one word:

MONITOR
ANALYZE
REPLAN
"""

    decision = ask_llm(prompt)

    if decision is None:
        return "replan"

    route = decision.strip().lower()

    if route not in ["monitor", "analyze", "replan"]:
        print("Invalid routing response. Defaulting to REPLAN.")
        route = "replan"

    print(f"Agent selected route: {route.upper()}")

    return route


if __name__ == "__main__":

    test_state = {
        "response_time": 4.0,
        "active_servers": 4,
        "utilization": 0.94,
        "dimmer": 1.0
    }

    test_diagnosis = "workload_saturation"

    test_verdict = {
        "status": "FAIL",
        "reason": "Target servers 7 exceeds maximum allowed 6"
    }

    route_failure(
        test_state,
        test_diagnosis,
        test_verdict
    )
