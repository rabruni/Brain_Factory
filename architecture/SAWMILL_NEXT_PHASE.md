# Sawmill Next Phase

This document defines the next two bounded phases after Sawmill Runtime v0.1.

No runtime truth-model changes are in scope here.

## Phase A — Real Backend Reintroduction

Objective:

- restore actual worker backends through registry/config only
- validate each role independently
- keep the deterministic mock backend available for canary validation

Rules:

- `run.sh` remains the canonical entry path
- no change to `events.jsonl`
- no change to `status.json` projection rules
- no change to convergence semantics
- backend rollout happens through registry/env configuration only

Execution order:

1. restore one real backend/role at a time
2. validate that role under the governed path
3. preserve deterministic mock/canary backend for harness proof
4. treat backend instability as governed failure, not operator workaround

Success criteria:

- each role can be validated independently under governed execution
- real backend failures are visible in the harness
- deterministic canary remains available

## Phase B — Optional Turn D/E Supervisor

Objective:

- introduce LangGraph only as a bounded Turn D/E supervisor if needed

Boundary:

- builder -> reviewer -> builder -> evaluator

Rules:

- same `events.jsonl` stream
- same `status.json` projection
- no independent truth store
- no change to `run.sh` authority

LangGraph scope:

- transition control
- retry edges
- escalation edges
- resumability

LangGraph non-scope:

- truth storage
- global factory orchestration
- documentation authority
- registry authority

Success criteria:

- Turn D/E supervision is durable and resumable
- all state still converges through the existing harness truth model
- no second authority surface is introduced
