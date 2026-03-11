# D2: Specification - sawmill-smoke
Meta: pkg:FMWK-900 | v:0.1.0 | status:Final | author:Codex Spec Agent | sources:AGENT_BOOTSTRAP.md; architecture/NORTH_STAR.md; architecture/BUILDER_SPEC.md; architecture/OPERATIONAL_SPEC.md; architecture/FWK-0-DRAFT.md; architecture/BUILD-PLAN.md; sawmill/FMWK-900-sawmill-smoke/TASK.md | constitution:D1_CONSTITUTION.md

## Purpose
FMWK-900 is a system-test canary for the sawmill pipeline. Its only job is to prove that a minimal Python framework can be specified, built, and verified end to end by returning `"pong"` from `ping()` and asserting that result in one test.

## NOT
- FMWK-900 is NOT a product framework. It does not implement DoPeJar or DoPeJarMo behavior.
- FMWK-900 is NOT a KERNEL or primitive framework. It does not reference the nine primitives.
- FMWK-900 is NOT an integration framework. It does not use services, Docker, or external APIs.
- FMWK-900 is NOT a schema or data-model framework. It does not define persistent entities.

## Scenarios
### Primary
SC-001
- Priority: P0
- Source: `sawmill/FMWK-900-sawmill-smoke/TASK.md` Build Target
- GIVEN the module `smoke.py` is imported WHEN `ping()` is called THEN it returns the exact string `"pong"`
- Testing Approach: Direct function call assertion

SC-002
- Priority: P1
- Source: `sawmill/FMWK-900-sawmill-smoke/TASK.md` Build Target
- GIVEN `test_smoke.py` imports `ping` WHEN the test suite runs THEN `test_ping` passes
- Testing Approach: Unit test execution

SC-003
- Priority: P1
- Source: `sawmill/FMWK-900-sawmill-smoke/TASK.md` Owns; Constraints
- GIVEN the framework is assembled WHEN ownership is reviewed THEN only `smoke.py` and `test_smoke.py` are in scope AND no dependency is added
- Testing Approach: File inventory and import review

### Edge Cases
SC-101
- Priority: P1
- Source: `sawmill/FMWK-900-sawmill-smoke/TASK.md` Build Target
- GIVEN `ping()` returns any value other than the exact string `"pong"` WHEN `test_ping` runs THEN the package fails verification
- Testing Approach: Negative assertion review

SC-102
- Priority: P1
- Source: `sawmill/FMWK-900-sawmill-smoke/TASK.md` Build Target
- GIVEN `smoke.py` or `ping` is renamed or mis-imported WHEN `test_smoke.py` runs THEN import or execution fails immediately
- Testing Approach: Import-path verification

SC-103
- Priority: P2
- Source: `sawmill/FMWK-900-sawmill-smoke/TASK.md` Constraints
- GIVEN an extra file, dependency, or framework concern is proposed WHEN scope is reviewed THEN the change is rejected as out of scope
- Testing Approach: Spec-to-task diff review

## Deferred Capabilities
DEF-001
- What: Additional smoke behaviors beyond `ping()`
- Why Deferred: `TASK.md` defines one function and one test as the entire scope
- Trigger to add: A new task explicitly expands the canary
- Impact if never added: None; current canary remains valid

DEF-002
- What: Integration or service-level smoke coverage
- Why Deferred: Dependencies and external services are explicitly forbidden
- Trigger to add: A separate framework is created for integration smoke tests
- Impact if never added: This framework remains unit-only by design

## Success Criteria
- [ ] `smoke.py` defines `ping()` with zero arguments
- [ ] `ping()` returns the exact string `"pong"`
- [ ] `test_smoke.py` imports `ping` and asserts `"pong"`
- [ ] The framework owns only `smoke.py` and `test_smoke.py`
- [ ] No dependency, service, schema, or data model is introduced

## Clarifications
See D6 CLR-001, CLR-002, CLR-003.
