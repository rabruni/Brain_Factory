# D7: Plan — FMWK-900-sawmill-smoke
Meta: v:1.0.0 (matches D2) | status:Draft | constitution:D1 v1.0.0 | gap_analysis:D6 PASS (0 open)

## Summary

FMWK-900-sawmill-smoke is a system-test canary whose only job is to prove the Sawmill path can carry a minimal framework cleanly from approved spec to builder output. The build creates exactly two files in `staging/FMWK-900-sawmill-smoke/`: `smoke.py`, which exposes `ping() -> "pong"`, and `test_smoke.py`, which imports `ping` and asserts the exact literal return. The first and only use case is local pytest execution that passes when the canary is correct and fails immediately when the function is missing or returns the wrong value.

## Technical Context

| Item | Value |
|------|-------|
| Language / Version | Python (version unspecified by D1-D6; keep syntax equivalent to `TASK.md`) |
| Key Dependencies | None in `smoke.py`; `pytest` in `test_smoke.py` only |
| Storage | Local staging filesystem only |
| Testing Framework | `pytest` |
| Platform | Brain_Factory repo, `staging/FMWK-900-sawmill-smoke/` |
| Performance Goals | Deterministic local pass/fail on one import and one assertion |
| Scale / Scope | Exactly one function, one test, two owned files |

## Constitution Check

| Article | Principle | Compliant | Notes |
|---------|-----------|-----------|-------|
| 1: SPLITTING | Independently authorable | YES | The plan creates only `smoke.py` and `test_smoke.py` in staging, with no co-authored framework or service dependency. |
| 2: MERGING | Minimal capability surface | YES | The only behavior is `ping() -> "pong"` and the only test is `test_ping`; no product, KERNEL, or infrastructure behavior is added. |
| 3: OWNERSHIP | Exclusive file ownership | YES | The plan owns exactly two private files and introduces no shared schemas, contracts, or reusable assets. |
| 4: SOURCE OF TRUTH | Task-locked scope | YES | Every component, task, and command traces back to `TASK.md`, D2 scenarios, and D4 contracts only. |
| 5: DETERMINISM | Literal validation only | YES | Validation is the exact assertion `ping() == "pong"` with no arguments and no fuzzy interpretation. |
| 6: ISOLATION | Local, fail-fast execution | YES | The build uses only local Python and pytest; it forbids `platform_sdk`, Docker, immudb, networking, custom errors, and data models. |

## Architecture Overview

```text
python3 -m pytest test_smoke.py
        |
        v
test_smoke.py imports ping from smoke
        |
        v
smoke.py exposes ping() -> "pong"
        |
        v
test_ping asserts ping() == "pong"
        |
        v
pytest exits 0 on success, non-zero on import or assertion failure
```

### Component Responsibilities

**`smoke.py`**
- File: `staging/FMWK-900-sawmill-smoke/smoke.py`
- Responsibility: define the single in-scope callable.
- Implements: D2 SC-001, SC-002
- Depends On: none
- Exposes: `ping() -> str`

**`test_smoke.py`**
- File: `staging/FMWK-900-sawmill-smoke/test_smoke.py`
- Responsibility: prove importability and exact literal behavior with one owned pytest.
- Implements: D2 SC-003, SC-004, SC-005
- Depends On: `smoke.py`, `pytest`
- Exposes: `test_ping() -> None`

### File Creation Order

```text
staging/FMWK-900-sawmill-smoke/
├── test_smoke.py   # single owned pytest; imports ping and asserts the literal result
└── smoke.py        # single zero-argument function returning "pong"
```

### Testing Strategy

- Unit Tests: one owned pytest, `test_ping`, covers import resolution and exact literal return.
- Integration Tests: none in scope; D1 Article 6 and D2 NOT explicitly forbid dependency or service integration.
- Smoke Test: `cd staging/FMWK-900-sawmill-smoke && python3 -m pytest test_smoke.py -v --tb=short`
  Expected result: `1 passed`.

### Complexity Tracking

| Component | Est. Lines | Risk | Notes |
|-----------|-----------|------|-------|
| `smoke.py` | ~3 | Low | One deterministic function, no imports, no state |
| `test_smoke.py` | ~4 | Low | One import and one exact assertion |
| Total source | ~3 | Low | Fixed by TASK.md |
| Total tests | ~4 | Low | Single canary assertion |

### Migration Notes

Greenfield — no migration.
