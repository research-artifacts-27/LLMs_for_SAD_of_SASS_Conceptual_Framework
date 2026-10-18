import json

from monitor import monitor
from analyzer import analyze
from planner import plan
from safety_checker import safety_check
from executor import execute
from runtime_kb import save_episode
from llm_client import ask_llm
from failure_router import route_failure
from outcome_evaluator import evaluate_outcome
from operator_notifier import notify_operator
from fallback_controller import select_safe_fallback


POLICY_FILE = "trusted_policies.json"

MAX_RETRIES = 2


# ============================================================
# LOAD TRUSTED POLICIES
# ============================================================

def load_policies():

    with open(POLICY_FILE, "r") as file:
        return json.load(file)


# ============================================================
# LLM-BASED REAL SWIM REPLANNING
# ============================================================

def replan(state, diagnosis, verdict):

    print("\n=== AGENTIC REPLANNING — REAL SWIM ===")

    print(
        f"Received failure reason: "
        f"{verdict['reason']}"
    )

    policies = load_policies()

    response_time_target = policies[
        "response_time_target"
    ]

    max_servers = policies[
        "max_servers"
    ]

    min_servers = policies[
        "min_servers"
    ]

    dimmer_min = policies[
        "dimmer_min"
    ]

    dimmer_max = policies[
        "dimmer_max"
    ]

    dimmer_step = policies[
        "dimmer_step"
    ]

    allowed_actions = policies[
        "allowed_actions"
    ]

    prompt = f"""
You are replanning an adaptation for the
REAL SWIM self-adaptive web-system exemplar.

CURRENT SWIM STATE:

Average response time:
{state['response_time']} seconds

Total servers:
{state['servers']}

Active servers:
{state['active_servers']}

Maximum servers reported by SWIM:
{state['max_servers']}

Server currently booting:
{state['server_booting']}

Average utilization:
{state['utilization'] * 100:.1f}%

Total utilization:
{state.get('total_utilization')}

Current dimmer:
{state['dimmer']}

Arrival rate:
{state['arrival_rate']}


CURRENT DIAGNOSIS:

{diagnosis}


PREVIOUS PLAN FAILURE:

{verdict['reason']}


TRUSTED POLICIES:

Response-time target:
{response_time_target} seconds

Minimum servers:
{min_servers}

Maximum servers:
{max_servers}

Minimum dimmer:
{dimmer_min}

Maximum dimmer:
{dimmer_max}

Dimmer step:
{dimmer_step}

Allowed actions:
{allowed_actions}


The previous candidate plan was rejected by
the deterministic safety checker.

Use the failure reason and current SWIM state
to create a DIFFERENT or corrected candidate
plan.

Available REAL SWIM actions:

add_server
- Add one server.
- Never exceed the maximum server count.
- Do not add another server while one is booting.

remove_server
- Remove one server.
- Never reduce below the minimum server count.
- Do not remove while a server is booting.
- Use only when sufficient spare capacity exists.

set_dimmer
- Change optional workload.
- Keep the value inside the trusted range.

none
- Use when no adaptation is required or when
  the current state should remain unchanged.


Return ONLY valid JSON.


For add_server:

{{
    "action": "add_server"
}}


For remove_server:

{{
    "action": "remove_server"
}}


For set_dimmer:

{{
    "action": "set_dimmer",
    "value": 0.75
}}


For no action:

{{
    "action": "none"
}}
"""

    llm_output = ask_llm(
        prompt
    )

    try:

        new_plan = json.loads(
            llm_output
        )

        print(
            "Agent replanned using "
            "the real LLM."
        )

        print(
            f"Revised Candidate Plan: "
            f"{new_plan}"
        )

        return new_plan

    except Exception:

        print(
            "LLM returned an invalid "
            "replanning format."
        )

        return {
            "action": "none"
        }


# ============================================================
# FAIL-SAFE MODE
# ============================================================

def fail_safe():

    print("\n======================================")
    print(" AGENTIC RECOVERY LIMIT REACHED")
    print("======================================")

    print(
        "No agentic candidate adaptation passed "
        "the deterministic safety check within "
        "the configured retry bound."
    )

    print(
        "The rejected agentic candidate will NOT "
        "be sent to the SWIM effectors."
    )

    print(
        "Agentic replanning is suspended for "
        "this control cycle."
    )

    print(
        "Control transfers to the deterministic "
        "fallback policy."
    )

    print(
        "Any fallback candidate must independently "
        "pass the existing deterministic safety check."
    )

    print(
        "If no safe fallback exists, the current "
        "SWIM configuration will be preserved."
    )


# ============================================================
# REAL OPERATOR ESCALATION
# ============================================================

def request_operator_escalation(
    reason,
    context
):

    """
    Send a real persistent/operator-facing notification.

    IMPORTANT:
    Notification delivery does NOT imply that a human
    acknowledged, approved, or cleared the adaptation.
    """

    return notify_operator(
        reason=reason,
        context=context,
        severity="HIGH"
    )


# ============================================================
# MAIN REAL-SWIM AGENTIC CONTROLLER
# ============================================================

if __name__ == "__main__":

    print("\n======================================")
    print(" REAL SWIM AGENTIC ADAPTATION")
    print("======================================")

    # ========================================================
    # STEP 1 — MONITOR REAL SWIM
    # ========================================================

    current_state = monitor()

    initial_state = current_state.copy()

    # ========================================================
    # STEP 2 — RAG + LLM ANALYSIS
    # ========================================================

    diagnosis = analyze(
        current_state
    )

    # ========================================================
    # STEP 3 — RAG + LLM PLANNING
    # ========================================================

    candidate_plan = plan(
        current_state,
        diagnosis
    )

    first_plan = candidate_plan.copy()

    # ========================================================
    # STEP 4 — DETERMINISTIC SAFETY CHECK
    # ========================================================

    verdict = safety_check(
        candidate_plan,
        current_state
    )

    first_verdict = verdict.copy()

    attempts = 0

    recovery_routes = []

    # ========================================================
    # STEP 5 — BOUNDED AGENTIC RECOVERY
    # ========================================================

    while (
        verdict["status"] == "FAIL"
        and attempts < MAX_RETRIES
    ):

        attempts += 1

        print(
            f"\n=== AGENTIC RECOVERY "
            f"{attempts} OF "
            f"{MAX_RETRIES} ==="
        )

        # ----------------------------------------------------
        # FAILURE ROUTING
        # ----------------------------------------------------

        route = route_failure(
            current_state,
            diagnosis,
            verdict
        )

        recovery_routes.append(
            route
        )

        # ----------------------------------------------------
        # ROUTE BACK TO MONITOR
        # ----------------------------------------------------

        if route == "monitor":

            print(
                "\nAgent requested fresh "
                "SWIM observations."
            )

            current_state = monitor()

            diagnosis = analyze(
                current_state
            )

            candidate_plan = plan(
                current_state,
                diagnosis
            )

        # ----------------------------------------------------
        # ROUTE BACK TO ANALYZE
        # ----------------------------------------------------

        elif route == "analyze":

            print(
                "\nAgent decided to reconsider "
                "the diagnosis."
            )

            diagnosis = analyze(
                current_state
            )

            candidate_plan = plan(
                current_state,
                diagnosis
            )

        # ----------------------------------------------------
        # ROUTE TO REPLAN
        # ----------------------------------------------------

        elif route == "replan":

            candidate_plan = replan(
                current_state,
                diagnosis,
                verdict
            )

        # ----------------------------------------------------
        # UNKNOWN ROUTE — SAFE FALLBACK
        # ----------------------------------------------------

        else:

            print(
                "\nUnknown recovery route."
            )

            print(
                "Using safe no-action candidate."
            )

            candidate_plan = {
                "action": "none"
            }

        # ----------------------------------------------------
        # REVALIDATE CORRECTED CANDIDATE
        # ----------------------------------------------------

        print(
            "\n=== SAFETY CHECK AGAIN ==="
        )

        verdict = safety_check(
            candidate_plan,
            current_state
        )

    # ========================================================
    # FINAL PRE-EXECUTION SAFETY VERDICT
    # ========================================================

    final_safety_verdict = verdict.copy()

    operator_used = False

    fail_safe_triggered = False

    operator_intervention_mode = None

    operator_alert_id = None

    operator_notification_delivered_to_os = False

    operator_acknowledgement_received = False

    fallback_invoked = False

    fallback_status = None

    fallback_attempted_candidates = []

    fallback_selected_plan = None

    fallback_safety_verdict = None

    fallback_executed = False

    fallback_outcome = None

    executed_plan = None

    executed_plan_source = None

    executed_safety_verdict = None

    # ========================================================
    # STEP 6 — EXECUTE SAFE PLAN
    # ========================================================

    if final_safety_verdict["status"] == "PASS":

        execute(
            candidate_plan
        )

        executed_plan = candidate_plan.copy()

        executed_plan_source = (
            "agentic_plan"
        )

        executed_safety_verdict = (
            final_safety_verdict.copy()
        )

        print(
            "\n=== MONITOR AFTER "
            "REAL SWIM ADAPTATION ==="
        )

        final_state = monitor()

        # ====================================================
        # STEP 7 — POST-EXECUTION VALIDATION
        # ====================================================

        actual_outcome = evaluate_outcome(
            current_state,
            final_state,
            candidate_plan
        )

    # ========================================================
    # STEP 6B — RETRY LIMIT REACHED
    # ========================================================

    else:

        fail_safe_triggered = True

        fail_safe()

        # ----------------------------------------------------
        # DETERMINISTIC FALLBACK SELECTION
        #
        # This path does NOT use an LLM.
        # Every candidate is checked by the existing
        # deterministic safety checker.
        # ----------------------------------------------------

        fallback_invoked = True

        fallback_result = select_safe_fallback(
            current_state
        )

        fallback_status = fallback_result.get(
            "status"
        )

        fallback_attempted_candidates = (
            fallback_result.get(
                "attempted_candidates",
                []
            )
        )

        fallback_selected_plan = (
            fallback_result.get(
                "selected_plan"
            )
        )

        fallback_safety_verdict = (
            fallback_result.get(
                "selected_safety_verdict"
            )
        )

        # ----------------------------------------------------
        # SAFE FALLBACK FOUND
        # ----------------------------------------------------

        if (
            fallback_status
            == "SAFE_FALLBACK_FOUND"
        ):

            print(
                "\n=== DETERMINISTIC FALLBACK "
                "SELECTED ==="
            )

            print(
                "Fallback Plan:",
                fallback_selected_plan
            )

            fallback_action = (
                fallback_selected_plan.get(
                    "action"
                )
            )

            # -----------------------------------------------
            # A real effector action is executed only after
            # deterministic safety approval.
            #
            # "none" requires no effector command.
            # -----------------------------------------------

            if fallback_action != "none":

                execute(
                    fallback_selected_plan
                )

                fallback_executed = True

                executed_plan = (
                    fallback_selected_plan.copy()
                )

                executed_plan_source = (
                    "deterministic_fallback"
                )

                executed_safety_verdict = (
                    fallback_safety_verdict.copy()
                    if fallback_safety_verdict
                    else None
                )

            else:

                print(
                    "Validated fallback is 'none'; "
                    "no SWIM effector command is sent."
                )

                executed_plan = (
                    fallback_selected_plan.copy()
                )

                executed_plan_source = (
                    "deterministic_fallback_no_action"
                )

                executed_safety_verdict = (
                    fallback_safety_verdict.copy()
                    if fallback_safety_verdict
                    else None
                )

            print(
                "\n=== MONITOR AFTER "
                "DETERMINISTIC FALLBACK ==="
            )

            final_state = monitor()

            fallback_outcome = evaluate_outcome(
                current_state,
                final_state,
                fallback_selected_plan
            )

            actual_outcome = (
                fallback_outcome
            )

        # ----------------------------------------------------
        # NO SAFE FALLBACK EXISTS
        # ----------------------------------------------------

        else:

            print(
                "\n=== NO SAFE FALLBACK ==="
            )

            print(
                "No deterministic fallback candidate "
                "passed the safety checker."
            )

            print(
                "No fallback action will be executed."
            )

            print(
                "The current SWIM configuration is "
                "preserved."
            )

            print(
                "\n=== RETURN TO MONITOR ==="
            )

            final_state = monitor()

            policies = load_policies()

            goal_satisfied = (
                final_state["response_time"]
                <= policies[
                    "response_time_target"
                ]
            )

            fallback_outcome = {
                "status":
                    "FAIL",

                "action_effect_observed":
                    False,

                "goal_satisfied":
                    goal_satisfied,

                "reason":
                    (
                        "Agentic recovery exhausted its "
                        "bounded retries and no deterministic "
                        "fallback candidate passed the safety "
                        "checker. No fallback action was "
                        "executed and the current SWIM "
                        "configuration was preserved."
                    )
            }

            actual_outcome = (
                fallback_outcome
            )

        # ----------------------------------------------------
        # REAL OPERATOR ESCALATION
        #
        # Notification occurs after deterministic fallback
        # handling. Delivery does not constitute human
        # acknowledgement or clearance.
        # ----------------------------------------------------

        operator_alert = request_operator_escalation(
            reason=(
                "Agentic recovery exhausted its bounded "
                "retry limit. Deterministic fallback "
                "handling was invoked."
            ),
            context={
                "recovery_attempts":
                    attempts,

                "recovery_routes":
                    recovery_routes,

                "rejected_agentic_plan":
                    candidate_plan,

                "agentic_safety_verdict":
                    final_safety_verdict,

                "fallback_status":
                    fallback_status,

                "fallback_attempted_candidates":
                    fallback_attempted_candidates,

                "fallback_selected_plan":
                    fallback_selected_plan,

                "fallback_safety_verdict":
                    fallback_safety_verdict,

                "fallback_executed":
                    fallback_executed,

                "fallback_outcome":
                    fallback_outcome,

                "final_state":
                    final_state,

                "control_action":
                    "deterministic_fallback_handled"
            }
        )

        operator_used = True

        operator_intervention_mode = (
            "real_notification_unacknowledged"
        )

        operator_alert_id = (
            operator_alert.get(
                "alert_id"
            )
        )

        operator_notification_delivered_to_os = (
            operator_alert.get(
                "notification",
                {}
            ).get(
                "delivery_to_os",
                {}
            ).get(
                "delivered_to_os",
                False
            )
        )

        operator_acknowledgement_received = (
            operator_alert.get(
                "operator_acknowledgement",
                {}
            ).get(
                "received",
                False
            )
        )

        print(
            "\n=== FAIL-SAFE / FALLBACK OUTCOME ==="
        )

        print(
            "Rejected agentic adaptation was "
            "NOT executed."
        )

        print(
            f"Fallback Status: "
            f"{fallback_status}"
        )

        print(
            f"Fallback Executed: "
            f"{fallback_executed}"
        )

        print(
            f"Fallback Outcome: "
            f"{fallback_outcome['status']}"
        )

        print(
            "Operator Escalation Mode: "
            "real_notification_unacknowledged"
        )

        print(
            f"Operator Alert ID: "
            f"{operator_alert_id}"
        )

        print(
            "Notification Delivered to OS: "
            f"{operator_notification_delivered_to_os}"
        )

        print(
            "Human Acknowledgement Received: "
            f"{operator_acknowledgement_received}"
        )

    # ========================================================
    # STEP 8 — STORE COMPLETE REAL SWIM EPISODE
    # ========================================================

    episode = {

        "initial_state":
            initial_state,

        "diagnosis":
            diagnosis,

        "first_plan":
            first_plan,

        "first_verdict":
            first_verdict,

        "final_plan":
            candidate_plan,

        # ----------------------------------------------------
        # Final PRE-execution deterministic safety decision.
        # ----------------------------------------------------

        "safety_verdict":
            final_safety_verdict,

        # ----------------------------------------------------
        # Actual runtime outcome.
        # ----------------------------------------------------

        "final_verdict":
            actual_outcome,

        "execution_outcome":
            actual_outcome,

        # ----------------------------------------------------
        # Explicit execution trace.
        #
        # final_plan above is retained for backward
        # compatibility and represents the final agentic
        # candidate. These fields identify what was actually
        # authorized for execution after all safety handling.
        # ----------------------------------------------------

        "executed_plan":
            executed_plan,

        "executed_plan_source":
            executed_plan_source,

        "executed_safety_verdict":
            executed_safety_verdict,

        # ----------------------------------------------------
        # Recovery information.
        # ----------------------------------------------------

        "recovery_attempts":
            attempts,

        "recovery_routes":
            recovery_routes,

        # ----------------------------------------------------
        # Fail-safe / escalation information.
        # ----------------------------------------------------

        "fail_safe_triggered":
            fail_safe_triggered,

        # ----------------------------------------------------
        # Deterministic fallback evidence.
        # ----------------------------------------------------

        "fallback_invoked":
            fallback_invoked,

        "fallback_status":
            fallback_status,

        "fallback_attempted_candidates":
            fallback_attempted_candidates,

        "fallback_selected_plan":
            fallback_selected_plan,

        "fallback_safety_verdict":
            fallback_safety_verdict,

        "fallback_executed":
            fallback_executed,

        "fallback_outcome":
            fallback_outcome,

        "operator_intervention":
            operator_used,

        "operator_intervention_mode":
            operator_intervention_mode,

        # Backward-compatible escalation indicator.
        "operator_escalation_requested":
            operator_used,

        "operator_alert_id":
            operator_alert_id,

        "operator_notification_delivered_to_os":
            operator_notification_delivered_to_os,

        "operator_acknowledgement_received":
            operator_acknowledgement_received,

        # ----------------------------------------------------
        # Final observed SWIM state.
        # ----------------------------------------------------

        "final_state":
            final_state.copy()
    }

    save_episode(
        episode
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n======================================")
    print(" REAL SWIM ADAPTATION CYCLE COMPLETE")
    print("======================================")

    print(
        f"Final Agentic Safety Status: "
        f"{final_safety_verdict['status']}"
    )

    print(
        f"Fallback Status: "
        f"{fallback_status}"
    )

    print(
        f"Executed Plan Source: "
        f"{executed_plan_source}"
    )

    print(
        "Executed Safety Status: "
        + (
            str(
                executed_safety_verdict.get(
                    "status"
                )
            )
            if executed_safety_verdict
            else "None"
        )
    )

    print(
        f"Runtime Outcome: "
        f"{actual_outcome['status']}"
    )

    print(
        f"Recovery Attempts: "
        f"{attempts}"
    )

    print(
        f"Fail-Safe Triggered: "
        f"{fail_safe_triggered}"
    )

    print(
        f"Operator Intervention Mode: "
        f"{operator_intervention_mode}"
    )
