# D8: Tasks — FMWK-001-ledger
Meta: plan:D7 v1.0.0 | status:Draft | total_tasks:12 | parallel_opportunities:5

---

## MVP Scope

**In Scope (all P0 and P1 scenarios):**

| D2 Scenario | Priority | In MVP |
|-------------|----------|--------|
| SC-001 — Append well-formed event | P0 | YES |
| SC-002 — Read event by sequence | P0 | YES |
| SC-003 — Read events since sequence | P0 | YES |
| SC-004 — Verify hash chain integrity | P0 | YES |
| SC-005 — Cold-storage verification (offline) | P0 | YES |
| SC-006 — Genesis event correct sentinel | P0 | YES |
| SC-007 — Sequential hash chain linkage | P0 | YES |
| SC-008 — Snapshot event recording | P1 | YES |
| SC-009 — Get current tip | P1 | YES |
| SC-EC-001 — Corrupted event detected | P0 | YES |
| SC-EC-002 — Concurrent write conflict | P1 | YES |
| SC-EC-003 — Connection lost during append | P1 | YES |
| SC-EC-004 — Connect to non-existent database | P0 | YES |

**Deferred (out of MVP scope):**

| D2 Item | Reason |
|---------|--------|
| DEF-001 — Payload schema validation | Payload schemas for 10 event types are owned by other frameworks; pluggable extension point, not KERNEL-phase blocker |
| DEF-002 — Paginated range read | Not needed for initial Graph reconstruction; added when memory pressure observed |

---

## Tasks

### Phase 0 — Foundation

---

**T-001: Create errors module**
- Phase: 0 — Foundation
- Parallel/Serial: Parallel with T-002, T-003
- Dependency: None
- Scope: S
- Scenarios Satisfied: SC-EC-001, SC-EC-002, SC-EC-003, SC-EC-004 (error classes referenced by all scenarios)
- Contracts Implemented: ERR-001 (LedgerConnectionError), ERR-002 (LedgerCorruptionError), ERR-003 (LedgerSequenceError), ERR-004 (LedgerSerializationError)

Acceptance Criteria:
1. File `staging/FMWK-001-ledger/ledger/errors.py` created.
2. `LedgerConnectionError(code="LEDGER_CONNECTION_ERROR")` defined as a non-retryable exception.
3. `LedgerCorruptionError(code="LEDGER_CORRUPTION_ERROR")` defined with `break_at: int` field.
4. `LedgerSequenceError(code="LEDGER_SEQUENCE_ERROR")` defined.
5. `LedgerSerializationError(code="LEDGER_SERIALIZATION_ERROR")` defined.
6. All four classes inherit from `platform_sdk.tier0_core.errors` base (do not use bare `Exception`).
7. `code` attribute matches the string in D4 Error Code Enum exactly (case-sensitive).

---

**T-002: Create schemas module**
- Phase: 0 — Foundation
- Parallel/Serial: Parallel with T-001, T-003
- Dependency: None
- Scope: M
- Scenarios Satisfied: SC-001, SC-002, SC-008, SC-009 (entity shapes used in all read/write operations)
- Contracts Implemented: D3 E-001, E-003, E-004, E-005, E-006, E-007, E-008, E-009

Acceptance Criteria:
1. File `staging/FMWK-001-ledger/ledger/schemas.py` created.
2. `LedgerEvent` dataclass with fields matching D3 E-001 exactly: `event_id`, `sequence`, `event_type`, `schema_version`, `timestamp`, `provenance`, `previous_hash`, `payload`, `hash`. All required.
3. `provenance` is a nested dataclass with `framework_id`, `pack_id`, `actor` (actor: Literal["system", "operator", "agent"]).
4. `LedgerTip` dataclass with `sequence_number: int` and `hash: str`. Empty-ledger default: `sequence_number=-1, hash=""`.
5. `VerifyChainResult` dataclass with `valid: bool` and `break_at: int | None = None`. Invariant: `break_at` must be absent (None) if `valid=True`; must be present (≥ 0) if `valid=False`.
6. `LedgerConfig` dataclass with fields `host: str`, `port: int`, `database: str`, `username: str`, `password: str`.
7. `LedgerConfig.from_env() -> LedgerConfig` reads `IMMUDB_HOST`, `IMMUDB_PORT`, and `IMMUDB_DATABASE` from environment variables, using `platform_sdk.tier0_core.config.get_config()` only for general platform bootstrap compatibility, and reads credentials via `platform_sdk.tier0_core.secrets.get_secret("immudb_username")` and `get_secret("immudb_password")`.
8. `LedgerConfig.from_env()` defaults: `IMMUDB_HOST="localhost"`, `IMMUDB_PORT=3322`, `IMMUDB_DATABASE="ledger"` if unset.
9. `SnapshotCreatedPayload` dataclass with `snapshot_path: str`, `snapshot_hash: str`, `snapshot_sequence: int`.
10. `NodeCreationPayload` dataclass with `node_id: str`, `node_type: str`, `base_weight: str`, `initial_methylation: str`. (Note: `base_weight` and `initial_methylation` are strings, not floats.)
11. `SessionStartPayload` dataclass with `session_id: str`, `operator_id: str | None`, `user_id: str | None`.
12. `SessionEndPayload` dataclass with `session_id: str`, `end_reason: Literal["operator_disconnect", "user_disconnect", "timeout", "system_shutdown"]`.
13. `PackageInstallPayload` dataclass with `package_id: str`, `package_version: str`, `gate_results: list[GateResult]`, `file_hashes: dict[str, str]`.
14. `EVENT_TYPE_CATALOG: frozenset[str]` containing exactly the 15 event types from D3 E-009. No more, no fewer.
15. Zero float-type fields on any schema (all decimal values are `str`).

---

**T-003: Create canonical serializer**
- Phase: 0 — Foundation
- Parallel/Serial: Parallel with T-001, T-002
- Dependency: None (depends only on stdlib and T-001 for error class)
- Scope: M
- Scenarios Satisfied: SC-001, SC-004, SC-005, SC-006, SC-007 (hash computation used in every append and every verify step)
- Contracts Implemented: E-002 (canonical JSON constraint), SIDE-002 (serialization + hash computation), ERR-004 (float detection trigger)

Acceptance Criteria:
1. File `staging/FMWK-001-ledger/ledger/serializer.py` created.
2. `GENESIS_SENTINEL: str` constant equals exactly `"sha256:0000000000000000000000000000000000000000000000000000000000000000"` (64 zero hex digits, lowercase). Verified by `assert GENESIS_SENTINEL == "sha256:" + "0" * 64`.
3. `canonical_bytes(event: dict) -> bytes` function:
   - Removes the `hash` key before serializing.
   - Calls `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`.
   - Encodes result to UTF-8 bytes with no BOM.
   - Null fields (`None` values) are included as `"key":null`, never omitted.
   - Integer fields are bare digits (no `.0`, no `e` notation).
4. `compute_hash(event: dict) -> str` function:
   - Calls `canonical_bytes(event)` to get input.
   - Calls `hashlib.sha256(bytes).hexdigest()` and prefixes with `"sha256:"`.
   - Result always matches regex `^sha256:[0-9a-f]{64}$`.
5. `check_no_floats(obj: Any) -> None` function:
   - Recursively walks the entire object (dicts at all nesting levels, lists).
   - Raises `LedgerSerializationError` if ANY value is `isinstance(x, float)`.
   - Does NOT raise on `int`, `str`, `bool`, `None`, `dict`, `list`.
6. Test file `staging/FMWK-001-ledger/tests/unit/test_serializer.py` created with exactly 12 tests:
   - `test_canonical_json_excludes_hash_field`: assert `hash` key absent from `canonical_bytes()` input.
   - `test_canonical_json_sorted_keys`: assert keys in output are alphabetically sorted (nested).
   - `test_canonical_json_no_whitespace_between_tokens`: assert no space after `:` or `,`.
   - `test_canonical_json_ensure_ascii_false_literal_utf8`: assert `café` stored as literal `café`, not `\u00e9` escape.
   - `test_canonical_json_null_field_included`: assert `{"k": null}` appears in output when field is None.
   - `test_canonical_json_integer_no_decimal`: assert `{"n": 42}` not `{"n": 42.0}`.
   - `test_hash_format_matches_regex`: assert `compute_hash(event)` matches `^sha256:[0-9a-f]{64}$`.
   - `test_hash_lowercase_hex_only`: assert no uppercase chars in hash output.
   - `test_float_detection_top_level_raises`: assert `check_no_floats({"v": 0.5})` raises `LedgerSerializationError`.
   - `test_float_detection_nested_dict_raises`: assert `check_no_floats({"a": {"b": 0.1}})` raises.
   - `test_float_detection_in_list_raises`: assert `check_no_floats({"a": [0.1, 0.2]})` raises.
   - `test_genesis_sentinel_exact_string`: assert `GENESIS_SENTINEL == "sha256:" + "0" * 64` using exact string comparison (no regex).
7. All 12 tests pass.

---

### Phase 1 — SDK Adapter

---

**T-004: Add immudb adapter to platform_sdk**
- Phase: 1 — SDK Adapter
- Parallel/Serial: Parallel with T-001, T-002, T-003
- Dependency: None (can start with Phase 0 in parallel; ledger.py imports it in Phase 2)
- Scope: L
- Scenarios Satisfied: SC-001, SC-002, SC-003, SC-009 (all storage operations route through this adapter)
- Contracts Implemented: SIDE-001 (immudb write shape — zero-padded key, canonical JSON value), IN-007 connect contract, SIDE-003 (reconnect behavior — 1 second wait, 1 retry)

Acceptance Criteria:
1. Files `staging/FMWK-001-ledger/platform_sdk/tier0_core/data/__init__.py` and `staging/FMWK-001-ledger/platform_sdk/tier0_core/data/immudb_adapter.py` created.
2. `staging/FMWK-001-ledger/platform_sdk/tier0_core/data/__init__.py` re-exports the existing `platform_sdk.tier0_core.data` functionality needed by the staging packet, plus the new immudb adapter symbols. The staging package structure is independent of the live SDK's single-file `data.py` layout.
3. `ImmudbAdapter` Protocol defined with methods: `connect(config: dict) -> None`, `kv_set(key: str, value: bytes) -> None`, `kv_get(key: str) -> bytes`, `kv_scan(start_key: str, end_key: str | None) -> list[tuple[str, bytes]]`, `list_databases() -> list[str]`.
4. `MockImmudbAdapter` class:
   - Stores KV pairs in `dict[str, bytes]`.
   - Tracks all method calls in `self.call_log: list[str]` for assertion in tests.
   - Exposes `set_failure_on_next_write(err: Exception)` for connection-lost simulation.
   - `list_databases()` returns `["ledger"]` by default; supports overriding to `[]` to simulate missing DB.
   - Zero immudb SDK imports.
5. `RealImmudbAdapter` class:
   - Wraps immudb gRPC SDK (`immudb` Python package) — only file permitted to import immudb SDK.
   - Uses zero-padded key format for `kv_set` and `kv_get`: key is exactly the string passed (caller formats key).
   - Reconnect logic (SIDE-003): on gRPC failure, waits exactly 1 second (`time.sleep(1)`), retries once; raises `LedgerConnectionError` if retry also fails.
   - MUST NOT call `CreateDatabaseV2`, `DatabaseDelete`, `DropDatabase`, `CompactIndex`, `TruncateDatabase`, or `CleanIndex` — ever.
   - Credentials loaded via `platform_sdk.tier0_core.secrets.get_secret("immudb_username")` and `get_secret("immudb_password")`.
6. `get_adapter() -> ImmudbAdapter` function selects provider via `PLATFORM_DATA_BACKEND` env var: `"mock"` → `MockImmudbAdapter`, `"immudb"` → `RealImmudbAdapter`.
7. `kv_scan()` returns entries in lexicographic key order (correct for zero-padded sequence keys).
8. No existing live platform_sdk file is modified — the staging `data/` package is additive only.

---

### Phase 2 — Core Ledger

---

**T-005: Implement Ledger.connect()**
- Phase: 2 — Core Ledger
- Parallel/Serial: Serial after T-001, T-002, T-003, T-004
- Dependency: T-001, T-002, T-003, T-004 (all foundation + adapter needed before Ledger class starts)
- Scope: S
- Scenarios Satisfied: SC-EC-004 (missing database), SC-EC-003 (connection failure path)
- Contracts Implemented: IN-007 (connect contract), ERR-001 (LedgerConnectionError on missing DB or unreachable), D1 Article 9 (infrastructure separation)

Acceptance Criteria:
1. File `staging/FMWK-001-ledger/ledger/ledger.py` created with `Ledger` class skeleton.
2. `Ledger.__init__(self)` initializes: `self._adapter = None`, `self._mutex = threading.Lock()`, `self._config = None`.
3. `Ledger.connect(self, config: LedgerConfig) -> None`:
   - `LedgerConfig` is defined in `ledger/schemas.py` and exposes `from_env()` for builder-controlled configuration loading.
   - `LedgerConfig.from_env()` reads `IMMUDB_HOST`, `IMMUDB_PORT`, and `IMMUDB_DATABASE` from environment variables; defaults are `localhost`, `3322`, and `ledger`.
   - `LedgerConfig.from_env()` may call `platform_sdk.tier0_core.config.get_config()` for general platform bootstrap compatibility, but immudb host/port/database are not read from `PlatformConfig` fields because the live SDK does not define them.
   - Reads credentials via `platform_sdk.tier0_core.secrets`.
   - Calls `self._adapter.connect(config)`.
   - Calls `self._adapter.list_databases()` to check `"ledger"` is present.
   - If `"ledger"` is NOT in the returned list, raises `LedgerConnectionError` immediately.
   - MUST NOT call any admin gRPC method to create the database.
   - Logs the connection attempt via `platform_sdk.tier0_core.logging`.
4. Unit tests in `test_ledger_unit.py` for connect (added in this task):
   - `test_connect_raises_on_missing_database`: mock `list_databases()` returns `[]`; assert `LedgerConnectionError` raised.
   - `test_connect_makes_zero_admin_calls`: assert mock `call_log` contains no admin operation strings after failed or successful connect.
5. Both tests pass.

---

**T-006: Implement Ledger.append() and Ledger.get_tip()**
- Phase: 2 — Core Ledger
- Parallel/Serial: Serial after T-005
- Dependency: T-005 (Ledger class and connect must exist)
- Scope: L
- Scenarios Satisfied: SC-001, SC-006, SC-007, SC-008, SC-009, SC-EC-002, SC-EC-003
- Contracts Implemented: IN-001 (append), IN-006 (get_tip), OUT-001 (append return), OUT-004 (get_tip return), SIDE-001 (immudb write), SIDE-002 (serialization + hash), SIDE-003 (reconnect), ERR-001, ERR-003, ERR-004

Acceptance Criteria:
1. `Ledger.get_tip(self) -> LedgerTip`:
   - Calls `self._adapter.kv_scan(start_key="", end_key=None)` and takes the last entry by key order.
   - Returns `LedgerTip(sequence_number=-1, hash="")` if no entries exist.
   - Returns `LedgerTip(sequence_number=N, hash=<event_N.hash>)` from deserializing the last entry.
   - Raises `LedgerConnectionError` if adapter unreachable.
2. `Ledger.append(self, event: dict) -> int`:
   - MUST accept no `sequence`, `previous_hash`, or `hash` parameter — signature is `append(self, event: dict) -> int`.
   - Calls `check_no_floats(event)` first; raises `LedgerSerializationError` if any float found.
   - Validates `event["event_type"]` is in `EVENT_TYPE_CATALOG`; raises `LedgerSerializationError` if not.
   - Acquires `self._mutex` before reading tip.
   - Reads tip via `get_tip()`.
   - Computes `sequence = tip.sequence_number + 1` (works correctly when tip is -1 → sequence = 0).
   - Assigns `event["sequence"] = sequence`.
   - Assigns `event["previous_hash"] = GENESIS_SENTINEL if sequence == 0 else tip.hash`.
   - Computes `event["hash"] = compute_hash(event)`.
   - Calls `self._adapter.kv_set(key=f"{sequence:012d}", value=canonical_json(event).encode("utf-8"))`.
   - Releases mutex after `kv_set` completes.
   - Returns `sequence` as `int`.
   - On gRPC failure: SIDE-003 reconnect (1s wait, 1 retry); if retry fails, raises `LedgerConnectionError`.
   - On sequence conflict (adapter raises sequence error): raises `LedgerSequenceError`.
3. Unit tests in `test_ledger_unit.py` (added in this task):
   - `test_append_returns_sequence_number`: append one event, assert return value is `0`.
   - `test_append_assigns_sequence_internally`: assert returned event (re-read from mock) has `sequence=0`.
   - `test_append_first_event_gets_genesis_previous_hash`: assert `event["previous_hash"] == GENESIS_SENTINEL` using exact string comparison.
   - `test_append_sequential_hash_chain_linkage`: append 5 events; for each pair assert `event[i]["previous_hash"] == event[i-1]["hash"]`; assert sequences are 0,1,2,3,4.
   - `test_append_hash_format_regex`: assert every appended event's `hash` matches `^sha256:[0-9a-f]{64}$`.
   - `test_append_blocks_caller_supplied_sequence_rejected`: call `append(event)` — confirm signature has no `sequence` param (inspect via `inspect.signature`).
   - `test_append_raises_serialization_error_on_float`: pass `{"payload": {"delta": 0.05}, ...}`; assert `LedgerSerializationError`.
   - `test_append_raises_serialization_error_on_invalid_event_type`: pass event with unknown `event_type`; assert `LedgerSerializationError`.
   - `test_append_raises_connection_error_on_immudb_failure`: mock kv_set to raise gRPC error; assert `LedgerConnectionError` after 1 retry.
   - `test_append_sequence_error_on_concurrent_write`: mock adapter raises sequence conflict; assert `LedgerSequenceError`.
   - `test_get_tip_empty_ledger`: no events; assert `LedgerTip(sequence_number=-1, hash="")`.
   - `test_get_tip_after_5_events`: append 5 events; assert tip is `{sequence_number: 4, hash: <hash_of_event_4>}`.
   - `test_get_tip_hash_matches_last_event`: re-read event at tip sequence; assert `tip.hash == event.hash`.
   - `test_get_tip_raises_connection_error_on_adapter_failure`: mock `kv_scan` to raise adapter error; assert `LedgerConnectionError`.
   - `test_snapshot_event_payload_fields_stored`: append `snapshot_created` event with E-005 payload; re-read; assert `snapshot_path`, `snapshot_hash`, `snapshot_sequence` present.
4. All 15 tests pass.

---

**T-007: Implement Ledger read methods**
- Phase: 2 — Core Ledger
- Parallel/Serial: Parallel with T-006 (both depend on T-005; they modify different methods)
- Dependency: T-005
- Scope: M
- Scenarios Satisfied: SC-002, SC-003
- Contracts Implemented: IN-002 (read), IN-003 (read_range), IN-004 (read_since), OUT-002 (event stream)

Acceptance Criteria:
1. `Ledger.read(self, sequence_number: int) -> LedgerEvent`:
   - Calls `self._adapter.kv_get(key=f"{sequence_number:012d}")`.
   - Deserializes and returns the event exactly as stored — no re-serialization or field mutation.
   - Raises `LedgerConnectionError` if adapter unreachable.
   - Raises `LedgerConnectionError` if `sequence_number` is out of range / missing in storage.
2. `Ledger.read_range(self, start: int, end: int) -> list[LedgerEvent]`:
   - Returns events with sequences in `[start, end]` inclusive, strictly ascending.
   - Returns empty list if `start > current_tip.sequence_number`.
   - Raises `LedgerConnectionError` if adapter unreachable.
3. `Ledger.read_since(self, sequence_number: int) -> list[LedgerEvent]`:
   - Returns all events with `sequence > sequence_number`, strictly ascending.
   - Returns empty list if `sequence_number == current_tip.sequence_number`.
   - Raises `LedgerConnectionError` if adapter unreachable.
4. Unit tests in `test_ledger_unit.py` (added in this task):
   - `test_read_returns_exact_stored_event`: write event, read back, assert byte-level equality of all fields.
   - `test_read_range_returns_ascending_order`: write 20 events, read range [5, 15], assert 11 events in order with no gaps.
   - `test_read_range_empty_beyond_tip`: call with start beyond tip; assert empty list returned (not error).
   - `test_read_since_returns_events_after_sequence`: write 20 events, call `read_since(10)`, assert events 11-20 returned in order.
   - `test_read_since_empty_at_tip`: call `read_since(N)` where N == current tip; assert empty list.
   - `test_read_returns_no_mutation`: assert read event fields are identical to written fields including `hash` and `previous_hash`.
   - `test_read_out_of_range_raises`: call `read(999)` on a 5-event ledger; assert `LedgerConnectionError`.
5. All 7 tests pass.

---

**T-008: Implement Ledger.verify_chain()**
- Phase: 2 — Core Ledger
- Parallel/Serial: Parallel with T-006, T-007 (depends only on T-005)
- Dependency: T-005
- Scope: L
- Scenarios Satisfied: SC-004, SC-005, SC-EC-001
- Contracts Implemented: IN-005 (verify_chain), OUT-003 (VerifyChainResult), ERR-002 (LedgerCorruptionError on catastrophic flag)

Acceptance Criteria:
1. `Ledger.verify_chain(self, start: int = 0, end: int | None = None) -> VerifyChainResult`:
   - Reads `end` from tip if not provided.
   - Iterates sequences from `start` to `end` inclusive.
   - For each event: recomputes `expected_hash = compute_hash(event_without_hash_field)`.
   - If `event.hash != expected_hash`: returns `VerifyChainResult(valid=False, break_at=seq)` immediately (stops walk).
   - Verifies `event.previous_hash == GENESIS_SENTINEL` for seq 0, or `== prev_event.hash` for seq > 0.
   - If `previous_hash` link broken: returns `VerifyChainResult(valid=False, break_at=seq)` immediately.
   - Returns `VerifyChainResult(valid=True)` if all events pass.
   - MUST NOT require kernel process, Graph, HO1, HO2, or any cognitive runtime — only the adapter connection.
   - `break_at` field is absent (`None`) when `valid=True` (D3 E-004 invariant).
   - Raises `LedgerConnectionError` if the adapter cannot reach immudb during the chain walk.
2. Unit tests in `test_ledger_unit.py` (added in this task):
   - `test_verify_chain_intact_returns_valid_true`: write 10 events, call `verify_chain()`, assert `{valid: True}` and `break_at` is absent.
   - `test_verify_chain_detects_hash_corruption_at_position_3`: write 6 events in mock, directly corrupt event 3's `hash` field in mock storage, call `verify_chain()`, assert `{valid: False, break_at: 3}`.
   - `test_verify_chain_stops_at_first_break`: corrupt event 3 in 6-event ledger, assert events 4 and 5 were NOT read (check adapter call_log shows no kv_get for keys `000000000004` and `000000000005`).
   - `test_verify_chain_detects_broken_previous_hash_link`: write 5 events, replace `event[2].previous_hash` with wrong value in mock, call `verify_chain()`, assert `{valid: False, break_at: 2}`.
   - `test_verify_chain_valid_true_has_no_break_at`: assert `VerifyChainResult.break_at is None` on success (not `0` or missing key — must be None).
   - `test_verify_chain_raises_connection_error_on_adapter_failure`: mock adapter raises on `kv_get`; assert `LedgerConnectionError`.
3. All 6 tests pass.

---

### Phase 3 — Validation

---

**T-009: Reconnect unit tests**
- Phase: 3 — Validation
- Parallel/Serial: Serial after T-006
- Dependency: T-006 (reconnect behavior is in append(); adapter needed for injection)
- Scope: S
- Scenarios Satisfied: SC-EC-003
- Contracts Implemented: SIDE-003 (reconnect: 1s wait, 1 retry)

Acceptance Criteria:
1. Unit tests in `test_ledger_unit.py` (added in this task):
   - `test_reconnect_waits_one_second_before_retry`: mock adapter raises on first gRPC call; assert `time.sleep(1)` called exactly once (mock or monkeypatch `time.sleep`).
   - `test_reconnect_raises_connection_error_after_one_retry_fails`: mock adapter fails on both attempts; assert `LedgerConnectionError` raised; assert exactly one `sleep(1)` call.
   - `test_reconnect_succeeds_on_second_attempt`: mock adapter fails first, succeeds second; assert append returns successfully; assert `sleep(1)` called once.
2. All 3 tests pass.

---

**T-010: Complete unit test suite (25 total across all test_ledger_unit.py)**
- Phase: 3 — Validation
- Parallel/Serial: Serial after T-005, T-006, T-007, T-008, T-009
- Dependency: T-005 through T-009 (all unit-tested methods must exist)
- Scope: M
- Scenarios Satisfied: All 13 D2 scenarios (P0 and P1) — final verification pass
- Contracts Implemented: All D4 contracts — final audit

Acceptance Criteria:
1. `test_ledger_unit.py` contains the complete set accumulated from T-005 through T-009 tests.
2. Final count: exactly 25 tests minimum in `test_ledger_unit.py`.
   - From T-005: 2 tests (connect tests)
   - From T-006: 15 tests (append + get_tip tests)
   - From T-007: 7 tests (read tests)
   - From T-008: 6 tests (verify_chain tests)
   - From T-009: 3 tests (reconnect tests)
   - Total: 33 tests (exceeds 25 minimum)
3. Combined with `test_serializer.py` (12 tests): 45 unit tests total.
4. All 45 unit tests pass against MockProvider (no Docker required).
5. `pytest tests/unit/ -v` exits with code 0.

---

**T-011: Integration and cold-storage tests**
- Phase: 3 — Validation
- Parallel/Serial: Serial after T-010
- Dependency: T-010 (unit tests must all pass before integration tests written)
- Scope: M
- Scenarios Satisfied: SC-001 through SC-009 (real immudb path), SC-005 (cold-storage path)
- Contracts Implemented: SIDE-001 (real immudb write), IN-007 (real connect), SC-005 full integration

Acceptance Criteria:
1. File `staging/FMWK-001-ledger/tests/integration/test_ledger_integration.py` created with 6 tests:
   - `test_integration_append_and_read_roundtrip`: append 1 event to real immudb, read it back, assert byte-level equality.
   - `test_integration_1000_event_chain_sequential`: write 1000 events, assert sequences are 0-999 with no gaps, assert hashes all match regex.
   - `test_integration_verify_chain_intact_1000_events`: after 1000-event write, call `verify_chain()`, assert `{valid: True}`.
   - `test_integration_read_since_after_20_events`: write 20 events, call `read_since(10)`, assert events 11-20 returned in order, none missing, none duplicated.
   - `test_integration_missing_database_raises_connection_error`: point Ledger at clean immudb (no `ledger` DB), assert `LedgerConnectionError`.
   - `test_integration_get_tip_sequence_matches_append_count`: append 5 events, assert `get_tip().sequence_number == 4`.
2. File `staging/FMWK-001-ledger/tests/integration/test_cold_storage.py` created with 2 tests:
   - `test_cold_verify_chain_without_kernel`: write 10 events with kernel up; stop kernel container; create new Ledger instance connecting directly to immudb on :3322; call `verify_chain()`; assert `{valid: True}`.
   - `test_cold_verify_chain_matches_online_result`: run verify online (kernel up), then offline (kernel stopped); assert both results are identical.
3. Integration tests require Docker Compose `ledger` service on :3322.
4. Integration tests are skipped (not failed) if `PLATFORM_DATA_BACKEND=mock` is set.
5. All 8 integration tests pass against Docker immudb.

---

**T-012: Static analysis gate**
- Phase: 3 — Validation
- Parallel/Serial: Parallel with T-011
- Dependency: T-010 (all code must exist before static analysis)
- Scope: S
- Scenarios Satisfied: D1 Article 2 (no cross-framework imports), D1 Article 4 (no admin ops), D1 Article 7 (no direct immudb imports outside adapter)
- Contracts Implemented: D1 NEVER boundaries as build gates

Acceptance Criteria:
1. File `staging/FMWK-001-ledger/scripts/static_analysis.sh` created with four grep checks (see below). All checks exit 0 on pass, non-zero on violation.
2. Check 1 — No direct immudb imports outside adapter file:
   ```bash
   grep -r "import immudb\|from immudb" ledger/ --include="*.py"
   # Expected: zero output
   ```
3. Check 2 — No immudb admin operations anywhere in FMWK-001 code:
   ```bash
   grep -r "DatabaseDelete\|DropDatabase\|CompactIndex\|TruncateDatabase\|CleanIndex" ledger/ platform_sdk/tier0_core/data/__init__.py --include="*.py"
   # Expected: zero output
   ```
4. Check 3 — append() signature contains no `sequence` parameter:
   ```bash
   grep "def append" ledger/ledger.py | grep -v "sequence"
   # Expected: one line output matching "def append(self, event: dict) -> int"
   ```
5. Check 4 — No base schema field definitions outside schemas.py:
   ```bash
   grep -r "\"event_id\"\|\"previous_hash\"\|\"sequence\"\|\"schema_version\"" ledger/ --include="*.py" | grep -v "schemas.py\|test_"
   # Expected: zero output (string literals in non-schema non-test files)
   ```
6. Script runs in CI (`bash staging/FMWK-001-ledger/scripts/static_analysis.sh`), exits 0 with message "Static analysis: ALL CHECKS PASSED".
7. Script is documented: failing any check prints the violation and exits non-zero.

---

## Task Dependency Graph

```
Phase 0 (Foundation)
─────────────────────
T-001 (errors) ──────────────────────────────────────────────────────┐
T-002 (schemas) ─────────────────────────────────────────────────────┤
T-003 (serializer) ──────────────────────────────────────────────────┤
T-004 (immudb adapter) ──────────────────────────────────────────────┤
  [All 4 run in parallel]                                            │
                                                                     ▼
Phase 2 (Core Ledger)                                        T-005 (connect)
─────────────────────                                               │
T-005 ──────────────────────┬──────────────────┬────────────────────┘
                             │                  │
                             ▼                  ▼                   ▼
                    T-006 (append)     T-007 (read)        T-008 (verify)
                    [serial after T-005] [parallel w/T-006] [parallel w/T-006]
                             │
                             ▼
                    T-009 (reconnect)
                    [serial after T-006]

Phase 3 (Validation)
─────────────────────
T-006 + T-007 + T-008 + T-009 ──→ T-010 (complete unit test suite)
                                              │
                                    ┌─────────┴─────────┐
                                    ▼                   ▼
                             T-011 (integration)  T-012 (static analysis)
                             [parallel]           [parallel]
```

**Serial waves:**
- Wave 1: T-001, T-002, T-003, T-004 (4 parallel)
- Wave 2: T-005 (1, serial after Wave 1)
- Wave 3: T-006, T-007, T-008 (3 parallel, after T-005)
- Wave 4: T-009 (1, serial after T-006)
- Wave 5: T-010 (1, serial after T-006, T-007, T-008, T-009)
- Wave 6: T-011, T-012 (2 parallel, after T-010)

---

## Summary

| Task | Phase | Scope | Serial/Parallel | Scenarios |
|------|-------|-------|-----------------|-----------|
| T-001: errors module | 0 | S | Parallel (w/ T-002, T-003, T-004) | SC-EC-001..004 |
| T-002: schemas module | 0 | M | Parallel (w/ T-001, T-003, T-004) | SC-001, SC-002, SC-008, SC-009 |
| T-003: canonical serializer | 0 | M | Parallel (w/ T-001, T-002, T-004) | SC-001, SC-004..007 |
| T-004: immudb adapter (platform_sdk) | 1 | L | Parallel (w/ T-001..003) | SC-001..003, SC-009 |
| T-005: Ledger.connect() | 2 | S | Serial (after Wave 1) | SC-EC-004 |
| T-006: Ledger.append() + get_tip() | 2 | L | Serial (after T-005) | SC-001, SC-006..009, SC-EC-002..003 |
| T-007: Ledger read methods | 2 | M | Parallel (w/ T-006) | SC-002, SC-003 |
| T-008: Ledger.verify_chain() | 2 | L | Parallel (w/ T-006, T-007) | SC-004, SC-005, SC-EC-001 |
| T-009: Reconnect unit tests | 3 | S | Serial (after T-006) | SC-EC-003 |
| T-010: Complete unit test suite | 3 | M | Serial (after T-006..009) | All 13 D2 scenarios |
| T-011: Integration + cold-storage tests | 3 | M | Parallel (w/ T-012) | SC-001..009, SC-005 |
| T-012: Static analysis gate | 3 | S | Parallel (w/ T-011) | D1 Articles 2, 4, 7 |

**Total: 12 tasks | 4 phases | 5 parallelizable pairs | 6 serial waves**

**MVP Tasks (all required — no deferrals):** T-001 through T-012.

**Test count: 45 unit + 8 integration = 53 tests minimum.**
