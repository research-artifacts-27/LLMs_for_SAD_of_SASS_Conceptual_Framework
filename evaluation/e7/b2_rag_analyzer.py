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
# B2 — RAG-AUGMENTED ANALYSIS
# ============================================================

def analyze_b2(
    state,
    run_id
):

    """
    B2 analysis.

    Uses:
    - current runtime state
    - trusted response-time target
    - isolated B2 runtime RAG
    - LLM reasoning

    Does NOT use:
    - B3/project runtime_kb.json
    - agentic failure routing
    - bounded replanning
    - deterministic fallback
    """

    print(
        "\n=== E7 B2 — RAG-AUGMENTED ANALYSIS ==="
    )

    policies = load_policies()

    response_time_target = float(
        policies[
            "response_time_target"
        ]
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

        previous_outcome = (
            retrieved_episode.get(
                "execution_outcome",
                retrieved_episode.get(
                    "final_verdict",
                    {}
                )
            )
        )

        previous_plan = (
            retrieved_episode.get(
                "candidate_plan",
                retrieved_episode.get(
                    "final_plan",
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


        retrieved_context = f"""
A semantically relevant adaptation episode
from THIS B2 experimental run was retrieved.

Past diagnosis:
{retrieved_episode.get('diagnosis')}

Past action:
{previous_plan.get('action')}

Past adaptation outcome:
{previous_outcome.get('status')}

Past action effect observed:
{previous_outcome.get('action_effect_observed')}

Past goal satisfied:
{previous_outcome.get('goal_satisfied')}

Past outcome reason:
{previous_outcome.get('reason')}

Past final response time:
{previous_final_state.get('response_time')}

Past final active servers:
{previous_final_state.get('active_servers')}

Past final utilization:
{previous_final_state.get('utilization')}

Interpret the retrieved episode as historical
experience only.

The CURRENT runtime observations remain the
primary evidence.
"""

    else:

        retrieved_context = """
No previous B2 adaptation episode is available
for this experimental run.
"""


    # ========================================================
    # RAG-AUGMENTED LLM ANALYSIS
    # ========================================================

    prompt = f"""
You are analyzing the SWIM self-adaptive
web-system exemplar.

This is the B2 experimental configuration.

Use:
- the CURRENT runtime state
- the trusted response-time target
- runtime experience retrieved ONLY from
  this B2 experimental run

Do NOT assume access to:
- B3 runtime history
- project-level runtime_kb.json
- agentic failure routing
- replanning history


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


RETRIEVED B2 RUNTIME KNOWLEDGE:

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
- the system may still have spare capacity.

unknown
- available evidence is insufficient or
  contradictory.


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
            "Invalid B2 diagnosis returned by LLM."
        )

        diagnosis = "unknown"


    print(
        "B2 LLM Diagnosis:",
        diagnosis
    )

    print(
        "Runtime RAG Used:",
        retrieved_episode is not None
    )

    print(
        "Runtime Memory Source: "
        "isolated B2 run"
    )


    return diagnosis


# ============================================================
# INFORMATIONAL MODE
# ============================================================

if __name__ == "__main__":

    print(
        "B2 RAG-augmented analyzer loaded."
    )

    print(
        "Running this file directly does NOT "
        "call embeddings or the LLM."
    )

    print(
        "B2 retrieval requires an explicit run_id."
    )
