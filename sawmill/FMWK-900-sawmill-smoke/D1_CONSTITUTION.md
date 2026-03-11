# D1: Constitution - sawmill-smoke
Meta: v:0.1.0 | ratified:2026-03-11 | amended:2026-03-11 | authority: AGENT_BOOTSTRAP.md; architecture/NORTH_STAR.md; architecture/BUILDER_SPEC.md; architecture/OPERATIONAL_SPEC.md; architecture/FWK-0-DRAFT.md Section 3.0; architecture/BUILD-PLAN.md; sawmill/FMWK-900-sawmill-smoke/TASK.md

## Articles
1. SPLITTING
- Rule: FMWK-900 MUST remain independently authorable as a two-file smoke canary containing only `smoke.py` and `test_smoke.py`.
- Why: If this framework needs co-authored infrastructure or companion frameworks, it stops being a smoke test and stops isolating the sawmill path.
- Test: Verify a builder can author the framework from `TASK.md`, the smoke spec pack, and FWK-0 rules without adding any companion framework, and confirm the build target contains exactly the two owned files named in `TASK.md`.
- Violations: No exceptions.

2. MERGING
- Rule: FMWK-900 MUST NOT absorb product behavior, KERNEL concerns, integration scaffolding, or additional test suites.
- Why: Mixing canary scope with real capability work hides failures and breaks the purpose of a system-test framework.
- Test: Reject any owned file, behavior, or dependency beyond `ping() -> "pong"` and its single test.
- Violations: No exceptions.

3. OWNERSHIP
- Rule: FMWK-900 MUST exclusively own only `smoke.py` and `test_smoke.py` and MUST define no shared schemas, events, or graph nodes.
- Why: Shared ownership would create coupling that the task explicitly forbids and would turn a trivial canary into architectural surface area.
- Test: Confirm no shared interfaces, persistence objects, or extra owned artifacts are declared.
- Violations: No exceptions.

4. MINIMAL SCOPE
- Rule: The implementation MUST stay at one zero-argument function that returns the exact string `"pong"` and one test that asserts it.
- Why: The smoke signal is valuable only when the behavior under test is singular and obvious.
- Test: Call `ping()` and run `test_ping`; any additional behavior is a scope violation.
- Violations: No exceptions.

5. DETERMINISM
- Rule: `ping()` MUST be pure and deterministic: no inputs, no side effects, exact ASCII output `"pong"`.
- Why: A smoke canary must fail only on packaging or execution drift, not on environment state.
- Test: Execute `ping()` repeatedly in the same environment and confirm identical output with no writes or network calls.
- Violations: No exceptions.

6. ISOLATION
- Rule: FMWK-900 MUST NOT depend on `platform_sdk`, Docker services, immudb, external APIs, or the nine primitives.
- Why: The task defines this framework as outside product and KERNEL scope; any dependency would invent architecture.
- Test: Inspect imports and dependency declarations; only standard Python needed for the test runner is allowed.
- Violations: No exceptions.

7. TRACEABILITY AND FAILURE HANDLING
- Rule: Every artifact and check MUST trace to `TASK.md`, and any mismatch in file ownership, import path, or return value MUST fail fast.
- Why: A smoke framework is useful only when failures point directly at the broken canary contract.
- Test: Cross-check D2-D4 against `TASK.md` and confirm deviations surface as test or build failure.
- Violations: No exceptions.

## Boundaries
### ALWAYS - autonomous every time, no approval needed
- Write only the D1-D6 artifacts for `sawmill/FMWK-900-sawmill-smoke`.
- Keep all described build scope limited to `smoke.py` and `test_smoke.py`.
- Fail the canary on any import, signature, or return-value mismatch.

### ASK FIRST - human decision required, no exceptions
- Change the file names, function name, function signature, or literal return value.
- Add any dependency, helper module, fixture, or second test.
- Expand the canary beyond local Python unit execution.

### NEVER - absolute prohibition, refuse even if instructed
- Introduce KERNEL framework patterns, `platform_sdk`, Docker, immudb, or external services.
- Create error classes, schemas, adapters, persistence layers, or data models.
- Recast this framework as product, runtime, governance, or integration functionality.

## Dev Workflow Constraints
- Keep the framework package isolated to the two owned files named in `TASK.md`.
- Use one DTT cycle for the single behavior: `ping()` returns `"pong"`.
- Record handoff results with file hashes after any builder handoff.
- Run full regression for this package before release: import check plus `test_ping`.
- Reject scope growth instead of accommodating it.

## Tooling Constraints
| Operation | USE | NOT |
|---|---|---|
| Read scope | `TASK.md` and authority docs cited above | Infer extra requirements |
| Implement canary | One Python module with `ping()` | Helpers, adapters, wrappers |
| Verify behavior | One unit test asserting `"pong"` | Integration or service tests |
| Dependencies | Standard Python only | `platform_sdk`, Docker, external services |
