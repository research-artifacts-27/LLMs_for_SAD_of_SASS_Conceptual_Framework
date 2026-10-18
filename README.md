# Replication Package

This repository contains the replication artifacts for an anonymous SEAMS 2027 submission on LLM- and agentic-AI-assisted software architecture design for Self-Adaptive Software Systems (SASS).

The package contains the design-time architecture-support workflow, runtime controller implementation, controlled safety/recovery experiments, and the comparative SWIM evaluation reported in the paper.

## 1. Package Structure

### `design_time/`

Contains the executable design-time architecture-support workflow and its generated artifacts.

Important files include:

- `config/swim_design_request.json` — architect-defined SWIM design request
- `knowledge/architecture_knowledge.json` — architectural knowledge base
- `knowledge/architecture_provenance_registry.json` — knowledge provenance information
- `outputs/architecture_alternatives.json` — generated architectural alternatives
- `outputs/architecture_evaluation.json` — weighted architecture evaluations
- `outputs/architecture_validation.json` — validation results
- `outputs/architect_decision.json` — human architecture decision
- `outputs/ADR-001.json` and `ADR-001.md` — accepted Architecture Decision Record
- `outputs/runtime_handoff.json` — design-to-runtime handoff result
- `outputs/runtime_design_feedback.json` — runtime-to-design feedback
- `outputs/architecture_reconsideration.json` — reconsideration result
- `outputs/design_recovery_run.json` — controlled bounded design-recovery result

### Runtime implementation

The runtime implementation is located at the repository root.

Important components include:

- `agent_controller.py`
- `monitor.py`
- `analyzer.py`
- `planner.py`
- `safety_checker.py`
- `executor.py`
- `rag_retriever.py`
- `runtime_kb.py`
- `failure_router.py`
- `outcome_evaluator.py`
- `fallback_planner.py`
- `fallback_controller.py`
- `operator_notifier.py`
- `swim_client.py`
- `llm_client.py`
- `trusted_policies.json`
- `trusted_fallback_policy.json`

The LLM supports analysis and planning, while deterministic mechanisms retain authority over safety checking and execution.

### `evaluation/e7/`

Contains the implementation of the four runtime-controller variants used in the comparative evaluation:

- **B0:** rule-based baseline with deterministic safety
- **B1:** LLM-based analysis and planning without runtime RAG or memory
- **B2:** LLM-based analysis and planning with runtime RAG and memory
- **B3:** full agentic architecture with RAG, runtime memory, failure routing, bounded replanning, deterministic safety, and fallback handling

The corresponding implementation files and `variant_spec.json` are included in this directory.

### `evaluation/e8/`

Contains the comparative evaluation infrastructure and results.

The evaluation includes five valid repetitions for each of B0, B1, B2, and B3, resulting in **20 valid live SWIM runs**.

The canonical experimental configuration is:

`evaluation/e8/config/e8_swim.ini`

Valid runs are stored under:

`evaluation/e8/results/<variant>/rep00` through `rep04`

Each valid run contains experimental evidence such as:

- `runtime_timeseries.csv`
- `cycle_metrics.jsonl`
- `episodes.jsonl`
- `manifest.json`
- `summary.json`
- `swim_simulator.log`
- `posthoc_actuation_validation.jsonl`

### `evaluation/e8/excluded_runs/`

Infrastructure- and API-related attempts excluded from the 20 valid comparative runs are retained separately for transparency.

These include attempts affected by:

- API anomalies
- API quota failures
- monitoring failure
- remote disconnection

These excluded attempts were not used when computing the reported comparative means.

### `evaluation/e8/aggregate/`

Contains the aggregated outputs used to report the comparative results.

Important files include:

- `aggregate_results.json`
- `variant_summary.csv`
- `run_level_metrics.csv`
- `paired_vs_b0.json`

Generated evaluation figures are available under:

`evaluation/e8/aggregate/figures/`

### `experiments/`

Contains controlled experiments EXP-A through EXP-F and their configuration.

Important safety/recovery evidence includes:

- `results/EXP-D_safety_rejection_run01.txt`
- `results/EXP-E_bounded_recovery_run01.txt`
- `results/EXP-F_fail_safe_run01.txt`

These experiments complement the nominal comparative evaluation by exercising safety rejection, bounded replanning, and fail-safe behavior.

## 2. Mapping to the Paper

### Comparative runtime-results table

The values reported in the comparative runtime-results table are available in:

`evaluation/e8/aggregate/variant_summary.csv`

The table reports means across five paired repetitions for each of B0, B1, B2, and B3.

### Longitudinal runtime figure

The underlying runtime data are stored in:

`evaluation/e8/results/B0/rep00` through `rep04`

`evaluation/e8/results/B1/rep00` through `rep04`

`evaluation/e8/results/B2/rep00` through `rep04`

`evaluation/e8/results/B3/rep00` through `rep04`

The corresponding time-series files are:

`runtime_timeseries.csv`

Figure-generation scripts are provided in:

- `evaluation/e8/e8_make_figures.py`
- `evaluation/e8/e8_make_additional_figures.py`

### Safety and recovery figure

The controlled experimental evidence underlying the safety/recovery results is available in:

- `experiments/results/EXP-D_safety_rejection_run01.txt`
- `experiments/results/EXP-E_bounded_recovery_run01.txt`
- `experiments/results/EXP-F_fail_safe_run01.txt`

EXP-D demonstrates deterministic rejection of an unsafe candidate, EXP-E demonstrates recovery through replanning, and EXP-F demonstrates bounded retry exhaustion followed by fail-safe handling.

### Post-hoc actuation validation

Post-hoc validation of runtime actuation is documented in:

- `evaluation/e8/POSTHOC_ACTUATION_VALIDATION.md`
- `evaluation/e8/posthoc_actuation_validation.csv`
- `evaluation/e8/posthoc_actuation_validation.json`

This validation preserves the original controller outcomes while separately examining whether expected configuration changes became observable shortly afterward.

## 3. Experimental Environment

Environment information is recorded in:

`experiments/config/environment.txt`

The experiments were executed using the SWIM self-adaptive web-system exemplar with Python and Docker.

The runtime LLM components obtain the API credential through the environment variable:

`OPENAI_API_KEY`

No API key or other credential is included in this package.

Because external LLM/API behavior can vary between executions, the complete raw data and outputs from the runs reported in the paper are preserved in this package.

## 4. Python Dependencies

The offline analysis and figure-generation scripts use common Python packages including:

- NumPy
- Matplotlib

Install the listed dependencies using:

```bash
python3 -m pip install -r requirements.txt

```

Most runtime components otherwise use the Python standard library.

## 5. Offline Inspection and Analysis

The stored raw and aggregate results can be inspected without executing SWIM or making LLM API calls.

The main aggregation script is:

```bash
python3 evaluation/e8/e8_aggregate.py
```

The included figure-generation scripts are:

```bash
python3 evaluation/e8/e8_make_figures.py
python3 evaluation/e8/e8_make_additional_figures.py
```

The already generated aggregate outputs corresponding to the reported evaluation are included under:

`evaluation/e8/aggregate/`

## 6. Live Comparative Harness

The live comparative experiment harness is:

`evaluation/e8/e8_live_harness.py`

A live rerun requires an appropriate SWIM/Docker environment and, for LLM-based variants, an externally supplied API credential.

A live rerun is not required to inspect the raw evidence or reproduce the offline analysis of the results reported in the paper.

## 7. Evaluation Notes

The comparative evaluation contains five paired repetitions per controller variant and is therefore interpreted descriptively. No statistical-significance claim is made.

The nominal sustained-overload workload did not naturally exercise all safety and recovery mechanisms. Controlled fault-injection experiments were therefore used separately to evaluate deterministic safety rejection, bounded replanning, and fail-safe behavior.

For the evaluated workload, the full agentic architecture did not outperform the rule-based baseline in nominal QoS and introduced additional reasoning overhead. Its additional capabilities concern grounded reasoning, runtime memory, explicit deterministic safety boundaries, bounded recovery, fallback handling, and separation between probabilistic reasoning and trusted runtime authority.
