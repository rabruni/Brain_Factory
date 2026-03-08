# D10: Agent Context — FMWK-900-sawmill-smoke
Meta: pkg:FMWK-900-sawmill-smoke | updated:2026-03-07

## What This Project Does

You are building the smallest valid Sawmill canary. Its entire purpose is to prove that the pipeline can carry an approved framework spec into a tiny Python implementation and a passing pytest without dragging in product logic, KERNEL patterns, or external dependencies. The finished package is exactly two owned files in `staging/FMWK-900-sawmill-smoke/`: `smoke.py`, which defines `ping() -> str` and returns `"pong"`, and `test_smoke.py`, which imports `ping` and asserts the exact literal return.

## Architecture Overview

```text
python3 -m pytest test_smoke.py
        |
        v
test_smoke.py -> from smoke import ping
        |
        v
ping() -> "pong"
        |
        v
assert ping() == "pong"
        |
        v
pass: exit 0
fail: import error or assertion failure
```

```text
staging/FMWK-900-sawmill-smoke/
├── smoke.py        # single zero-argument function, no imports required
└── test_smoke.py   # single pytest proving importability and literal return
```

## Key Patterns

**1. Task-Locked Scope** — D1 Article 2, D1 Article 4, D5 RQ-001  
Build exactly one function and one test; any third file or extra behavior is scope drift.

**2. Literal Determinism** — D1 Article 5  
`ping()` takes no arguments and always returns the exact string `"pong"`.

**3. Test-First Local Proof** — D1 Dev Workflow Constraint 2, D1 Dev Workflow Constraint 4  
Write the owned pytest first, then implement the function, then prove the package by running that exact pytest.

**4. Isolation From Framework Plumbing** — D1 Article 6, D5 RQ-001  
Do not introduce `platform_sdk`, Docker, immudb, networking, schemas, adapters, or custom error types.

**5. Fail-Fast Native Errors** — D1 ALWAYS, D1 Article 5  
Import errors and assertion failures are the intended failure mode; do not wrap or soften them.

## Commands

```bash
# Work in the staging directory
cd staging/FMWK-900-sawmill-smoke

# Syntax/import sanity
python3 -m py_compile smoke.py test_smoke.py

# Manual run
python3 -c "from smoke import ping; print(ping())"

# Run the single owned test
python3 -m pytest test_smoke.py::test_ping -v --tb=short

# Full package regression (same as the owned test for this canary)
python3 -m pytest test_smoke.py -v --tb=short
```

## Tool Rules

| USE THIS | NOT THIS | WHY |
|----------|----------|-----|
| Plain Python function | Framework scaffolding, adapters, service clients | D1 limits the module to one deterministic callable |
| `pytest` on `test_smoke.py` | Integration harnesses, networked tests | Validation is local-only and fail-fast |
| Python stdlib + pytest | `platform_sdk`, Docker, immudb, external APIs | External dependencies are out of scope |
| Exact literal assertion `ping() == "pong"` | Heuristics, snapshots, mocks of unrelated systems | The canary is binary and literal by constitution |

## Coding Conventions

| Convention | Rule |
|------------|------|
| Python version | Keep syntax equivalent to the approved `TASK.md` snippet; no version-specific features beyond that |
| Stdlib policy | `smoke.py` needs no imports; `test_smoke.py` uses `pytest` only |
| Type hints | Keep the public signature as `def ping() -> str` |
| Dataclasses | None in scope |
| Error handling | Use native import/assertion failures only; do not add custom exceptions |
| Exit codes | `pytest` exit code is the package verdict: `0` pass, non-zero fail |
| Test framework | `pytest` only |

## Submission Protocol

1. Answer all 13 questions from the dispatched builder prompt and STOP.
2. Wait for human greenlight before creating files.
3. Record a baseline snapshot of `staging/FMWK-900-sawmill-smoke/` before writing code.
4. Write `test_smoke.py` first so the canary exists before the implementation.
5. Implement `smoke.py` with `ping() -> str` returning the exact literal `"pong"`.
6. Run `python3 -m pytest test_smoke.py -v --tb=short` and keep the exact output for the results file.
7. Write `sawmill/FMWK-900-sawmill-smoke/RESULTS.md` with SHA-256 hashes for created files and the pasted command output.
8. The full regression for this handoff is the single owned pytest canary; record it as the full package regression.
9. Branch naming: `feature/FMWK-900-sawmill-smoke`
10. Commit format: `test(FMWK-900): add sawmill smoke canary`
11. Results file path: `sawmill/FMWK-900-sawmill-smoke/RESULTS.md`

## Active Components

| Component | Where | Interface (signature) |
|-----------|-------|----------------------|
| `ping` | `smoke.py` | `ping() -> str` |
| `test_ping` | `test_smoke.py` | `test_ping() -> None` |

## Links to Deeper Docs

| Doc | What to Find There |
|-----|--------------------|
| `D1_CONSTITUTION.md` | Scope boundaries, ALWAYS/ASK FIRST/NEVER rules, tooling constraints |
| `D2_SPECIFICATION.md` | The five approved scenarios, success criteria, and what the canary is not |
| `D3_DATA_MODEL.md` | The two private owned artifacts and their invariants |
| `D4_CONTRACTS.md` | The inbound call, outbound result, side-effect, and error contracts |
| `D5_RESEARCH.md` | Confirmation that no expansion beyond one function and one test is justified |
| `D6_GAP_ANALYSIS.md` | Zero unresolved gaps and the approved clarifications that keep the canary tiny |
| `D7_PLAN.md` | Constitution check, architecture overview, file creation order, and test strategy |
| `D8_TASKS.md` | The three implementation tasks and their exact acceptance criteria |
| D9 (holdout scenarios) | Not available to builders during active build. Do not request it. |
