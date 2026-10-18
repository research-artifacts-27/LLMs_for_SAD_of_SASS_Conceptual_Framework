#!/usr/bin/env python3

import json
import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve()
    .parents[2]
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )


from llm_client import ask_llm


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
# B1 — LLM-ONLY PLANNING
# ============================================================

def plan_b1(
    state,
    diagnosis
):

    """
    B1 planning.

    Uses:
    - current runtime state
    - current LLM diagnosis
    - trusted policies
    - LLM reasoning

    Does NOT use:
    - RAG
    - runtime KB
    - previous episodes
    - failure routing
    - replanning
    - deterministic fallback

    The returned candidate must still pass the
    common deterministic safety checker.
    """

    print(
        "\n=== E7 B1 — LLM-ONLY PLANNING ==="
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


    prompt = f"""
You are the planning component for the SWIM
self-adaptive web-system exemplar.

This is the B1 experimental configuration.

IMPORTANT:
Reason ONLY from:
- the CURRENT runtime state
- the CURRENT diagnosis
- the trusted policies shown below

Do NOT assume access to:
- previous runtime episodes
- runtime memory
- retrieval-augmented generation
- historical adaptation outcomes
- agentic failure routing
- replanning history


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


ADAPTATION PRIORITIES:


CASE 1 — RESPONSE TIME ABOVE TARGET

If response time is above
{response_time_target} seconds:

1. If NO server is already booting and the
   total number of servers is below the
   maximum, prefer add_server.

2. If a server is already booting, do NOT
   request another add_server action.

3. If additional server capacity is not
   available, consider lowering the dimmer
   to reduce optional workload.

4. Never exceed the maximum server count.


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
        ] = "B1_llm_only"

        candidate_plan[
            "decision_reason"
        ] = (
            "LLM-generated candidate based only "
            "on the current state, diagnosis, "
            "and trusted policies."
        )


        print(
            "B1 LLM Candidate Plan:",
            candidate_plan
        )

        print(
            "Runtime RAG Used: False"
        )

        print(
            "Runtime Memory Used: False"
        )


        return candidate_plan


    except Exception:

        print(
            "B1 LLM returned an invalid "
            "planning format."
        )

        return {
            "action":
                "none",

            "decision_source":
                "B1_llm_only_invalid_output",

            "decision_reason":
                (
                    "Invalid LLM planning output; "
                    "safe no-action candidate returned."
                )
        }


# ============================================================
# INFORMATIONAL MODE
# ============================================================

if __name__ == "__main__":

    print(
        "B1 LLM-only planner loaded."
    )

    print(
        "Running this file directly does NOT "
        "call the LLM."
    )
