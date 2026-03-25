# Builder Handoff — Sawmill Smoke Canary (FMWK-900)
Prompt Contract Version: 1.0.0

## 1. Mission
Build the `FMWK-900-sawmill-smoke` framework as the smallest possible Sawmill canary. The implementation is intentionally limited to one Python module, `smoke.py`, containing `ping() -> str`, and one test file, `test_smoke.py`, containing `test_ping()`. The only acceptable runtime behavior is that `ping()` returns the exact literal `"pong"`. This framework exists to exercise the pipeline, not to add product, KERNEL, or infrastructure capability.

## 2. Critical Constraints
1. Staging-only. Write only inside `staging/FMWK-900-sawmill-smoke/`.
2. DTT is mandatory. For each behavior in D8, define the test expectation first, run it, then implement the minimum code to pass. If code was written before the test, delete it and redo. Reference: `Templates/TDD_AND_DEBUGGING.md`.
3. Package everything required for the framework, but nothing more. The final package contains only `smoke.py` and `test_smoke.py`.
4. E2E verify before declaring done. Run the exact pytest command and paste the full output into `RESULTS.md`.
5. No hardcoding beyond the declared contract. The only allowed literal runtime output is `"pong"`.
6. No file replacement. Edit incrementally; if you must rewrite a file, explain why in `RESULTS.md`.
7. Deterministic archives only. If any archive is produced, it must be reproducible byte-for-byte.
8. Results file is mandatory. Write `sawmill/FMWK-900-sawmill-smoke/RESULTS.md` before reporting completion.
9. Full regression of all packages in scope is mandatory. For this framework, that means the full framework-local pytest run, not a partial or hand-waved check.
10. Baseline snapshot is mandatory. Record the pre-build package/test baseline observed in this session before implementation.
11. TDD discipline is enforced. Every “tests pass” claim requires pasted output from this session.
12. No hardcoded expansion of architecture. Do not add `platform_sdk`, Docker, immudb, services, schemas, adapters, error classes, or any primitive-related code.

## 3. Architecture/Design
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

Data flow:
1. A caller or test imports `ping` from `smoke`.
2. `ping()` executes with zero arguments.
3. The function returns `"pong"`.
4. `test_ping()` compares the return value to the exact literal.
5. Any signature drift, import drift, or return drift becomes a direct test failure.

Interfaces and boundaries:
- `smoke.py`
  - Interface: `ping() -> str`
  - Boundary: no arguments, no side effects, no imports required
- `test_smoke.py`
  - Interface: `test_ping() -> None`
  - Boundary: imports `ping`, executes one assertion, no fixtures or mocks

## 4. Implementation Steps
1. Create `test_smoke.py` with a single failing test importing `ping` from `smoke` and asserting `ping() == "pong"`.
Why: the test defines the only allowed observable behavior before production code exists.
2. Run `pytest -q test_smoke.py` and capture the failure.
Why: DTT requires evidence that the behavior was specified before implementation.
3. Create `smoke.py` with exactly `def ping() -> str:` returning `"pong"`.
Why: D2 and D4 define one callable surface only; anything else is scope drift.
4. Re-run `pytest -q test_smoke.py` until the test passes.
Why: D1 Article 6 requires executed proof, not inspection.
5. Inspect the framework directory and confirm only `smoke.py` and `test_smoke.py` are present.
Why: D1 Articles 1-3 and D4 ERR-003 reject extra scope.
6. Run the full framework regression and write `RESULTS.md` with pasted output, file hashes, and baseline snapshot.
Why: completion requires evidence and traceability, not an informal claim.

## 5. Package Plan
Package ID: `FMWK-900-sawmill-smoke`
Layer: SYSTEM-TEST

| Asset | Type | Action |
|-------|------|--------|
| `smoke.py` | Source | CREATE |
| `test_smoke.py` | Test | CREATE |

Dependencies:
- Python stdlib only for source
- `pytest` for test execution

Manifest expectations:
- Package remains a two-file canary
- No additional package metadata, schemas, or service integrations are introduced

## 6. Test Plan
Mandatory minimum for a 1-2 file package: 10+ tests is the standard, but this framework’s spec authorizes only one owned test file and one behavior. Do not add synthetic extra tests just to inflate the count; keep the implementation aligned with D1/D2 and flag the standard/minimal-scope mismatch in `RESULTS.md` if questioned.

| Test Method | Description | Expected Behavior |
|-------------|-------------|-------------------|
| `test_ping` | Import `ping` from `smoke` and call it directly | Assertion passes only when the function exists, takes no arguments, and returns exactly `"pong"` |

## 7. Existing Code to Reference
| What | Where | Why |
|------|-------|-----|
| Framework task definition | `sawmill/FMWK-900-sawmill-smoke/TASK.md` | Authoritative source for owned files, dependencies, and constraints |
| Constitution boundaries | `sawmill/FMWK-900-sawmill-smoke/D1_CONSTITUTION.md` | Defines ALWAYS/ASK FIRST/NEVER scope |
| Scenario and contract traceability | `sawmill/FMWK-900-sawmill-smoke/D2_SPECIFICATION.md`, `sawmill/FMWK-900-sawmill-smoke/D4_CONTRACTS.md` | Confirms exact behavior and rejection conditions |

## 8. E2E Verification
Run exactly:

```bash
cd staging/FMWK-900-sawmill-smoke && pytest -q test_smoke.py
```

Expected output:
```text
1 passed
```

Optional confirming scope check:

```bash
cd staging/FMWK-900-sawmill-smoke && ls
```

Expected visible files:
```text
smoke.py
test_smoke.py
```

## 9. Files Summary
| File | Location | Action (CREATE/MODIFY) |
|------|----------|------------------------|
| `smoke.py` | `staging/FMWK-900-sawmill-smoke/smoke.py` | CREATE |
| `test_smoke.py` | `staging/FMWK-900-sawmill-smoke/test_smoke.py` | CREATE |

## 10. Design Principles
1. Keep the framework minimal enough to remain a true canary.
2. Prefer direct behavior over architecture scaffolding.
3. Treat any extra file or dependency as scope drift.
4. Use executed tests as the only proof of correctness.
5. Preserve deterministic, literal behavior with no fallback paths.

## 11. Verification Discipline
Every “pass” claim must include the exact command and pasted output from this session. `RESULTS.md` must include:
- Status
- Files created with SHA256
- Files modified, if any, with before/after SHA256
- Test command and full output
- Full regression command and full output
- Baseline snapshot
- Clean-room verification notes
- Issues encountered
- Notes for reviewer
- Session log

Red flags:
- “Should work”
- “Probably passes”
- “It’s trivial so I didn’t run it”
- Any completion claim without pasted test output

Reference: `Templates/TDD_AND_DEBUGGING.md`

## 12. Mid-Build Checkpoint
After `test_smoke.py` passes and before writing `RESULTS.md`, record:
- the exact pytest command
- pasted output showing one passing test
- the list of files created
- any deviation from spec, or `None`

Continue unless the orchestrator escalates.

## 13. Self-Reflection
Before reporting completion, verify all of the following:
- The code matches D2 and D4 exactly: one function, one test, exact `"pong"` literal.
- D8 edge cases are covered by direct failure behavior: signature drift, return drift, and scope drift all fail review or test.
- The code will still be obvious six months from now because there is almost nothing to interpret.
- TDD was followed for the one declared behavior.
- If any code was written before the failing test, it was deleted and rewritten under DTT discipline.
