# D2: Specification — FMWK-900-sawmill-smoke
Meta: pkg:FMWK-900-sawmill-smoke | v:1.0.0 | status:Final | author:Codex spec-agent | sources:AGENT_BOOTSTRAP.md, architecture/NORTH_STAR.md, architecture/BUILDER_SPEC.md, architecture/OPERATIONAL_SPEC.md, architecture/FWK-0-DRAFT.md, architecture/BUILD-PLAN.md, sawmill/FMWK-900-sawmill-smoke/TASK.md | constitution:D1_CONSTITUTION.md

## Purpose
Provide the smallest possible end-to-end Sawmill canary: one Python function named `ping` that returns `"pong"` and one test that proves it. This framework exists only to exercise the pipeline, not to provide product, KERNEL, or infrastructure capability.

## NOT
- FMWK-900-sawmill-smoke is NOT a product framework. It does not implement DoPeJar or DoPeJarMo behavior.
- FMWK-900-sawmill-smoke is NOT a KERNEL framework. It does not implement or depend on the nine primitives.
- FMWK-900-sawmill-smoke is NOT an integration harness. It does not call services, Docker, immudb, or `platform_sdk`.
- FMWK-900-sawmill-smoke is NOT an extensible scaffold. It does not add schemas, adapters, error classes, or extra modules.

## Scenarios
### Primary
SC-001
- Priority: P1
- Source: `TASK.md` Build Target
- GIVEN a Python caller invokes `ping()` with no arguments WHEN the function executes THEN it returns the exact string `"pong"`
- Testing Approach: direct function-level assertion

SC-002
- Priority: P1
- Source: `TASK.md` Build Target
- GIVEN the test runner imports `ping` from `smoke` WHEN `test_ping()` runs THEN the assertion passes
- Testing Approach: local unit test execution

SC-003
- Priority: P1
- Source: `TASK.md` Owns, Dependencies, Constraints
- GIVEN the framework is prepared for build/review WHEN its contents are inspected THEN only `smoke.py` and `test_smoke.py` are in scope and no dependencies are declared
- Testing Approach: staged file and import inspection

### Edge Cases
SC-004
- Priority: P1
- Source: `TASK.md` Constraints
- GIVEN `ping()` returns any value other than the exact lowercase literal `"pong"` WHEN `test_ping()` runs THEN the framework fails validation
- Testing Approach: negative mutation of the return literal

SC-005
- Priority: P1
- Source: `TASK.md` Constraints
- GIVEN additional files, services, or framework patterns are introduced WHEN the framework is reviewed THEN the build is treated as out of scope and rejected
- Testing Approach: scope review against D1 NEVER and D6 clarifications

## Deferred Capabilities
DEF-001
- What: Additional smoke-test behaviors or helper modules
- Why Deferred: The task defines one function and one test as the entire scope
- Trigger to add: A future task explicitly expands the canary specification
- Impact if never added: None; this framework remains a valid minimal pipeline canary

## Success Criteria
- [ ] `smoke.py` defines `ping() -> str`
- [ ] `ping()` returns exactly `"pong"`
- [ ] `test_smoke.py` imports `ping` and asserts `"pong"`
- [ ] No extra files or dependencies are introduced
- [ ] No product, KERNEL, or service behavior appears in the framework

## Clarifications
See D6 CLR-001, CLR-002, CLR-003
