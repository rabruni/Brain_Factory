# D10: Agent Context — sawmill smoke canary
Meta: pkg:FMWK-900-sawmill-smoke | updated:2026-03-17

## What This Project Does
This framework is a Sawmill smoke canary. The builder must stage one Python source file that defines `ping() -> str`, one test file that imports that function, and verify the test passes when `ping()` returns the literal `"pong"`. Nothing else belongs in scope.

## Architecture Overview
```text
test_smoke.py -> imports ping -> smoke.py -> returns "pong"
```

```text
smoke.py          source canary module
test_smoke.py     single unit test for ping()
RESULTS.md        builder evidence written after implementation
```

## Key Patterns (4-6)
- Minimal canary only: keep the framework to one function and one test, per D1 MERGING and D2 Purpose.
- Task-as-authority: treat `TASK.md` and D2 as the entire build scope, per D1 SOURCE OF TRUTH.
- Dependency-free execution: no `platform_sdk`, services, or external setup, per D1 ISOLATION and D5 RQ-001.
- Fail-fast validation: use normal import/assertion failures instead of custom error layers, per D1 FAILURE HANDLING and D4 ERR-001/ERR-002.
- Deterministic output: `ping()` must always return the literal `"pong"`, per D1 DETERMINISM and D4 OUT-001.

## Commands
```bash
pytest test_smoke.py
python -m pytest test_smoke.py
python -m pytest
```

## Tool Rules
| USE THIS | NOT THIS | WHY |
| --- | --- | --- |
| plain Python module | framework scaffolding | D1 tooling constraint: Implementation must stay as a plain Python module. |
| single Python unit test | integration harness | D1 tooling constraint: Testing must stay as a single Python unit test. |
| none | platform_sdk or external packages | D1 tooling constraint: Dependencies must remain none. |
| direct import and assertion | service bootstrapping | D1 tooling constraint: Verification must be direct import and assertion only. |

## Coding Conventions
Use Python 3.x with standard library only. Keep type hints limited to the required `-> str` signature. Do not introduce dataclasses, custom error handling, exit-code plumbing, or helper layers. Use a pytest-style test function for the single assertion.

## Submission Protocol
1. Read the handoff and answer the 13Q gate with `Builder Prompt Contract Version: 1.0.0` in `13Q_ANSWERS.md`, then STOP for reviewer PASS.
2. Build via DTT per behavior: create the failing test, implement the minimum code to pass, and avoid code written before tests.
3. Write `RESULTS.md` with file hashes and pasted verification output from this session.
4. Run the framework test command and then the required full regression step before closing the handoff.

Branch naming and commit format: follow orchestrator or repository defaults if a commit is requested; no special branch contract is defined in D1-D6.
Results file path: `sawmill/FMWK-900-sawmill-smoke/RESULTS.md`.

## Active Components
| Component | Where | Interface (signature) |
| --- | --- | --- |
| source module | `smoke.py` | `def ping() -> str` |
| unit test | `test_smoke.py` | `def test_ping() -> None` |

## Links to Deeper Docs
- D1_CONSTITUTION.md: non-negotiable boundaries, ownership, and tooling constraints.
- D2_SPECIFICATION.md: purpose, scenarios, success criteria, and explicit out-of-scope items.
- D3_DATA_MODEL.md: artifact-level description of the two owned files.
- D4_CONTRACTS.md: inbound, outbound, side-effect, and error behavior for the canary.
- D5_RESEARCH.md: confirms no research is needed and scope must stay minimal.
- D6_GAP_ANALYSIS.md: resolved boundary review with zero open items.
- D7_PLAN.md: architecture, testing approach, and constitution compliance for the build.
- D8_TASKS.md: ordered implementation tasks with scenario and contract traceability.
- D9: kept separate from builders during active build.
