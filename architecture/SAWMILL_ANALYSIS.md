# Sawmill Analysis

**Status**: HISTORICAL ANALYSIS (non-operational)
**Authority label**: historical
**Date**: 2026-03-10

This file is design analysis and rationale, not runtime contract.
Operational source of truth for execution behavior is:

- `sawmill/run.sh`
- `sawmill/EXECUTION_CONTRACT.md`
- `sawmill/ROLE_REGISTRY.yaml`
- `sawmill/PROMPT_REGISTRY.yaml`
- `sawmill/ARTIFACT_REGISTRY.yaml`

## Why This Exists

Sawmill is the governed framework factory for converting framework tasks into
verified artifacts through a staged multi-agent pipeline.

This analysis records design intent, tradeoffs, and guardrail rationale.
It should not be used to override runtime behavior.

## Current Runtime Snapshot (Reference)

- Entry path: `./sawmill/run.sh <FMWK-ID>`
- Default mode: unattended; `--interactive` is exception-only
- Turn ownership:
  - A: spec-agent
  - B: spec-agent (plan outputs)
  - C: holdout-agent
  - D: builder -> reviewer -> builder
  - E: evaluator
- Reviewer verdicts: PASS, RETRY, ESCALATE
- Evaluator verdicts: PASS, FAIL
- Shared attempt budget: 3 attempts across review/evaluation loop
- Pipeline endpoint: PASS or FAIL (merge/release is out of runtime scope)

## Design Rationale

### 1. Separation of generation and evaluation

Builder never sees holdouts. Evaluator never sees builder planning context.
This reduces teaching-to-the-test behavior and confirmation bias.

### 2. Controlled comprehension gate before implementation

Turn D begins with a 13Q artifact reviewed by a separate reviewer role.
This pushes scope/contract errors earlier than code execution.

### 3. Registry-governed dispatch

Role routing, prompt ownership, and artifact paths are registry-defined and
validator-backed to reduce ad hoc shell branching and config drift.

### 4. Fail-closed prompt flow

Prompt rendering, required inputs, and expected outputs are enforced before a
stage is accepted. Runtime prefers explicit failure over silent continuation.

### 5. Portal as verification surface, not runtime authority

Portal pages are guidance and evidence surfaces. Runtime truth remains in
`run.sh` and execution contract artifacts.

## Known Residual Risks

- Some artifact registry fields remain metadata-heavy compared to strict
  runtime policy enforcement.
- Freshness checks are mtime-based; strong regeneration proof is future
  hardening work.
- Doc drift can reappear if source-vs-mirror discipline is not enforced.

## Maintenance Rule

When runtime semantics change, update this file only as analysis context.
Update runtime authorities first.
