# H-001_BUILDER_HANDOFF

## 1. Mission
Build the `FMWK-900-sawmill-smoke` canary exactly as specified in D1-D8: one Python module exposing `ping() -> str`, one unit test proving it returns `"pong"`, and the required build evidence. This exists only to exercise the Sawmill pipeline end to end with the smallest possible deterministic package.

## 2. Critical Constraints
1. Work staging-only and keep implementation limited to the framework-owned canary files plus required evidence artifacts.
2. Use DTT for every behavior: write the failing test first, then the minimum implementation needed to pass.
3. Package everything required for this framework and nothing beyond it.
4. Perform end-to-end verification with the exact test command used for this canary.
5. Do not hardcode anything beyond the literal task requirement that `ping()` returns `"pong"`.
6. Do not replace or rewrite unrelated files; create or edit only the files required by this handoff.
7. Keep archives and any recorded hashes deterministic if packaging artifacts are produced.
8. Write `sawmill/FMWK-900-sawmill-smoke/RESULTS.md` with hashes and pasted command output from this session.
9. Run the required full regression of all packages/framework tests after the package-specific test.
10. Record a baseline snapshot before claiming completion.
11. Follow TDD discipline from `Templates/TDD_AND_DEBUGGING.md`; if code was written before tests, delete it and redo the behavior cycle.
12. Do not add schemas, adapters, custom exceptions, KERNEL patterns, external dependencies, or service integration.
13. Do not reference `platform_sdk`, Docker services, immudb, or the nine primitives in the canary code.

## 3. Architecture/Design
```text
test_smoke.py
  imports ping from smoke.py
  calls ping()
  asserts result == "pong"
```

Boundaries:
- Source boundary: `smoke.py` owns the only runtime behavior.
- Validation boundary: `test_smoke.py` owns the only verification behavior.
- Failure boundary: import and assertion failures surface directly through the Python test runner.
- Scope boundary: no external imports, no extra owned files, no supporting architecture.

Interfaces:
- `smoke.py`: `def ping() -> str`
- `test_smoke.py`: `def test_ping() -> None`

## 4. Implementation Steps
1. Create the single failing test in `test_smoke.py` with `from smoke import ping` and `def test_ping() -> None: assert ping() == "pong"`.
Why: This enforces DTT and locks the implementation to the exact observable behavior from D2 SC-002 and D4 OUT-001.
2. Run the test to capture the initial failure caused by the missing module or function.
Why: This proves the behavior was test-driven and establishes baseline failure evidence for RESULTS.md.
3. Create `smoke.py` with exactly `def ping() -> str` returning the literal `"pong"`.
Why: This satisfies the complete canary scope from D2 SC-001 without introducing hidden capability.
4. Re-run the single test until it passes with no additional imports or side effects.
Why: This verifies D4 IN-001, OUT-001, SIDE-001, ERR-001, and ERR-002 in the smallest possible loop.
5. Inspect the final framework output to confirm only the owned code files are present and no forbidden dependencies or architecture were added.
Why: This enforces D2 SC-003, SC-004 and D4 ERR-003 before handoff.
6. Write `RESULTS.md` with hashes, package test output, full regression output, baseline snapshot, and any issues encountered.
Why: Reviewer validation requires evidence, not summaries.

## 5. Package Plan
| Package ID | Layer | Assets | Dependencies | Manifest |
| --- | --- | --- | --- | --- |
| FMWK-900-sawmill-smoke | SYSTEM-TEST | `smoke.py`, `test_smoke.py`, `RESULTS.md` | none | use framework/task metadata already established; do not invent extra package assets |

## 6. Test Plan
Authority note: the generic handoff standard's small-package test-count minimum is superseded here by the approved framework scope in D1 article 7, D2 SC-002, and `TASK.md`, which define exactly one test for this canary. Adding more tests would violate source-of-truth scope.

Because this is a two-file canary, the functional minimum from D2/D4 is one test method:

| Test Name | Description | Expected Behavior |
| --- | --- | --- |
| `test_ping` | Import `ping` and call it with no arguments | Test passes only when `ping()` returns `"pong"` |

Additional mandatory checks for this handoff:
- file inspection check: confirm only `smoke.py` and `test_smoke.py` are the owned canary code files.
- dependency inspection check: confirm there are no external imports or service references.
- regression step: run the repository/framework regression command required by the active build environment and paste the output.

## 7. Existing Code to Reference
| What | Where | Why |
| --- | --- | --- |
| Approved scope and success criteria | `sawmill/FMWK-900-sawmill-smoke/D2_SPECIFICATION.md` | Defines the exact behaviors and out-of-scope boundaries. |
| Contract definitions | `sawmill/FMWK-900-sawmill-smoke/D4_CONTRACTS.md` | Defines the allowed interfaces, outputs, side effects, and failure modes. |
| Build order and acceptance detail | `sawmill/FMWK-900-sawmill-smoke/D8_TASKS.md` | Provides the implementation sequence and traceability. |
| Builder process constraints | `Templates/compressed/BUILDER_PROMPT_CONTRACT.md` | Defines the 13Q gate and STOP requirement before implementation. |

## 8. E2E Verification
Use exact copy-pasteable commands and record their output in `RESULTS.md`:

```bash
python -m pytest test_smoke.py
python -m pytest
```

Expected result:
- `test_smoke.py` reports one passing test for the package-specific run.
- The full regression step completes without introducing new failures.

## 9. Files Summary
| File | Location | Action (CREATE/MODIFY) |
| --- | --- | --- |
| `smoke.py` | framework staging output for this canary | CREATE |
| `test_smoke.py` | framework staging output for this canary | CREATE |
| `RESULTS.md` | `sawmill/FMWK-900-sawmill-smoke/RESULTS.md` | CREATE |

## 10. Design Principles
1. Keep the canary minimal: one behavior, one test, nothing else.
2. Preserve determinism: `ping()` must always return the exact literal `"pong"`.
3. Prefer directness over architecture: no abstractions, adapters, or helper layers.
4. Fail fast with default Python/test behavior rather than custom error machinery.
5. Keep the framework isolated from product code, services, and platform dependencies.

## 11. Verification Discipline
Every claim that a test passed must include pasted command output from this session in `RESULTS.md`. Include the exact command used, the visible passing/failing summary, file hashes, and the regression evidence. Do not write “should pass,” “probably works,” or equivalent unsupported language. Follow `Templates/TDD_AND_DEBUGGING.md`.

## 12. Mid-Build Checkpoint
After the package unit test passes and before final reporting, record in `RESULTS.md`:
- the passing test command and pasted output
- files created so far
- whether any spec deviation occurred
- the current scope check result confirming no extra code files or dependencies were added

Continue unless the orchestrator escalates.

## 13. Self-Reflection
Before marking any step complete, confirm:
- the code matches D2 and D4 exactly
- D8 edge cases on dependency-free scope and extra-file prohibition are covered
- the implementation is still obvious six months from now
- DTT was followed for the behavior
- any code written before the test was deleted and rewritten through the required cycle
