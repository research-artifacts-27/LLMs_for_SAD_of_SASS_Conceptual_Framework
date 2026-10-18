import json


KB_FILE = "runtime_kb.json"


def load_episodes():
    try:
        with open(KB_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def save_episode(episode):
    episodes = load_episodes()
    episodes.append(episode)

    with open(KB_FILE, "w") as file:
        json.dump(episodes, file, indent=4)

    print("\n=== RUNTIME KNOWLEDGE BASE ===")
    print("Adaptation episode stored successfully.")


def retrieve_previous_episode():
    episodes = load_episodes()

    if len(episodes) == 0:
        print("\n=== KNOWLEDGE RETRIEVAL ===")
        print("No previous episodes found.")
        return None

    previous_episode = episodes[-1]

    print("\n=== KNOWLEDGE RETRIEVAL ===")
    print("Previous adaptation episode retrieved.")
    print(f"Previous Diagnosis: {previous_episode['diagnosis']}")
    print(
        f"Previous Successful Target Servers: "
        f"{previous_episode['final_plan']['target_servers']}"
    )
    print(
        f"Previous Final Response Time: "
        f"{previous_episode['final_state']['response_time']} seconds"
    )

    return previous_episode

