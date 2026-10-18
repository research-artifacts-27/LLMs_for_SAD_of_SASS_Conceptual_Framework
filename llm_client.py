import os
import json
import urllib.request
import urllib.error


def ask_llm(prompt):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not loaded.")

    data = {
        "model": "gpt-6-astra",
        "input": prompt
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
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

        for item in result.get("output", []):
            if item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        return content.get("text")

        return None

    except urllib.error.HTTPError as error:
        print("LLM API request failed.")
        print(error.read().decode())
        return None


if __name__ == "__main__":
    answer = ask_llm(
        "A web system has response time 4.0 seconds and "
        "CPU utilization 94%. In one short sentence, "
        "what is the likely problem?"
    )

    print("\n=== LLM RESPONSE ===")
    print(answer)
