Builder Prompt Contract Version: 1.0.0

# 13Q Answers — FMWK-001-ledger

## Q1. What am I building?
I am building `FMWK-001-ledger` as the Ledger primitive: a Python package in `staging/FMWK-001-ledger/` that owns the canonical Ledger event envelope, internal sequence assignment, canonical JSON serialization, SHA-256 hash computation, ordered replay APIs, chain verification in online and offline-export modes, and a Ledger-owned immudb adapter.

## Q2. What am I NOT building?
I am not building write-path decision logic, fold logic, Graph state/query behavior, package-lifecycle gates, snapshot file creation/loading, immudb admin surfaces, or any runtime repo changes outside this framework staging root.

## Q3. What are the D1 boundaries I must honor?
The Ledger must remain append-only truth, must assign sequence numbers internally, must use one canonical serializer for append and verify, must fail closed on connection/serialization/sequence/corruption faults, and must keep storage transport details behind the Ledger-owned adapter boundary.
[CRITICAL_REVIEW_REQUIRED]: I am deriving the D1 boundary summary from D10, D2, and the handoff because D1 itself was not in the required reading order for this prompt; the synthesis appears consistent, but it is still an indirect reading.

## Q4. What public APIs and error surfaces am I implementing?
Public APIs are `Ledger.append`, `Ledger.read`, `Ledger.read_range`, `Ledger.read_since`, `Ledger.verify_chain`, and `Ledger.get_tip`. Declared typed errors are `LedgerConnectionError`, `LedgerSerializationError`, `LedgerSequenceError`, and `LedgerCorruptionError`.

## Q5. Where does each implementation piece live?
Production files live under `staging/FMWK-001-ledger/ledger/`: `__init__.py`, `errors.py`, `models.py`, `serialization.py`, `backend.py`, and `service.py`. Tests live under `staging/FMWK-001-ledger/tests/`: `conftest.py`, `test_models.py`, `test_serialization.py`, `test_append_and_read.py`, `test_verification.py`, `test_connection_failures.py`, and `test_integration_immudb.py`.

## Q6. What exact data-format rules are fixed by the spec?
Append input must exclude caller-supplied `sequence`, `previous_hash`, and `hash`. Canonical serialization must use JSON with sorted keys, separators `,` and `:`, UTF-8 bytes, `ensure_ascii=false`, nulls included, and the `hash` field excluded from hash input. Hash strings must be exact `sha256:<64 lowercase hex>`. Genesis `previous_hash` is `sha256:` plus 64 zeros. `read_since(-1)` means replay from genesis. `verify_chain` must return the same verdict shape online and offline.

## Q7. What packaging/manifests are required?
The framework package must include the Ledger source, tests, fixtures if needed, and only minimal support files following local repo convention. A framework-local manifest or metadata file is only allowed if the resolved staging root already uses one; I must not invent a packaging system.
[CRITICAL_REVIEW_REQUIRED]: The handoff intentionally leaves the manifest format conditional on existing local convention, so I should not assume any packaging metadata file exists until I inspect the staging root after reviewer PASS.

## Q8. What dependency boundaries and hash/provenance rules matter?
Runtime dependency boundaries are Python 3.11+, `platform_sdk` for config/secrets/logging, `pytest` for tests, and immudb transport only behind the Ledger adapter. Hash provenance depends on one shared canonical byte-generation path for append and verify so online and offline verification cannot drift.

## Q9. What testing burden do I have before claiming completion?
I need at least 25 tests total, covering every behavior in the handoff test plan, with DTT red-then-green evidence per behavior. Final verification requires `python -m compileall ledger tests`, the full unit suite, targeted append/read and verification commands, the opt-in integration suite, and the staged-package regression command against this framework tests plus `staging/FMWK-900-sawmill-smoke`.

## Q10. How does this framework integrate with existing components?
Upstream callers include FMWK-002 write-path and approved system-event producers for append, plus diagnostics/recovery tooling and FMWK-005 graph rebuild/recovery for reads and verification. Downstream, only the Ledger-owned backend touches immudb, and it must source host/port/database/credentials through `platform_sdk` boundaries rather than hardcoded values.

## Q11. Adversarial: what is the most likely scope-drift failure here?
The highest-risk drift is letting Ledger absorb write-path, graph, or snapshot-management behavior. The guardrail is to keep Ledger limited to storing self-describing events, replaying them in order, and verifying integrity; `snapshot_created` is metadata only, not snapshot file ownership.

## Q12. Adversarial: what assumption could make a correct-looking implementation wrong?
The v1 atomic append mechanism is assumed to be the in-process mutex option under a single-writer architecture. If I implemented a different reservation strategy or tolerated caller-side fallback sequencing, I could pass superficial tests while violating the recorded D6 assumption and the no-forks requirement.
[CRITICAL_REVIEW_REQUIRED]: The atomicity choice is explicitly an assumption locked in D6 CLR-004 rather than a stronger direct contract statement in the handoff, so reviewer confirmation is useful before implementation.

## Q13. Adversarial: what evidence standard must block me from claiming success?
I cannot claim success from reasoning alone. I need session-local evidence: failing-then-passing tests for each behavior, pasted command output in `RESULTS.md`, full-suite results, staged-package regression results, and no unverifiable statements such as "should pass" or "probably works."
