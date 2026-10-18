# Human-Triggered Architecture Reconsideration

Status: **PENDING HUMAN ARCHITECT REVIEW**

No architecture has been changed or approved by this review.

## Runtime Evidence

Triggers: RTD-02

## Current Architecture Assessment

A1, Centralized Agentic MAPE-K, remains the approved baseline recorded in ADR-001. RTD-02 warrants targeted review of planning adequacy and outcome evaluation, but does not establish that centralized control should be replaced. A1 already supports coordinated proposals and per-action revalidation of multi-action plans; the review should distinguish incomplete implementation or operating-policy specification from a genuinely missing architectural capability. No architecture, policy, or approval status is changed by this assessment.

### Runtime Evidence Interpretation

The supplied summary reports 86 PASS and 8 PARTIAL outcomes. Episodes 5, 6, 27, 28, 78, 79, 80, and 81 had actions take effect while the runtime goal remained unsatisfied. This supports examining adaptation magnitude, sequencing, planning horizon, settling criteria, and sustained-goal recovery. It does not establish that actions were too small, that LLM latency caused violations, or that any alternative would perform better. No final QoS violations at maximum capacity, safety rejections, recovery attempts, or fail-safe events were reported; these absences neither prove available capacity would have resolved the violations nor demonstrate safety and recovery mechanisms under fault conditions. Episode-level measurements, timing, action sequences, and experiment provenance are not supplied. Some episodes may involve controlled fault injection, but their provenance cannot be inferred. Episode indices alone do not establish a continuous overload event or eventual recovery.

## Review Options

### R1 — Retain A1 and investigate episode-level behavior

**Disposition:** retain_current

Retain the approved architecture without structural changes. Examine the eight PARTIAL episodes and comparable PASS episodes to determine whether existing A1 capabilities were implemented, configured, and evaluated as intended. This option treats RTD-02 as an evidence and conformance investigation, not as a reason to dismiss the symptom or authorize policy changes.

**Risks:**

- If inadequate planning is the actual cause, retaining current behavior may prolong repeated response-time violations.
- Missing historical telemetry may prevent reliable reconstruction.
- An investigation without explicit review milestones could defer a necessary decision indefinitely.

**Validation needed before any approval:**

- Inspect all eight PARTIAL episodes and matched PASS episodes, including response-time values, workload, utilization, dimmer state, active and pending servers, and action timing.
- Check outcome windows against server activation and dimmer settling; keep genuinely unsettled effects pending rather than prematurely labeling them PARTIAL or PASS.
- Verify actual multi-action proposal support, per-action state revalidation, and policy-compliant sequencing.
- Audit PARTIAL-to-recovery transitions, episode identity, budget resets, and the meaning of zero recorded recovery attempts.
- Determine provenance where records permit; otherwise retain an unknown-provenance label and avoid population-level conclusions.

### R2 — Refine A1 with bounded outcome-oriented planning

**Disposition:** revise_current

Consider a bounded refinement of A1's planner, execution coordination, and evaluator contracts to make expected adaptation magnitude and planning horizon explicit. This is not the introduction of multi-action planning from scratch: A1 already permits coordinated multi-action proposals. The proposed revision would make staged progress toward the unmet objective inspectable and bounded while preserving centralized control. If implementation review shows these mechanisms already exist, the issue may instead be conformance or configuration and need no architectural revision.

**Proposed architectural changes:**

- Extend the proposal contract with the observed goal gap, an expected effect range with uncertainty, a bounded horizon, staged allowed actions, dependencies, observation checkpoints, and stop conditions.
- Add explicit comparison of feasible action sequences, including dimming while capacity starts, avoiding duplicate additions, and coordinating optional-content restoration with scale-in.
- Refine the execution coordinator to execute only the currently validated stage, refresh observations at checkpoints, and invalidate remaining stages when workload, policy version, or relevant state changes.
- Extend outcome evaluation and memory to link stage-level results with an overall goal-recovery episode, distinguishing partial progress, unsettled effects, and unsuccessful settled outcomes.
- Define a deterministic recovery-episode contract covering PARTIAL handling, attempt and elapsed-time limits, and escalation. Exact bounds and thresholds would require separate architect approval.

**Risks:**

- The refinement may not address the actual cause if PARTIAL outcomes arise from observation timing, injected faults, or rapidly changing demand.
- Longer plans can become stale, overshoot capacity needs, or create oscillation.
- Predicted action effects may be inaccurate or confounded by workload changes.
- Poor episode-boundary design could still permit indefinite recovery through budget resets.

**Validation needed before any approval:**

- First establish which proposed capabilities are absent from the actual A1 implementation.
- Compare unchanged A1 with a separately authorized experimental refinement using matched initial states, workload traces, and labeled fault scenarios.
- Measure time to target restoration, violation duration and excess, delivered optional content, server-time usage, control latency, and action reversals; do not optimize PARTIAL counts alone.
- Test delayed activation, changing workload between stages, stale observations, lost acknowledgments, partial execution, restart, and cancellation of obsolete remaining stages.
- Verify unchanged bounds, step semantics, last-serving-server protection, and gate enforcement for every action.
- Have the architect review horizon limits, checkpoints, recovery limits, and escalation rules before any executable policy is adopted.

### R3 — Reassess A3 against retained and refined A1

**Disposition:** reopen_selection

Reopen architectural comparison with A3, Two-Timescale Supervisory Adaptation, as a candidate alongside unchanged and refined A1. This larger redesign would be relevant if timing evidence shows that LLM-dependent reaction delay materially contributes to unresolved goals. RTD-02 alone does not establish that condition. A3's original 4.0 score versus A1's 3.8 remains historical advisory assessment, not measured superiority or authorization to replace A1.

**Proposed architectural changes:**

- Consider an independent deterministic fast dimmer proposer using architect-approved rules, with no direct effector access.
- Retain an agentic supervisory loop for capacity planning and sustained optional-quality recovery.
- Introduce deterministic cross-loop arbitration through the preserved safety boundary, with current-state revalidation and explicit actuator ownership.
- Add joint episode records and cross-timescale evaluation for immediate dimmer effects and delayed capacity effects.

**Risks:**

- No supplied timing evidence shows that a fast loop would address these eight PARTIAL outcomes.
- Cross-loop restoration and scale-in can produce oscillation despite individually valid actions.
- Additional implementation and validation would weaken immediate alignment with the demonstrated centralized prototype.
- The historical numerical lead could distract from implementation maturity and unverified operational benefits.

**Validation needed before any approval:**

- Measure monitoring, retrieval, inference, gate, effector, and activation delays to determine whether an LLM-independent dimmer path addresses the observed problem.
- Compare unchanged A1, the proposed bounded A1 refinement, and A3 under matched workloads and explicitly labeled fault scenarios.
- Validate arbitration during simultaneous dimmer restoration, overload response, and server removal.
- Test prolonged optional-content suppression, dimmer exhaustion, stale observations, supervisory failure, and shared-gate failure behavior.
- Retain architect-defined weights unless the architect explicitly changes them; justify any future score revisions with evidence and keep implementation maturity separate.
- Prepare a proposed decision record for human review only if selection is reopened; leave ADR-001 accepted unless the architect approves a superseding decision.

## LLM Advisory Recommendation

Option: R2

Advisory recommendation: prioritize investigation and specification of the bounded A1 refinement in R2, using R1's episode reconstruction as a prerequisite to deciding whether any revision is warranted. This most directly addresses the human review question about magnitude, sequencing, and horizon without assuming centralized control is defective. If existing capabilities already cover the need or the symptom is explained by evaluation timing, retaining A1 may be sufficient. Consider R3 only if comparative timing and workload evidence supports the larger redesign. A1 remains the approved baseline, and the human architect alone can approve any change.

Confidence: medium

## Authority Boundary

This artifact is decision support only. The human architect must explicitly decide whether to retain, revise, or reopen the architecture. No trusted runtime policy, approved architecture, SWIM configuration, or runtime controller is modified.
