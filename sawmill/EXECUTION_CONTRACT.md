# Sawmill Execution Contract

**Status**: OPERATIONAL SOURCE OF TRUTH
**Date**: 2026-03-09

## Purpose

This document defines the authoritative runtime execution model for the
Sawmill system. If documentation about stage flow, worker ownership, or portal
freshness disagrees with this file or with `sawmill/run.sh`, this file and
`sawmill/run.sh` win.

## Authoritative Runtime Chain

```text
Human -> Claude orchestrator -> Codex worker -> Sawmill turns A-E
```

- **Human** starts the run, approves explicit gates, and resolves true
  source-truth conflicts.
- **Claude** is the orchestrator. Claude reads state, invokes `run.sh`,
  supervises retries, and reports verdicts.
- **Codex** is the default worker backend for Turns A-E. Codex executes the
  assigned role file and produces turn artifacts.
- Alternate CLIs may exist, but they are overrides, not the default contract.

## Runtime Authority

- `sawmill/run.sh` is the runtime authority for stage execution.
- Agent role files in `.claude/agents/` define role behavior and isolation.
- `AGENTS.md` / `CLAUDE.md` provide institutional context and summarize this
  contract, but do not replace it.
- If documentation names a runtime stage step, that step must exist in
  `run.sh`.

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

that doc is stale and must be corrected.
