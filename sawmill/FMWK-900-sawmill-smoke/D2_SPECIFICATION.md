# D2: Specification - FMWK-900-sawmill-smoke
Meta: pkg:FMWK-900 | v:1.0.0 | status:Draft | author:Spec Agent | sources:sawmill/FMWK-900-sawmill-smoke/TASK.md, architecture/FWK-0-DRAFT.md v0.2 Section 3.0 | constitution:D1_CONSTITUTION.md

## Purpose

FMWK-900-sawmill-smoke is a system-test canary used only to prove the Sawmill pipeline can extract a minimal spec, build one tiny Python module, and verify one unit test. It is intentionally outside product and KERNEL scope and exists only to show that the end-to-end path can carry a trivial framework cleanly.

## NOT

FMWK-900-sawmill-smoke is NOT a product framework. It does not implement DoPeJar or DoPeJarMo behavior.

FMWK-900-sawmill-smoke is NOT a KERNEL framework. It does not implement primitives, lifecycle logic, governance plumbing, or runtime services.

FMWK-900-sawmill-smoke is NOT a dependency integration test. It does not use `platform_sdk`, Docker, immudb, or external services.

FMWK-900-sawmill-smoke is NOT a reusable framework pattern. It should stay smaller than any real framework.

## Scenarios

### Primary

**SC-001 - Module Exposes `ping`**
- Priority: P1
- Source: `TASK.md` Build Target
- GIVEN `smoke.py` exists in `staging/FMWK-900-sawmill-smoke/`
  WHEN Python imports `ping` from `smoke`
  THEN the symbol resolves successfully as a callable zero-argument function
- Testing Approach: Import `ping` directly in the test file and fail on import error.

**SC-002 - `ping()` Returns `"pong"`**
- Priority: P1
- Source: `TASK.md` Build Target
- GIVEN `ping` is imported successfully
  WHEN `ping()` is called
  THEN it returns the exact string `"pong"`
- Testing Approach: Unit assertion on exact string equality.

**SC-003 - Smoke Test Passes**
- Priority: P1
- Source: `TASK.md` Build Target
- GIVEN `test_smoke.py` imports `ping`
  WHEN pytest runs `test_ping`
  THEN the test passes with the assertion `ping() == "pong"`
- Testing Approach: Run pytest against the single owned test file.

### Edge Cases

**SC-004 - Missing or Renamed Function Fails Fast**
- Priority: P1
- Source: `TASK.md` Constraints
- GIVEN `smoke.py` does not expose `ping`
  WHEN `test_smoke.py` imports from `smoke`
  THEN the run fails immediately with an import error
- Testing Approach: Negative import check or direct failure during pytest collection.

**SC-005 - Wrong Return Literal Fails the Canary**
- Priority: P1
- Source: `TASK.md` Build Target
- GIVEN `ping()` returns anything other than `"pong"`
  WHEN pytest runs `test_ping`
  THEN the assertion fails and the package is rejected
- Testing Approach: Assertion failure in the owned unit test.

## Deferred Capabilities

**DEF-001**
- What: Any behavior beyond one function and one test
- Why Deferred: `TASK.md` explicitly limits scope to the smallest valid canary
- Trigger to add: A future smoke assignment explicitly expands the canary target
- Impact if never added: The canary stays intentionally tiny, which is acceptable

## Success Criteria

- [ ] `smoke.py` exists and exports `ping`
- [ ] `ping()` takes no arguments
- [ ] `ping()` returns the exact string `"pong"`
- [ ] `test_smoke.py` passes under pytest
- [ ] No extra files or dependencies are introduced

## Clarifications

See D6 CLR-001 and CLR-002.
