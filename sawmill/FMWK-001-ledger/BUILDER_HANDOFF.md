# Builder Handoff — H-1
Handoff ID: H-1 | Framework: FMWK-001-ledger | Prompt Contract Version: 1.0.0
Agent: H-1 — Build the append-only hash-chained event store (Ledger) for DoPeJarMo

---

## 1. Mission

You are building FMWK-001-ledger, the append-only hash-chained event store that is the sole source
of truth for DoPeJarMo. Every state mutation in the system is recorded here as an immutable,
sequenced, SHA-256-linked event. Your deliverable has three parts: (1) an immudb adapter added to
`platform_sdk.tier0_core.data` that wraps immudb behind a Protocol + MockProvider + RealProvider
pattern; (2) the Ledger class in `staging/FMWK-001-ledger/ledger/` implementing seven methods
(connect, append, read, read_range, read_since, get_tip, verify_chain) with full error handling
and mutex-based append atomicity; (3) 53 tests (45 unit via MockProvider, 8 integration via Docker
immudb) that fully cover all 13 D2 scenarios including cold-storage verification (SC-005: kernel
stopped, CLI connects directly to immudb). Nothing goes to the governed filesystem — all work
stays in `staging/FMWK-001-ledger/`.

---

## 2. Critical Constraints

1. **Staging only.** ALL work in `staging/FMWK-001-ledger/` (relative to Brain_Factory repo root). NEVER write to the governed filesystem during authoring. The governed filesystem is populated by GENESIS, not by this build. The existing platform_sdk is at `/Users/raymondbruni/dopejar/platform_sdk/`. Import from there. Do not stub it.
2. **DTT per behavior.** For every acceptance criterion in D8: write the failing test first, implement the behavior, confirm the test passes. No behavior ships without a test.
3. **No hardcoding.** immudb host, port, database, and credentials are config/secret driven. Define `LedgerConfig` in `ledger/schemas.py`; `LedgerConfig.from_env()` reads `IMMUDB_HOST`, `IMMUDB_PORT`, and `IMMUDB_DATABASE`, and reads credentials via `platform_sdk.tier0_core.secrets`. The only hardcoded value permitted is the 1-second reconnect delay (specified in SOURCE_MATERIAL.md as non-configurable).
4. **No file replacement.** The immudb adapter is a NEW file added to platform_sdk — no existing platform_sdk file is modified or replaced.
5. **Deterministic archives.** When building the deliverable archive, use Python `zipfile` or `tarfile` with fixed-order file enumeration. NEVER use `shell tar` (non-deterministic on macOS).
6. **SHA-256 hashes in results file.** Every file listed in the results file must have a `sha256:<64hex>` hash. Compute with `hashlib.sha256(open(f,'rb').read()).hexdigest()` and prefix `"sha256:"`.
7. **Full regression, ALL packages.** Run `python3 -m pytest tests/ -v --tb=short` from `staging/FMWK-001-ledger/`. Report total/passed/failed/skipped. Zero failures permitted.
8. **Results file mandatory.** Write `sawmill/FMWK-001-ledger/RESULTS.md` with all required sections per BUILDER_HANDOFF_STANDARD.md before this handoff is complete.
9. **Mock in unit tests, never real immudb.** Unit tests use `MockImmudbAdapter`. `PLATFORM_DATA_BACKEND=mock` env var selects it. Integration tests use `PLATFORM_DATA_BACKEND=immudb` and Docker.
10. **Environment bootstrap required.** From `staging/FMWK-001-ledger/`, run `export PYTHONPATH=/Users/raymondbruni/dopejar:$PYTHONPATH` before invoking Python so `import platform_sdk` resolves from the staging directory.

## Prerequisites

- Python 3.12+ is required.
- Install Python 3.12 with `brew install python@3.12`.
- Docker and `docker-compose` must be available.
- Export `PYTHONPATH=/Users/raymondbruni/dopejar:$PYTHONPATH` before running any Python commands from `staging/FMWK-001-ledger/`.
10. **Baseline snapshot.** Record the full list of packages installed and total test count in the results file baseline snapshot section.
11. **Zero admin ops.** No call to `DatabaseDelete`, `DropDatabase`, `CompactIndex`, `TruncateDatabase`, `CleanIndex`, or any immudb method that modifies or deletes existing data — anywhere in FMWK-001 code. Static analysis gate must catch any violation.
12. **No float-type values.** `check_no_floats()` must be called before any `json.dumps()` in `append()`. A Python `float` anywhere in the event dict is a `LedgerSerializationError`.

---

## 3. Architecture / Design

### Component Map

```
staging/FMWK-001-ledger/
│
├── ledger/errors.py          ── 4 error classes (ERR-001..004)
├── ledger/schemas.py         ── E-001..E-009: dataclasses + EVENT_TYPE_CATALOG
├── ledger/serializer.py      ── compute_hash(), check_no_floats(), GENESIS_SENTINEL
├── ledger/ledger.py          ── Ledger class (7 public methods)
├── ledger/__init__.py        ── exports
│
├── platform_sdk/tier0_core/data/__init__.py
│                             ── staging-only package shim re-exporting existing
│                             ── `platform_sdk.tier0_core.data` behavior plus immudb adapter
├── platform_sdk/tier0_core/data/immudb_adapter.py
│                             ── ImmudbAdapter (Protocol)
│                             ── MockImmudbAdapter (dict-backed, call tracking)
│                             ── RealImmudbAdapter (wraps immudb gRPC SDK)
│                             ── get_adapter() -> ImmudbAdapter
│
├── tests/unit/test_serializer.py    12 tests
├── tests/unit/test_ledger_unit.py   33 tests
├── tests/integration/test_ledger_integration.py  6 tests
├── tests/integration/test_cold_storage.py        2 tests
│
└── scripts/static_analysis.sh   4 grep checks → exits 0 or non-zero
```

### Append() Data Flow

```
Caller: append(event_dict_without_seq_or_hash)
  ↓
check_no_floats(event)        → LedgerSerializationError if float found
validate event_type in catalog → LedgerSerializationError if unknown
  ↓
mutex.acquire()
  ↓
tip = get_tip()               → LedgerTip {sequence_number, hash}
seq = tip.sequence_number + 1 → (works: -1 + 1 = 0 for empty ledger)
prev_hash = GENESIS_SENTINEL if seq == 0 else tip.hash
  ↓
event["sequence"] = seq
event["previous_hash"] = prev_hash
event["hash"] = compute_hash(event)   → serializer excludes hash field from input
  ↓
adapter.kv_set(
  key=f"{seq:012d}",          → zero-padded 12-digit key (lexicographic scan order)
  value=canonical_json(event).encode("utf-8")
)                             → synchronous gRPC — blocks until immudb confirms
  ↓
mutex.release()
  ↓
return seq                    → int (OUT-001)
```

### Verify Chain() Data Flow (kernel-independent)

```
Caller: verify_chain(start=0, end=N)
  ↓
for seq in range(start, N+1):
  raw = adapter.kv_get(f"{seq:012d}")
  event = json.loads(raw)
  expected_hash = compute_hash(event)   → hash field excluded from input
  if event["hash"] != expected_hash:
      return VerifyChainResult(valid=False, break_at=seq)   → STOP
  expected_prev = GENESIS_SENTINEL if seq == 0 else prev_event["hash"]
  if event["previous_hash"] != expected_prev:
      return VerifyChainResult(valid=False, break_at=seq)   → STOP
  prev_event = event
  ↓
return VerifyChainResult(valid=True)
[No kernel, Graph, HO1, HO2 imported — only adapter connection to immudb]
```

### Key Interface Boundaries

```python
# D4 IN-001 — Caller supplies these; Ledger assigns sequence/previous_hash/hash
{
    "event_id": "<uuid_v7>",
    "event_type": "<from EVENT_TYPE_CATALOG>",
    "schema_version": "1.0.0",
    "timestamp": "2026-03-01T14:22:00Z",
    "provenance": {"framework_id": "FMWK-NNN", "pack_id": "PC-NNN", "actor": "system"},
    "payload": {}   # no float-type values anywhere
}
# Returns: int (sequence assigned)

# D4 IN-005 — verify_chain (cold-storage safe)
verify_chain(start: int = 0, end: int | None = None) -> VerifyChainResult

# D4 ERR-001..004 — error codes (exact strings)
LEDGER_CONNECTION_ERROR | LEDGER_CORRUPTION_ERROR | LEDGER_SEQUENCE_ERROR | LEDGER_SERIALIZATION_ERROR

# Canonical JSON (E-002) — exact call:
json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
# Then: utf-8 encode → sha256 → hexdigest → "sha256:" prefix

# GENESIS_SENTINEL (exact string):
"sha256:" + "0" * 64   # = "sha256:0000000000000000000000000000000000000000000000000000000000000000"

# immudb key format (D4 SIDE-001):
f"{sequence:012d}"    # e.g., sequence 42 → "000000000042"
```

---

## 4. Implementation Steps

Work strictly in this order. Each step includes a "Why" where safety or architecture depends on the sequence.

1. **Create `staging/FMWK-001-ledger/` directory structure** (ledger/, tests/unit/, tests/integration/, scripts/).
   WHY: D1 Dev Workflow Constraint 1 — governed filesystem never touched. Staging is the only place to work.

2. **Create `ledger/errors.py`** — 4 error classes inheriting `platform_sdk.tier0_core.errors` base. Verify `code` attributes match D4 Error Code Enum exactly.

3. **Create `ledger/schemas.py`** — dataclasses for E-001 through E-009. All decimal fields are `str`. Verify `EVENT_TYPE_CATALOG` contains exactly 15 event types from D3 E-009.

4. **Write `tests/unit/test_serializer.py`** — all 12 tests. Run with MockProvider; all 12 should fail (no implementation yet). Confirm failures are "not found" type, not import errors.
   WHY: DTT enforced — write the failing test before implementing.

5. **Create `ledger/serializer.py`** — implement `GENESIS_SENTINEL`, `canonical_bytes()`, `compute_hash()`, `check_no_floats()`. Run test_serializer.py — all 12 must pass.
   WHY: Canonical serialization (SIDE-002) is a byte-level contract. Isolate it as a pure module and verify it completely before it is used by append() or verify_chain(). A bug here is silent until cold-storage verification fails across language boundaries.

6. **Create `platform_sdk/tier0_core/data/__init__.py` and `platform_sdk/tier0_core/data/immudb_adapter.py`** — staging-only `data/` package shim plus ImmudbAdapter Protocol, MockImmudbAdapter, RealImmudbAdapter, get_adapter().
   WHY: D1 Article 7 — all immudb access through platform_sdk. The live SDK uses a single-file `platform_sdk/tier0_core/data.py`; the staging packet intentionally creates a `data/` package that is independent of the live SDK layout and re-exports the existing functionality needed by the builder. This adapter is the ONLY file permitted to import the immudb SDK. Build and verify Mock before RealProvider — unit tests only ever touch Mock.
   - MockImmudbAdapter MUST track all method calls in `self.call_log` for admin-op assertions.
   - RealImmudbAdapter MUST implement SIDE-003 reconnect: wait 1 second, retry once, then raise LedgerConnectionError.
   - RealImmudbAdapter MUST NOT call CreateDatabaseV2, DatabaseDelete, or any other admin method.

7. **Create `ledger/ledger.py`** Ledger class skeleton — `__init__` with `_adapter`, `_mutex`, `_config`.

8. **Implement `Ledger.connect()`** — uses `LedgerConfig.from_env()` for `IMMUDB_HOST`, `IMMUDB_PORT`, `IMMUDB_DATABASE`, reads secrets via platform_sdk, calls `list_databases()`, raises `LedgerConnectionError` immediately if `"ledger"` absent.
   WHY: D1 Article 9 — connect does NOT provision. Zero admin calls. If this is wrong, every subsequent build that depends on FMWK-001 starts with the wrong assumption about database lifecycle.
   - Write connect() tests (`test_connect_raises_on_missing_database`, `test_connect_makes_zero_admin_calls`) — confirm both pass.

9. **Implement `Ledger.get_tip()`** — scans adapter for last key, returns LedgerTip. Handle empty ledger (returns `{sequence_number: -1, hash: ""}`) and adapter-unreachable error path. Write and pass `test_get_tip_empty_ledger`, `test_get_tip_after_5_events`, and `test_get_tip_raises_connection_error_on_adapter_failure`.

10. **Implement `Ledger.append()`** — full implementation with mutex.
    WHY (mutex): CLR-001 — in-process mutex is the chosen atomicity mechanism (Option B). The single-writer design makes this sufficient. `LedgerSequenceError` is the safety net if the invariant breaks. Without the mutex, two concurrent callers read the same tip and write duplicate sequence numbers — silent corruption.
    WHY (synchronous write): D1 NEVER "buffer or batch writes." Every append blocks until immudb confirms via gRPC. No buffering, no fire-and-forget.
    WHY (no caller sequence param): D1 Article 6. Caller-supplied sequences can produce forks. Ledger owns the guarantee.
    - After implementing, run append() unit tests (T-006 list). All 15 must pass.

11. **Implement `Ledger.read()`, `read_range()`, `read_since()`** — return events exactly as stored. No re-serialization. `read()` raises `LedgerConnectionError` for out-of-range sequence numbers (missing key).
    WHY: D1 NEVER "re-serialize or mutate events during read." If the stored canonical JSON changes shape on read, verify_chain() will compute a different hash than what was stored at write time.
    - Run T-007 tests (7 tests). All must pass.

12. **Implement `Ledger.verify_chain()`** — walk from start to end, recompute each hash, check chain linkage. Stop at first mismatch. Raise `LedgerConnectionError` if the adapter becomes unreachable during the walk.
    WHY: Must be kernel-independent (D1 Article 8). Do NOT import anything from the kernel, Graph, or cognitive runtime. Any such import would break cold-storage verification if the kernel is down.
    WHY (stop at first break): D2 SC-EC-001 specifies stop-at-first — returning the position of first corruption is the operator's starting point for manual investigation.
    - Run T-008 tests (6 tests). All must pass.

13. **Write `tests/unit/test_ledger_unit.py`** reconnect tests (T-009) — `test_reconnect_waits_one_second_before_retry`, `test_reconnect_raises_connection_error_after_one_retry_fails`, `test_reconnect_succeeds_on_second_attempt`. Monkeypatch `time.sleep`. Run — all 3 must pass.

14. **Run full unit regression** — `python3 -m pytest tests/unit/ -v`. Confirm 45 tests pass.

15. **Write `tests/integration/test_ledger_integration.py`** (6 tests) and `tests/integration/test_cold_storage.py` (2 tests). Requires Docker `ledger` service on :3322.
    - For test_cold_storage.py: the test writes events with kernel up, stops the kernel container via subprocess or Docker SDK, creates a fresh Ledger instance that connects directly to immudb :3322, calls verify_chain(), asserts result matches the online result.

16. **Create `scripts/static_analysis.sh`** — 4 checks. Run it. Fix any violations before continuing.
    WHY: D1 Articles 2, 4, 7 are absolute prohibitions. A violation discovered after KERNEL installation requires a hand-verified rebuild. The static analysis gate catches violations at author time.

17. **Run full regression** — `python3 -m pytest tests/ -v --tb=short`. All 53 tests must pass.

18. **Generate `sawmill/FMWK-001-ledger/RESULTS.md`** per BUILDER_HANDOFF_STANDARD.md with SHA-256 hashes for every file created or modified.

---

## 5. Package Plan

| Item | Value |
|------|-------|
| Package ID | FMWK-001-ledger |
| Layer | KERNEL (hand-verified — no automated install gate for KERNEL phase) |
| Staging Path | `staging/FMWK-001-ledger/` |
| Dependencies | FMWK-000 (GENESIS — immudb running, `ledger` DB created), platform_sdk (all tiers already present) |

**Assets:**

| File | Purpose |
|------|---------|
| `ledger/__init__.py` | Package exports |
| `ledger/errors.py` | 4 error classes |
| `ledger/schemas.py` | E-001..E-009 entities |
| `ledger/serializer.py` | Canonical JSON + hash computation |
| `ledger/ledger.py` | Ledger class (7 methods) |
| `platform_sdk/tier0_core/data/__init__.py` | staging-only package shim re-exporting existing `data.py` behavior plus immudb adapter |
| `platform_sdk/tier0_core/data/immudb_adapter.py` | immudb Protocol + Mock + Real |
| `tests/unit/test_serializer.py` | 12 unit tests |
| `tests/unit/test_ledger_unit.py` | 33 unit tests |
| `tests/integration/test_ledger_integration.py` | 6 integration tests |
| `tests/integration/test_cold_storage.py` | 2 cold-storage tests |
| `scripts/static_analysis.sh` | 4-check analysis gate |

**Manifest:** SHA-256 of each asset recorded in `RESULTS.md`.

---

## 6. Test Plan

Minimum: 45 unit tests (medium codebase: 3-5 files → 25+ minimum; 45 exceeds). 8 integration tests. 53 total.

### test_serializer.py — 12 tests

| Test Name | Description | Expected |
|-----------|-------------|----------|
| `test_canonical_json_excludes_hash_field` | Call canonical_bytes on event with `hash` field; assert `hash` absent from output | `"hash"` not in decoded output |
| `test_canonical_json_sorted_keys` | Event with keys in non-alphabetical order; assert output has sorted keys | `"event_id"` before `"hash"` before `"payload"` etc. |
| `test_canonical_json_no_whitespace_between_tokens` | Assert no space after `:` or `,` in output | No `", "` or `": "` in output |
| `test_canonical_json_ensure_ascii_false_literal_utf8` | Event with `café` string value; assert literal `café` in output bytes, not `\u00e9` escape | Raw UTF-8 bytes present |
| `test_canonical_json_null_field_included` | Event with `None` value field; assert `"field":null` in output | `"field":null` present |
| `test_canonical_json_integer_no_decimal` | Event with integer field `42`; assert `42` not `42.0` in output | No `.` after integer |
| `test_hash_format_matches_regex` | Call compute_hash on event; assert output matches `^sha256:[0-9a-f]{64}$` | Regex match passes |
| `test_hash_lowercase_hex_only` | Assert no uppercase A-F in hash output | `hash.lower() == hash` |
| `test_float_detection_top_level_raises` | Pass `{"v": 0.5}` to check_no_floats | Raises LedgerSerializationError |
| `test_float_detection_nested_dict_raises` | Pass `{"a": {"b": 0.1}}` | Raises LedgerSerializationError |
| `test_float_detection_in_list_raises` | Pass `{"a": [1, 0.1, 2]}` | Raises LedgerSerializationError |
| `test_genesis_sentinel_exact_string` | Assert `GENESIS_SENTINEL == "sha256:" + "0" * 64` | Exact string comparison, no regex |

### test_ledger_unit.py — 33 tests

| Test Name | Description | Expected |
|-----------|-------------|----------|
| `test_connect_raises_on_missing_database` | Mock list_databases returns `[]`; call connect() | LedgerConnectionError raised |
| `test_connect_makes_zero_admin_calls` | Call connect() (pass or fail); inspect call_log | No admin op strings in call_log |
| `test_append_returns_sequence_number` | Append one event to empty ledger | Returns `0` (int) |
| `test_append_assigns_sequence_internally` | Re-read appended event; check sequence field | `event["sequence"] == 0` |
| `test_append_first_event_gets_genesis_previous_hash` | Append first event | `event["previous_hash"] == GENESIS_SENTINEL` (exact string) |
| `test_append_sequential_hash_chain_linkage` | Append 5 events | `event[i]["previous_hash"] == event[i-1]["hash"]` for i in 1..4 |
| `test_append_sequences_are_0_1_2_3_4` | Append 5 events | `[e["sequence"] for e in events] == [0,1,2,3,4]` |
| `test_append_hash_format_regex` | Append one event | `event["hash"]` matches `^sha256:[0-9a-f]{64}$` |
| `test_append_signature_has_no_sequence_param` | Inspect append signature | `"sequence"` not in `inspect.signature(ledger.append).parameters` |
| `test_append_raises_serialization_error_on_float` | Append event with `{"payload": {"v": 0.5}}` | LedgerSerializationError raised |
| `test_append_raises_serialization_error_on_invalid_event_type` | Append event with unknown event_type | LedgerSerializationError raised |
| `test_append_raises_connection_error_on_immudb_failure` | Mock kv_set raises gRPC error both attempts | LedgerConnectionError raised after 1 retry |
| `test_append_sequence_error_on_concurrent_write` | Mock adapter raises on sequence conflict | LedgerSequenceError raised |
| `test_snapshot_event_payload_fields_stored` | Append snapshot_created event with E-005 payload | Re-read event has snapshot_path, snapshot_hash, snapshot_sequence |
| `test_get_tip_empty_ledger` | Call get_tip() on empty ledger | `LedgerTip(sequence_number=-1, hash="")` |
| `test_get_tip_after_5_events` | Append 5 events, call get_tip() | `sequence_number=4`, hash matches event[4].hash |
| `test_get_tip_hash_matches_last_event` | Re-read event at tip.sequence_number | `tip.hash == event.hash` |
| `test_get_tip_raises_connection_error_on_adapter_failure` | Mock kv_scan raises adapter error | LedgerConnectionError raised |
| `test_read_returns_exact_stored_event` | Append event, read back by sequence | All fields identical including hash and previous_hash |
| `test_read_no_mutation_of_fields` | Assert read event fields not transformed or re-serialized | Field-by-field equality including hash values |
| `test_read_out_of_range_raises` | read(999) on 5-event ledger | LedgerConnectionError raised |
| `test_read_range_returns_ascending_order` | Write 20 events, read_range(5, 15) | 11 events returned, sequences 5..15 in order, no gaps |
| `test_read_range_empty_beyond_tip` | read_range(100, 200) on 20-event ledger | Returns empty list, no error |
| `test_read_since_returns_events_after_sequence` | Write 20 events, read_since(10) | Events 11..20 returned in ascending order |
| `test_read_since_empty_at_tip` | read_since(N) where N == tip | Returns empty list |
| `test_verify_chain_intact_returns_valid_true` | Write 10 events, verify_chain() | `VerifyChainResult(valid=True)` |
| `test_verify_chain_break_at_absent_on_success` | verify_chain() on intact chain | `result.break_at is None` (not 0, not absent key — must be None) |
| `test_verify_chain_raises_connection_error_on_adapter_failure` | Mock adapter raises on kv_get | LedgerConnectionError raised |
| `test_verify_chain_detects_hash_corruption` | Corrupt event[3].hash in mock storage, verify_chain() | `VerifyChainResult(valid=False, break_at=3)` |
| `test_verify_chain_stops_at_first_break` | Corrupt event[3] in 6-event ledger, verify_chain() | kv_get NOT called for keys `000000000004` and `000000000005` (check call_log) |
| `test_verify_chain_detects_broken_previous_hash_link` | Replace event[2].previous_hash with wrong value | `VerifyChainResult(valid=False, break_at=2)` |
| `test_reconnect_waits_one_second_before_retry` | Mock gRPC failure; monkeypatch time.sleep | `time.sleep(1)` called exactly once |
| `test_reconnect_raises_connection_error_after_one_retry_fails` | Both gRPC attempts fail | LedgerConnectionError raised; exactly one sleep(1) |

### test_ledger_integration.py — 6 tests (Docker immudb required)

| Test Name | Description | Expected |
|-----------|-------------|----------|
| `test_integration_append_and_read_roundtrip` | Append 1 event; read back | Byte-level equality of all fields |
| `test_integration_1000_event_chain_sequential` | Write 1000 events | Sequences 0..999, all hashes match regex |
| `test_integration_verify_chain_intact_1000_events` | After 1000-event write, verify_chain() | `{valid: True}` |
| `test_integration_read_since_after_20_events` | Write 20, read_since(10) | Events 11..20, none missing, none duplicated |
| `test_integration_missing_database_raises` | Connect to immudb with no `ledger` DB | LedgerConnectionError immediately |
| `test_integration_get_tip_sequence` | Append 5 events, get_tip() | `sequence_number == 4` |

### test_cold_storage.py — 2 tests (Docker required, stops kernel container)

| Test Name | Description | Expected |
|-----------|-------------|----------|
| `test_cold_verify_chain_without_kernel` | Write 10 events; stop kernel container; connect CLI adapter directly to :3322; verify_chain() | `{valid: True}` — no kernel needed |
| `test_cold_verify_chain_matches_online_result` | Online result vs offline result (kernel stopped) | Both results identical |

---

## 7. Existing Code to Reference

| What | Where | Why |
|------|-------|-----|
| Existing data module | `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/data.py` | Live SDK is a single-file module. In staging, create `platform_sdk/tier0_core/data/__init__.py` as a shim that re-exports the needed behavior plus the new adapter. |
| Error base class | `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/errors.py` | LedgerXxx errors must inherit from the live platform_sdk base class |
| Logging conventions | `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/logging.py` | `get_logger()` call pattern; every Ledger operation must log via this |
| Config access | `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/config.py` | Use `get_config()` only for general platform bootstrap compatibility; immudb host/port/database come from `LedgerConfig.from_env()` using `IMMUDB_HOST`, `IMMUDB_PORT`, `IMMUDB_DATABASE` |
| Secrets access | `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/secrets.py` | How to call `get_secret("immudb_username")` — never os.getenv() for secrets |
| Existing ledger provider pattern | `platform_sdk/tier0_core/ledger.py` | Use `LedgerProvider` at line 70 as a structural Protocol example only — not as a behavioral example |
| All 46 SDK modules | `/Users/raymondbruni/dopejar/platform_sdk/MODULES.md` | Check before reaching for any external library — may already be covered |
| Docker service definition | `/Users/raymondbruni/dopejar/docker-compose.yml` | immudb service name, port mapping, volume name for integration tests |

Note: the live SDK file `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/ledger.py` predates the FMWK-001 packet and calls `CreateDatabaseV2`. That admin-op behavior is now prohibited by D1/D4/D8. Do not copy its connection logic; use it only for the Protocol pattern shape.

---

## 8. E2E Verification

After completing all implementation steps, run these commands in order. Every line must succeed.

```bash
# From: staging/FMWK-001-ledger/ (inside Brain_Factory repo)

# Step 1: Unit tests — no Docker needed
export PYTHONPATH=/Users/raymondbruni/dopejar:$PYTHONPATH
PLATFORM_DATA_BACKEND=mock python3 -m pytest tests/unit/ -v --tb=short
# Expected final line: "45 passed in <Xs>"
# Accept: 45 passed, 0 failed, 0 errors

# Step 2: Static analysis gate
bash scripts/static_analysis.sh
# Expected final line: "Static analysis: ALL CHECKS PASSED"
# Accept: exit code 0

# Step 3: Start Docker immudb (from repo root)
cd ../..
docker-compose -f /Users/raymondbruni/dopejar/docker-compose.yml up -d ledger
docker-compose -f /Users/raymondbruni/dopejar/docker-compose.yml ps ledger
# Expected: State=Up, Port=0.0.0.0:3322->3322/tcp
cd staging/FMWK-001-ledger

# Step 4: Integration tests
PLATFORM_DATA_BACKEND=immudb python3 -m pytest tests/integration/test_ledger_integration.py -v --tb=short
# Expected: "6 passed in <Xs>"

# Step 5: Cold-storage test
PLATFORM_DATA_BACKEND=immudb python3 -m pytest tests/integration/test_cold_storage.py -v --tb=short
# Expected: "2 passed in <Xs>"

# Step 6: Full regression
PLATFORM_DATA_BACKEND=immudb python3 -m pytest tests/ -v --tb=short
# Expected: "53 passed in <Xs>" (or "53 passed, 0 failed")

# Step 7: Verify static analysis catches violations (self-test of gate)
echo "from immudb import grpc" >> /tmp/test_violation.py
grep -r "from immudb" /tmp/test_violation.py
# Expected: one line (shows grep works — this file is not in FMWK-001 scope)
rm /tmp/test_violation.py

# Step 8: Confirm append() signature has no sequence param
python -c "
import inspect
from ledger.ledger import Ledger
params = list(inspect.signature(Ledger.append).parameters.keys())
assert 'sequence' not in params, f'FAIL: sequence in append() params: {params}'
print('PASS: append() signature has no sequence parameter')
"
# Expected: "PASS: append() signature has no sequence parameter"

# Step 9: Confirm genesis sentinel exact value
python -c "
from ledger.serializer import GENESIS_SENTINEL
expected = 'sha256:' + '0' * 64
assert GENESIS_SENTINEL == expected, f'FAIL: got {GENESIS_SENTINEL!r}'
print('PASS: GENESIS_SENTINEL is exactly correct')
"
# Expected: "PASS: GENESIS_SENTINEL is exactly correct"
```

---

## 9. Files Summary

| File | Location | Action |
|------|----------|--------|
| `ledger/__init__.py` | `staging/FMWK-001-ledger/ledger/__init__.py` | CREATE |
| `ledger/errors.py` | `staging/FMWK-001-ledger/ledger/errors.py` | CREATE |
| `ledger/schemas.py` | `staging/FMWK-001-ledger/ledger/schemas.py` | CREATE |
| `ledger/serializer.py` | `staging/FMWK-001-ledger/ledger/serializer.py` | CREATE |
| `ledger/ledger.py` | `staging/FMWK-001-ledger/ledger/ledger.py` | CREATE |
| `platform_sdk/tier0_core/data/__init__.py` | `staging/FMWK-001-ledger/platform_sdk/tier0_core/data/__init__.py` | CREATE |
| `platform_sdk/tier0_core/data/immudb_adapter.py` | `staging/FMWK-001-ledger/platform_sdk/tier0_core/data/immudb_adapter.py` | CREATE |
| `tests/__init__.py` | `staging/FMWK-001-ledger/tests/__init__.py` | CREATE |
| `tests/unit/__init__.py` | `staging/FMWK-001-ledger/tests/unit/__init__.py` | CREATE |
| `tests/unit/test_serializer.py` | `staging/FMWK-001-ledger/tests/unit/test_serializer.py` | CREATE |
| `tests/unit/test_ledger_unit.py` | `staging/FMWK-001-ledger/tests/unit/test_ledger_unit.py` | CREATE |
| `tests/integration/__init__.py` | `staging/FMWK-001-ledger/tests/integration/__init__.py` | CREATE |
| `tests/integration/test_ledger_integration.py` | `staging/FMWK-001-ledger/tests/integration/test_ledger_integration.py` | CREATE |
| `tests/integration/test_cold_storage.py` | `staging/FMWK-001-ledger/tests/integration/test_cold_storage.py` | CREATE |
| `scripts/static_analysis.sh` | `staging/FMWK-001-ledger/scripts/static_analysis.sh` | CREATE |
| `RESULTS.md` | `sawmill/FMWK-001-ledger/RESULTS.md` | CREATE (by builder after completion) |

**Total new files: 16 (15 source/test/script + 1 results)**
**Files modified in dopejar: 0** (all work is additive in staging)

---

## 10. Design Principles

1. **Store only, never interpret.** The Ledger appends events and returns them unchanged. It does not fold, accumulate signals, or interpret payloads. Any logic that changes the meaning of an event belongs in FMWK-002 or later.

2. **Immutability is absolute.** No delete. No update. No admin operation that modifies existing data. If you feel pressure to add one — for any reason — stop and flag it. The NORTH_STAR guarantee "can't forget, can't drift" depends on this being unconditional.

3. **The hash is a byte-level contract.** The canonical JSON serialization (E-002) is not a suggestion or a convention — it is a byte-for-byte specification that must be reproduced identically by every verifier in every language. Any deviation (uppercase hex, different separator, ASCII escaping) silently breaks cross-language verification. Test with exact string comparisons, never regex equivalence.

4. **Infrastructure separation is a lifecycle guarantee.** `connect()` does not create. GENESIS creates. If connect() were allowed to provision, concurrent agent startups would race on database creation and could corrupt the immudb system catalog. The boundary is enforced in code and tested — not just documented.

5. **The mutex protects sequence integrity.** The in-process lock on append() is not defensive programming — it is the agreed atomicity mechanism (CLR-001). Remove it and the sequence guarantee becomes caller-dependent. The lock ensures get_tip() and kv_set() are atomic from the perspective of this process.

6. **The platform_sdk contract is non-negotiable.** Any concern covered by platform_sdk MUST be satisfied through platform_sdk. No shortcuts, no bypasses, no "just this once." The bypass becomes permanent. The static analysis gate enforces this — treat any gate violation as a build failure, not a warning.

---

## 13 Questions (Answer All Before Writing Any Code)

You are a builder agent for DoPeJarMo.
Agent: H-1 — Build FMWK-001-ledger (append-only hash-chained event store)
Prompt Contract Version: 1.0.0

Read `sawmill/FMWK-001-ledger/D10_AGENT_CONTEXT.md` as your primary reference, then answer
all 13 questions below. STOP after answering all 13. Do NOT create directories, write tests, or
write any code until the human greenlights you.

**Scope Questions:**
- Q1: What are you building? (Name every file from the Files Summary. Account for all 16.)
- Q2: What are you explicitly NOT building? (Reference D2 Deferred Capabilities and D8 deferred scope.)
- Q3: What is the very first test you will write, and what does it test? (From T-003 in D8.)

**Technical Questions:**
- Q4: What exact Python call produces the canonical JSON for hash computation? (Write the exact line of code.)
- Q5: What is the genesis sentinel value? (Write it out in full — all 71 characters.)
- Q6: What is the immudb key format for sequence number 7? (Write the exact string.)

**Packaging Questions:**
- Q7: Which existing platform_sdk files will you MODIFY (if any)? Which will you only CREATE new alongside?
- Q8: What environment variable selects MockImmudbAdapter vs RealImmudbAdapter?

**Verification Question:**
- Q9: How many tests will you have in total across all test files? What is the breakdown by file?

**Integration Question:**
- Q10: After a caller appends an event, how does FMWK-002 (write-path) consume it? (Name the method and the D4 contract it implements.)

**Adversarial Questions (Genesis set):**
- Q11 (Dependency Trap): Which piece of your implementation depends on something that does not yet exist in the Brain_Factory repo, and how will you handle that gap?
- Q12 (Scope Creep Check): What is the one thing closest to being in scope that you are explicitly prohibited from building, and why is it out of scope?
- Q13 (Semantic Audit): The word "atomic" appears in both the mutex description and the immudb gRPC call description. What does "atomic" mean in each context, and are the two guarantees the same? (Flag CRITICAL_REVIEW_REQUIRED if your answer makes an assumption.)

STOP AFTER ANSWERING ALL 13. Do NOT proceed until human says go.
