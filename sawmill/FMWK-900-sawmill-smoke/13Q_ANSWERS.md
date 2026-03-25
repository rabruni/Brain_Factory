Builder Prompt Contract Version: 1.0.0

# 13Q Comprehension Gate — FMWK-900-sawmill-smoke (Turn D)

Date: 2026-03-21
Attempt: 2

## Q1 — What am I building?

I am building exactly one framework-local canary deliverable under `staging/FMWK-900-sawmill-smoke/`:
- `smoke.py` containing one function: `def ping() -> str`
- `test_smoke.py` containing one test: `test_ping()`

The only accepted runtime behavior is that `ping()` takes no arguments and returns the exact lowercase literal `"pong"`. The framework exists only to exercise the Sawmill Turn D/Turn E pipeline with the smallest real artifact.

## Q2 — What am I NOT building?

I am not building:
- product behavior for DoPeJar or DoPeJarMo
- any KERNEL primitive, write-path logic, graph logic, orchestration, execution, or package-lifecycle behavior
- any integration with `platform_sdk`, Docker, immudb, services, schemas, adapters, manifests, error classes, config, or persistence
- any file beyond `smoke.py` and `test_smoke.py`
- any extra test cases beyond the single declared behavior

## Q3 — What are the D1 constitutional boundaries?

ALWAYS:
- Author only `smoke.py` and `test_smoke.py`
- Keep the contract to zero arguments in and exact `"pong"` out
- Use task/authority docs as the only spec source
- Prove compliance with one deterministic direct test

ASK FIRST:
- Adding any file beyond the two owned files
- Introducing any dependency, service, configuration, framework interface, or architecture pattern
- Expanding the canary into product, KERNEL, or package-lifecycle behavior

NEVER:
- Reference or implement the nine primitives in this framework
- Add Docker, immudb, `platform_sdk`, external services, schemas, adapters, error classes, or data stores
- Change the canary into anything larger than `ping() -> "pong"`
- Read holdouts or evaluator artifacts

## Q4 — What are the APIs from D4?

The only runtime API is:
- `ping() -> str`

Inbound contract from D4 IN-001:
- callable surface is zero-argument only
- no positional or keyword arguments are part of the contract

Outbound contract from D4 OUT-001:
- success means the caller-observable value is `"pong"`
- there is no framework-level failure payload

The only test API is:
- `test_ping() -> None`
- it imports `ping` from `smoke` and asserts the exact literal

## Q5 — What are the file locations from D2/D4?

Implementation files:
- `staging/FMWK-900-sawmill-smoke/smoke.py`
- `staging/FMWK-900-sawmill-smoke/test_smoke.py`

Sawmill artifacts for this turn:
- `sawmill/FMWK-900-sawmill-smoke/13Q_ANSWERS.md`
- `sawmill/FMWK-900-sawmill-smoke/RESULTS.md`
- `sawmill/FMWK-900-sawmill-smoke/builder_evidence.json`

Reference files read for this gate:
- `sawmill/FMWK-900-sawmill-smoke/TASK.md`
- `sawmill/FMWK-900-sawmill-smoke/D1_CONSTITUTION.md`
- `sawmill/FMWK-900-sawmill-smoke/D2_SPECIFICATION.md`
- `sawmill/FMWK-900-sawmill-smoke/D4_CONTRACTS.md`

## Q6 — What are the data formats from D3/D4?

This framework has no persistent data model, no event schema, and no side-effect payloads.

The only caller-visible format implied by D4 is:
- inbound request shape: effectively empty, because `ping()` takes no arguments
- outbound value: exact Python string `"pong"`

D4’s example success JSON (`{"value":"pong"}`) is documentation of the response meaning, not a separate serialized runtime artifact I need to implement. The actual deliverable remains a plain Python function returning a plain Python `str`.

## Q7 — What are the packaging and hash obligations?

The staged package must remain a two-file canary:
- `smoke.py`
- `test_smoke.py`

Later, after reviewer PASS and implementation, I must also produce:
- `RESULTS.md`
- `builder_evidence.json`

Hash/evidence obligations called out by the handoff/process:
- record SHA-256 values for created files in `RESULTS.md`
- compute `results_hash` after writing `RESULTS.md`
- record `handoff_hash` and `q13_answers_hash` verbatim when writing builder evidence if provided by the orchestrator

[CRITICAL_REVIEW_REQUIRED]: The smoke framework has manifest expectations but no explicit standalone manifest file path is defined in the handoff or D1/D2/D4. My interpretation is that the package surface itself is just the two staged files, and the hash/provenance evidence is carried in `RESULTS.md` and `builder_evidence.json`, not in a separate package manifest file.

## Q8 — What are the dependencies?

Allowed dependencies:
- Python stdlib only for `smoke.py`
- `pytest` for test execution

Disallowed dependencies:
- `platform_sdk`
- Docker services
- immudb
- external APIs
- schemas/adapters/wrappers
- any primitive-related code

## Q9 — What is the testing obligation?

The owned behavior count is one, so the required test surface is one direct unit test:
- `test_ping`

Verification criteria:
- `pytest -q test_smoke.py` must pass
- framework-local full regression (`pytest -q`) must pass after implementation
- the test only passes when `ping` exists, is importable from `smoke`, takes no arguments, and returns exactly `"pong"`

The handoff explicitly says not to inflate the count with synthetic tests just to satisfy a general 10+ test heuristic.

## Q10 — How does this connect to existing components?

It connects only through normal Python import and local `pytest` execution:
- caller/test runner imports `ping` from `smoke`
- `ping()` returns `"pong"`
- `test_ping()` asserts that exact result

There is no connection to runtime services, no use of the SDK, no cross-framework dependency, and no integration plumbing beyond the test runner invoking the local module.

## Q11 — Adversarial: what failure mode must fail fast rather than be tolerated?

The required fail-fast modes are:
- signature drift: `ping` missing, renamed, or changed to accept arguments
- return drift: `ping()` returns anything other than exact `"pong"`
- scope drift: extra files, dependencies, or framework behaviors appear

These are not handled with fallback code. They are handled by immediate test/review failure per D1 Article 7 and D4 ERR-001/ERR-003.

## Q12 — Adversarial: what shortcut would violate the build contract even if the code looks trivial?

Invalid shortcuts include:
- writing `smoke.py` before creating and running the failing test
- claiming the result is obvious and skipping executed pytest evidence
- adding helper files, package scaffolding, fixtures, mocks, or architecture wrappers
- broadening the canary to look more “complete”
- treating manual inspection as proof instead of test output

Because the framework is trivial, the easiest way to drift is to overbuild it. The correct implementation is the smallest one that satisfies the single test and nothing else.

## Q13 — Adversarial: semantic audit

The semantic meaning of this framework is “pipeline canary,” not “mini product package” and not “seed of a larger architecture.” If I add any abstraction, dependency, extra file, or non-literal behavior, I have changed the meaning of the assignment even if the test still passes.

The correct semantic read is:
- one function
- one test
- one exact literal contract
- one isolated framework-local proof

Everything else is scope drift.
