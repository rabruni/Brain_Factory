# D8: Tasks — FMWK-001-ledger
Meta: plan: D7 1.0.0 | status:Final | total tasks:8 | parallel opportunities:2

## MVP Scope
In scope: all D2 scenarios SC-001 through SC-010. Nothing in D2 is deferred for Turn D because the D6 gate is closed and the framework is foundational. Deferred capabilities remain only the D2 `DEF-001` through `DEF-003` items and must not expand the build beyond the listed event payloads, snapshot metadata contract, and approved v1 atomicity assumption.

## Tasks (T-### IDs, phased)

- Phase 0 Foundation: T-001 Define the package skeleton, typed errors, canonical entities, and shared test fixtures
  Parallel/Serial: Serial
  Dependency: None
  Scope: M
  Scenarios Satisfied: D2 SC-005, SC-006
  Contracts Implemented: D4 IN-001, OUT-001, OUT-005, ERR-001, ERR-002, ERR-003, ERR-004
  Acceptance Criteria:
  1. Create `ledger/__init__.py`, `ledger/errors.py`, `ledger/models.py`, and `tests/conftest.py`.
  2. `ledger/models.py` defines `LedgerEvent`, `EventProvenance`, `LedgerTip`, `ChainVerificationResult`, and the minimum payload models from D3 E-003 through E-007.
  3. Validation rejects missing required envelope fields and caller-controlled `sequence`, `previous_hash`, or `hash` in append requests.
  4. At least 5 unit tests prove the envelope and payload constraints from D3 and D4.

- Phase 1 Core Logic: T-002 Implement canonical serialization, sequence key mapping, and exact hash helpers
  Parallel/Serial: Parallel with T-003
  Dependency: T-001 (needs models and errors)
  Scope: M
  Scenarios Satisfied: D2 SC-001, SC-002, SC-004, SC-008, SC-010
  Contracts Implemented: D4 SIDE-002, OUT-004, ERR-002, ERR-004
  Acceptance Criteria:
  1. Create `ledger/serialization.py` with `canonical_event_bytes(event) -> bytes`, `compute_event_hash(event) -> str`, and `event_key(sequence: int) -> str`.
  2. Canonical serialization uses sorted keys, separators `,` and `:`, UTF-8, `ensure_ascii=False`, excludes `hash` from hash input, and includes explicit `null` fields.
  3. At least 6 unit tests assert exact-string hash format, all-zero genesis `previous_hash`, Unicode behavior, null handling, and corruption detection support.

- Phase 1 Core Logic: T-003 Implement the Ledger-owned storage adapter and reconnect-once policy
  Parallel/Serial: Parallel with T-002
  Dependency: T-001 (needs errors and fixtures)
  Scope: M
  Scenarios Satisfied: D2 SC-003, SC-009
  Contracts Implemented: D4 IN-002, IN-003, IN-004, IN-006, OUT-002, OUT-003, OUT-005, SIDE-003, ERR-001
  Acceptance Criteria:
  1. Create `ledger/backend.py` with connection bootstrap, ordered byte reads, append-by-key, and one-second reconnect-once retry behavior.
  2. Connection parameters are read through `platform_sdk` configuration/secrets boundaries, not hardcoded.
  3. Missing database or failed retry raises `LedgerConnectionError`.
  4. At least 5 unit tests cover read failures, reconnect success, reconnect failure, and ordered byte retrieval.

- Phase 2 Ledger Operations: T-004 Implement append with internal sequence assignment and append-only persistence
  Parallel/Serial: Serial
  Dependency: T-002 and T-003 (needs hashing and backend)
  Scope: L
  Scenarios Satisfied: D2 SC-001, SC-002, SC-005, SC-006, SC-007, SC-008, SC-009
  Contracts Implemented: D4 IN-001, OUT-001, SIDE-001, SIDE-002, SIDE-003, ERR-001, ERR-002, ERR-003
  Acceptance Criteria:
  1. Create `ledger/service.py` and implement `Ledger.append(request) -> tuple[int, LedgerEvent]`.
  2. Append assigns sequence `0` on genesis and otherwise uses the current tip plus one with the approved v1 single-writer atomicity assumption.
  3. Caller-supplied sequencing/hash fields are rejected before persistence.
  4. Sequence conflict raises `LedgerSequenceError`; serialization failure raises `LedgerSerializationError`; connection failure raises `LedgerConnectionError`.
  5. At least 7 unit tests cover genesis append, subsequent append linkage, `snapshot_created` persistence, and fail-closed behavior.

- Phase 2 Ledger Operations: T-005 Implement exact read, bounded replay, read-since, and tip queries
  Parallel/Serial: Parallel with T-006
  Dependency: T-004 (needs stored events)
  Scope: M
  Scenarios Satisfied: D2 SC-003, SC-006
  Contracts Implemented: D4 IN-002, IN-003, IN-004, IN-006, OUT-002, OUT-003, OUT-005
  Acceptance Criteria:
  1. `Ledger.read`, `Ledger.read_range`, `Ledger.read_since`, and `Ledger.get_tip` return canonical stored events and ordered results only.
  2. `read_since(-1)` replays from genesis; `read_range(start, end)` preserves ascending sequence order.
  3. At least 5 unit tests cover point read, range replay, snapshot boundary replay, and tip behavior.

- Phase 2 Ledger Operations: T-006 Implement online and offline chain verification with first-break reporting
  Parallel/Serial: Parallel with T-005
  Dependency: T-002 and T-004 (needs canonical bytes and persisted events)
  Scope: M
  Scenarios Satisfied: D2 SC-004, SC-010
  Contracts Implemented: D4 IN-005, OUT-004, SIDE-002, ERR-004
  Acceptance Criteria:
  1. `Ledger.verify_chain` accepts `source_mode` values `online` and `offline_export`.
  2. Verification recomputes hashes from canonical bytes, not from stored hash chaining alone.
  3. Corruption reports `valid=false` and the first failing sequence in `break_at`.
  4. At least 5 unit tests prove parity between online and offline verification and deterministic corruption position reporting.

- Phase 3 Validation: T-007 Add opt-in real immudb integration coverage
  Parallel/Serial: Serial
  Dependency: T-005 and T-006 (needs public surface complete)
  Scope: M
  Scenarios Satisfied: D2 SC-001, SC-002, SC-003, SC-004, SC-009
  Contracts Implemented: D4 IN-001, IN-002, IN-003, IN-004, IN-005, IN-006, OUT-001, OUT-002, OUT-003, OUT-004, OUT-005, SIDE-001, SIDE-003
  Acceptance Criteria:
  1. Create `tests/test_integration_immudb.py` guarded so the default unit suite does not require live immudb.
  2. Integration tests prove append/read/verify/get_tip behavior against a real immudb instance and explicit failure when the `ledger` database is absent.
  3. At least 3 integration tests cover happy path, missing database, and reconnect-once behavior.

- Phase 3 Validation: T-008 Run regression, capture builder evidence, and package the framework artifacts
  Parallel/Serial: Serial
  Dependency: T-007 (needs implementation complete)
  Scope: S
  Scenarios Satisfied: D2 SC-001, SC-002, SC-003, SC-004, SC-005, SC-006, SC-007, SC-008, SC-009, SC-010
  Contracts Implemented: D4 full contract set as verification evidence
  Acceptance Criteria:
  1. Run the full unit suite and any available integration suite with pasted output captured in `RESULTS.md`.
  2. Record file hashes for every created or modified file and note any spec deviations as `NONE` or explicit blockers.
  3. Run full regression across all staged packages in the workspace and record whether new failures were introduced.

## Task Dependency Graph
```text
T-001
  |\
  | +--> T-002 --+
  |              |
  +--> T-003 --+ |
               | |
               v v
               T-004
               /   \
              v     v
            T-005  T-006
               \   /
                v v
                T-007
                  |
                  v
                T-008
```

## Summary
| Task | Phase | Scope | Serial/Parallel | Scenarios |
| T-001 | 0 Foundation | M | Serial | SC-005, SC-006 |
| T-002 | 1 Core Logic | M | Parallel | SC-001, SC-002, SC-004, SC-008, SC-010 |
| T-003 | 1 Core Logic | M | Parallel | SC-003, SC-009 |
| T-004 | 2 Ledger Operations | L | Serial | SC-001, SC-002, SC-005, SC-006, SC-007, SC-008, SC-009 |
| T-005 | 2 Ledger Operations | M | Parallel | SC-003, SC-006 |
| T-006 | 2 Ledger Operations | M | Parallel | SC-004, SC-010 |
| T-007 | 3 Validation | M | Serial | SC-001, SC-002, SC-003, SC-004, SC-009 |
| T-008 | 3 Validation | S | Serial | SC-001, SC-002, SC-003, SC-004, SC-005, SC-006, SC-007, SC-008, SC-009, SC-010 |

Total: 8 tasks, 4 phases, 2 parallelizable pairs, 6 serial waves.
MVP Tasks: T-001, T-002, T-003, T-004, T-005, T-006, T-007, T-008.
