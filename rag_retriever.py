import json
import math

from embedding_test import get_embedding


KB_FILE = "runtime_kb.json"
POLICY_FILE = "trusted_policies.json"


# ============================================================
# LOAD DATA
# ============================================================

def load_runtime_episodes():

    try:

        with open(KB_FILE, "r") as file:
            return json.load(file)

    except FileNotFoundError:

        return []


def load_policies():

    with open(POLICY_FILE, "r") as file:
        return json.load(file)


# ============================================================
# CLASSIFY RUNTIME REGIME
# ============================================================

def classify_runtime_regime(state):

    policies = load_policies()

    response_time_target = policies[
        "response_time_target"
    ]

    response_time = state.get(
        "response_time",
        0.0
    )

    arrival_rate = state.get(
        "arrival_rate",
        0.0
    )

    # --------------------------------------------------------
    # IDLE / NO WORKLOAD
    # --------------------------------------------------------

    if arrival_rate <= 0.01:

        return "idle"

    # --------------------------------------------------------
    # OVERLOADED
    # --------------------------------------------------------

    if response_time > response_time_target:

        return "overloaded"

    # --------------------------------------------------------
    # HEALTHY WITH WORKLOAD
    # --------------------------------------------------------

    return "healthy"


# ============================================================
# EPISODE → SEMANTIC TEXT
# ============================================================

def episode_to_text(episode):

    initial_state = episode.get(
        "initial_state",
        {}
    )

    final_state = episode.get(
        "final_state",
        {}
    )

    final_plan = episode.get(
        "final_plan",
        {}
    )

    safety_verdict = episode.get(
        "safety_verdict",
        episode.get(
            "first_verdict",
            {}
        )
    )

    actual_outcome = episode.get(
        "execution_outcome",
        episode.get(
            "final_verdict",
            {}
        )
    )

    outcome_status = actual_outcome.get(
        "status"
    )

    runtime_regime = classify_runtime_regime(
        initial_state
    )

    if outcome_status == "PASS":

        experience_meaning = (
            "SUCCESSFUL EXPERIENCE. "
            "The action took effect and the "
            "runtime goal was achieved."
        )

    elif outcome_status == "PARTIAL":

        experience_meaning = (
            "PARTIAL EXPERIENCE. "
            "The action took effect successfully, "
            "but the runtime goal remained violated. "
            "Additional adaptation may have been needed."
        )

    elif outcome_status == "FAIL":

        experience_meaning = (
            "FAILED EXPERIENCE. "
            "The adaptation did not take effect, "
            "or no safe executable adaptation "
            "was found."
        )

    else:

        experience_meaning = (
            "UNKNOWN EXPERIENCE OUTCOME."
        )

    return f"""
REAL SWIM ADAPTATION EPISODE

RUNTIME REGIME:
{runtime_regime}

EXPERIENCE INTERPRETATION:
{experience_meaning}

INITIAL STATE

Response time:
{initial_state.get('response_time')}

Total servers:
{initial_state.get('servers')}

Active servers:
{initial_state.get('active_servers')}

Maximum servers:
{initial_state.get('max_servers')}

Server booting:
{initial_state.get('server_booting')}

Average utilization:
{initial_state.get('utilization')}

Total utilization:
{initial_state.get('total_utilization')}

Dimmer:
{initial_state.get('dimmer')}

Arrival rate:
{initial_state.get('arrival_rate')}


DIAGNOSIS

{episode.get('diagnosis')}


FINAL PLAN

Action:
{final_plan.get('action')}

Dimmer value:
{final_plan.get('value')}


PRE-EXECUTION SAFETY VERDICT

Status:
{safety_verdict.get('status')}

Reason:
{safety_verdict.get('reason')}


ACTUAL POST-EXECUTION OUTCOME

Status:
{actual_outcome.get('status')}

Action effect observed:
{actual_outcome.get('action_effect_observed')}

Goal satisfied:
{actual_outcome.get('goal_satisfied')}

Reason:
{actual_outcome.get('reason')}


FINAL STATE

Response time:
{final_state.get('response_time')}

Total servers:
{final_state.get('servers')}

Active servers:
{final_state.get('active_servers')}

Server booting:
{final_state.get('server_booting')}

Average utilization:
{final_state.get('utilization')}

Total utilization:
{final_state.get('total_utilization')}

Dimmer:
{final_state.get('dimmer')}

Arrival rate:
{final_state.get('arrival_rate')}
"""


# ============================================================
# CURRENT STATE → SEMANTIC QUERY
# ============================================================

def state_to_query(state):

    runtime_regime = classify_runtime_regime(
        state
    )

    return f"""
Find the most relevant previous REAL SWIM
adaptation experience for this current state.

CURRENT RUNTIME REGIME:
{runtime_regime}

CURRENT STATE

Response time:
{state.get('response_time')}

Total servers:
{state.get('servers')}

Active servers:
{state.get('active_servers')}

Maximum servers:
{state.get('max_servers')}

Server booting:
{state.get('server_booting')}

Average utilization:
{state.get('utilization')}

Total utilization:
{state.get('total_utilization')}

Dimmer:
{state.get('dimmer')}

Arrival rate:
{state.get('arrival_rate')}

Outcome interpretation:

PASS means the action took effect and the
runtime goal was achieved.

PARTIAL means the action took effect but
additional adaptation may still have been
needed.

FAIL means the action itself did not take
effect, or no safe executable adaptation
was found.
"""


# ============================================================
# COSINE SIMILARITY
# ============================================================

def cosine_similarity(
    vector_a,
    vector_b
):

    dot_product = sum(
        a * b
        for a, b in zip(
            vector_a,
            vector_b
        )
    )

    magnitude_a = math.sqrt(
        sum(
            a * a
            for a in vector_a
        )
    )

    magnitude_b = math.sqrt(
        sum(
            b * b
            for b in vector_b
        )
    )

    if (
        magnitude_a == 0
        or magnitude_b == 0
    ):

        return 0.0

    return (
        dot_product
        / (
            magnitude_a
            * magnitude_b
        )
    )


# ============================================================
# STATE-AWARE SEMANTIC RAG
# ============================================================

def retrieve_relevant_episode(state):

    print("\n=== RAG RETRIEVAL ===")

    episodes = load_runtime_episodes()

    if not episodes:

        print(
            "No runtime episodes are available."
        )

        return None

    current_regime = classify_runtime_regime(
        state
    )

    print(
        f"Current Runtime Regime: "
        f"{current_regime}"
    )

    # ========================================================
    # FIRST FILTER BY RUNTIME REGIME
    # ========================================================

    matching_episodes = []

    for episode in episodes:

        initial_state = episode.get(
            "initial_state",
            {}
        )

        episode_regime = classify_runtime_regime(
            initial_state
        )

        if episode_regime == current_regime:

            matching_episodes.append(
                episode
            )

    # If there is no same-regime historical
    # experience, fall back to the complete KB.
    if matching_episodes:

        candidate_episodes = (
            matching_episodes
        )

        print(
            "Retrieval Scope: "
            "same-regime episodes"
        )

        print(
            f"Candidate Episodes: "
            f"{len(candidate_episodes)}"
        )

    else:

        candidate_episodes = episodes

        print(
            "No same-regime episode exists."
        )

        print(
            "Retrieval Scope: "
            "all runtime episodes"
        )

    # ========================================================
    # THEN APPLY EMBEDDING SIMILARITY
    # ========================================================

    query_text = state_to_query(
        state
    )

    query_embedding = get_embedding(
        query_text
    )

    best_episode = None
    best_similarity = -1.0

    for episode in candidate_episodes:

        episode_text = episode_to_text(
            episode
        )

        episode_embedding = get_embedding(
            episode_text
        )

        similarity = cosine_similarity(
            query_embedding,
            episode_embedding
        )

        if similarity > best_similarity:

            best_similarity = similarity
            best_episode = episode

    # ========================================================
    # DISPLAY RETRIEVED EXPERIENCE
    # ========================================================

    if best_episode is not None:

        final_plan = best_episode.get(
            "final_plan",
            {}
        )

        actual_outcome = best_episode.get(
            "execution_outcome",
            best_episode.get(
                "final_verdict",
                {}
            )
        )

        final_state = best_episode.get(
            "final_state",
            {}
        )

        initial_state = best_episode.get(
            "initial_state",
            {}
        )

        status = actual_outcome.get(
            "status"
        )

        retrieved_regime = (
            classify_runtime_regime(
                initial_state
            )
        )

        print(
            "Most relevant past episode retrieved."
        )

        print(
            f"Retrieved Runtime Regime: "
            f"{retrieved_regime}"
        )

        print(
            f"Similarity score: "
            f"{best_similarity:.4f}"
        )

        print(
            f"Retrieved diagnosis: "
            f"{best_episode.get('diagnosis')}"
        )

        print(
            f"Retrieved final action: "
            f"{final_plan.get('action')}"
        )

        if (
            final_plan.get("action")
            == "set_dimmer"
        ):

            print(
                f"Retrieved dimmer value: "
                f"{final_plan.get('value')}"
            )

        print(
            f"Retrieved adaptation outcome: "
            f"{status}"
        )

        print(
            f"Action effect observed: "
            f"{actual_outcome.get('action_effect_observed')}"
        )

        print(
            f"Goal satisfied: "
            f"{actual_outcome.get('goal_satisfied')}"
        )

        print(
            f"Retrieved outcome reason: "
            f"{actual_outcome.get('reason')}"
        )

        print(
            f"Retrieved initial servers: "
            f"{initial_state.get('servers')}"
        )

        print(
            f"Retrieved initial arrival rate: "
            f"{initial_state.get('arrival_rate')}"
        )

        print(
            f"Retrieved final servers: "
            f"{final_state.get('servers')}"
        )

        print(
            f"Retrieved final response time: "
            f"{final_state.get('response_time')}"
        )

        if status == "PASS":

            print(
                "Memory interpretation: "
                "successful adaptation experience."
            )

        elif status == "PARTIAL":

            print(
                "Memory interpretation: "
                "action worked, but additional "
                "adaptation may have been required."
            )

        elif status == "FAIL":

            print(
                "Memory interpretation: "
                "failed or non-executable "
                "adaptation experience."
            )

    return best_episode


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test_state = {
        "response_time": 0.0,
        "servers": 1,
        "active_servers": 1,
        "max_servers": 6,
        "server_booting": False,
        "utilization": 0.0,
        "total_utilization": 0.0,
        "dimmer": 1.0,
        "arrival_rate": 0.0
    }

    retrieve_relevant_episode(
        test_state
    )
