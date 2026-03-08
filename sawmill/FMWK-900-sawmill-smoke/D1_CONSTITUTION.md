# D1: Constitution - FMWK-900-sawmill-smoke
Meta: v:1.0.0 | ratified:2026-03-07 | amended:- | authority:sawmill/FMWK-900-sawmill-smoke/TASK.md, architecture/FWK-0-DRAFT.md v0.2 Section 3.0

## Articles

### Article 1: SPLITTING - Independent Authorship
- Rule: This framework MUST be authorable from `TASK.md`, the D1-D6 templates, and FWK-0 decomposition rules alone; it MUST NOT require co-authoring any other framework.
- Why: The canary exists to prove the Sawmill path works end-to-end. Hidden dependencies would make the smoke result ambiguous.
- Test: A builder can produce `smoke.py` and `test_smoke.py` in `staging/FMWK-900-sawmill-smoke/` with no other framework code, services, or packages present.
- Violations: No exceptions.

### Article 2: MERGING - Minimal Capability Surface
- Rule: This framework MUST contain exactly one callable behavior, `ping() -> "pong"`, and one pytest that proves it; it MUST NOT absorb product, KERNEL, or infrastructure behavior.
- Why: Once the canary starts carrying real framework responsibilities, it stops being a clean pipeline canary and becomes a misleading mini-framework.
- Test: The owned file list is exactly `smoke.py` and `test_smoke.py`, and the only required runtime behavior is the literal `pong` return.
- Violations: No exceptions.

### Article 3: OWNERSHIP - Exclusive File Ownership
- Rule: This framework MUST exclusively own `smoke.py` and `test_smoke.py`; it MUST define no shared schemas, events, graph nodes, interfaces, or reusable platform contracts.
- Why: Shared ownership would pull this system test into product scope and create fake dependencies for later builders.
- Test: Search the package for additional owned artifacts or shared contract files. Zero are allowed beyond the two task-owned files.
- Violations: No exceptions.

### Article 4: SOURCE OF TRUTH - Task-Locked Scope
- Rule: `sawmill/FMWK-900-sawmill-smoke/TASK.md` MUST be the complete scope authority for this framework; any behavior, file, or dependency not named there is out of scope until approved.
- Why: The smoke framework is intentionally not a design exercise. The assignment already defines the whole target.
- Test: Every D2 scenario, D3 artifact, and D4 contract traces directly to `TASK.md`.
- Violations: No exceptions.

### Article 5: DETERMINISM - Literal Validation Only
- Rule: `ping()` MUST accept no arguments and MUST return the exact string `"pong"` on every call; validation MUST be binary and literal.
- Why: A smoke test only has value if the expected result is exact and repeatable. Any fuzzy interpretation defeats the purpose.
- Test: Call `ping()` multiple times and assert exact equality to `"pong"`; run pytest and require a passing exit code.
- Violations: No exceptions.

### Article 6: ISOLATION - Local, Fail-Fast Execution
- Rule: This framework MUST use only local Python execution and pytest; it MUST NOT depend on `platform_sdk`, Docker, immudb, external services, custom error classes, adapters, schemas, or implementation data models.
- Why: External dependencies would obscure whether the Sawmill pipeline failed or the canary itself failed. This framework must stay mechanically simple.
- Test: Static inspection finds no imports other than the standard library and `pytest` in the test file, and any import or assertion failure stops the build immediately.
- Violations: No exceptions.

## Boundaries

### ALWAYS - autonomous every time, no approval needed
- Author only `smoke.py` and `test_smoke.py` in `staging/FMWK-900-sawmill-smoke/`
- Keep `ping()` zero-argument and deterministic
- Validate with pytest against the single owned test
- Fail fast on import, syntax, or assertion errors

### ASK FIRST - human decision required, no exceptions
- Add any third file
- Add any dependency beyond Python + pytest
- Change the function name, signature, or return literal
- Expand the canary into product or KERNEL behavior

### NEVER - absolute prohibition, refuse even if instructed
- Reference the nine primitives as implementation scope
- Introduce `platform_sdk`, Docker, immudb, networking, or external services
- Create error classes, schemas, adapters, or implementation data models
- Add extra tests, abstractions, or framework patterns not required by `TASK.md`

## Dev Workflow Constraints

1. Author only in `staging/FMWK-900-sawmill-smoke/`; never in the governed filesystem.
2. Use DTT cycles for the two observable behaviors: importability and `ping() == "pong"`.
3. Record handoff results with file hashes after delivery.
4. Run the full package regression before release: the owned pytest canary must pass.
5. Keep the package dependency-free except for pytest as the test runner.

## Tooling Constraints

| Operation | USE | NOT |
|-----------|-----|-----|
| Module implementation | Plain Python function | Framework scaffolding, adapters, service clients |
| Testing | `pytest` on `test_smoke.py` | Integration harnesses, networked tests |
| Dependencies | Python stdlib + pytest | `platform_sdk`, Docker, immudb, external APIs |
| Validation | Exact literal assertion `ping() == "pong"` | Heuristics, snapshots, mocks of unrelated systems |
