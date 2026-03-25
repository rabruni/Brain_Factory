# D7: Plan — Sawmill Smoke Canary (FMWK-900)
Meta: v:1.0.0 (matches D2) | status:Final | constitution: D1 v1.0.0 | gap analysis: D6 PASS (0 open)

## Summary
FMWK-900-sawmill-smoke is the smallest possible end-to-end Sawmill canary. It implements one Python function, `ping()`, that returns the exact literal `"pong"`, plus one unit test that proves the contract and fails on drift. The build stays intentionally narrow so Sawmill can validate spec generation, review, build, and test execution without pulling in product logic, KERNEL patterns, services, or shared abstractions. The first and only use case is a local Python caller or test runner invoking `ping()` and receiving `"pong"`.

## Technical Context
| Dimension | Value |
|-----------|-------|
| Language/Version | Python 3.11+ |
| Key Dependencies | Python stdlib only; `pytest` for test execution |
| Storage | None |
| Testing Framework | `pytest` |
| Platform | Local file-based framework staging |
| Performance Goals | Single test completes quickly and deterministically |
| Scale/Scope | One source file, one test file, one behavior |

## Constitution Check
| Article | Principle | Compliant (YES/NO) | Notes (how architecture satisfies) |
|---------|-----------|--------------------|-----------------------------------|
| 1. SPLITTING | Independently authorable as one module and one test | YES | The plan creates only `smoke.py` and `test_smoke.py`, with no companion framework or shared package. |
| 2. MERGING | No capability beyond `ping() -> "pong"` | YES | No helpers, adapters, schemas, CLI, or extra behavior are planned. |
| 3. OWNERSHIP | Exclusive ownership of two files and no shared state | YES | The framework owns only the module and its test and introduces no persistent artifacts or interfaces. |
| 4. SOURCE OF TRUTH | Scope comes from task and authority docs only | YES | Every task in D8 traces to D2 scenarios and D4 contracts derived from the provided sources. |
| 5. ISOLATION | No `platform_sdk`, Docker, external APIs, or primitives | YES | The plan uses only plain Python and a direct unit test. |
| 6. VALIDATION | One deterministic test proves compliance | YES | `test_ping()` is the sole validation path and asserts the exact literal. |
| 7. FAILURE HANDLING AND DETERMINISM | Drift fails fast through tests | YES | The return value and import/signature are checked directly so any deviation becomes an immediate test failure. |
| 8. TRACEABILITY | All artifacts map directly to smoke assignment | YES | Components, tasks, and commands all reference only `ping()` and `test_ping()`. |

## Architecture Overview
```text
Python caller / pytest
        |
        v
   smoke.py
   ping() -> "pong"
        |
        v
 test_smoke.py
 assert ping() == "pong"
```

### Component Responsibilities
- File: `smoke.py`
  - Responsibility | Implements (D2 SC-001, SC-003, SC-004) | Depends On: none | Exposes: `ping() -> str`
- File: `test_smoke.py`
  - Responsibility | Implements (D2 SC-002, SC-004, SC-005) | Depends On: `smoke.ping` and `pytest` runner | Exposes: `test_ping() -> None`

### File Creation Order
```text
staging/FMWK-900-sawmill-smoke/
├── smoke.py        create first; defines the single owned runtime behavior
└── test_smoke.py   create second; proves the contract and catches drift
```

### Testing Strategy
- Unit Tests: one direct assertion in `test_ping()`; no mocks, fixtures, or doubles
- Integration Tests: none; D2 explicitly excludes services and integrations
- Smoke Test: `cd staging/FMWK-900-sawmill-smoke && pytest -q test_smoke.py` with expected result `1 passed`

### Complexity Tracking
| Component | Est. Lines | Risk (Low/Med/High) | Notes |
|-----------|------------|---------------------|-------|
| `smoke.py` | ~3 | Low | One function, zero dependencies |
| `test_smoke.py` | ~4 | Low | One assertion, deterministic |
| Total source | ~3 | Low | |
| Total tests | ~4 | Low | |

### Migration Notes
Greenfield — no migration.
