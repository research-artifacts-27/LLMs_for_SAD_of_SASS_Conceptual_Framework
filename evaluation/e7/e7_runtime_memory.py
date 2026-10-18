#!/usr/bin/env python3

import json
from pathlib import Path


E7_DIR = (
    Path(__file__).resolve()
    .parent
)

RUNTIME_KB_ROOT = (
    E7_DIR
    / "runtime_kb"
)

SUPPORTED_VARIANTS = {
    "B2",
    "B3"
}


# ============================================================
# PATH RESOLUTION
# ============================================================

def get_run_kb_path(
    variant,
    run_id
):

    variant = str(
        variant
    ).upper()

    run_id = str(
        run_id
    ).strip()


    if variant not in SUPPORTED_VARIANTS:

        raise ValueError(
            "Isolated runtime memory is supported "
            "only for B2 and B3."
        )


    if not run_id:

        raise ValueError(
            "run_id must not be empty."
        )


    safe_run_id = (
        run_id
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )


    return (
        RUNTIME_KB_ROOT
        / variant
        / f"{safe_run_id}.json"
    )


# ============================================================
# INITIALIZE FRESH RUN MEMORY
# ============================================================

def initialize_run_kb(
    variant,
    run_id,
    overwrite=False
):

    path = get_run_kb_path(
        variant,
        run_id
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    if (
        path.exists()
        and not overwrite
    ):

        raise FileExistsError(
            "Run KB already exists: "
            + str(path)
        )


    with path.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            [],
            file,
            indent=2
        )


    return path


# ============================================================
# LOAD EPISODES
# ============================================================

def load_run_episodes(
    variant,
    run_id
):

    path = get_run_kb_path(
        variant,
        run_id
    )


    if not path.exists():

        return []


    with path.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)


    if not isinstance(
        data,
        list
    ):

        raise ValueError(
            "E7 run KB must contain a JSON list."
        )


    return data


# ============================================================
# SAVE EPISODE
# ============================================================

def save_run_episode(
    variant,
    run_id,
    episode
):

    path = get_run_kb_path(
        variant,
        run_id
    )

    episodes = load_run_episodes(
        variant,
        run_id
    )

    episodes.append(
        episode
    )


    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    with path.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            episodes,
            file,
            indent=2
        )


    return path


# ============================================================
# INFORMATIONAL MODE
# ============================================================

if __name__ == "__main__":

    print(
        "E7 isolated runtime-memory helper loaded."
    )

    print(
        "Existing project runtime_kb.json is not "
        "used or modified by this module."
    )
