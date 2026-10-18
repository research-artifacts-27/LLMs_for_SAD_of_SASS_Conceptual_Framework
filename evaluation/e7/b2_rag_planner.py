#!/usr/bin/env python3

import json
import sys
from pathlib import Path


# ============================================================
# PROJECT IMPORTS
# ============================================================

PROJECT_ROOT = (
    Path(__file__).resolve()
    .parents[2]
)

E7_DIR = (
    PROJECT_ROOT
    / "evaluation"
    / "e7"
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )

if str(E7_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(E7_DIR)
    )


from llm_client import ask_llm

from b2_rag_retriever import (
    retrieve_b2_episode
)


POLICY_FILE = (
    PROJECT_ROOT
    / "trusted_policies.json"
)


# ============================================================
# LOAD TRUSTED POLICIES
# ============================================================

def load_policies():

    with POLICY_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# B2 — RAG-AUGMENTED PLANNING
# ============================================================

def plan_b2(
    state,
    diagnosis,
    run_id
):

    """
    B2 planning.

    Uses:
    - current runtime state
    - current diagnosis
    - trusted policies
    - isolated B2 runtime RAG
    - LLM reasoning

    Does NOT use:
    - B3/project runtime_kb.json
    - agentic failure routing
    - bounded replanning
    - deterministic fallback

    The returned candidate must still pass the
    common deterministic safety checker.
    """

    print(
        "\n=== E7 B2 — RAG-AUGMENTED PLANNING ==="
    )

    policies = load_policies()

    response_time_target = float(
        policies[
            "response_time_target"
        ]
    )

    max_servers = int(
        policies[
            "max_servers"
        ]
    )

    min_servers = int(
        policies[
            "min_servers"
        ]
    )

    dimmer_min = float(
        policies[
            "dimmer_min"
        ]
    )

    dimmer_max = float(
        policies[
            "dimmer_max"
        ]
    )

    dimmer_step = float(
        policies[
            "dimmer_step"
        ]
    )

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
    # RETRIEVE FROM THIS B2 RUN ONLY
    # ========================================================

    retrieved_episode = (
        retrieve_b2_episode(
            state,
            run_id
        )
    )


    if retrieved_episode is not None:

        previous_plan = (
            retrieved_episode.get(
                "candidate_plan",
                retrieved_episode.get(
                    "final_plan",
                    {}
                )
            )
        )

        actual_outcome = (
            retrieved_episode.get(
                "execution_outcome",
                retrieved_episode.get(
                    "final_verdict",
                    {}
                )
            )
        )

        previous_final_state = (
            retrieved_episode.get(
                "final_state",
                {}
            )
        )

        outcome_status = (
            actual_outcome.get(
                "status"
            )
        )


        # ====================================================
        # MEMORY SEMANTICS
        # ====================================================

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
A semantically relevant adaptation episode
from THIS B2 experimental run was retrieved.

Past diagnosis:
{retrieved_episode.get('diagnosis')}

Past action:
{previous_plan.get('action')}

Past dimmer value:
{previous_plan.get('value')}

Past adaptation outcome:
{outcome_status}

Past action effect observed:
{actual_outcome.get('action_effect_observed')}

Past goal satisfied:
{actual_outcome.get('goal_satisfied')}

Past outcome reason:
{actual_outcome.get('reason')}

Past final total servers:
{previous_final_state.get('servers')}

Past final active servers:
{previous_final_state.get('active_servers')}

Past final response time:
{previous_final_state.get('response_time')}

Past final utilization:
{previous_final_state.get('utilization')}


EXPERIENCE INTERPRETATION:

{experience_interpretation}
"""

    else:

        retrieved_context = """
No previous B2 adaptation episode is available
for this experimental run.
"""


    # ========================================================
    # RAG-AUGMENTED LLM PLANNING
    # ========================================================

    prompt = f"""
You are the planning component for the SWIM
self-adaptive web-system exemplar.

This is the B2 experimental configuration.

Use:
- the CURRENT runtime state
- the CURRENT diagnosis
- the trusted policies
- runtime experience retrieved ONLY from
  this B2 experimental run

Do NOT assume access to:
- B3 runtime history
- project-level runtime_kb.json
- agentic failure routing
- replanning history
- deterministic fallback


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


RETRIEVED B2 RUNTIME KNOWLEDGE:

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
action may still be appropriate.

FAIL:
The action itself did not take effect, or no
safe executable adaptation was found.

Do not blindly repeat a failed action.


ADAPTATION PRIORITIES:


CASE 1 — RESPONSE TIME ABOVE TARGET

If response time is above
{response_time_target} seconds:

1. If NO server is already booting and the
   total number of servers is below the
   maximum, prefer add_server.

2. A previous PARTIAL add_server outcome
   does not prohibit another add_server.

3. If a server is already booting, do NOT
   request another add_server action.

4. If additional server capacity is not
   available, consider lowering the dimmer
   to reduce optional workload.

5. Never exceed the maximum server count.


CASE 2 — RESPONSE TIME WITHIN TARGET

If response time is within the target:

1. Determine whether substantial spare
   capacity exists.

2. If spare capacity is greater than one
   equivalent server AND dimmer is below 1.0,
   restore optional functionality FIRST by
   increasing the dimmer.

3. Only after the dimmer is already 1.0,
   consider remove_server when sufficient
   spare capacity exists.

4. Do not remove a server while another
   server is booting.

5. Never remove below the minimum server
   count.


DIMMER RULE:

Changing the dimmer should normally follow
the trusted step of {dimmer_step}, clipped
to the permitted range
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
    "value": 0.75
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

        if not isinstance(
            candidate_plan,
            dict
        ):

            raise ValueError(
                "LLM output is not a JSON object."
            )


        candidate_plan[
            "decision_source"
        ] = "B2_llm_rag"

        candidate_plan[
            "decision_reason"
        ] = (
            "LLM-generated candidate based on "
            "current runtime evidence, trusted "
            "policies, and isolated B2 runtime RAG."
        )


        print(
            "B2 LLM Candidate Plan:",
            candidate_plan
        )

        print(
            "Runtime RAG Used:",
            retrieved_episode is not None
        )

        print(
            "Runtime Memory Source: "
            "isolated B2 run"
        )


        return candidate_plan


    except Exception:

        print(
            "B2 LLM returned an invalid "
            "planning format."
        )

        return {
            "action":
                "none",

            "decision_source":
                "B2_llm_rag_invalid_output",

            "decision_reason":
                (
                    "Invalid B2 LLM planning output; "
                    "safe no-action candidate returned."
                )
        }


# ============================================================
# INFORMATIONAL MODE
# ============================================================

if __name__ == "__main__":

    print(
        "B2 RAG-augmented planner loaded."
    )

    print(
        "Running this file directly does NOT "
        "call embeddings or the LLM."
    )

    print(
        "B2 retrieval requires an explicit run_id."
    )
