# Agent Constraints

**Status**: AUTHORITY (runtime-adjacent)
**Authority label**: operational
**Date**: 2026-03-10

This document defines how Sawmill agents stay within governed boundaries.
If any statement here conflicts with `sawmill/run.sh` or
`sawmill/EXECUTION_CONTRACT.md`, those runtime authorities win.

## Runtime Truth Boundary

- Canonical pipeline path: `./sawmill/run.sh <FMWK-ID>`
- Default execution mode: unattended, exception-driven
- Interactive mode: `--interactive` only when explicitly requested
- Runtime endpoint: PASS or FAIL verdict (merge/release is out of runtime scope)
- Runtime routing source of truth: role, prompt, and artifact registries

## Core Constraints

1. Resolve ambiguity by walking the authority chain upward, never by guessing.
2. Follow turn inputs and outputs exactly; no out-of-scope reads.
3. Do not bypass the reviewer/evaluator loop in Turn D/E.
4. Do not simulate approvals with piped stdin or synthetic input.
5. Block and escalate when instructions conflict with authority docs.

## Turn Constraints

### Turn A/B (spec-agent)

- Reads design authority and prior turn artifacts only.
- Produces D1-D6 (A) and D7/D8/D10 plus handoff (B).
- Gate progression is runtime-enforced by `run.sh` stage checks.

### Turn C (holdout-agent)

- Reads D2 + D4 only.
- Produces D9 holdout scenarios.
- Must remain isolated from plan/build artifacts.

### Turn D (builder + reviewer)

- Builder must produce 13Q answers first.
- Reviewer returns one parseable verdict line: PASS, RETRY, or ESCALATE.
- Implementation proceeds only on reviewer PASS.
- Shared attempt budget with evaluator loop: max 3 attempts.

### Turn E (evaluator)

- Reads D9 holdouts + staged build output.
- Produces evaluation report and failure lines.
- Final parseable verdict line: PASS or FAIL.

## Isolation Rules

- Builder NEVER reads holdouts.
- Evaluator NEVER reads handoff/spec/builder reasoning.
- Holdout agent reads D2 + D4 only.
- Cleared context means a fresh worker session.

## Drift Signals

- Human-gate language presented as mandatory runtime behavior.
- PR branch or merge actions described as runtime success criteria.
- Direct worker dispatch presented as equivalent to requested `run.sh` path.
- Role ownership that disagrees with the registries.

## Override Protocol

When an instruction conflicts with authority:

1. Stop.
2. Cite the conflict with file references.
3. Escalate for human resolution.
4. Resume only after the conflict is resolved.
