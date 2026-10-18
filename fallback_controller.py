#!/usr/bin/env python3

from fallback_planner import (
    generate_fallback_candidates
)

from safety_checker import (
    safety_check
)


# ============================================================
# DETERMINISTIC FALLBACK SELECTION
# ============================================================

def select_safe_fallback(
    state
):

    """
    Generate deterministic fallback candidates and
    return the first candidate approved by the
    existing deterministic safety checker.

    IMPORTANT:
    - No LLM is used.
    - No SWIM action is executed.
    - This function only SELECTS a safe fallback.
    """

    candidates = (
        generate_fallback_candidates(
            state
        )
    )

    attempts = []


    for index, candidate in enumerate(
        candidates,
        start=1
    ):

        print()
        print(
            "=== FALLBACK CANDIDATE "
            f"{index} ==="
        )

        print(
            "Candidate:",
            candidate
        )


        verdict = safety_check(
            candidate,
            state
        )


        attempt = {
            "candidate_index":
                index,

            "candidate":
                candidate.copy(),

            "safety_verdict":
                verdict.copy()
        }

        attempts.append(
            attempt
        )


        if (
            verdict.get("status")
            == "PASS"
        ):

            print(
                "Fallback candidate accepted "
                "by deterministic safety checker."
            )

            return {
                "status":
                    "SAFE_FALLBACK_FOUND",

                "selected_plan":
                    candidate.copy(),

                "selected_safety_verdict":
                    verdict.copy(),

                "attempted_candidates":
                    attempts,

                "execution_performed":
                    False
            }


        print(
            "Fallback candidate rejected."
        )


    print()
    print(
        "No fallback candidate passed "
        "the deterministic safety checker."
    )

    print(
        "Current configuration must be preserved."
    )


    return {
        "status":
            "NO_SAFE_FALLBACK",

        "selected_plan":
            None,

        "selected_safety_verdict":
            None,

        "attempted_candidates":
            attempts,

        "execution_performed":
            False
    }


# ============================================================
# INFORMATIONAL MODE
# ============================================================

if __name__ == "__main__":

    print(
        "Deterministic fallback controller loaded."
    )

    print(
        "This module does NOT execute SWIM actions."
    )

    print(
        "Use select_safe_fallback(state) "
        "to select a validated fallback."
    )
