# Builder Handoff — FMWK-001-ledger

## 1. Mission
Implement the first real governed build of `FMWK-001-ledger` in `staging/FMWK-001-ledger` so DoPeJarMo has an append-only, hash-chained event store that can synchronously append approved events, replay them in sequence order, and verify the chain online or offline. This framework is the KERNEL foundation: if ledger durability, sequencing, or canonical hashing drift, every downstream framework loses deterministic replay and cold-storage validation.

## 2. Critical Constraints
1. Work in staging only: all code, tests, and package assets stay inside `staging/FMWK-001-ledger`.
2. Follow DTT strictly: write the failing test first, then the minimum implementation to pass it, then rerun before moving on.
3. Package everything needed for this framework: source, tests, and local documentation.
4. End-to-end verify before reporting completion: run the full staged regression, not only targeted tests.
5. No hardcoding of runtime credentials or environment-specific secrets; use `platform_sdk` config/secrets surfaces.
6. No file replacement shortcuts: do not wipe or replace whole directories when editing a single file will do.
7. Deterministic artifacts only: canonical JSON bytes, exact hash strings, and reproducible test fixtures.
8. Write `sawmill/FMWK-001-ledger/RESULTS.md` with SHA256 evidence and pasted test output from this session.
9. Run full regression of all files in this package after implementation, even if targeted tests already pass.
10. Record a baseline snapshot in `RESULTS.md` before reporting PASS, including package files created and the exact full-test command.
11. Follow `Templates/TDD_AND_DEBUGGING.md` discipline: if code was written before the test, delete and redo it under test.
12. Do not import or expose forbidden immudb administrative operations.
13. Do not invent scope outside D2 SC-001 through SC-011 and the minimum approved payload schemas.
14. Do not route around the 13Q gate: create `13Q_ANSWERS.md`, stop, and wait for reviewer PASS before implementation.

## 3. Architecture/Design
```text
append caller
   |
   v
Ledger facade (api.py)
   |
   +--> schemas.py
   |      validates approved append requests and payload catalog
   |
   +--> serialization.py
   |      canonical UTF-8 JSON bytes
   |      sha256:<64 lowercase hex>
   |
   +--> store.py
   |      mutex-protected tip-read + write
   |      synchronous persistence
   |      reconnect once on disconnect
   |
   +--> verify.py
          online replay verification
          offline exported-data verification

Outputs:
- LedgerEvent
- list[LedgerEvent]
- LedgerTip
- VerificationResult
- explicit ledger errors
```

Interfaces and boundaries:
- Public boundary:
  `class Ledger`
  `append(self, request) -> LedgerEvent`
  `read(self, sequence_number: int) -> LedgerEvent`
  `read_range(self, start: int, end: int) -> list[LedgerEvent]`
  `read_since(self, sequence_number: int) -> list[LedgerEvent]`
  `verify_chain(self, start: int | None = None, end: int | None = None, source_mode: str = "online") -> VerificationResult`
  `get_tip(self, include_hash: bool = True) -> LedgerTip`
- Internal boundary:
  `schemas.py` owns request and payload validation only.
  `serialization.py` owns canonical bytes and hash formatting only.
  `store.py` owns persistence, sequencing, and reconnect-once behavior only.
  `verify.py` owns online/offline verification only.
- Explicit non-boundaries:
  no graph folds
  no gate logic
  no orchestration/work-order state
  no runtime DB provisioning
  no direct caller access to immudb

## 4. Implementation Steps
1. Create `staging/FMWK-001-ledger/13Q_ANSWERS.md` with exactly `Builder Prompt Contract Version: 1.0.0`, then STOP. WHY: the builder prompt contract forbids implementation before reviewer PASS.
2. Create the package skeleton: `ledger/__init__.py`, `ledger/errors.py`, `ledger/models.py`, `ledger/schemas.py`, `ledger/serialization.py`, `ledger/store.py`, `ledger/verify.py`, `ledger/api.py`, `tests/`, and `README.md`. WHY: the package boundary must be explicit before behavior work starts.
3. Write failing tests for D3 entity shapes and error-code mapping, then implement `ledger/errors.py` and `ledger/models.py`. WHY: D3 is the typed contract every later module depends on.
4. Write failing tests for approved append request validation and implement `ledger/schemas.py` for `node_creation`, `signal_delta`, `package_install`, `session_start`, and `snapshot_created` only. WHY: D6 closed unsupported payload schemas by refusing them, not by guessing.
5. Write failing fixtures for canonical JSON bytes and hash formatting, then implement `ledger/serialization.py`. WHY: hash determinism is a byte-level constitutional rule and must be locked first.
6. Write failing tests for genesis append and next append, then implement append sequencing in `ledger/store.py` with an in-process mutex around tip-read plus write. WHY: D5 selected the mutex assumption for atomicity in the single-writer model.
7. Write failing tests for `read`, `read_range`, `read_since`, and `get_tip`, then complete the corresponding storage methods. WHY: replay and diagnostics depend on strict ascending order and exact tip reporting.
8. Write failing tests for disconnect handling, absent database failure, and sequence race rejection, then complete reconnect-once and explicit error propagation in `ledger/store.py`. WHY: D4 defines fail-closed operational boundaries that must not become implicit retries or partial success.
9. Write failing tests for online intact verification, corruption detection, and offline parity, then implement `ledger/verify.py`. WHY: cold-storage verification is one of the framework's core reasons to exist.
10. Wire `ledger/api.py` as a thin public facade over validation, storage, and verification. WHY: the public surface must remain mechanical and not absorb internal logic.
11. Add API-level tests covering approved event append flows, snapshot marker append behavior, and failure propagation. WHY: the public contract, not only internals, must satisfy D4.
12. Add `README.md` with exact local commands and scope notes. WHY: staged package usage must be inspectable without reading implementation internals.
13. Run targeted tests after each behavior and keep evidence for the session log. WHY: verification claims require real output from this session.
14. After all unit and integration tests pass, record the mid-build checkpoint with counts, pasted output, files created, and any spec deviations. WHY: the handoff standard requires a checkpoint before final regression.
15. Run the full staged regression command: `PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests`. WHY: package completion requires whole-package evidence, not local confidence.
16. Write `sawmill/FMWK-001-ledger/RESULTS.md` with status, SHA256s, command lines, full pasted output, baseline snapshot, and issues encountered. WHY: provenance and reviewer validation depend on this artifact.
17. Perform self-reflection against D2, D4, D8, and TDD discipline before reporting completion. WHY: this is the last check against silent scope creep or unverifiable claims.

## 5. Package Plan
| Package ID | Layer | Assets | Dependencies | Manifest |
| PC-001-ledger-core | KERNEL | `ledger/__init__.py`, `ledger/errors.py`, `ledger/models.py`, `ledger/schemas.py`, `ledger/serialization.py`, `ledger/store.py`, `ledger/verify.py`, `ledger/api.py`, `tests/test_serialization.py`, `tests/test_store.py`, `tests/test_verify.py`, `tests/test_api.py`, `README.md`, `13Q_ANSWERS.md` | Python stdlib, `platform_sdk` config/secrets/logging/errors surfaces, immudb reachable only through the ledger abstraction boundary | Builder records file inventory and hashes in `RESULTS.md`; no separate manifest format is invented here |

## 6. Test Plan
Minimum target: 25+ tests.

Required test methods and expected behaviors:
- `test_append_genesis_assigns_sequence_zero_and_zero_previous_hash`
  Expected behavior: first append returns `sequence=0` and genesis zero hash.
- `test_append_uses_previous_tip_hash_and_next_sequence`
  Expected behavior: second append links to the prior event hash and increments by one.
- `test_append_rejects_caller_supplied_sequence_fields`
  Expected behavior: request validation rejects `sequence`, `previous_hash`, or `hash`.
- `test_append_validates_minimum_node_creation_payload`
  Expected behavior: approved `node_creation` payload is accepted.
- `test_append_validates_minimum_signal_delta_payload`
  Expected behavior: approved `signal_delta` payload is accepted and integer-only `delta` is enforced.
- `test_append_validates_minimum_package_install_payload`
  Expected behavior: approved `package_install` payload is accepted with canonical hash string validation.
- `test_append_validates_minimum_session_start_payload`
  Expected behavior: approved `session_start` payload is accepted.
- `test_append_validates_snapshot_created_reference_payload`
  Expected behavior: snapshot marker accepts sequence/path/hash only and does not define file contents.
- `test_serialization_uses_sorted_keys_without_whitespace`
  Expected behavior: canonical bytes match exact fixture output.
- `test_serialization_excludes_hash_field_from_hash_input`
  Expected behavior: changing only the stored `hash` field does not change hash input bytes.
- `test_serialization_preserves_nulls_and_utf8_literals`
  Expected behavior: nulls are kept and unicode is emitted as literal UTF-8.
- `test_compute_event_hash_returns_sha256_prefixed_lowercase_hex`
  Expected behavior: hash string matches exact required format.
- `test_read_returns_single_event_by_sequence`
  Expected behavior: a stored event is returned unchanged by sequence lookup.
- `test_read_range_returns_ascending_inclusive_sequence_order`
  Expected behavior: range output is contiguous and ascending.
- `test_read_since_excludes_boundary_sequence`
  Expected behavior: replay starts strictly after the provided sequence.
- `test_get_tip_returns_latest_sequence_and_hash`
  Expected behavior: tip reflects the most recent committed event.
- `test_append_rejects_tip_mismatch_with_sequence_error`
  Expected behavior: forced race or tip drift raises `LEDGER_SEQUENCE_ERROR`.
- `test_connect_fails_fast_when_database_absent`
  Expected behavior: absent `ledger` database surfaces `LEDGER_CONNECTION_ERROR`.
- `test_disconnect_retries_once_then_succeeds`
  Expected behavior: one reconnect retry occurs before success.
- `test_disconnect_retries_once_then_fails`
  Expected behavior: final failure returns `LEDGER_CONNECTION_ERROR`.
- `test_verify_chain_online_returns_valid_true_for_intact_chain`
  Expected behavior: online verification of intact data returns `valid=true`.
- `test_verify_chain_reports_first_corrupted_sequence`
  Expected behavior: corruption returns `valid=false` and exact `break_at`.
- `test_verify_chain_offline_matches_online_result`
  Expected behavior: offline verification matches online for the same data.
- `test_verify_chain_surfaces_serialization_error_for_unhashable_event`
  Expected behavior: invalid canonical serialization fails closed.
- `test_ledger_api_propagates_explicit_error_codes`
  Expected behavior: facade does not swallow or remap contract errors incorrectly.

## 7. Existing Code to Reference
| What | Where | Why |
| Existing staged smoke test shape | `staging/FMWK-900-sawmill-smoke/` | Small local reference for staged code plus pytest layout. |
| Pre-existing ledger provider | `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/ledger.py` | Reference for provider structure and mock-vs-runtime separation only; not authority and not a copy source. |
| SDK module inventory | `/Users/raymondbruni/dopejar/platform_sdk/MODULES.md` | Confirms `platform_sdk` is the required import surface for config, errors, logging, and related concerns. |
| Approved specs | `sawmill/FMWK-001-ledger/D1_CONSTITUTION.md` through `D8_TASKS.md` | Build authority for scope, contracts, tasks, and constraints. |

## 8. E2E Verification
Exact commands:
```bash
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_serialization.py
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_store.py
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_verify.py
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_api.py
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests
```

Expected output:
- Each targeted test command exits `0`.
- Full regression exits `0`.
- No skipped failures for SC-001 through SC-011.
- `RESULTS.md` contains pasted output for every command above from this session.

## 9. Files Summary
| File | Location | Action (CREATE/MODIFY) |
| `13Q_ANSWERS.md` | `staging/FMWK-001-ledger/13Q_ANSWERS.md` | CREATE |
| `__init__.py` | `staging/FMWK-001-ledger/ledger/__init__.py` | CREATE |
| `errors.py` | `staging/FMWK-001-ledger/ledger/errors.py` | CREATE |
| `models.py` | `staging/FMWK-001-ledger/ledger/models.py` | CREATE |
| `schemas.py` | `staging/FMWK-001-ledger/ledger/schemas.py` | CREATE |
| `serialization.py` | `staging/FMWK-001-ledger/ledger/serialization.py` | CREATE |
| `store.py` | `staging/FMWK-001-ledger/ledger/store.py` | CREATE |
| `verify.py` | `staging/FMWK-001-ledger/ledger/verify.py` | CREATE |
| `api.py` | `staging/FMWK-001-ledger/ledger/api.py` | CREATE |
| `test_serialization.py` | `staging/FMWK-001-ledger/tests/test_serialization.py` | CREATE |
| `test_store.py` | `staging/FMWK-001-ledger/tests/test_store.py` | CREATE |
| `test_verify.py` | `staging/FMWK-001-ledger/tests/test_verify.py` | CREATE |
| `test_api.py` | `staging/FMWK-001-ledger/tests/test_api.py` | CREATE |
| `README.md` | `staging/FMWK-001-ledger/README.md` | CREATE |
| `RESULTS.md` | `sawmill/FMWK-001-ledger/RESULTS.md` | CREATE |

## 10. Design Principles
1. Ledger stays mechanical: storage, ordering, and verification only.
2. Hash determinism beats convenience: exact bytes, exact strings, exact fixtures.
3. Append-only is enforced by code shape, not by comments.
4. Fail closed on corruption, connection, sequence, and serialization errors.
5. Minimum approved payload catalog only; unsupported schemas are rejected, not improvised.
6. Offline verification must work without Graph, HO1, HO2, or kernel services.

## 11. Verification Discipline
Every claim that a test passes must include pasted command output from this session in `sawmill/FMWK-001-ledger/RESULTS.md`. Do not write “should pass,” “probably passes,” or “confidence high” in place of evidence. Include full commands, exit status evidence, total/passed/failed/skipped counts, and any retries performed. The results file must include SHA256 for every created file and before/after hashes for any modified file.

## 12. Mid-Build Checkpoint
After all unit and integration tests pass but before final reporting:
- record the count of passing tests
- paste the exact latest test output
- list files created
- state whether any spec deviations occurred
- continue to full regression unless the orchestrator escalates

## 13. Self-Reflection
Before reporting any step complete, verify:
- code matches D2 scenarios and D4 contracts exactly
- D8 edge cases and P1 scenarios are all covered by tests
- the implementation would still be understandable in six months
- TDD was followed for every behavior
- if any code was written before its failing test, delete and redo it under test
