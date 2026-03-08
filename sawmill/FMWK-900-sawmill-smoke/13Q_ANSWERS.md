# 13Q Answers — FMWK-900-sawmill-smoke (Turn D, H-1)

Infrastructure adversarial set used for Q11-Q13 because the Sawmill handoff/gate process already exists and is the system being exercised by this canary.

## Q1 — What am I building?
I am building exactly one tiny canary package in `staging/FMWK-900-sawmill-smoke/`:

1. `smoke.py` with one public function, `ping() -> str`, returning the exact literal `"pong"`.
2. `test_smoke.py` with one pytest, `test_ping()`, importing `ping` and asserting `ping() == "pong"`.

After a greenlight and implementation, the only non-staging artifact I add is `sawmill/FMWK-900-sawmill-smoke/RESULTS.md`.

## Q2 — What am I explicitly NOT building?
I am explicitly NOT building:

1. Any product or KERNEL behavior.
2. Any framework plumbing, primitives, lifecycle logic, governance logic, or runtime services.
3. Any third file in the staging package.
4. Any dependency on `platform_sdk`, Docker, immudb, networking, schemas, adapters, custom errors, or data models.
5. Any extra tests beyond the single owned pytest.
6. Any flexible behavior beyond the exact zero-argument `ping() -> "pong"` contract.

## Q3 — What are the D1 boundaries I must obey?
`ALWAYS`

1. Author only `smoke.py` and `test_smoke.py` in `staging/FMWK-900-sawmill-smoke/`.
2. Keep `ping()` zero-argument and deterministic.
3. Validate with pytest against the single owned test.
4. Fail fast on import, syntax, or assertion errors.

`ASK FIRST`

1. Add any third file.
2. Add any dependency beyond Python and pytest.
3. Change the function name, signature, or return literal.
4. Expand the canary into product or KERNEL behavior.

`NEVER`

1. Reference the nine primitives as implementation scope.
2. Introduce `platform_sdk`, Docker, immudb, networking, or external services.
3. Create error classes, schemas, adapters, or implementation data models.
4. Add extra tests, abstractions, or framework patterns not required by `TASK.md`.

## Q4 — What exact API do I have to implement?
The only approved API is:

```python
def ping() -> str:
    return "pong"
```

Constraints from D1/D4:

1. `ping()` takes no arguments.
2. The only valid outbound value is the exact string `"pong"`.
3. There is no alternate mode, fallback, or config-driven variation.

## Q5 — Where do the owned files live and how do they connect?
The owned files are:

1. `staging/FMWK-900-sawmill-smoke/smoke.py`
2. `staging/FMWK-900-sawmill-smoke/test_smoke.py`

Runtime/test flow:

1. `pytest` runs `test_smoke.py`.
2. `test_smoke.py` imports `ping` from `smoke`.
3. `test_ping()` calls `ping()`.
4. The assertion checks exact equality with `"pong"`.

## Q6 — What outbound values and failure modes are approved by D4?
Approved outputs:

1. Calling `ping()` returns `"pong"`.
2. Running the owned pytest yields a passing result, represented as `1 passed`.

Approved failure behavior:

1. Missing or renamed `ping` causes a native import failure.
2. Any return other than `"pong"` causes a native pytest assertion failure.
3. Import, syntax, or assertion errors must fail fast; no wrappers or custom exceptions are allowed.

## Q7 — What packaging evidence, manifest, and hashes are required?
For this canary:

1. No archive is required.
2. `sawmill/FMWK-900-sawmill-smoke/RESULTS.md` is mandatory after implementation.
3. `RESULTS.md` must include the baseline snapshot, commands run, pasted command output, and SHA-256 hashes in `sha256:<64hex>` format.
4. The created files that need hashes are `smoke.py`, `test_smoke.py`, and `RESULTS.md`.

[CRITICAL_REVIEW_REQUIRED]: D10 says the branch should be `feature/FMWK-900-sawmill-smoke`, while the builder role says `build/<FMWK-ID>`. I am treating that as a process-level discrepancy for finalization, not as code scope, but it needs human resolution before PR creation.

## Q8 — What dependencies and extra assets are allowed?
Allowed:

1. Plain Python for `smoke.py`.
2. `pytest` for `test_smoke.py`.
3. Python stdlib only if needed, although `smoke.py` needs no imports.

Not allowed:

1. `platform_sdk`
2. Docker or immudb
3. External APIs or services
4. Extra helper modules, fixtures, configs, or scaffolding

Runtime dependency count is none. Test dependency count is `pytest` only.

## Q9 — How many tests are in scope, and what exactly counts as success?
Exactly one owned pytest is in scope: `test_ping`.

Success criteria:

1. `test_smoke.py` imports `ping` from `smoke` successfully.
2. `ping()` takes no arguments.
3. `ping()` returns the exact string `"pong"`.
4. Running `python3 -m pytest test_smoke.py -v --tb=short` from `staging/FMWK-900-sawmill-smoke/` ends with `1 passed`.

The required TDD proof is:

1. Write `test_smoke.py` first.
2. Run pytest before `smoke.py` exists and observe failure.
3. Implement `smoke.py`.
4. Rerun the same pytest and observe success.

## Q10 — How does this connect to existing components?
This canary has only two real integration points:

1. Local Python import wiring: `test_smoke.py` imports `ping` from `smoke.py`.
2. The Sawmill process consumes the resulting evidence later through the passing pytest output and `RESULTS.md`.

It does not integrate with runtime DoPeJarMo components, the nine primitives, `platform_sdk`, Docker, immudb, or any external service.

## Q11 — Adversarial: The Failure Mode
If a gate check fails, the most likely culprit in scope is `staging/FMWK-900-sawmill-smoke/smoke.py`.

Why:

1. If `ping` is missing or renamed, import fails immediately.
2. If `ping()` returns anything other than `"pong"`, the only owned test fails immediately.
3. Both core scenarios in D2 hinge on that one file matching the literal contract exactly.

Secondary culprit: `test_smoke.py` if the import statement or assertion drifts from the approved snippet.

## Q12 — Adversarial: The Shortcut Check
The obvious shortcut is to skip the required RED step because the implementation is trivial and write `smoke.py` first.

I will not do that because:

1. `Templates/TDD_AND_DEBUGGING.md` makes failing-test-first mandatory.
2. D10 and the handoff require proving the import boundary with a failing pytest before implementation.
3. The whole point of this canary is process proof, not just getting to `"pong"` quickly.

The other shortcut I will not take is replacing pytest with only `python3 -c "from smoke import ping; print(ping())"`. The manual call is supplementary evidence, not the package verdict.

## Q13 — Adversarial: The Semantic Audit
Ambiguous word: `package`

Precise definition for this handoff:

`Package` means exactly the approved deliverable surface for FMWK-900-sawmill-smoke: the two owned files in `staging/FMWK-900-sawmill-smoke/` plus the evidence file `sawmill/FMWK-900-sawmill-smoke/RESULTS.md`.

It does not mean:

1. A Python distribution artifact
2. An archive file
3. A reusable framework skeleton
4. Permission to add supporting modules or configuration
