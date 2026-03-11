# Sawmill Execution Contract

**Status**: OPERATIONAL SOURCE OF TRUTH
**Authority label**: operational
**Date**: 2026-03-09

## Purpose

This document defines the authoritative runtime execution model for the
Sawmill system. If documentation about stage flow, worker ownership, or portal
freshness disagrees with this file or with `sawmill/run.sh`, this file and
`sawmill/run.sh` win.

## Authoritative Runtime Chain

```text
Human -> Claude orchestrator -> registry-resolved workers -> Sawmill turns A-E
```

- **Human** starts the run, and resolves true source-truth conflicts or explicit escalations.
- **Claude** is the orchestrator. Claude reads state, invokes `run.sh`,
  supervises retries, and reports verdicts.
- **Workers** are resolved from `sawmill/ROLE_REGISTRY.yaml`. Spec/build/holdout/portal work use the registry defaults, and critical review/evaluation roles may use a max-capability policy.
- Alternate CLIs may exist, but they are overrides, not the default contract.

## Runtime Authority

- `sawmill/run.sh` is the runtime authority for stage execution.
- `sawmill/ROLE_REGISTRY.yaml` is the canonical source for role metadata,
  role-file paths, default backends, model policies, allowed backends, and env override names.
- `sawmill/PROMPT_REGISTRY.yaml` is the canonical source for stage/task prompt files.
- `sawmill/ARTIFACT_REGISTRY.yaml` is the canonical source for runtime artifact paths and standards references.
- `docs/sawmill/RUN_VERIFICATION.md` is the steward-owned human-readable evidence checklist for verifying runs against the filesystem.
- `SAWMILL_*_AGENT` environment variables are runtime overrides to registry
  defaults, not a second source of truth.
- Agent role files in `.claude/agents/` define role behavior and isolation.
- `AGENTS.md` / `CLAUDE.md` provide institutional context and summarize this
  contract, but do not replace it.
- If documentation names a runtime stage step, that step must exist in
  `run.sh`.

## Document Authority Labels

Runtime-adjacent docs should declare one authority label near the top:

- `operational`: binding runtime behavior (must match `run.sh`)
- `narrative`: guidance/checklists that explain runtime evidence
- `status`: portal/status reporting surfaces
- `historical`: analysis or archival rationale, non-operational

## Checkpoint and Escalation Policy

- Default execution is unattended and exception-driven.
- `./sawmill/run.sh --interactive` is the supported opt-in mode for live human checkpoints.
- Non-interactive stdin, piped input, `yes ''`, or synthetic newlines are never valid approval mechanisms.
- Turn A and Turn B/C reviews are automatic checkpoints plus stage validation.
- Turn D uses automated builder review before implementation and evaluator review after implementation.
- Final merge or release is outside the runtime path. The pipeline ends in PASS or FAIL.
- When the requested execution path is `./sawmill/run.sh`, direct worker dispatch is not an equivalent substitute unless the human explicitly changes the request.

## Portal Ownership Split

### Runner-owned

These happen inside the authoritative stage flow:

- stage-local status updates
- framework-local stage audits
- stop-on-mismatch behavior for stage-local portal state

### Portal-steward-owned

These run after each stage for broader portal alignment:

- mirror gaps not covered by pre-commit sync
- `mkdocs.yml` nav drift
- `catalog-info.yaml` drift
- narrative freshness
- `docs/PORTAL_STATUS.md` and `sawmill/PORTAL_CHANGESET.md` maintenance
- `docs/PORTAL_MAP.yaml` upkeep

### Auditor-owned

- drift diagnosis
- contradiction reporting
- evidence collection

Audits diagnose. They do not rewrite source truth.

## Mirror Freshness

- `.githooks/pre-commit` is the primary automatic mirror-sync mechanism.
- `portal-steward` verifies and repairs anything the hook does not cover.
- `docs/PORTAL_MAP.yaml` declares which source-to-surface mappings must exist.

## Automatic vs Manual

### Automatic

- `run.sh` stage execution
- `run.sh` stage-local portal updates and stage audits
- portal-steward alignment after each stage
- pre-commit mirror sync for covered source files

### Manual or maintenance-triggered

- portal narrative cleanup beyond stage-relevant scope
- nav/catalog reconciliation beyond stage-relevant scope
- portal health refreshes outside stage-local status updates

## Failure Rule

If a doc claims:

- a runtime role that `run.sh` never invokes, or
- a per-stage runtime step that `run.sh` does not perform,
- or that synthetic stdin can satisfy a human approval gate,

that doc is stale and must be corrected.
