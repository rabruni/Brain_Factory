# D8: Tasks — sawmill smoke canary
Meta: plan: D7 1.0.0 | status:Final | total tasks:3 | parallel opportunities:0

## MVP Scope
In scope: D2 SC-001, SC-002, SC-003, SC-004. Deferred: only D2 DEF-001, which remains out of scope unless a future task broadens the canary beyond `ping() -> "pong"`.

## Tasks (T-### IDs, phased)
### T-001
- Phase + name: 1 = Core Logic: implement deterministic source module
- Parallel/Serial: Serial
- Dependency: None
- Scope: S
- Scenarios Satisfied: D2 SC-001, SC-003
- Contracts Implemented: D4 IN-001, OUT-001, SIDE-001, ERR-002
- Acceptance Criteria:
  1. `smoke.py` exists and is one of the two owned files from D3 E-001.
  2. `smoke.py` defines exactly `def ping() -> str`.
  3. `ping()` accepts no arguments, matching D4 IN-001.
  4. `ping()` returns the literal string `"pong"`, matching D4 OUT-001.
  5. `smoke.py` introduces no side effects or external imports, satisfying D4 SIDE-001 and D2 SC-003.

### T-002
- Phase + name: 2 = Validation Logic: implement the single unit test
- Parallel/Serial: Serial
- Dependency: T-001 (test must import implemented function)
- Scope: S
- Scenarios Satisfied: D2 SC-002, SC-003
- Contracts Implemented: D4 IN-001, OUT-001, ERR-001, ERR-002
- Acceptance Criteria:
  1. `test_smoke.py` exists and is one of the two owned files from D3 E-002.
  2. `test_smoke.py` imports `ping` from `smoke.py`.
  3. `test_smoke.py` defines exactly one test function named `test_ping`.
  4. `test_ping` asserts `ping() == "pong"` exactly, matching D3 E-002 and D4 OUT-001.
  5. Import failure or wrong return value fails through the normal test run, satisfying D4 ERR-001 and ERR-002.

### T-003
- Phase + name: 3 = Scope Verification: verify minimal package boundaries
- Parallel/Serial: Serial
- Dependency: T-002 (verify final staged output)
- Scope: S
- Scenarios Satisfied: D2 SC-003, SC-004
- Contracts Implemented: D4 SIDE-001, ERR-003
- Acceptance Criteria:
  1. Final staged source contains only `smoke.py` and `test_smoke.py` for framework-owned code.
  2. Neither file imports `platform_sdk`, Docker clients, or external services.
  3. No schemas, adapters, custom exceptions, or additional support files are introduced.
  4. The single unit test is executed and passes as the scope-compliance proof point.

## Task Dependency Graph
```text
T-001 --> T-002 --> T-003
```

## Summary
| Task | Phase | Scope | Serial/Parallel | Scenarios |
| --- | --- | --- | --- | --- |
| T-001 | 1 | S | Serial | SC-001, SC-003 |
| T-002 | 2 | S | Serial | SC-002, SC-003 |
| T-003 | 3 | S | Serial | SC-003, SC-004 |

Total: 3 tasks, 3 phases, 0 parallelizable pairs, 3 serial waves.
MVP Tasks: T-001, T-002, T-003.
