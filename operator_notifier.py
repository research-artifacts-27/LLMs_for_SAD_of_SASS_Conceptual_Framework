#!/usr/bin/env python3

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

ALERT_LOG = (
    PROJECT_ROOT
    / "operator_alerts.jsonl"
)

LATEST_ALERT = (
    PROJECT_ROOT
    / "latest_operator_alert.json"
)


# ============================================================
# HELPERS
# ============================================================

def utc_now():

    return datetime.now(
        timezone.utc
    ).isoformat()


def escape_applescript_text(
    text
):

    return (
        str(text)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", " ")
    )


def persist_alert(
    alert
):

    with ALERT_LOG.open(
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            json.dumps(
                alert,
                ensure_ascii=False
            )
            + "\n"
        )

        file.flush()

        os.fsync(
            file.fileno()
        )


    with LATEST_ALERT.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            alert,
            file,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# MACOS NOTIFICATION
# ============================================================

def send_macos_notification(
    title,
    message
):

    title = escape_applescript_text(
        title
    )

    message = escape_applescript_text(
        message
    )


    script = (
        'display notification "'
        + message
        + '" with title "'
        + title
        + '"'
    )


    try:

        result = subprocess.run(
            [
                "/usr/bin/osascript",
                "-e",
                script
            ],
            capture_output=True,
            text=True,
            timeout=10
        )


        if result.returncode == 0:

            return {
                "attempted":
                    True,

                "delivered_to_os":
                    True,

                "return_code":
                    0,

                "error":
                    None
            }


        return {
            "attempted":
                True,

            "delivered_to_os":
                False,

            "return_code":
                result.returncode,

            "error":
                (
                    result.stderr.strip()
                    or
                    result.stdout.strip()
                    or
                    "Unknown osascript error"
                )
        }


    except Exception as error:

        return {
            "attempted":
                True,

            "delivered_to_os":
                False,

            "return_code":
                None,

            "error":
                str(
                    error
                )
        }


# ============================================================
# OPERATOR ESCALATION
# ============================================================

def notify_operator(
    reason,
    context=None,
    severity="HIGH"
):

    if context is None:

        context = {}


    timestamp = utc_now()


    alert_id = (
        "OP-"
        + timestamp
        .replace("-", "")
        .replace(":", "")
        .replace("+", "")
        .replace(".", "")
    )


    fallback_status = context.get(
        "fallback_status"
    )

    fallback_invoked = (
        fallback_status is not None
    )

    fallback_executed = bool(
        context.get(
            "fallback_executed",
            False
        )
    )

    current_configuration_preserved = (
        not fallback_executed
    )


    if fallback_executed:

        notification_message = (
            "Agentic replanning reached its retry bound. "
            "The rejected agentic plan was not executed. "
            "A safety-validated deterministic fallback "
            "was executed. Reason: "
            + str(
                reason
            )
        )

    elif fallback_invoked:

        notification_message = (
            "Agentic replanning reached its retry bound. "
            "No fallback effector action was executed; "
            "the current configuration was preserved. "
            "Reason: "
            + str(
                reason
            )
        )

    else:

        notification_message = (
            "Autonomous adaptation has been suspended. "
            "Current configuration is preserved. "
            "Reason: "
            + str(
                reason
            )
        )


    delivery = send_macos_notification(
        title=(
            "SWIM Operator Escalation"
        ),
        message=notification_message
    )


    alert = {
        "alert_id":
            alert_id,

        "timestamp_utc":
            timestamp,

        "severity":
            severity,

        "reason":
            reason,

        "context":
            context,

        # Legacy/general suspension indicator.
        # False when a validated deterministic fallback
        # actually performs an effector action.
        "autonomous_adaptation_suspended":
            not fallback_executed,

        "agentic_replanning_suspended":
            True,

        "deterministic_fallback_invoked":
            fallback_invoked,

        "fallback_executed":
            fallback_executed,

        "current_configuration_preserved":
            current_configuration_preserved,

        # The rejected AGENTIC plan is never executed.
        "rejected_plan_executed":
            False,

        "rejected_agentic_plan_executed":
            False,

        "notification": {
            "channel":
                "macOS Notification Center",

            "delivery_to_os":
                delivery
        },

        "operator_acknowledgement": {
            "received":
                False,

            "note":
                (
                    "Notification delivery does not "
                    "constitute human acknowledgement "
                    "or clearance."
                )
        }
    }


    persist_alert(
        alert
    )


    print()
    print(
        "======================================"
    )
    print(
        " OPERATOR ESCALATION"
    )
    print(
        "======================================"
    )

    print(
        "Alert ID:",
        alert_id
    )

    print(
        "Persistent alert recorded:",
        ALERT_LOG
    )

    print(
        "macOS notification delivered to OS:",
        delivery[
            "delivered_to_os"
        ]
    )


    if delivery[
        "error"
    ]:

        print(
            "Notification error:",
            delivery[
                "error"
            ]
        )


    print(
        "Human acknowledgement received: False"
    )

    print(
        "No operator clearance is assumed."
    )


    return alert


# ============================================================
# SAFE STANDALONE TEST
# ============================================================

if __name__ == "__main__":

    print(
        "Standalone operator-notification test."
    )

    print(
        "This test does NOT start or modify SWIM."
    )

    print(
        "This test does NOT execute adaptations."
    )

    print()


    notify_operator(
        reason=(
            "Standalone notification mechanism test."
        ),
        context={
            "test_mode":
                True,

            "SWIM_interaction":
                False,

            "adaptation_execution":
                False
        },
        severity="TEST"
    )
