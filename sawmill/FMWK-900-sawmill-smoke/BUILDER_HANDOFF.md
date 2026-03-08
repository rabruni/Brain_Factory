# Builder Handoff — H-1
Handoff ID: H-1 | Framework: FMWK-900-sawmill-smoke | Prompt Contract Version: 1.0.0
Agent: H-1 — Build the two-file Sawmill smoke canary

## 1. Mission

You are building FMWK-900-sawmill-smoke, the smallest valid Sawmill canary. Its only purpose is to prove that the approved spec can move through the builder path without drift. Deliver exactly two owned files in `staging/FMWK-900-sawmill-smoke/`: `smoke.py`, defining `ping() -> str` and returning the literal `"pong"`, and `test_smoke.py`, importing `ping` and asserting `ping() == "pong"`. Nothing else is in scope.

## 2. Critical Constraints

1. **Staging only.** Do all implementation work in `staging/FMWK-900-sawmill-smoke/`. Do not write framework code anywhere else.
2. **DTT/TDD is mandatory.** Write the failing pytest first, then implement `smoke.py`, then rerun pytest. If you wrote implementation before the test, delete it and redo the sequence. Reference: `Templates/TDD_AND_DEBUGGING.md`.
3. **Package everything, but only the approved package.** For this canary, "package everything" means the deliverable is exactly the two owned files plus the results record. Do not add helper modules, fixtures, configs, or scaffolding.
4. **E2E verify the actual canary.** The required end-to-end proof is `python3 -m pytest test_smoke.py -v --tb=short` from the staging directory, with pasted output in `RESULTS.md`.
5. **No hardcoding beyond the approved literal contract.** The only allowed hardcoded behavior is the approved function name `ping`, file names, and return literal `"pong"`. Do not introduce hidden constants, fallback values, or expansion hooks.
6. **No file replacement.** Create or edit only the owned target files and the required `RESULTS.md`. Do not replace unrelated files or expand the package surface.
7. **Deterministic archives only if you create one for local verification.** No archive is required by approved scope. If you create one anyway, use deterministic Python stdlib tooling, never shell tar.
8. **Results file is mandatory.** Write `sawmill/FMWK-900-sawmill-smoke/RESULTS.md` with status, SHA-256 hashes, commands, and pasted outputs per `BUILDER_HANDOFF_STANDARD.md`.
9. **Full regression means the full approved package regression.** For this handoff there is one owned pytest only. Treat that command as the full regression for the framework and record it explicitly.
10. **Baseline snapshot is mandatory.** Record the starting contents of `staging/FMWK-900-sawmill-smoke/` and the pre-build test surface before implementation.
11. **No dependency drift.** Do not add `platform_sdk`, Docker, immudb, networking, custom exceptions, schemas, adapters, or data models.
12. **Keep the test count exactly at one owned pytest.** The generic handoff standard's minimum-count heuristic does not apply here because D1 Article 2, D2 SC-003, and `TASK.md` lock this framework to one test. Adding more tests is a spec violation.

## 3. Architecture / Design

### Component Map

```text
staging/FMWK-900-sawmill-smoke/
├── smoke.py
│   └── ping() -> str
│       returns "pong"
└── test_smoke.py
    └── test_ping()
        imports ping from smoke
        asserts ping() == "pong"
```

### Runtime Flow

```text
python3 -m pytest test_smoke.py
        |
        v
pytest collects test_ping
        |
        v
test_smoke.py imports ping from smoke
        |
        v
ping() executes with no args
        |
        v
returns "pong"
        |
        v
assertion passes -> exit 0
or
import/assertion fails -> non-zero exit
```

### Interface Boundary

```python
# staging/FMWK-900-sawmill-smoke/smoke.py
def ping() -> str:
    return "pong"

# staging/FMWK-900-sawmill-smoke/test_smoke.py
from smoke import ping

def test_ping() -> None:
    assert ping() == "pong"
```

The only inbound call is `ping()` with no arguments. The only valid outbound value is the exact string `"pong"`. The only approved failure modes are native import failure or pytest assertion failure.

## 4. Implementation Steps

1. **Record baseline state** for `staging/FMWK-900-sawmill-smoke/` and note it for `RESULTS.md`.
   Why: the results file requires a before/after snapshot and this framework must remain visibly minimal.
2. **Create `staging/FMWK-900-sawmill-smoke/test_smoke.py` first** with:
   - `from smoke import ping`
   - `def test_ping() -> None:`
   - `assert ping() == "pong"`
   Why: DTT is mandatory; the canary test must exist before the implementation.
3. **Run `python3 -m pytest test_smoke.py -v --tb=short` immediately after creating the test** and confirm it fails before `smoke.py` exists.
   Why: this proves the import boundary is real and fail-fast, not mocked or assumed.
4. **Create `staging/FMWK-900-sawmill-smoke/smoke.py`** with the exact public signature `def ping() -> str:` and the exact return statement `return "pong"`.
   Why: D1 Article 5 requires a literal deterministic contract, not a flexible implementation.
5. **Rerun `python3 -m pytest test_smoke.py -v --tb=short`** and confirm the final output is `1 passed`.
   Why: the one owned pytest is the entire package proof for SC-001 through SC-005.
6. **Audit the staging directory** and confirm the only human-authored framework files are `smoke.py` and `test_smoke.py`.
   Why: D1 Articles 2, 3, and 6 prohibit expansion beyond the approved two-file surface.
7. **Write `sawmill/FMWK-900-sawmill-smoke/RESULTS.md`** with SHA-256 hashes, pasted command output, baseline snapshot, and the full package regression entry.
   Why: reviewer validation depends on exact evidence from this session, not summaries.

## 5. Package Plan

| Item | Value |
|------|-------|
| Package ID | FMWK-900-sawmill-smoke |
| Layer | SYSTEM-TEST |
| Staging Path | `staging/FMWK-900-sawmill-smoke/` |
| Runtime Dependencies | None |
| Test Dependency | `pytest` only |

**Assets**

| File | Purpose |
|------|---------|
| `smoke.py` | Single owned implementation file exposing `ping() -> str` |
| `test_smoke.py` | Single owned pytest proving importability and literal return |
| `RESULTS.md` | Builder evidence file required by the handoff standard |

**Manifest**

Record SHA-256 for every created file in `sawmill/FMWK-900-sawmill-smoke/RESULTS.md` using `sha256:<64hex>`.

## 6. Test Plan

Approved exception: the generic small-package minimum-count heuristic is overridden here by the approved framework constitution. This canary must contain exactly one owned pytest.

| Test Name | Description | Expected Behavior |
|-----------|-------------|------------------|
| `test_ping` | Imports `ping` from `smoke` and asserts the exact literal `ping() == "pong"` | Passes only when `ping` exists, takes no arguments, and returns `"pong"`; fails fast on import error or wrong return |

## 7. Existing Code to Reference

| What | Where | Why |
|------|-------|-----|
| Approved canary snippet | `sawmill/FMWK-900-sawmill-smoke/TASK.md` | This is the exact source of truth for the function and test bodies |
| Scope boundaries | `sawmill/FMWK-900-sawmill-smoke/D1_CONSTITUTION.md` | Prevents extra files, dependencies, or framework patterns |
| Scenario trace | `sawmill/FMWK-900-sawmill-smoke/D2_SPECIFICATION.md` | Shows which behaviors must be satisfied and nothing more |
| Contract trace | `sawmill/FMWK-900-sawmill-smoke/D4_CONTRACTS.md` | Confirms the only approved error behavior is native import/assertion failure |

## 8. E2E Verification

Run these commands exactly from `staging/FMWK-900-sawmill-smoke/` after implementation:

```bash
# Manual function proof
python3 -c "from smoke import ping; print(ping())"
# Expected output:
# pong

# Full package regression for this handoff
python3 -m pytest test_smoke.py -v --tb=short
# Expected output includes:
# test_smoke.py::test_ping PASSED
# ============================== 1 passed in <time> ===============================
```

If pytest does not end with `1 passed`, the handoff is not complete.

## 9. Files Summary

| File | Location | Action |
|------|----------|--------|
| `smoke.py` | `staging/FMWK-900-sawmill-smoke/smoke.py` | CREATE |
| `test_smoke.py` | `staging/FMWK-900-sawmill-smoke/test_smoke.py` | CREATE |
| `RESULTS.md` | `sawmill/FMWK-900-sawmill-smoke/RESULTS.md` | CREATE |

## 10. Design Principles

1. Keep the package at the exact two-file scope approved in D1/D2.
2. Prefer the simplest valid Python that satisfies the literal contract.
3. Let pytest and Python raise native failures; do not wrap them.
4. Treat any extra dependency or file as scope drift.
5. Validate with one exact assertion, not generalized test infrastructure.

## 11. Verification Discipline

Every claim of success must include evidence from this session. `RESULTS.md` must contain the exact pytest command, the pasted output, and SHA-256 hashes for all created files. Do not write "should pass," "expected to pass," or similar language without command output. Reference: `Templates/TDD_AND_DEBUGGING.md`.

## 12. Mid-Build Checkpoint

After the single owned pytest passes:
1. Report the command run and paste the exact output showing `1 passed`.
2. Report the files created so far.
3. Report any spec deviations, even if corrected.
4. WAIT for human greenlight before writing the final `RESULTS.md`.

There are no integration tests in scope. The checkpoint happens after the owned pytest passes and before handoff completion.

## 13. Self-Reflection

Before reporting any step complete, confirm all of the following:
1. The code matches D2 and D4 exactly, with no extra behavior.
2. SC-004 and SC-005 are covered by the same owned pytest through fail-fast import/assertion behavior.
3. The package is still understandable in six months because there are only two obvious files and one literal contract.
4. TDD was followed in order; if code was written before the test, it was deleted and redone before claiming completion.
