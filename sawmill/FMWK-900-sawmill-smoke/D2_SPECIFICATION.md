# D2: Specification — sawmill-smoke
Meta: pkg:FMWK-900 | v:1.0.0 | status:Final | author:Codex spec-agent | sources:AGENT_BOOTSTRAP.md, architecture/NORTH_STAR.md, architecture/BUILDER_SPEC.md, architecture/OPERATIONAL_SPEC.md, architecture/FWK-0-DRAFT.md, architecture/BUILD-PLAN.md, sawmill/FMWK-900-sawmill-smoke/TASK.md | constitution:D1_CONSTITUTION.md

## Purpose
FMWK-900 is a minimal Sawmill system-test canary. Its only job is to prove that the pipeline can carry a trivial framework from specification to build output by defining one Python function, `ping()`, that returns `"pong"`, and one test that asserts that behavior.

## NOT (3+ items)
- `sawmill-smoke` is NOT a product framework. It does not implement DoPeJar or DoPeJarMo behavior.
- `sawmill-smoke` is NOT a KERNEL framework. It does not use the nine primitives as scope.
- `sawmill-smoke` is NOT an integration test. It does not require Docker, immudb, platform SDK, or external services.
- `sawmill-smoke` is NOT a modeling exercise. It does not define schemas, adapters, or custom errors.

## Scenarios
### Primary (3-7, SC-### IDs, e.g. SC-001)
- SC-001
  - Priority: P0(blocker)
  - Source: sawmill/FMWK-900-sawmill-smoke/TASK.md
  - GIVEN the module `smoke.py` is imported WHEN `ping()` is called THEN it returns the literal string `"pong"`.
  - Testing Approach: Unit test direct function call.
- SC-002
  - Priority: P0(blocker)
  - Source: sawmill/FMWK-900-sawmill-smoke/TASK.md
  - GIVEN the test file imports `ping` from `smoke` WHEN `test_ping` runs THEN the assertion `ping() == "pong"` passes.
  - Testing Approach: Execute the single test under Python test runner.

### Edge Cases (2-4, same SC-### format)
- SC-003
  - Priority: P1(must)
  - Source: sawmill/FMWK-900-sawmill-smoke/TASK.md
  - GIVEN no external services are configured WHEN the module and test run THEN they still succeed because the framework has no dependencies.
  - Testing Approach: Run in a clean local Python environment without service setup.
- SC-004
  - Priority: P1(must)
  - Source: sawmill/FMWK-900-sawmill-smoke/TASK.md
  - GIVEN the canary is reviewed for scope WHEN files and behavior are inspected THEN nothing exists beyond `smoke.py`, `test_smoke.py`, and the specified ping behavior.
  - Testing Approach: File inventory review against task ownership and constraints.

## Deferred Capabilities (DEF-### IDs)
- DEF-001
  - What: Additional functions or richer smoke behavior.
  - Why Deferred: `TASK.md` states the current scope is the entire scope.
  - Trigger to add: Explicit human change to the assignment.
  - Impact if never added: None; the canary still fulfills its purpose.
- DEF-002
  - What: Integration with package lifecycle, services, or SDKs.
  - Why Deferred: `TASK.md` explicitly forbids such dependencies.
  - Trigger to add: Explicit human request for a non-trivial system test.
  - Impact if never added: The canary remains intentionally isolated.

## Success Criteria
- [ ] `smoke.py` defines `ping() -> str`.
- [ ] `ping()` returns `"pong"`.
- [ ] `test_smoke.py` imports `ping` from `smoke`.
- [ ] `test_ping` asserts `ping() == "pong"`.
- [ ] No extra files, dependencies, schemas, or adapters are required by the spec.

## Clarifications
See D6 CLR-001, CLR-002
