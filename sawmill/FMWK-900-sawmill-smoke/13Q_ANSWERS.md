Builder Prompt Contract Version: 1.0.0

# 13Q Answers

## 1. What am I building?
I am building exactly one staging-scoped smoke canary for `FMWK-900-sawmill-smoke`: a plain Python module `smoke.py` that exposes `ping() -> str` and returns the literal `"pong"`, plus one pytest-style unit test `test_smoke.py` that imports `ping` and asserts `ping() == "pong"`.

## 2. What am I NOT building?
I am not building product behavior, KERNEL/framework primitives, service integrations, schemas, adapters, custom exceptions, helper layers, additional tests, extra owned code files, dependencies, or any behavior beyond the single deterministic `ping()` canary.

## 3. What are the D1 boundaries?
The effective D1 boundaries reflected in D10, D2, D4, and the handoff are: task-as-authority scope only, staging-only work, dependency-free/plain-Python implementation, direct import/assertion validation, fail-fast through normal Python/pytest behavior, deterministic `"pong"` output, and no extra architecture or files beyond the canary-owned `smoke.py` and `test_smoke.py`.

## 4. What APIs/interfaces must I implement?
The runtime interface is exactly `def ping() -> str` in `smoke.py`, callable with no arguments per D4 `IN-001`, and the validation interface is exactly `def test_ping() -> None` in `test_smoke.py`, importing `ping` and asserting the returned value equals `"pong"`.

## 5. Where do the files go?
Implementation files go under the authoritative staging root `staging/FMWK-900-sawmill-smoke/`. Evidence/report files go to `sawmill/FMWK-900-sawmill-smoke/`, specifically `13Q_ANSWERS.md` now and later `RESULTS.md` plus `builder_evidence.json`.

## 6. What data formats and behaviors are required?
There is no custom data model beyond Python source and pytest test code. The functional contract is: inbound call with no arguments, outbound literal string `"pong"`, no side effects, and failures surfaced by normal import failure or assertion failure. Scope validation is file/dependency inspection only.

## 7. What packaging/manifests are required?
The package plan says to use existing framework/task metadata and not invent extra package assets. The owned package assets are `smoke.py`, `test_smoke.py`, and later `RESULTS.md`, with no added manifest authored by me unless an existing framework artifact already provides it. [CRITICAL_REVIEW_REQUIRED]: I am assuming "use framework/task metadata already established; do not invent extra package assets" means no new manifest file should be created during this canary build, because the handoff explicitly forbids inventing extra assets.

## 8. What hashes/dependencies constraints apply?
Dependencies must remain none: no `platform_sdk`, external packages, Docker/service references, or other imports beyond what is needed for the direct test/module relationship. If packaging evidence is produced later, any recorded hashes must be deterministic, and `RESULTS.md` must include file hashes plus pasted command output from this session.

## 9. What is the testing requirement?
The test plan defines exactly one functional test: `test_ping`. I must follow DTT, meaning the test is written and run red before implementation, then implementation is added to make it green. Later verification requires both `python -m pytest test_smoke.py` and the full regression command `python -m pytest`, with passing output recorded in `RESULTS.md`.

## 10. How does this integrate with existing components?
Integration is intentionally minimal: `test_smoke.py` imports `ping` from `smoke.py` and the framework participates in Sawmill only through staged files and evidence artifacts. It does not integrate with `platform_sdk`, runtime services, DoPeJar product code, or any of the nine primitives.

## 11. Adversarial: Failure mode
The expected failure modes are limited and explicit: missing module/function causes import failure (`ERR-001`), wrong return value causes assertion failure (`ERR-002`), and extra dependencies/files cause scope rejection (`ERR-003`). I should not add custom handling; the normal test runner and reviewer checks must surface these failures directly.

## 12. Adversarial: Shortcut check
The main shortcut risks are writing `smoke.py` before the failing test, adding convenience scaffolding/helpers, or broadening scope with extra files/tests. I must not take those shortcuts; the handoff requires one behavior, one test, dependency-free code, and STOP before implementation until reviewer PASS.

## 13. Adversarial: Semantic audit
The semantic meaning of this framework is "Sawmill smoke canary only." A correct implementation proves the pipeline can stage and verify the smallest deterministic Python package. Anything that starts modeling product behavior, governance machinery, abstractions, or external systems would violate that meaning even if the single test still passed.
