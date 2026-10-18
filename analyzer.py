import json

from monitor import monitor
from rag_retriever import retrieve_relevant_episode
from llm_client import ask_llm


POLICY_FILE = "trusted_policies.json"


def load_policies():

    with open(POLICY_FILE, "r") as file:
        return json.load(file)


def analyze(state):

    print("\n=== ANALYZE — REAL SWIM ===")

    # ========================================================
    # STEP 1 — LOAD TRUSTED SWIM POLICIES
    # ========================================================

    policies = load_policies()

    response_time_target = policies[
        "response_time_target"
    ]

    # ========================================================
    # STEP 2 — RETRIEVE REAL SWIM EXPERIENCE
    # ========================================================

    retrieved_episode = retrieve_relevant_episode(
        state
    )

    if retrieved_episode is not None:

        previous_verdict = retrieved_episode.get(
            "final_verdict",
            {}
        )

        retrieved_context = f"""
A semantically similar REAL SWIM runtime
episode was retrieved.

Past diagnosis:
{retrieved_episode.get('diagnosis')}

Past adaptation outcome:
{previous_verdict.get('status')}

Past verdict reason:
{previous_verdict.get('reason')}

Past final response time:
{retrieved_episode.get('final_state', {}).get('response_time')}

Past final active servers:
{retrieved_episode.get('final_state', {}).get('active_servers')}

Past final utilization:
{retrieved_episode.get('final_state', {}).get('utilization')}

A PASS episode may provide positive evidence.

A FAIL episode should be treated as negative
experience and should not be blindly repeated.
"""

    else:

        retrieved_context = """
No previous REAL SWIM adaptation episode
is available yet.
"""

    # ========================================================
    # STEP 3 — RAG-AUGMENTED LLM ANALYSIS
    # ========================================================

    prompt = f"""
You are analyzing the REAL SWIM
self-adaptive web-system exemplar.

CURRENT SWIM STATE:

Average response time:
{state['response_time']} seconds

Active servers:
{state['active_servers']}

Maximum servers:
{state['max_servers']}

Average utilization:
{state['utilization'] * 100:.1f}%

Dimmer:
{state['dimmer']}

Arrival rate:
{state['arrival_rate']}

Basic response time:
{state['basic_response_time']} seconds

Optional response time:
{state['optional_response_time']} seconds


TRUSTED RESPONSE-TIME TARGET:

{response_time_target} seconds


RETRIEVED RUNTIME KNOWLEDGE:

{retrieved_context}


Diagnose the current SWIM condition.

Use the CURRENT SWIM observations as the
primary evidence.

Interpretation:

workload_saturation
- response time is above the trusted target
  and the system appears overloaded.

normal
- response time is within the trusted target.
- The system may still have spare capacity;
  planning may optimize resources or dimmer.

unknown
- available evidence is insufficient or
  contradictory.


Return ONLY one of these labels:

workload_saturation
normal
unknown
"""

    llm_diagnosis = ask_llm(
        prompt
    )

    if llm_diagnosis:

        diagnosis = (
            llm_diagnosis
            .strip()
            .lower()
        )

    else:

        diagnosis = "unknown"

    # ========================================================
    # STEP 4 — DISPLAY RESULT
    # ========================================================

    print(
        "\n=== RAG-AUGMENTED "
        "REAL SWIM LLM DIAGNOSIS ==="
    )

    print(
        f"LLM Diagnosis: {diagnosis}"
    )

    print(
        f"Trusted Response-Time Target: "
        f"{response_time_target} seconds"
    )

    return diagnosis


if __name__ == "__main__":

    current_state = monitor()

    analyze(
        current_state
    )
