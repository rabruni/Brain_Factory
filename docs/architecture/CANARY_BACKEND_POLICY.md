# Canary Backend Policy

## Purpose

This document defines how Sawmill distinguishes governed runtime truth validation from external worker/backend reliability.

## Runtime Truth Validation

Sawmill harness validation proves:

- `events.jsonl` is canonical
- `status.json` is rebuildable from events
- evidence-gated completion works
- convergence validation works
- `run.sh` remains the canonical entry path

These properties may be validated with deterministic mock/canary worker backends.

## External Worker / Backend Reliability

External worker backends such as `codex`, `claude`, `gemini`, or later production backends are separate from harness truth validation.

Backend failures such as:

- connectivity failure
- authentication failure
- timeout
- startup failure

MUST appear as governed failures in the harness record.

They MUST NOT be hidden by manual operator substitution or undocumented bypass.

## Allowed Canary Practice

Mock or canary backends are allowed for:

- harness validation
- deterministic pipeline proof
- controlled canary execution

They are not a replacement for production backend rollout.

## Production Backend Reintroduction

Production backends MUST be reintroduced through configuration only:

- registry changes
- environment overrides

They MUST NOT require harness changes.

## Non-Negotiable Rule

Backend instability MUST appear as a governed failure, never as hidden operator substitution.
