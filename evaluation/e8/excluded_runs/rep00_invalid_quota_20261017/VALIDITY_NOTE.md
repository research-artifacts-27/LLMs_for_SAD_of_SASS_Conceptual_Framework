# E8 B1 rep00 Validity Note

Status: INVALID_FOR_PRIMARY_COMPARISON

Reason:
All B1 LLM analysis and planning calls failed because the OpenAI API
returned insufficient_quota / credit_balance_exhausted.

Consequences:
- No valid LLM diagnosis was produced.
- No valid LLM plan was produced.
- The deterministic safety checker rejected the absence of a valid plan.
- No SWIM adaptation action was executed.
- The observed QoS behavior therefore does not represent the intended
  B1 LLM-only treatment.
- Reported LLM-related decision latencies reflect API failure handling,
  not successful LLM inference latency.

Scientific handling:
- Preserve all raw artifacts.
- Exclude this run from the primary B0-B3 comparative analysis.
- It may be reported separately as an infrastructure-failure / fail-closed
  observation if useful.
- Re-run B1 repetition 0 only after API availability is restored.
