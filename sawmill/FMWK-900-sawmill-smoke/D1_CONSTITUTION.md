# D1: Constitution — FMWK-900-sawmill-smoke
Meta: v:1.0.0 | ratified:2026-03-21 | amended:2026-03-21 | authority:AGENT_BOOTSTRAP.md, architecture/NORTH_STAR.md, architecture/BUILDER_SPEC.md, architecture/OPERATIONAL_SPEC.md, architecture/FWK-0-DRAFT.md, architecture/BUILD-PLAN.md, sawmill/FMWK-900-sawmill-smoke/TASK.md

## Articles
1. SPLITTING
- Rule: This framework MUST remain independently authorable as one module and one test with no co-authored companion framework.
- Why: The assignment defines a canary for Sawmill, not a product capability. If extra components become required, the smoke test stops being a minimal end-to-end signal.
- Test: Verify the deliverable contains only `smoke.py` and `test_smoke.py` and has no declared dependency on another framework.
- Violations: No exceptions.

2. MERGING
- Rule: This framework MUST NOT absorb any capability beyond a single `ping() -> "pong"` smoke path.
- Why: Adding adapters, schemas, services, or product behavior hides separate capabilities inside a system test and defeats the canary purpose.
- Test: Inspect staged files and confirm no behavior exists beyond `ping()` and one passing test.
- Violations: No exceptions.

3. OWNERSHIP
- Rule: This framework MUST own only `smoke.py` and `test_smoke.py` and MUST NOT introduce shared schemas, events, or graph/state ownership.
- Why: The task explicitly removes this framework from product and primitive scope. Shared ownership would create fake architecture around a trivial canary.
- Test: Verify no additional owned files, no persistence artifacts, and no interface contract beyond the direct Python function call.
- Violations: No exceptions.

4. SOURCE OF TRUTH
- Rule: The authoritative scope MUST come from `TASK.md`; any missing detail MUST be recorded in D6 rather than invented.
- Why: This framework has intentionally tiny scope. Guessing would expand it faster than the source material allows.
- Test: Cross-check every D2-D6 claim back to `TASK.md` or the authority docs.
- Violations: No exceptions.

5. ISOLATION
- Rule: The implementation MUST remain isolated from `platform_sdk`, Docker services, external APIs, and the nine primitives.
- Why: The task forbids all of those dependencies. Pulling them in would convert a smoke test into an architecture exercise.
- Test: Verify imports are limited to the local module and standard test execution.
- Violations: No exceptions.

6. VALIDATION
- Rule: Compliance MUST be proven by one deterministic unit test that asserts `ping()` returns exactly `"pong"`.
- Why: The canary only works if its pass/fail signal is simple, binary, and cheap to run in every pipeline pass.
- Test: Run the smoke test and confirm a single passing assertion.
- Violations: No exceptions.

7. FAILURE HANDLING AND DETERMINISM
- Rule: Any deviation from the exact signature or return literal MUST fail fast through the test suite rather than fallback behavior.
- Why: A canary loses value if it tolerates drift. The pipeline needs an unambiguous failure when the trivial contract breaks.
- Test: Mutate the return value or import path and confirm the test fails.
- Violations: No exceptions.

8. TRACEABILITY
- Rule: Every artifact in this framework MUST trace directly to the smoke-test assignment and its declared owned files.
- Why: Sawmill needs a minimal but real provenance chain even for a canary. Untraceable files would indicate scope drift.
- Test: Confirm D2 scenarios, D3 entities, and D4 contracts all map only to `ping()` and `test_ping()`.
- Violations: No exceptions.

## Boundaries
### ALWAYS
- Author only `smoke.py` and `test_smoke.py`.
- Keep the runtime contract to zero arguments in and literal `"pong"` out.
- Use the task and authority docs as the only specification sources.
- Fail on drift through a direct test assertion.

### ASK FIRST
- Add any file beyond the two owned files.
- Introduce any dependency, service, framework interface, or configuration.
- Expand the canary into package-lifecycle, KERNEL, or product behavior.

### NEVER
- Reference or implement the nine primitives in this framework.
- Create error classes, schemas, adapters, or persistent data stores.
- Add Docker, immudb, platform SDK, or external service dependencies.
- Change the framework into a product or KERNEL framework.

## Dev Workflow Constraints
- Work in behavior-sized DTT cycles: define the `ping()` contract, implement it, run the one test.
- Keep package isolation: no edits outside the framework's smoke module and test.
- Record only scope-backed artifacts in handoff/results files; do not pad the canary with extra inventory.
- Run the full framework-local regression before handoff: the single smoke test must pass.

## Tooling Constraints
| Operation:text | USE:approach | NOT:anti-pattern |
| Author module | plain Python function in `smoke.py` | classes, adapters, wrappers |
| Author test | direct unit test in `test_smoke.py` | integration harnesses, service mocks |
| Validate behavior | local test runner with one assertion | manual inspection as proof |
| Resolve ambiguity | document in D6 | invent extra scope |
