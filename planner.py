import json

from monitor import monitor
from analyzer import analyze
from rag_retriever import retrieve_relevant_episode
from llm_client import ask_llm


POLICY_FILE = "trusted_policies.json"


def load_policies():

    with open(POLICY_FILE, "r") as file:
        return json.load(file)


def plan(state, diagnosis):

    print("\n=== PLAN — REAL SWIM ===")

    policies = load_policies()

    response_time_target = policies[
        "response_time_target"
    ]

    max_servers = policies[
        "max_servers"
    ]

    min_servers = policies[
        "min_servers"
    ]

    dimmer_min = policies[
        "dimmer_min"
    ]

    dimmer_max = policies[
        "dimmer_max"
    ]

    dimmer_step = policies[
        "dimmer_step"
    ]

    allowed_actions = policies[
        "allowed_actions"
    ]

    total_utilization = state.get(
        "total_utilization",
        state["utilization"]
        * state["active_servers"]
    )

    spare_capacity = (
        state["active_servers"]
        - total_utilization
    )

    # ========================================================
    # RAG RETRIEVAL
    # ========================================================

    retrieved_episode = (
        retrieve_relevant_episode(
            state
        )
    )

    if retrieved_episode is not None:

        past_plan = retrieved_episode.get(
            "final_plan",
            {}
        )

        actual_outcome = retrieved_episode.get(
            "execution_outcome",
            retrieved_episode.get(
                "final_verdict",
                {}
            )
        )

        past_final_state = retrieved_episode.get(
            "final_state",
            {}
        )

        outcome_status = actual_outcome.get(
            "status"
        )

        if outcome_status == "PASS":

            experience_interpretation = (
                "This was a successful adaptation. "
                "The action took effect and the runtime "
                "goal was achieved."
            )

        elif outcome_status == "PARTIAL":

            experience_interpretation = (
                "This was a PARTIAL adaptation. "
                "The action itself took effect successfully, "
                "but the runtime goal remained violated. "
                "Do NOT treat the action itself as failed. "
                "If the current state is still overloaded "
                "and additional capacity remains available, "
                "another adaptation of the same type may "
                "still be appropriate."
            )

        elif outcome_status == "FAIL":

            experience_interpretation = (
                "This was a failed or non-executable "
                "adaptation. The previous action should "
                "not be blindly repeated."
            )

        else:

            experience_interpretation = (
                "The previous outcome is unknown."
            )

        retrieved_context = f"""
A semantically similar REAL SWIM adaptation
episode was retrieved.

Past diagnosis:
{retrieved_episode.get('diagnosis')}

Past final action:
{past_plan.get('action')}

Past dimmer value:
{past_plan.get('value')}

Past adaptation outcome:
{outcome_status}

Past action effect observed:
{actual_outcome.get('action_effect_observed')}

Past goal satisfied:
{actual_outcome.get('goal_satisfied')}

Past outcome reason:
{actual_outcome.get('reason')}

Past final total servers:
{past_final_state.get('servers')}

Past final active servers:
{past_final_state.get('active_servers')}

Past final response time:
{past_final_state.get('response_time')}

Past final utilization:
{past_final_state.get('utilization')}

EXPERIENCE INTERPRETATION:

{experience_interpretation}
"""

    else:

        retrieved_context = """
No previous REAL SWIM adaptation episode
is available yet.
"""

    # ========================================================
    # LLM PLANNING PROMPT
    # ========================================================

    prompt = f"""
You are the planning component of an
agentic controller for the REAL SWIM exemplar.

CURRENT SWIM STATE:

Average response time:
{state['response_time']} seconds

Response-time target:
{response_time_target} seconds

Total servers:
{state['servers']}

Active servers:
{state['active_servers']}

Maximum servers reported by SWIM:
{state['max_servers']}

Is a server currently booting?
{state['server_booting']}

Average utilization:
{state['utilization'] * 100:.1f}%

Total utilization:
{total_utilization}

Equivalent spare capacity:
{spare_capacity}

Current dimmer:
{state['dimmer']}

Arrival rate:
{state['arrival_rate']}

CURRENT DIAGNOSIS:
{diagnosis}


TRUSTED POLICIES:

Minimum servers:
{min_servers}

Maximum servers:
{max_servers}

Minimum dimmer:
{dimmer_min}

Maximum dimmer:
{dimmer_max}

Dimmer step:
{dimmer_step}

Allowed actions:
{allowed_actions}


RETRIEVED RUNTIME KNOWLEDGE:

{retrieved_context}


IMPORTANT MEMORY SEMANTICS:

PASS:
The previous action took effect and the
runtime goal was achieved.

PARTIAL:
The previous action took effect successfully,
but the goal remained violated.

A PARTIAL action is NOT automatically a bad
action.

For example, if a previous add_server action
was PARTIAL because one added server was not
enough, and the current system is still above
the response-time target with additional
server capacity available, another add_server
action may be appropriate.

FAIL:
The action itself did not take effect, or no
safe executable adaptation was found.
Do not blindly repeat a failed action.


Follow the adaptation priorities used by
the SWIM reference controller.


CASE 1 — RESPONSE TIME ABOVE TARGET

If response time is above
{response_time_target} seconds:

1. If NO server is already booting and the
   total number of servers is below the
   maximum, prefer add_server.

2. A previous PARTIAL add_server outcome
   does not prohibit another add_server.
   It may mean that additional capacity
   is still required.

3. If a server is already booting, DO NOT
   request another add_server action.

4. If additional server capacity is not
   available, consider lowering the dimmer
   to reduce optional workload.

5. Never exceed the maximum server count.


CASE 2 — RESPONSE TIME BELOW TARGET

If response time is below the target:

1. Determine whether substantial spare
   capacity exists.

2. If spare capacity is greater than one
   equivalent server AND dimmer is below 1.0,
   restore optional functionality FIRST by
   increasing the dimmer.

3. Only after the dimmer is already 1.0,
   consider remove_server when enough spare
   capacity exists.

4. Do not remove a server while another
   server is booting.

5. Never remove below the minimum server
   count.


IMPORTANT:

For the current dimmer, changing it upward
or downward should normally follow the
trusted step of {dimmer_step}, clipped to
the permitted range
[{dimmer_min}, {dimmer_max}].

Choose ONE candidate action.

Return ONLY valid JSON.


Add server:

{{
    "action": "add_server"
}}


Remove server:

{{
    "action": "remove_server"
}}


Change dimmer:

{{
    "action": "set_dimmer",
    "value": 1.0
}}


No adaptation:

{{
    "action": "none"
}}
"""

    llm_output = ask_llm(
        prompt
    )

    try:

        candidate_plan = json.loads(
            llm_output
        )

        print(
            "\n=== RAG-AUGMENTED "
            "REAL SWIM LLM PLAN ==="
        )

        print(
            "LLM Candidate Plan:"
        )

        print(
            candidate_plan
        )

        print(
            f"Calculated Spare Capacity: "
            f"{spare_capacity:.3f}"
        )

        print(
            f"Server Booting: "
            f"{state['server_booting']}"
        )

        return candidate_plan

    except Exception:

        print(
            "\n=== RAG-AUGMENTED "
            "REAL SWIM LLM PLAN ==="
        )

        print(
            "LLM returned an invalid "
            "plan format."
        )

        return {
            "action": "none"
        }


if __name__ == "__main__":

    current_state = monitor()

    diagnosis = analyze(
        current_state
    )

    plan(
        current_state,
        diagnosis
    )
