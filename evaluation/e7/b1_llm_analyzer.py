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
# B1 — LLM-ONLY ANALYSIS
# ============================================================

def analyze_b1(state):

    """
    B1 analysis.

    Uses:
    - current runtime state
    - trusted response-time target
    - LLM reasoning

    Does NOT use:
    - RAG
    - runtime KB
    - previous episodes
    - agentic recovery
    """

    print(
        "\n=== E7 B1 — LLM-ONLY ANALYSIS ==="
    )

    policies = load_policies()

    response_time_target = float(
        policies[
            "response_time_target"
        ]
    )


    prompt = f"""
You are analyzing the SWIM self-adaptive
web-system exemplar.

This is the B1 experimental configuration.

IMPORTANT:
You must reason ONLY from the CURRENT runtime
state and the trusted policy values shown below.

Do NOT assume access to:
- previous adaptation episodes
- runtime memory
- retrieval-augmented generation
- historical outcomes


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


Diagnose the current SWIM condition.

Use the CURRENT observations as the only
runtime evidence.

Interpretation:

workload_saturation
- response time is above the trusted target
  and the system appears overloaded.

normal
- response time is within the trusted target.
- the system may still have spare capacity.

unknown
- available current-state evidence is
  insufficient or contradictory.


Return ONLY one of these labels:

workload_saturation
normal
unknown
"""


    llm_output = ask_llm(
        prompt
    )


    if llm_output:

        diagnosis = (
            llm_output
            .strip()
            .lower()
        )

    else:

        diagnosis = "unknown"


    allowed = {
        "workload_saturation",
        "normal",
        "unknown"
    }


    if diagnosis not in allowed:

        print(
            "Invalid B1 diagnosis returned by LLM."
        )

        diagnosis = "unknown"


    print(
        "B1 LLM Diagnosis:",
        diagnosis
    )

    print(
        "Runtime RAG Used: False"
    )

    print(
        "Runtime Memory Used: False"
    )


    return diagnosis


# ============================================================
# INFORMATIONAL MODE
# ============================================================

if __name__ == "__main__":

    print(
        "B1 LLM-only analyzer loaded."
    )

    print(
        "Running this file directly does NOT "
        "call the LLM."
    )
