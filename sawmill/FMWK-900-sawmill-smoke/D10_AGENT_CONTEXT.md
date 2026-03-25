# D10: Agent Context — Sawmill Smoke Canary (FMWK-900)
Meta: pkg:FMWK-900-sawmill-smoke | updated:2026-03-21

## What This Project Does
This framework is a Sawmill pipeline canary. It does not build product behavior, KERNEL behavior, or integration plumbing. The entire deliverable is one Python function, `ping()`, in `smoke.py`, returning the exact string `"pong"`, plus one test in `test_smoke.py` proving that contract. The framework exists so Turn D and Turn E can verify the build pipeline with the smallest possible real artifact.

## Architecture Overview
```text
pytest / Python caller
        |
        v
   smoke.py
   ping() -> "pong"
        |
        v
 test_smoke.py
 test_ping()
```

Directory structure:
```text
staging/FMWK-900-sawmill-smoke/
├── smoke.py        single runtime function
└── test_smoke.py   single validation test
```

## Key Patterns (4-6)
- Minimal owned surface: only `smoke.py` and `test_smoke.py` may exist for this framework. Reference: D1 Articles 1-3.
- Exact literal contract: `ping()` takes no arguments and returns exactly `"pong"`. Reference: D2 SC-001, D4 IN-001/OUT-001.
- Fail-fast drift detection: signature drift, import drift, return drift, and scope drift are all treated as immediate failures. Reference: D1 Article 7, D4 ERR-001/ERR-003.
- Zero dependency isolation: do not add `platform_sdk`, Docker, services, schemas, adapters, or primitives. Reference: D1 Article 5, D2 NOT.
- Single deterministic proof: the sole validation path is one direct unit test. Reference: D1 Article 6.

## Commands
```bash
# Build is just file creation in staging
cd staging/FMWK-900-sawmill-smoke

# Run the framework test
cd staging/FMWK-900-sawmill-smoke && pytest -q test_smoke.py

# Run the same test with verbose output for RESULTS.md
cd staging/FMWK-900-sawmill-smoke && pytest test_smoke.py -v

# Full regression for this framework
cd staging/FMWK-900-sawmill-smoke && pytest -q
```

## Tool Rules
| USE THIS | NOT THIS | WHY |
|----------|----------|-----|
| Plain Python function in `smoke.py` | Classes, wrappers, adapters | D1 tooling constraint requires the smallest direct implementation |
| Direct unit test in `test_smoke.py` | Integration harnesses, mocks, service fixtures | D1 tooling constraint limits validation to one deterministic local test |
| Local `pytest` execution as proof | Manual inspection as proof | D1 validation rule requires an executed test result |
| Document ambiguity in artifacts | Invent extra scope | D1 Article 4 and D2 scope limits forbid guesses |

## Coding Conventions
- Python 3.11+
- Stdlib-only implementation in the source file
- Full function signature: `def ping() -> str`
- No dataclasses, schemas, error classes, or custom exit codes
- Test framework: `pytest`
- Error handling is externalized to the test runner; the framework itself has no custom error surface

## Submission Protocol
1. Read `BUILDER_HANDOFF.md` in this framework directory.
2. Create `13Q_ANSWERS.md` with first line exactly `Builder Prompt Contract Version: 1.0.0`.
3. Stop and wait for reviewer PASS before implementation.
4. After PASS, follow D8 in order using DTT: define failing test expectation, implement the minimum code, rerun until green.
5. Run the full framework regression with pasted output.
6. Write `sawmill/FMWK-900-sawmill-smoke/RESULTS.md` with commands, output, file hashes, and scope confirmation.

Branch naming: `feature/fmwk-900-sawmill-smoke`
Commit format: `feat(fmwk-900): add smoke canary`
Results file path: `sawmill/FMWK-900-sawmill-smoke/RESULTS.md`

## Active Components
| Component | Where | Interface (signature) |
|-----------|-------|-----------------------|
| `ping` | `smoke.py` | `ping() -> str` |
| `test_ping` | `test_smoke.py` | `test_ping() -> None` |

## Links to Deeper Docs
- D1: Constitution, boundaries, tooling constraints, and decomposition tests
- D2: The exact in-scope scenarios and what the framework is not
- D3: Documentation-only request/response entities for the smoke surface
- D4: Inbound, outbound, side-effect, and error contracts for `ping()`
- D5: Research log confirming no extra research is needed
- D6: Gap analysis showing zero open items and resolved clarifications
- D7: Build plan tying the architecture to D1
- D8: Ordered task list with D2 and D4 traceability
- D9: Held back from builders; used only for evaluation after implementation
