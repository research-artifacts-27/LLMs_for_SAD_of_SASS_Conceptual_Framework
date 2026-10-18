from swim_client import SwimClient


def execute(plan):

    print("\n=== EXECUTE — REAL SWIM ===")

    action = plan.get("action")

    client = SwimClient()

    try:

        client.connect()

        # ====================================================
        # ADD SERVER
        # ====================================================

        if action == "add_server":

            print(
                "Executing approved SWIM action: "
                "add_server"
            )

            reply = client.add_server()

            print(
                f"SWIM Reply: {reply}"
            )

            print(
                "add_server command sent successfully."
            )

        # ====================================================
        # REMOVE SERVER
        # ====================================================

        elif action == "remove_server":

            print(
                "Executing approved SWIM action: "
                "remove_server"
            )

            reply = client.remove_server()

            print(
                f"SWIM Reply: {reply}"
            )

            print(
                "remove_server command sent successfully."
            )

        # ====================================================
        # SET DIMMER
        # ====================================================

        elif action == "set_dimmer":

            value = plan.get("value")

            print(
                "Executing approved SWIM action: "
                f"set_dimmer {value}"
            )

            reply = client.set_dimmer(
                value
            )

            print(
                f"SWIM Reply: {reply}"
            )

            print(
                "set_dimmer command sent successfully."
            )

        # ====================================================
        # NO ACTION
        # ====================================================

        elif action == "none":

            print(
                "No SWIM adaptation action "
                "needs to be executed."
            )

        # ====================================================
        # UNKNOWN ACTION
        # ====================================================

        else:

            raise RuntimeError(
                f"Unknown SWIM action: {action}"
            )

    finally:

        client.close()


# ============================================================
# SAFE TEST
# ============================================================

if __name__ == "__main__":

    test_plan = {
        "action": "set_dimmer",
        "value": 1.0
    }

    execute(
        test_plan
    )
