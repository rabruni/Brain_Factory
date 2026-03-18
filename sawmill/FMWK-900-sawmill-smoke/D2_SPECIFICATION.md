# D2: Specification — sawmill smoke canary
Meta: pkg:FMWK-900-sawmill-smoke | v:1.0.0 | status:Final | author:spec-agent | sources:AGENT_BOOTSTRAP.md, architecture/NORTH_STAR.md, architecture/BUILDER_SPEC.md, architecture/OPERATIONAL_SPEC.md, architecture/FWK-0-DRAFT.md, architecture/BUILD-PLAN.md, sawmill/FMWK-900-sawmill-smoke/TASK.md | constitution:D1_CONSTITUTION.md

## Purpose
This framework is a minimal system-test canary for the Sawmill pipeline. It exists only to stage one Python function that returns `"pong"` and one test that proves the function works, with no dependencies and no product behavior.

## NOT
- The canary is NOT a product framework. It does not implement DoPeJar or DoPeJarMo behavior.
- The canary is NOT a KERNEL framework. It does not use or model the nine primitives.
- The canary is NOT an integration target. It does not start services or touch external systems.
- The canary is NOT an architecture exercise. It does not define schemas, adapters, or custom errors.

## Scenarios
### Primary
- SC-001
  - Priority: P0
  - Source: sawmill/FMWK-900-sawmill-smoke/TASK.md
  - GIVEN the module `smoke.py` is imported WHEN `ping()` is called THEN it returns the literal string `"pong"`
  - Testing Approach: direct function call in unit test
- SC-002
  - Priority: P1
  - Source: sawmill/FMWK-900-sawmill-smoke/TASK.md
  - GIVEN `test_smoke.py` imports `ping` WHEN `test_ping()` runs THEN the assertion `ping() == "pong"` passes
  - Testing Approach: execute the single unit test

### Edge Cases
- SC-003
  - Priority: P1
  - Source: sawmill/FMWK-900-sawmill-smoke/TASK.md
  - GIVEN the smoke canary has no dependencies WHEN the module is loaded THEN no platform or service setup is required
  - Testing Approach: verify imports contain no external dependencies
- SC-004
  - Priority: P1
  - Source: sawmill/FMWK-900-sawmill-smoke/TASK.md
  - GIVEN the task forbids extra architecture WHEN the canary is implemented THEN no extra files, schemas, adapters, or error classes are present
  - Testing Approach: inspect staged output for only the two owned files

## Deferred Capabilities
- DEF-001: What: Any behavior beyond `ping() -> "pong"` | Why Deferred: Out of scope for the canary task | Trigger to add: A new task explicitly broadens scope | Impact if never added: None; the smoke canary remains valid

## Success Criteria
- [ ] `smoke.py` defines `ping() -> str`
- [ ] `ping()` returns `"pong"`
- [ ] `test_smoke.py` imports `ping`
- [ ] `test_ping()` asserts `ping() == "pong"`
- [ ] No external dependencies or service references exist
- [ ] No extra files or architectural artifacts are introduced

## Clarifications
See D6 CLR-001 and CLR-002.
