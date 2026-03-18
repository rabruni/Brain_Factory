# D1: Constitution — sawmill smoke canary
Meta: v:1.0.0 | ratified:2026-03-17 | amended:2026-03-17 | authority:AGENT_BOOTSTRAP.md, architecture/NORTH_STAR.md, architecture/BUILDER_SPEC.md, architecture/OPERATIONAL_SPEC.md, architecture/FWK-0-DRAFT.md, architecture/BUILD-PLAN.md, sawmill/FMWK-900-sawmill-smoke/TASK.md

## Articles
1. SPLITTING
- Rule: This canary MUST remain independently authorable as exactly one module and one test.
- Why: The task defines a minimal end-to-end pipeline exercise. Adding co-authored components would violate the smoke-test purpose and stop it from being a clean canary.
- Test: Verify the framework output is limited to `smoke.py` and `test_smoke.py` as declared in the task.
- Violations: No exceptions.

2. MERGING
- Rule: This canary MUST NOT absorb any capability beyond `ping() -> "pong"` and its single test.
- Why: If more behavior is added, the framework stops testing the pipeline minimally and starts hiding unrelated capability behind a canary label.
- Test: Inspect staged source and reject any additional modules, adapters, schemas, or services.
- Violations: No exceptions.

3. OWNERSHIP
- Rule: This canary MUST exclusively own `smoke.py` and `test_smoke.py`.
- Why: The task gives the canary a closed scope with no dependencies. Shared ownership would introduce ambiguity that the task explicitly forbids.
- Test: Verify only this framework declares those two files.
- Violations: No exceptions.

4. SOURCE OF TRUTH
- Rule: The task file MUST be treated as the complete scope authority for this canary.
- Why: This is a system-test framework, not a product framework. The task explicitly says not to apply KERNEL patterns or expand scope.
- Test: Cross-check every D2 item against `TASK.md`; anything extra is a failure.
- Violations: No exceptions.

5. ISOLATION
- Rule: The canary MUST have zero runtime dependencies and MUST NOT require `platform_sdk`, Docker services, or external systems.
- Why: The task declares no dependencies. Dependency-free execution is what makes this a reliable smoke test.
- Test: Review imports and test setup for any external dependency or service reference.
- Violations: No exceptions.

6. TRACEABILITY
- Rule: Every artifact in this framework MUST trace directly to the canary task.
- Why: The spec agent extracts; it does not invent. Direct traceability is the only way to keep the artifact minimal and valid.
- Test: Map each file and scenario back to a task statement.
- Violations: No exceptions.

7. VALIDATION
- Rule: Validation MUST be limited to importing `ping()` and asserting that it returns `"pong"`.
- Why: The task defines one test only. Broader validation would introduce unrequested behavior or infrastructure.
- Test: Confirm the staged test contains one assertion on `ping() == "pong"`.
- Violations: No exceptions.

8. FAILURE HANDLING
- Rule: Any failure in import or return value MUST fail fast through the single test without adding custom error machinery.
- Why: The task explicitly forbids custom error classes and extra architecture.
- Test: Ensure failures surface as normal Python import or assertion failures.
- Violations: No exceptions.

9. DETERMINISM
- Rule: `ping()` MUST return the literal string `"pong"` on every invocation.
- Why: A smoke canary is only useful if it is fully deterministic and trivial to verify.
- Test: Run the test repeatedly and confirm stable output.
- Violations: No exceptions.

## Boundaries
### ALWAYS
- Author only `smoke.py` and `test_smoke.py`.
- Keep the function side-effect free.
- Keep the test self-contained and deterministic.

### ASK FIRST
- Any additional file beyond the two owned files.
- Any dependency, fixture, or runtime integration.
- Any change to the return value or function signature.

### NEVER
- Add product behavior, framework infrastructure, or KERNEL primitive logic.
- Add schemas, adapters, custom exceptions, or service clients.
- Reference `platform_sdk`, immudb, Docker, or external APIs.

## Dev Workflow Constraints
- Work only from the explicit task scope; no speculative expansion.
- Use one behavior loop: implement `ping()`, verify `test_ping()`.
- Record only the required sawmill artifacts; no auxiliary design inventory.
- Run the single smoke test before handoff.

## Tooling Constraints
| Operation:text | USE:approach | NOT:anti-pattern |
| --- | --- | --- |
| Implementation | USE:plain Python module | NOT:framework scaffolding |
| Testing | USE:single Python unit test | NOT:integration harness |
| Dependencies | USE:none | NOT:platform_sdk or external packages |
| Verification | USE:direct import and assertion | NOT:service bootstrapping |
