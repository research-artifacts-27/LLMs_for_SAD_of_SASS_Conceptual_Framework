import os
import json
import urllib.request
import urllib.error


def get_embedding(text):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not loaded.")

    data = {
        "model": "text-embedding-3-small",
        "input": text
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request) as response:
            result = json.load(response)

        return result["data"][0]["embedding"]

    except urllib.error.HTTPError as error:
        print("Embedding API request failed.")
        print(error.read().decode())
        return None


if __name__ == "__main__":

    text = (
        "Response time is 4 seconds, CPU utilization is 94%, "
        "and the system is experiencing workload saturation."
    )

    embedding = get_embedding(text)

    if embedding is not None:
        print("\n=== EMBEDDING TEST ===")
        print("Embedding created successfully.")
        print(f"Vector length: {len(embedding)}")
        print("First 5 values:")
        print(embedding[:5])
