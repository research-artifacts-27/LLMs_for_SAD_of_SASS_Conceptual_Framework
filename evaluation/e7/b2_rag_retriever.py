#!/usr/bin/env python3

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


from embedding_test import get_embedding

from rag_retriever import (
    classify_runtime_regime,
    state_to_query,
    episode_to_text,
    cosine_similarity
)

from e7_runtime_memory import (
    load_run_episodes
)


# ============================================================
# B2 — ISOLATED STATE-AWARE SEMANTIC RAG
# ============================================================

def retrieve_b2_episode(
    state,
    run_id
):

    """
    Retrieve the most relevant B2 runtime episode.

    IMPORTANT:
    - Reads ONLY the selected B2 E7 run KB.
    - Does NOT read project runtime_kb.json.
    - Uses the same regime classification,
      textual representations, cosine similarity,
      and embedding mechanism as the B3 retriever.
    """

    print(
        "\n=== E7 B2 RAG RETRIEVAL ==="
    )

    episodes = load_run_episodes(
        "B2",
        run_id
    )


    print(
        "B2 Run ID:",
        run_id
    )

    print(
        "Available B2 Episodes:",
        len(episodes)
    )


    if not episodes:

        print(
            "No B2 runtime episodes are available "
            "for this run."
        )

        return None


    current_regime = (
        classify_runtime_regime(
            state
        )
    )


    print(
        "Current Runtime Regime:",
        current_regime
    )


    # ========================================================
    # SAME-REGIME FILTERING
    # ========================================================

    matching_episodes = []


    for episode in episodes:

        initial_state = episode.get(
            "initial_state",
            {}
        )

        episode_regime = (
            classify_runtime_regime(
                initial_state
            )
        )


        if (
            episode_regime
            == current_regime
        ):

            matching_episodes.append(
                episode
            )


    if matching_episodes:

        candidate_episodes = (
            matching_episodes
        )

        print(
            "Retrieval Scope: "
            "same-regime B2 episodes"
        )

    else:

        candidate_episodes = (
            episodes
        )

        print(
            "No same-regime B2 episode exists."
        )

        print(
            "Retrieval Scope: "
            "all episodes from this B2 run"
        )


    print(
        "Candidate Episodes:",
        len(candidate_episodes)
    )


    # ========================================================
    # SAME EMBEDDING-SIMILARITY PROCEDURE AS B3
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
    # DISPLAY RETRIEVAL RESULT
    # ========================================================

    if best_episode is not None:

        actual_outcome = (
            best_episode.get(
                "execution_outcome",
                best_episode.get(
                    "final_verdict",
                    {}
                )
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

        candidate_plan = (
            best_episode.get(
                "candidate_plan",
                best_episode.get(
                    "final_plan",
                    {}
                )
            )
        )


        print(
            "Most relevant B2 episode retrieved."
        )

        print(
            "Similarity Score:",
            f"{best_similarity:.4f}"
        )

        print(
            "Retrieved Diagnosis:",
            best_episode.get(
                "diagnosis"
            )
        )

        print(
            "Retrieved Action:",
            candidate_plan.get(
                "action"
            )
        )

        print(
            "Retrieved Outcome:",
            actual_outcome.get(
                "status"
            )
        )

        print(
            "Retrieved Initial Response Time:",
            initial_state.get(
                "response_time"
            )
        )

        print(
            "Retrieved Final Response Time:",
            final_state.get(
                "response_time"
            )
        )


    return best_episode


# ============================================================
# INFORMATIONAL MODE
# ============================================================

if __name__ == "__main__":

    print(
        "B2 isolated RAG retriever loaded."
    )

    print(
        "Running this file directly does NOT "
        "call the embedding API."
    )

    print(
        "Project runtime_kb.json is not used "
        "by retrieve_b2_episode()."
    )
