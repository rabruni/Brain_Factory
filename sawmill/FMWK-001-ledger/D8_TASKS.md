# D8: Tasks — Ledger (FMWK-001)
Meta: plan: D7 v1.0.0 | status:Final | total tasks:12 | parallel opportunities:4

---

## MVP Scope

All 11 D2 scenarios are in scope for this build. No scenarios are deferred.

| D2 Scenario | Priority | Scope |
|------------|----------|-------|
| SC-001 — Append genesis event | P0 (blocker) | IN |
| SC-002 — Append chain continuation | P0 (blocker) | IN |
| SC-003 — Read by sequence number | P0 (blocker) | IN |
| SC-006 — Get tip | P0 (blocker) | IN |
| SC-007 — Verify intact chain | P0 (blocker) | IN |
| SC-008 — Detect corruption | P0 (blocker) | IN |
| SC-009 — Offline cold-storage verify | P0 (blocker) | IN |
| SC-010 — immudb unreachable on append | P1 (must) | IN |
| SC-004 — Read range | P1 (must) | IN |
| SC-005 — Read since | P1 (must) | IN |
| SC-011 — Concurrent append (design violation) | P1 (must) | IN |

Deferred: DEF-001 (snapshot file format — FMWK-005), DEF-002 (non-Ledger payload schemas), DEF-003 (read performance optimization). None affect this build.

---

## Tasks (T-### IDs, phased)

Phases: 0=Foundation, 1=Store+Verify, 2=API Layer, 3=Integration+CLI

---

### Phase 0 — Foundation

#### T-001 — Error classes

- Parallel/Serial: Serial (first task, no deps)
- Dependency: None
- Scope: S
- Scenarios Satisfied: Precondition for all error-raising scenarios (SC-010, SC-011, all validation scenarios)
- Contracts Implemented: ERR-001, ERR-002, ERR-003, ERR-004
- Acceptance Criteria:
  1. `ledger/errors.py` exists with exactly 4 classes: `LedgerConnectionError`, `LedgerCorruptionError`, `LedgerSequenceError`, `LedgerSerializationError`
  2. All four subclass `Exception`
  3. Each carries a `code` attribute matching the D4 Error Code Enum values: `LEDGER_CONNECTION_ERROR`, `LEDGER_CORRUPTION_ERROR`, `LEDGER_SEQUENCE_ERROR`, `LEDGER_SERIALIZATION_ERROR`
  4. Each carries a `message` attribute (str)
  5. All four importable: `from ledger.errors import LedgerConnectionError` succeeds with no dependencies on platform_sdk or immudb
  6. Test file `tests/test_errors.py` (or errors section of another test file) exists with ≥4 test methods — one per class verifying instantiation, `code` attribute, `message` attribute, and `isinstance(e, Exception)` check

---

#### T-002 — Data models

- Parallel/Serial: Serial (after T-001)
- Dependency: T-001 (errors must exist for import consistency)
- Scope: S
- Scenarios Satisfied: SC-001, SC-002, SC-003, SC-006 (entity shapes used by all methods)
- Contracts Implemented: D3 E-001, E-002, E-003, E-004; D3 EventType enum
- Acceptance Criteria:
  1. `ledger/models.py` exists with `@dataclass` definitions for: `LedgerEvent`, `Provenance`, `TipRecord`, `ChainVerificationResult`, and `EventType` enum
  2. `LedgerEvent` has all 9 fields per D3 E-001: `event_id: str`, `sequence: int`, `event_type: str`, `schema_version: str`, `timestamp: str`, `provenance: Provenance`, `previous_hash: str`, `payload: dict`, `hash: str`
  3. `Provenance` has: `framework_id: str`, `pack_id: Optional[str]`, `actor: str`
  4. `TipRecord` has: `sequence_number: int`, `hash: str`
  5. `ChainVerificationResult` has: `valid: bool`, `break_at: Optional[int]`
  6. `EventType` enum has exactly 15 values from D3: `node_creation`, `signal_delta`, `methylation_delta`, `suppression`, `unsuppression`, `mode_change`, `consolidation`, `work_order_transition`, `intent_transition`, `session_start`, `session_end`, `package_install`, `package_uninstall`, `framework_install`, `snapshot_created`
  7. Each model instantiates correctly from the D3 JSON examples (verify in tests)
  8. Test file contains ≥6 test methods: all fields present in each model, EventType iteration returns 15 values, correct Optional typing for nullable fields

---

#### T-003 — Canonical JSON + SHA-256

- Parallel/Serial: Parallel with T-002 (no shared dependency — stdlib only)
- Dependency: None
- Scope: S
- Scenarios Satisfied: SC-001, SC-002 (hash computation on append); SC-007, SC-008 (hash recomputation on verify)
- Contracts Implemented: D3 Canonical JSON Serialization Constraint, D4 SIDE-002
- Acceptance Criteria:
  1. `ledger/serialization.py` exists with `canonical_json(event_dict: dict) -> str` and `canonical_hash(event_dict: dict) -> str`
  2. `canonical_json`: applies `json.dumps` with `sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=False`; does NOT exclude the `hash` field (that is `canonical_hash`'s concern)
  3. `canonical_hash`: builds dict excluding the `hash` key, calls `canonical_json`, encodes UTF-8, SHA-256 digests, returns `"sha256:" + hexdigest` in lowercase
  4. Test vector: given a fully-specified event dict (all fields set to known values, `hash` field omitted), `canonical_hash()` returns a pre-computed hardcoded expected value
  5. Test: modifying ANY field in the event dict changes the hash
  6. Test: the `hash` field is excluded — adding/changing `hash` key in the dict does NOT change `canonical_hash` output
  7. Test: float as string `"0.1"` hashes differently than float as number `0.1` — string variant matches the canonical representation
  8. Test: null fields are included (`{"field": null}`) — omitting them produces a different hash
  9. Test: nested object keys are also sorted (e.g. `provenance` subfields appear alphabetically)
  10. Test: output contains no spaces or newlines
  11. `tests/test_serialization.py` exists with ≥8 test methods

---

#### T-004 — Field validators

- Parallel/Serial: Serial (after T-002 — needs models and EventType enum)
- Dependency: T-002 (needs EventType enum)
- Scope: S
- Scenarios Satisfied: SC-001, SC-002 (validation required before append); D1 Article 6 enforcement
- Contracts Implemented: D4 IN-001 constraints, D1 Article 6
- Acceptance Criteria:
  1. `ledger/schemas.py` exists with `validate_event_data(event_data: dict) -> None`
  2. Raises `LedgerSerializationError` if `event_type` is missing
  3. Raises `LedgerSerializationError` if `event_type` is not a valid `EventType` enum value
  4. Raises `LedgerSerializationError` if `schema_version` is missing
  5. Raises `LedgerSerializationError` if `timestamp` is missing
  6. Raises `LedgerSerializationError` if `provenance` is missing
  7. Raises `LedgerSerializationError` if `provenance.framework_id` is missing or empty
  8. Raises `LedgerSerializationError` if `provenance.actor` is not one of: `"system"`, `"operator"`, `"agent"`
  9. Raises `LedgerSerializationError` if `payload` is present but is not JSON-serializable (e.g. contains a Python object that cannot be serialized)
  10. Does NOT raise if `provenance.pack_id` is absent (optional field per D3 E-002)
  11. Does NOT validate payload field content — opaque payload policy (D1 Article 5, D2 NOT section)
  12. `tests/test_schemas.py` (or schemas section) exists with ≥8 test methods: one per validation rule, plus one valid-event-passes test

---

### Phase 1 — Store + Verify

#### T-005 — ImmudbStore

- Parallel/Serial: Serial (after Phase 0 complete)
- Dependency: T-001, T-002, T-003 (errors, models, serialization must exist before testing)
- Scope: M
- Scenarios Satisfied: SC-001, SC-002 (write path); SC-003, SC-004, SC-005 (read path); SC-010 (connection failure); SC-011 (mutex discipline)
- Contracts Implemented: D4 SIDE-001, ERR-001, D5 RQ-001 (mutex), D5 RQ-005 (retry policy), D6 CLR-001 (fail-fast if DB absent)
- Acceptance Criteria:
  1. `ledger/store.py` exists with `ImmudbStore` class
  2. `__init__(self, config: PlatformConfig)` stores config; does NOT connect; does NOT import immudb directly
  3. `connect()` uses `platform_sdk.tier0_core.data` to establish connection; raises `LedgerConnectionError` if database `"ledger"` does not exist (CLR-001); WHY: prevents race condition if multiple processes start simultaneously before DB is provisioned
  4. `set(key: str, value: bytes) -> None` acquires `self._lock`, writes to immudb; on gRPC failure: releases lock, closes connection, waits 1 second (`time.sleep(1)`), reconnects once, retries once; if retry fails, raises `LedgerConnectionError` and releases lock; WHY: in-process mutex prevents sequence forks (D5 RQ-001 single-writer assumption)
  5. `get(key: str) -> bytes` retrieves from immudb; raises `LedgerConnectionError` if immudb unreachable; raises `LedgerSequenceError` if key not found (sequence out of range)
  6. `scan(start_key: str, end_key: str) -> list[bytes]` retrieves ordered range; returns events in ascending key order; empty list if range is empty
  7. `get_count() -> int` returns number of stored keys (used to determine if Ledger is empty)
  8. `self._lock: threading.Lock` is an in-process mutex initialized in `__init__`
  9. All tests use `PLATFORM_ENVIRONMENT=test` (MockProvider); zero live immudb connections in unit tests
  10. Test: `connect()` with mock "DB does not exist" → `LedgerConnectionError`
  11. Test: simulated connection failure in `set()` → `LedgerConnectionError`; `get_count()` unchanged after failure
  12. Test: mock `set()` that fails first attempt, succeeds on retry → no error raised
  13. Test: mock `set()` that fails both attempts → `LedgerConnectionError`
  14. `tests/test_store.py` exists with ≥10 test methods

---

#### T-006 — Chain verification walker

- Parallel/Serial: Parallel with T-005 (no shared dependency after Phase 0)
- Dependency: T-002, T-003 (models and serialization)
- Scope: S
- Scenarios Satisfied: SC-007, SC-008, SC-009
- Contracts Implemented: D4 IN-005 (walk algorithm), OUT-005, D1 Articles 7 and 8
- Acceptance Criteria:
  1. `ledger/verify.py` exists with `walk_chain(events: list[LedgerEvent]) -> ChainVerificationResult`
  2. Empty list input → `ChainVerificationResult(valid=True, break_at=None)`
  3. Single intact event (genesis: previous_hash = sha256+64zeros, hash = canonical_hash of event) → `valid=True`
  4. Multi-event intact chain (each event's previous_hash = prior event's hash) → `valid=True, break_at=None`
  5. Event at position N has wrong stored hash → `valid=False, break_at=events[N].sequence`
  6. Event at position N has wrong previous_hash link → `valid=False, break_at=events[N].sequence`
  7. Returns the LOWEST sequence number with failure — if events 2 and 5 both fail, `break_at=2`; WHY: identifies the earliest corruption point per D4 IN-005 postcondition #4
  8. Pure function: does NOT call immudb or platform_sdk; operates only on the events list passed to it
  9. `tests/test_verify.py` exists with ≥8 test methods

---

### Phase 2 — API Layer (DTT per method)

#### T-007 — LedgerClient.get_tip()

- Parallel/Serial: Serial (after Phase 1 — first API method, establishes LedgerClient skeleton)
- Dependency: T-005 (ImmudbStore must exist)
- Scope: S
- Scenarios Satisfied: SC-006
- Contracts Implemented: D4 IN-006, OUT-004, ERR-001
- Acceptance Criteria:
  1. `ledger/api.py` exists with `LedgerClient` class skeleton + `connect()` + `get_tip()` methods
  2. `get_tip()` on empty Ledger returns `TipRecord(sequence_number=-1, hash="sha256:0000000000000000000000000000000000000000000000000000000000000000")`; WHY: Write Path uses `tip.sequence_number + 1` to compute genesis sequence=0 without a special case (D6 CLR-002)
  3. `get_tip()` on non-empty Ledger returns `TipRecord(sequence_number=N, hash=<stored_hash_of_event_at_N>)`
  4. Returned `hash` equals the hash field of the stored event — NOT recomputed
  5. `get_tip()` when immudb unreachable → raises `LedgerConnectionError`
  6. Test: empty Ledger → `TipRecord(sequence_number=-1, hash="sha256:"+64zeros)`
  7. Test: after appending 5 events → `sequence_number=4, hash=<last_event_hash>`
  8. Test: connection failure → `LedgerConnectionError`
  9. `tests/test_api.py` exists with ≥4 test methods for `get_tip()`

---

#### T-008 — LedgerClient.append()

- Parallel/Serial: Serial (after T-007 — get_tip must work; append depends on it)
- Dependency: T-007 (get_tip), T-003 (serialization), T-004 (validation), T-005 (store)
- Scope: M
- Scenarios Satisfied: SC-001, SC-002, SC-010, SC-011
- Contracts Implemented: D4 IN-001, OUT-001, SIDE-001, SIDE-002, ERR-001, ERR-003, ERR-004
- Acceptance Criteria:
  1. `append(event_data: dict) -> int` on `LedgerClient`
  2. Calls `validate_event_data(event_data)` first; raises `LedgerSerializationError` on invalid input before any storage read; WHY: reject malformed events before acquiring the lock
  3. Acquires `store._lock` before reading tip; reads tip via `get_tip()`; computes `sequence = tip.sequence_number + 1`; WHY: atomic read-tip + write prevents sequence forks (D5 RQ-001)
  4. Assigns `event_id` via `platform_sdk.tier0_core.ids` (UUID v7 format); WHY: platform_sdk contract — no raw uuid imports
  5. Sets `previous_hash = tip.hash`
  6. Builds full event dict with all fields; computes `hash = canonical_hash(event_dict_without_hash)` via `serialization.py`
  7. Serializes full event (including `hash`) to canonical JSON bytes and writes to store
  8. Returns integer `sequence_number`
  9. SC-001: genesis event has `sequence=0`, `previous_hash="sha256:"+64zeros`, `hash` computed correctly; subsequent `get_tip()` returns `{0, event_hash}`
  10. SC-002: `event[N].previous_hash == event[N-1].hash` for N=1..4 in a 5-event sequence
  11. SC-010: immudb unreachable → `LedgerConnectionError`; `get_tip()` unchanged after failure (no partial write)
  12. SC-011: concurrent append via threading → exactly one success, one `LedgerSequenceError`; `get_tip().sequence_number` incremented by exactly 1 (no fork)
  13. Serialization failure → `LedgerSerializationError`; Ledger state unchanged
  14. `tests/test_api.py` contains ≥10 test methods for `append()`

---

#### T-009 — LedgerClient.read(), read_range(), read_since()

- Parallel/Serial: Serial (after T-007 — LedgerClient skeleton exists)
- Dependency: T-007 (LedgerClient structure), T-005 (store)
- Scope: M
- Scenarios Satisfied: SC-003, SC-004, SC-005
- Contracts Implemented: D4 IN-002, IN-003, IN-004, OUT-002, OUT-003, ERR-001, ERR-003
- Acceptance Criteria:
  1. `read(sequence_number: int) -> LedgerEvent` on `LedgerClient`
  2. `read(N)` where N ≤ tip: returns complete `LedgerEvent` with all 9 fields as stored; `hash` field equals stored value (not recomputed)
  3. `read(N)` where N > tip: raises `LedgerSequenceError`
  4. `read(-1)` (negative): raises `LedgerSequenceError`
  5. `read_range(start: int, end: int) -> list[LedgerEvent]` on `LedgerClient`
  6. `read_range(3, 7)` returns exactly 5 events at sequences [3, 4, 5, 6, 7] in ascending order; WHY: inclusive both bounds per D6 CLR-004
  7. `read_range(N, N)` returns a list containing exactly one event (equivalent to `[read(N)]`)
  8. `read_range(start, end)` where `end > tip`: raises `LedgerSequenceError`
  9. `read_range(start, end)` where `start > tip`: raises `LedgerSequenceError`
  10. `read_since(sequence_number: int) -> list[LedgerEvent]` on `LedgerClient`
  11. `read_since(5)` with tip at 10 returns events at sequences [6, 7, 8, 9, 10] in ascending order (exclusive lower bound: returns events with sequence > N)
  12. `read_since(tip)` returns `[]` (nothing new)
  13. `read_since(N)` where N > tip: raises `LedgerSequenceError`
  14. immudb unreachable for any of the three methods: raises `LedgerConnectionError`
  15. `tests/test_api.py` contains ≥12 test methods for the three read methods combined

---

#### T-010 — LedgerClient.verify_chain()

- Parallel/Serial: Serial (after T-009 — uses `read_range` internally)
- Dependency: T-009 (read_range), T-006 (walk_chain), T-005 (store)
- Scope: S
- Scenarios Satisfied: SC-007, SC-008, SC-009
- Contracts Implemented: D4 IN-005, OUT-005, ERR-001, ERR-002
- Acceptance Criteria:
  1. `verify_chain(start: int = 0, end: int | None = None) -> ChainVerificationResult` on `LedgerClient`
  2. Default args: `start=0`, `end=tip.sequence_number`
  3. Intact chain: returns `ChainVerificationResult(valid=True, break_at=None)`
  4. Corruption at sequence 3: returns `ChainVerificationResult(valid=False, break_at=3)`
  5. Delegates chain walking to `verify.walk_chain(events)` (does not re-implement the walk logic)
  6. immudb unreachable: raises `LedgerConnectionError`; WHY: unreachable immudb is an infrastructure failure, NOT a corruption result — per D4 IN-005 postcondition #6
  7. Empty Ledger (tip.sequence_number = -1): returns `ChainVerificationResult(valid=True, break_at=None)` without attempting reads
  8. Single event: verifies genesis event correctly (previous_hash = sha256+64zeros, hash correct)
  9. SC-009: `verify_chain()` produces the same result whether called from `LedgerClient` or from the CLI tool (test via mock CLI invocation)
  10. `tests/test_api.py` contains ≥8 test methods for `verify_chain()`

---

### Phase 3 — Integration + CLI

#### T-011 — Package assembly + full test regression

- Parallel/Serial: Serial (after all Phase 2 tasks complete)
- Dependency: T-007, T-008, T-009, T-010 (all 6 API methods complete)
- Scope: S
- Scenarios Satisfied: All (integration validation)
- Contracts Implemented: All
- Acceptance Criteria:
  1. `ledger/__init__.py` exports all public symbols: `LedgerClient`, `LedgerEvent`, `Provenance`, `TipRecord`, `ChainVerificationResult`, `EventType`, `LedgerConnectionError`, `LedgerCorruptionError`, `LedgerSequenceError`, `LedgerSerializationError`
  2. `from ledger import LedgerClient` works with no import errors
  3. `tests/conftest.py` provides fixtures: `mock_config`, `mock_ledger_client` (connected to MockProvider), `sample_node_creation_event` (valid dict), `sample_session_start_event` (valid dict)
  4. `conftest.py` sets `PLATFORM_ENVIRONMENT=test` via env var or `pytest` fixture to activate MockProvider
  5. `pytest tests/ --collect-only` shows test methods covering all 11 D2 scenarios (SC-001 through SC-011)
  6. `PLATFORM_ENVIRONMENT=test pytest tests/ -v` — all tests pass; zero failures; zero errors
  7. Total test count ≥ 55 (mandatory minimum for 6+ source files per BUILDER_HANDOFF_STANDARD)
  8. RESULTS.md written to `sawmill/FMWK-001-ledger/RESULTS.md` with full test output pasted

---

#### T-012 — CLI entry point (cold-storage verifier)

- Parallel/Serial: Parallel with T-011 (no shared dependency on assembly)
- Dependency: T-010 (verify_chain), T-007 (get_tip)
- Scope: S
- Scenarios Satisfied: SC-009 (cold-storage verifiability, D1 Article 8)
- Contracts Implemented: D4 IN-005 postcondition #7, D1 Article 8
- Acceptance Criteria:
  1. `ledger/__main__.py` exists: `python -m ledger --verify` connects to immudb directly using `platform_sdk.tier0_core.config` (no hardcoded host/port); WHY: cold-storage verification must work with no kernel process running (D1 Article 8)
  2. Output to stdout: `{"valid": true|false, "break_at": null|N, "tip": {"sequence_number": N, "hash": "sha256:..."}}`
  3. Exit code `0` if chain is valid; exit code `1` if chain is invalid or connection error
  4. Reads connection parameters from `platform_sdk.tier0_core.config` (default: localhost:3322)
  5. No kernel process required — connects directly to immudb
  6. Test: mock CLI test asserts output format and exit code on intact chain
  7. Test: mock CLI test asserts exit code 1 on connection error
  8. Tests use MockProvider only

---

## Task Dependency Graph

```
Phase 0 (Foundation):
  T-001 (errors) ──────────────────────────┐
  T-003 (serial) ──────────────────────────┤ (parallel, no deps)
  T-002 (models) ← T-001                   │
  T-004 (schemas) ← T-002                  │
                                           │ all Phase 0 complete
Phase 1 (Store + Verify):                  │
  T-005 (ImmudbStore) ← T-001,T-002,T-003 ─┤
  T-006 (walk_chain)  ← T-002,T-003 ───────┤ (T-005 ‖ T-006 parallel)
                                           │ all Phase 1 complete
Phase 2 (API Layer — serial):              │
  T-007 (get_tip)      ← T-005 ───────────┘
  T-008 (append)       ← T-007,T-003,T-004,T-005
  T-009 (read*)        ← T-007,T-005
  T-010 (verify_chain) ← T-009,T-006,T-005
                                           │ all Phase 2 complete
Phase 3 (Integration + CLI):               │
  T-011 (assembly)  ← all Phase 2 ─────────┤ (T-011 ‖ T-012 parallel)
  T-012 (CLI)       ← T-010,T-007 ─────────┘
```

---

## Summary

| Task | Phase | Scope | Serial/Parallel | Scenarios |
|------|-------|-------|----------------|-----------|
| T-001 Error classes | 0 | S | Serial | ERR-001..004 |
| T-002 Data models | 0 | S | Serial (after T-001) | SC-001,002,003,006 |
| T-003 Canonical JSON | 0 | S | Parallel with T-002 | SC-001,002,007,008 |
| T-004 Field validators | 0 | S | Serial (after T-002) | SC-001,002 |
| T-005 ImmudbStore | 1 | M | Serial (after Phase 0) | SC-001,002,003,004,005,010,011 |
| T-006 walk_chain | 1 | S | Parallel with T-005 | SC-007,008,009 |
| T-007 get_tip() | 2 | S | Serial (after Phase 1) | SC-006 |
| T-008 append() | 2 | M | Serial (after T-007) | SC-001,002,010,011 |
| T-009 read*() | 2 | M | Serial (after T-007) | SC-003,004,005 |
| T-010 verify_chain() | 2 | S | Serial (after T-009) | SC-007,008,009 |
| T-011 Package assembly | 3 | S | Serial (after Phase 2) | All |
| T-012 CLI verifier | 3 | S | Parallel with T-011 | SC-009 |

**Total: 12 tasks, 4 phases, 4 parallelizable pairs (T-002/T-003, T-005/T-006, T-008/T-009, T-011/T-012), 4 serial waves.**
MVP Tasks: T-001 through T-012 (all in scope — no task is post-MVP).
