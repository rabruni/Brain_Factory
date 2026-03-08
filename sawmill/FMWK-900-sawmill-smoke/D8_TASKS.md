# D8: Tasks — FMWK-900-sawmill-smoke
Meta: plan:D7 v1.0.0 | status:Draft | total_tasks:3 | parallel_opportunities:0

## MVP Scope

**In Scope (all P1 scenarios):**

| D2 Scenario | Priority | In MVP |
|-------------|----------|--------|
| SC-001 - Module Exposes `ping` | P1 | YES |
| SC-002 - `ping()` Returns `"pong"` | P1 | YES |
| SC-003 - Smoke Test Passes | P1 | YES |
| SC-004 - Missing or Renamed Function Fails Fast | P1 | YES |
| SC-005 - Wrong Return Literal Fails the Canary | P1 | YES |

**Deferred:**

| D2 Item | Reason |
|---------|--------|
| DEF-001 - Any behavior beyond one function and one test | `TASK.md`, D1 Article 2, and D2 defer all expansion beyond the canary itself |

## Tasks

### Phase 0 — Test Harness

**T-001: Author the owned pytest canary**
- Phase: 0 — Test Harness
- Parallel/Serial: Serial
- Dependency: None
- Scope: S
- Scenarios Satisfied: SC-001, SC-002, SC-003, SC-004, SC-005
- Contracts Implemented: IN-002, OUT-002, ERR-001, ERR-002

Acceptance Criteria:
1. Create `staging/FMWK-900-sawmill-smoke/test_smoke.py`.
2. The file contains `from smoke import ping`.
3. The file defines exactly one in-scope test, `def test_ping():`.
4. The test uses the exact assertion `assert ping() == "pong"`.
5. Before `smoke.py` is implemented, running pytest fails because the import boundary is real and fail-fast.

### Phase 1 — Core Logic

**T-002: Implement the smoke module**
- Phase: 1 — Core Logic
- Parallel/Serial: Serial
- Dependency: T-001 (DTT: test exists first)
- Scope: S
- Scenarios Satisfied: SC-001, SC-002
- Contracts Implemented: IN-001, OUT-001, SIDE-001

Acceptance Criteria:
1. Create `staging/FMWK-900-sawmill-smoke/smoke.py`.
2. The file defines `def ping() -> str:`.
3. `ping()` accepts no arguments.
4. `ping()` returns the exact string literal `"pong"` on every call.
5. `smoke.py` introduces no imports, helpers, adapters, schemas, or custom error handling.

### Phase 2 — Validation

**T-003: Prove the canary and enforce scope**
- Phase: 2 — Validation
- Parallel/Serial: Serial
- Dependency: T-001, T-002 (test and implementation must both exist)
- Scope: S
- Scenarios Satisfied: SC-003, SC-004, SC-005
- Contracts Implemented: IN-002, OUT-002, SIDE-001, ERR-001, ERR-002

Acceptance Criteria:
1. From `staging/FMWK-900-sawmill-smoke/`, run `python3 -m pytest test_smoke.py -v --tb=short`.
2. The expected final result is `1 passed`.
3. Any import failure or wrong return literal produces a non-zero exit and blocks handoff.
4. The human-authored files in `staging/FMWK-900-sawmill-smoke/` are exactly `smoke.py` and `test_smoke.py`.
5. No dependency beyond Python and pytest is introduced.

## Task Dependency Graph

```text
T-001 -> T-002 -> T-003
```

## Summary

| Task | Phase | Scope | Serial/Parallel | Scenarios |
|------|-------|-------|-----------------|-----------|
| T-001 | 0 — Test Harness | S | Serial | SC-001, SC-002, SC-003, SC-004, SC-005 |
| T-002 | 1 — Core Logic | S | Serial | SC-001, SC-002 |
| T-003 | 2 — Validation | S | Serial | SC-003, SC-004, SC-005 |

Total: 3 tasks, 3 phases, 0 parallelizable pairs, 3 serial waves.
MVP Tasks: T-001, T-002, T-003.
