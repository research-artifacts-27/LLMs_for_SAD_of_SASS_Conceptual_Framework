# Runtime-to-Design Feedback Report

Generated: 2026-10-16T09:22:45.865554+00:00

## Purpose

Deterministically summarize accumulated runtime adaptation evidence and identify evidence that may justify human-initiated architecture review.

## Evidence Coverage

- Runtime episodes: 96
- Explicit execution outcomes: 94
- Episodes with safety information: 96
- Episodes with fail-safe field: 85

## Runtime Summary

- Final QoS violations: 8
- QoS violations at maximum capacity: 0
- Safety rejections: 0
- Episodes with recovery attempts: 0
- Total recovery attempts: 0
- Fail-safe episodes: 0
- Operator-intervention episodes: 0

## Architecture Review Triggers

### RTD-02 — Repeated partial adaptation outcomes

- Severity: medium
- Evidence count: 8
- Episode indices: [5, 6, 27, 28, 78, 79, 80, 81]
- Interpretation: Individual adaptations may be too incremental for some operating conditions, requiring multiple control cycles before the goal is restored.
- Design-review question: Should the architecture support stronger multi-step plans, adaptive planning horizons, or explicit reasoning about expected adaptation magnitude?

## Authority Boundary

This report does not redesign the architecture, approve an architecture, or modify trusted runtime policies. It provides evidence for human architect review.
