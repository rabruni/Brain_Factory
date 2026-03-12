# D1: Constitution — sawmill-smoke
Meta: v:1.0.0 | ratified:2026-03-12 | amended:2026-03-12 | authority:AGENT_BOOTSTRAP.md, architecture/NORTH_STAR.md, architecture/BUILDER_SPEC.md, architecture/OPERATIONAL_SPEC.md, architecture/FWK-0-DRAFT.md, architecture/BUILD-PLAN.md, sawmill/FMWK-900-sawmill-smoke/TASK.md

## Articles (5-10, sequential numbering)
1. SPLITTING
- Rule: FMWK-900 MUST remain independently authorable as a single trivial canary framework containing only `smoke.py` and `test_smoke.py`.
- Why: If the smoke canary requires co-authoring with another framework, it stops being a pipeline smoke test and starts depending on unrelated build scope.
- Test: Verify the framework output is limited to one Python module and one test, with no declared dependencies.
- Violations: No exceptions.

2. MERGING
- Rule: FMWK-900 MUST NOT absorb product, KERNEL, or infrastructure capability beyond the single ping canary.
- Why: If extra capability is merged in, the smoke test no longer isolates Sawmill artifact generation and becomes a disguised implementation task.
- Test: Verify all scenarios, contracts, and files trace only to `ping() -> "pong"` and its test.
- Violations: No exceptions.

3. OWNERSHIP
- Rule: FMWK-900 MUST own only `smoke.py` and `test_smoke.py`, with no shared schemas, events, or node types.
- Why: Shared ownership would create cross-framework coupling that the task explicitly forbids.
- Test: Verify D3 lists zero shared entities and D2 ownership scope matches the task's Owns section exactly.
- Violations: No exceptions.

4. SCOPE
- Rule: The framework MUST implement exactly one function returning `"pong"` and one test asserting that value.
- Why: The task defines the full build target. Any added behavior is invented scope.
- Test: Verify the build target matches the code snippets in `TASK.md` exactly in behavior.
- Violations: No exceptions.

5. TRACEABILITY
- Rule: Every artifact in D1-D6 MUST trace directly to `TASK.md` or the required authority documents, never to unstated assumptions.
- Why: This smoke framework exists to validate extraction discipline; untraceable content defeats the test.
- Test: For each D2 scenario and D4 contract, confirm the cited source is `TASK.md` or an explicit D6 assumption.
- Violations: No exceptions.

6. DETERMINISM
- Rule: `ping()` MUST be deterministic and side-effect free.
- Why: The smoke canary is only useful if it is stable across runs and does not depend on environment state.
- Test: Execute the test repeatedly and confirm the same `"pong"` result with no external setup.
- Violations: No exceptions.

7. FAILURE HANDLING
- Rule: The framework MUST fail only through normal Python import or test execution failure, with no custom error system.
- Why: The task explicitly forbids creating error classes or extra structure.
- Test: Verify no custom error types, adapters, or recovery logic are specified or generated.
- Violations: No exceptions.

8. VALIDATION
- Rule: Validation MUST be limited to importing `ping()` and asserting it returns `"pong"`.
- Why: Broader validation would introduce requirements not present in the smoke assignment.
- Test: Confirm the only acceptance test is `test_ping`.
- Violations: No exceptions.

## Boundaries (unlisted actions default to ASK FIRST, always)
### ALWAYS — autonomous every time, no approval needed
- Write and maintain only the six D1-D6 artifacts for FMWK-900.
- Keep the framework scope limited to the module and test defined in `TASK.md`.
- Record any unresolved ambiguity as a resolved assumption in D6 rather than expanding scope.

### ASK FIRST — human decision required, no exceptions
- Adding any file beyond `smoke.py` and `test_smoke.py`.
- Introducing dependencies, tooling, or framework integrations.
- Expanding the canary beyond the single ping behavior.

### NEVER — absolute prohibition, refuse even if instructed
- Do not apply KERNEL framework patterns to this system test canary.
- Do not create error classes, schemas, adapters, or persistent data models.
- Do not reference the nine primitives as part of FMWK-900 scope.

## Dev Workflow Constraints (4+)
- Work in isolation under `staging/FMWK-900-sawmill-smoke/` only.
- Use DTT cycles only for the single `ping` behavior and its single test.
- Produce results artifacts with hashes after each Sawmill handoff if a downstream turn requires them.
- Run full regression for this framework's owned files before release; do not imply broader system regression coverage.

## Tooling Constraints
| Operation:text | USE:approach | NOT:anti-pattern |
| Define scope | USE:extract directly from `TASK.md` | NOT:infer product behavior |
| Implement behavior | USE:plain Python function returning `"pong"` | NOT:framework scaffolds or adapters |
| Validate behavior | USE:single Python test importing `ping` | NOT:service, Docker, or SDK integration |
| Document assumptions | USE:D6 resolved assumptions | NOT:silent scope expansion |
