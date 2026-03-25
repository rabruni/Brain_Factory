# D8: Tasks — Sawmill Smoke Canary (FMWK-900)
Meta: plan: D7 v1.0.0 | status:Final | total tasks:4 | parallel opportunities:0

## MVP Scope
All P1 scenarios in D2 are in scope for this build: SC-001, SC-002, SC-003, SC-004, and SC-005. No scenarios are deferred.

## Tasks (T-### IDs, phased)
Phases: 0=Foundation, 1=Core Logic, 2=Validation, 3=Final Verification

### T-001 — Establish framework-local test target
- Phase + name: Phase 0 — Establish framework-local test target
- Parallel/Serial: Serial
- Dependency: None
- Scope: S
- Scenarios Satisfied: D2 SC-003, SC-005
- Contracts Implemented: D4 ERR-003, ERR-001
- Acceptance Criteria:
  1. Builder confirms only `smoke.py` and `test_smoke.py` are created for this framework.
  2. No dependencies, services, schemas, adapters, or extra modules are introduced.
  3. The working test command is defined as framework-local `pytest -q test_smoke.py`.

### T-002 — Implement canary function
- Phase + name: Phase 1 — Implement canary function
- Parallel/Serial: Serial
- Dependency: T-001 (scope must be fixed before code is written)
- Scope: S
- Scenarios Satisfied: D2 SC-001, SC-003
- Contracts Implemented: D4 IN-001, OUT-001, SIDE-001, ERR-002, ERR-003
- Acceptance Criteria:
  1. `smoke.py` exists.
  2. `smoke.py` defines exactly `def ping() -> str:`.
  3. `ping()` accepts zero arguments.
  4. `ping()` returns the exact lowercase literal `"pong"`.
  5. The module introduces no side effects, persistence, or imports beyond what is needed for the function definition.

### T-003 — Implement deterministic validation test
- Phase + name: Phase 2 — Implement deterministic validation test
- Parallel/Serial: Serial
- Dependency: T-002 (`ping()` must exist to validate the contract)
- Scope: S
- Scenarios Satisfied: D2 SC-002, SC-004
- Contracts Implemented: D4 IN-001, OUT-001, ERR-001, ERR-002
- Acceptance Criteria:
  1. `test_smoke.py` exists.
  2. `test_smoke.py` imports `ping` from `smoke`.
  3. `test_smoke.py` defines exactly one test, `test_ping()`.
  4. `test_ping()` asserts `ping() == "pong"`.
  5. The test fails if the function is missing, renamed, takes arguments, or returns anything other than `"pong"`.

### T-004 — Run full framework verification
- Phase + name: Phase 3 — Run full framework verification
- Parallel/Serial: Serial
- Dependency: T-003 (verification requires finished source and test files)
- Scope: S
- Scenarios Satisfied: D2 SC-002, SC-003, SC-004, SC-005
- Contracts Implemented: D4 ERR-001, ERR-002, ERR-003
- Acceptance Criteria:
  1. Builder runs `cd staging/FMWK-900-sawmill-smoke && pytest -q test_smoke.py`.
  2. The command reports one passing test and zero failures.
  3. Builder records the exact command and pasted output in `RESULTS.md`.
  4. Final review confirms only the two owned files are in scope.

## Task Dependency Graph
```text
T-001 -> T-002 -> T-003 -> T-004
```

## Summary
| Task | Phase | Scope | Serial/Parallel | Scenarios |
|------|-------|-------|-----------------|-----------|
| T-001 | 0 | S | Serial | SC-003, SC-005 |
| T-002 | 1 | S | Serial | SC-001, SC-003 |
| T-003 | 2 | S | Serial | SC-002, SC-004 |
| T-004 | 3 | S | Serial | SC-002, SC-003, SC-004, SC-005 |

Total: 4 tasks, 4 phases, 0 parallelizable pairs, 4 serial waves.
MVP Tasks: T-001, T-002, T-003, T-004.
