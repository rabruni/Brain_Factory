# Builder Handoff — Ledger (FMWK-001)
Prompt Contract Version: 1.0.0

---

## 1. Mission

Build the `ledger` Python package for FMWK-001-ledger: the append-only, hash-chained event store primitive for DoPeJarMo. The package exposes a `LedgerClient` with six methods (`append`, `read`, `read_range`, `read_since`, `verify_chain`, `get_tip`) backed by immudb through the platform_sdk. It computes SHA-256 hash chains using deterministic canonical JSON serialization and enforces single-writer discipline via an in-process threading.Lock. Every state mutation in DoPeJarMo enters the system as a `LedgerClient.append()` call from the Write Path — this is the primitive everything else depends on. Package ID: `FMWK-001-ledger`.

---

## 2. Critical Constraints

1. **Staging only.** All code is written to `staging/FMWK-001-ledger/`. Do NOT write to the governed filesystem (`/Users/raymondbruni/dopejar/`) directly.
2. **DTT (Define-Test-Then-Implement) per behavior.** For every task in D8: write the test methods first, run pytest and watch them fail, then implement, then watch them pass. Any code written before tests must be deleted and restarted. No exceptions. Reference: `Templates/TDD_AND_DEBUGGING.md`.
3. **Package everything.** The `ledger` directory must be an importable Python package (`__init__.py` required). All public symbols exported from `__init__.py`.
4. **E2E verify before declaring done.** Run `PLATFORM_ENVIRONMENT=test pytest tests/ -v` and paste full output into RESULTS.md. Do not declare done without pasted evidence.
5. **No hardcoding.** immudb host, port, credentials must come from `platform_sdk.tier0_core.config` and `platform_sdk.tier0_core.secrets`. No string literals for connection params.
6. **No file replacement.** Do not overwrite files by replacing their entire content. Edit incrementally. If you must rewrite, document why in RESULTS.md Session Log.
7. **Deterministic archives.** If you produce any archive, it must be reproducible byte-for-byte.
8. **Results file is mandatory.** Write `sawmill/FMWK-001-ledger/RESULTS.md` with all required sections before reporting completion. No partial results files.
9. **Full regression before done.** Run the complete test suite with `PLATFORM_ENVIRONMENT=test pytest tests/ -v --tb=short` and paste the output. Not just the new tests — all tests.
10. **Baseline snapshot.** RESULTS.md must include the baseline snapshot: list of packages installed, total test count at start of session.
11. **TDD discipline is enforced.** If you claim tests pass, paste the output from THIS session. "Should work" and "I'm confident" are not evidence. Only test output is evidence.
12. **Platform SDK contract is absolute.** No direct `import immudb`. No direct `import uuid`. No `os.getenv()` for config. All covered concerns go through `platform_sdk`. This is not optional — it is architectural.

---

## 3. Architecture / Design

```
Caller (Write Path FMWK-002 / Graph FMWK-005 / CLI)
         │ 6 methods
         ▼
 ┌───────────────────────────────────────────────────────┐
 │ LedgerClient (api.py)                                  │
 │  append(event_data) -> int                             │
 │  read(seq) -> LedgerEvent                              │
 │  read_range(start, end) -> [LedgerEvent]               │
 │  read_since(seq) -> [LedgerEvent]                      │
 │  verify_chain(start=0, end=None) -> ChainVerifResult   │
 │  get_tip() -> TipRecord                                │
 └──────┬────────────────────┬──────────────────────────-┘
        │                    │
        ▼                    ▼
 ImmudbStore (store.py)    serialization.py  verify.py
  threading.Lock            canonical_json()  walk_chain()
  1-reconnect+retry         canonical_hash()
        │
        ▼
 platform_sdk.tier0_core.data
        │
        ▼
 immudb gRPC :3322
 database "ledger"
 key  = zero-padded sequence (20 chars)
 value = canonical JSON bytes of full LedgerEvent

Supporting modules:
  errors.py   → 4 error classes
  models.py   → LedgerEvent, Provenance, TipRecord,
                ChainVerificationResult, EventType
  schemas.py  → validate_event_data()
```

**immudb key format:**
Keys are the sequence number zero-padded to 20 characters: sequence 0 → `"00000000000000000000"`, sequence 5 → `"00000000000000000005"`. This ensures lexicographic scan order = numeric order.

**append() critical path (all inside store._lock):**
```
1. validate_event_data(event_data)   ← raises LedgerSerializationError if invalid
2. acquire store._lock
3. tip = get_tip()                   ← reads stored tip; empty = TipRecord(seq=-1, hash=sha256+64zeros)
4. sequence = tip.sequence_number + 1
5. event_id = platform_sdk.tier0_core.ids.generate()  ← UUID v7
6. previous_hash = tip.hash
7. full_event = {all fields except hash}
8. hash = canonical_hash(full_event)
9. full_event["hash"] = hash
10. value = canonical_json(full_event).encode("utf-8")
11. store.set(zero_pad(sequence), value)
12. release store._lock
13. return sequence
```

**Hash chain invariants:**
- `event[0].previous_hash` = `"sha256:" + "0" * 64`
- `event[N].previous_hash` = `event[N-1].hash`
- `event[N].hash` = `canonical_hash({all fields of event[N] except hash})`

**Error behavior:**
- Any failure in steps 1-11 → raise appropriate Ledger error; if lock was acquired, release it; Ledger state unchanged
- immudb unreachable → `LedgerConnectionError` (not silently buffered)
- Non-JSON-serializable payload → `LedgerSerializationError` (raised at step 1, before lock)

---

## 4. Implementation Steps

Follow D8 task order. Each step is DTT: tests first, then implementation.

**Step 1: errors.py** (T-001)
Implement 4 error classes. WHY: errors have zero dependencies — defining them first lets every subsequent module import them without circular imports.
File: `ledger/errors.py`
Classes: `LedgerConnectionError(Exception)`, `LedgerCorruptionError(Exception)`, `LedgerSequenceError(Exception)`, `LedgerSerializationError(Exception)`
Each has `code: str` attribute and `message: str` attribute.
Write tests first. Minimum 4 test methods.

**Step 2: models.py** (T-002)
Implement 4 dataclasses + EventType enum. WHY: all other modules need these types; defining them after errors establishes the complete type foundation.
File: `ledger/models.py`
Implement: `@dataclass LedgerEvent` (9 fields), `@dataclass Provenance` (3 fields), `@dataclass TipRecord` (2 fields), `@dataclass ChainVerificationResult` (2 fields), `EventType(str, Enum)` with 15 values from D3.
Write tests first. Minimum 6 test methods.

**Step 3: serialization.py** (T-003 — parallel with Step 2)
Implement canonical JSON and SHA-256. WHY: pure stdlib functions; no other modules needed; a test vector establishes byte-level correctness before any integration.
File: `ledger/serialization.py`
Implement `canonical_json(event_dict: dict) -> str` and `canonical_hash(event_dict: dict) -> str`.
Reference: D3 Canonical JSON Serialization Constraint, D4 SIDE-002.
Write tests first with hardcoded test vector. Minimum 8 test methods.

**Step 4: schemas.py** (T-004 — after Step 2)
Implement field validators. WHY: validation runs before every append; it must reject malformed events before any lock is acquired or storage touched.
File: `ledger/schemas.py`
Implement `validate_event_data(event_data: dict) -> None`.
Write tests first. Minimum 8 test methods.

**Step 5: store.py** (T-005 — after Steps 1-4)
Implement ImmudbStore. WHY: all immudb access goes through this; the threading.Lock lives here; the retry policy lives here.
File: `ledger/store.py`
Key constraint: acquire `self._lock` in `set()` BEFORE reading any state. WHY: prevents two callers from computing the same next sequence number.
Key constraint: `connect()` must fail fast with `LedgerConnectionError` if database "ledger" does not exist. WHY: prevents race on database creation if multiple agents start simultaneously (D6 CLR-001).
Key constraint: on gRPC failure in `set()`: release lock, close connection, sleep 1 second, reconnect once, retry once, raise `LedgerConnectionError` if retry fails. WHY: one built-in reconnect attempt; Write Path owns further retry (D5 RQ-005).
All tests use MockProvider. Minimum 10 test methods.

**Step 6: verify.py** (T-006 — parallel with Step 5)
Implement walk_chain. WHY: pure function; no storage access; can be tested in isolation against constructed LedgerEvent lists.
File: `ledger/verify.py`
Implement `walk_chain(events: list[LedgerEvent]) -> ChainVerificationResult`.
Walk logic: for each event, recompute `canonical_hash(event_without_hash_field)`, compare to `event.hash`; verify `event.previous_hash == prior_event.hash`; return first failure.
Write tests first. Minimum 8 test methods.

**Step 7: api.py — get_tip()** (T-007 — after Steps 5-6)
Implement LedgerClient skeleton + get_tip(). WHY: simplest method; establishes LedgerClient structure; all other API methods depend on get_tip() working first.
File: `ledger/api.py`
Implement: `LedgerClient.__init__`, `LedgerClient.connect()`, `LedgerClient.get_tip()`.
Empty Ledger sentinel: `TipRecord(sequence_number=-1, hash="sha256:0000000000000000000000000000000000000000000000000000000000000000")`. WHY: Write Path computes `next_sequence = tip.sequence_number + 1 = 0` for genesis with no special case (D6 CLR-002).
Write tests first. Minimum 4 test methods.

**Step 8: api.py — append()** (T-008 — after Step 7)
Implement append(). WHY: most complex method; implements the full hash chain construction; mutex must wrap tip-read + write atomically.
Add `append(event_data: dict) -> int` to LedgerClient.
Follow the critical path in Section 3 exactly.
Acquire `store._lock` before reading tip. WHY: prevents sequence forks (D5 RQ-001 single-writer assumption).
Write tests first. Minimum 10 test methods.

**Step 9: api.py — read(), read_range(), read_since()** (T-009 — after Step 7)
Implement the three read methods. WHY: builds on get_tip() for range validation; straightforward delegation to store.
Add three methods to LedgerClient.
read_range() uses INCLUSIVE bounds on both ends: `read_range(3, 7)` returns sequences [3,4,5,6,7]. WHY: D6 CLR-004 resolved this explicitly.
read_since(N) returns events with sequence > N (exclusive lower bound).
Write tests first. Minimum 12 test methods.

**Step 10: api.py — verify_chain()** (T-010 — after Steps 9 and 6)
Implement verify_chain(). WHY: uses read_range() to fetch events, then delegates to walk_chain() for pure verification.
Add `verify_chain(start=0, end=None)` to LedgerClient.
If immudb unreachable: raise `LedgerConnectionError`. Do NOT return `{valid: false}` for connection errors. WHY: unreachable immudb is an infrastructure failure, not a corruption result (D4 IN-005 postcondition #6).
Write tests first. Minimum 8 test methods.

**Step 11: Package assembly + regression** (T-011 — after all API methods)
Write `ledger/__init__.py` with all public exports. Write `tests/conftest.py` with MockProvider fixtures. Run full regression. Write RESULTS.md.

**Step 12: CLI entry point** (T-012 — parallel with Step 11)
Implement `ledger/__main__.py`. WHY: cold-storage verifiability (D1 Article 8) requires that `python -m ledger --verify` works with NO kernel process running — connecting to immudb directly.
Output format: `{"valid": bool, "break_at": int|null, "tip": {"sequence_number": int, "hash": "sha256:..."}}`.
Exit code 0 = valid; exit code 1 = invalid or error.

---

## 5. Package Plan

**Package ID:** `FMWK-001-ledger`
**Layer:** KERNEL (Phase 1)
**All Assets:**

| File | Type | Action |
|------|------|--------|
| `ledger/__init__.py` | Source | CREATE |
| `ledger/api.py` | Source | CREATE |
| `ledger/errors.py` | Source | CREATE |
| `ledger/models.py` | Source | CREATE |
| `ledger/schemas.py` | Source | CREATE |
| `ledger/serialization.py` | Source | CREATE |
| `ledger/store.py` | Source | CREATE |
| `ledger/verify.py` | Source | CREATE |
| `ledger/__main__.py` | Source (CLI) | CREATE |
| `tests/conftest.py` | Test | CREATE |
| `tests/test_api.py` | Test | CREATE |
| `tests/test_serialization.py` | Test | CREATE |
| `tests/test_store.py` | Test | CREATE |
| `tests/test_verify.py` | Test | CREATE |
| `README.md` | Docs | CREATE |

**Dependencies:**
- `platform_sdk.tier0_core.data` — immudb access
- `platform_sdk.tier0_core.ids` — UUID v7 generation
- `platform_sdk.tier0_core.config` — connection config
- `platform_sdk.tier0_core.secrets` — immudb credentials
- `platform_sdk.tier0_core.logging` — structured logging
- `platform_sdk.tier0_core.metrics` — append/error/latency metrics
- Python stdlib: `hashlib`, `json`, `threading`, `dataclasses`, `typing`, `time`, `sys`

**Manifest fields (for RESULTS.md):**
- `package_id`: `FMWK-001-ledger`
- `framework_id`: `FMWK-001`
- `version`: `1.0.0`
- `manifest_hash`: SHA-256 of package manifest file (compute after writing all files)

---

## 6. Test Plan

Mandatory minimum for 6+ source files: **40 tests**. Target: **≥55 tests**.

### tests/test_serialization.py (≥8 tests)

| Test Method | Description | Expected Behavior |
|-------------|-------------|-------------------|
| `test_canonical_json_sorts_keys` | Dict with keys in reverse order | Keys appear alphabetically in output string |
| `test_canonical_json_no_whitespace` | Event dict serialized | Output contains no spaces, no newlines, no tabs |
| `test_canonical_json_ensure_ascii_false` | Payload contains UTF-8 string (e.g. `"café"`) | Output contains literal `café`, not `\u0063\u0061\u0066\u00e9` |
| `test_canonical_json_nested_keys_sorted` | Provenance subobject with unsorted keys | Nested object keys also appear alphabetically |
| `test_canonical_hash_excludes_hash_field` | Dict with and without `hash` key | `canonical_hash(d)` == `canonical_hash({k:v for k,v in d.items() if k!="hash"})` |
| `test_canonical_hash_test_vector` | Known event dict with all fields set | `canonical_hash(d)` == hardcoded expected value (pre-computed reference) |
| `test_canonical_hash_any_field_change_changes_hash` | Modify each field one at a time | Every field change produces a different hash |
| `test_canonical_hash_null_fields_included` | Dict with `{"field": null}` vs same dict with field omitted | Different hashes — null is not the same as absent |
| `test_float_string_vs_float_number_hash_differs` | `{"val": "0.1"}` vs `{"val": 0.1}` | Different hashes; string variant is canonical |
| `test_canonical_hash_returns_sha256_prefix` | Any event dict | Return value starts with `"sha256:"` and has exactly 71 chars total |

### tests/test_store.py (≥10 tests)

| Test Method | Description | Expected Behavior |
|-------------|-------------|-------------------|
| `test_connect_fails_if_database_missing` | MockProvider simulates "ledger" DB absent | `connect()` raises `LedgerConnectionError` |
| `test_connect_succeeds_with_database_present` | MockProvider has "ledger" DB | `connect()` returns without error |
| `test_set_and_get_roundtrip` | `set("00000000000000000000", value)` then `get(...)` | Returns same value bytes |
| `test_get_missing_key_raises_sequence_error` | `get("99999999999999999999")` on empty store | Raises `LedgerSequenceError` |
| `test_set_connection_failure_raises_connection_error` | MockProvider fails all attempts | `set()` raises `LedgerConnectionError` |
| `test_set_retry_succeeds_on_second_attempt` | MockProvider fails first, succeeds second | `set()` returns without error |
| `test_set_state_unchanged_after_connection_failure` | `set()` fails | `get_count()` unchanged; key not present |
| `test_scan_returns_ascending_order` | `set` keys for sequences 0,2,1 | `scan("000..00", "000..02")` returns [0,1,2] order |
| `test_get_count_zero_on_empty` | Fresh MockProvider store | `get_count() == 0` |
| `test_get_count_increments_after_set` | `set` one key | `get_count() == 1` |
| `test_lock_serializes_concurrent_sets` | Two threads call `set()` simultaneously | Both complete; `get_count() == 2`; no exception |

### tests/test_verify.py (≥8 tests)

| Test Method | Description | Expected Behavior |
|-------------|-------------|-------------------|
| `test_empty_list_returns_valid` | `walk_chain([])` | `ChainVerificationResult(valid=True, break_at=None)` |
| `test_single_intact_genesis_event` | One event with correct hash and genesis previous_hash | `valid=True, break_at=None` |
| `test_intact_chain_six_events` | 6 events with correct hashes and links | `valid=True, break_at=None` |
| `test_corrupted_hash_at_sequence_3` | Inject wrong `hash` at index 3 | `valid=False, break_at=3` |
| `test_broken_link_at_sequence_3` | Inject wrong `previous_hash` at index 3 | `valid=False, break_at=3` |
| `test_returns_lowest_failure_sequence` | Corrupt events at sequences 2 and 5 | `break_at=2` (lowest) |
| `test_single_event_wrong_hash` | One event with wrong hash | `valid=False, break_at=0` |
| `test_genesis_wrong_previous_hash` | Genesis event with wrong previous_hash (not sha256+64zeros) | `valid=False, break_at=0` |

### tests/test_api.py (≥35 tests)

**get_tip() tests (≥4):**

| Test Method | Description | Expected Behavior |
|-------------|-------------|-------------------|
| `test_get_tip_empty_ledger` | Fresh MockProvider ledger | `TipRecord(sequence_number=-1, hash="sha256:"+64zeros)` |
| `test_get_tip_after_one_append` | Append 1 event, call get_tip() | `TipRecord(sequence_number=0, hash=<event_hash>)` |
| `test_get_tip_sequence_advances_each_append` | Append 5 events, call get_tip after each | `sequence_number` = 0,1,2,3,4 respectively |
| `test_get_tip_connection_error` | MockProvider unreachable | Raises `LedgerConnectionError` |

**append() tests (≥10):**

| Test Method | Description | Expected Behavior |
|-------------|-------------|-------------------|
| `test_append_genesis_returns_sequence_zero` | SC-001: first append | Returns integer `0` |
| `test_append_genesis_previous_hash_is_zeros` | SC-001: genesis event | Stored event has `previous_hash="sha256:"+64zeros` |
| `test_append_genesis_hash_correct` | SC-001: genesis event | `event.hash == canonical_hash(event_without_hash)` |
| `test_append_genesis_persisted` | SC-001: after append | `read(0)` returns the same event |
| `test_append_genesis_tip_advances` | SC-001: after append | `get_tip()` returns `{sequence_number:0, hash:<event_hash>}` |
| `test_append_chain_continuation_previous_hash` | SC-002: 5 sequential appends | Each event's `previous_hash == prior event's hash` |
| `test_append_monotonic_sequence` | SC-002: 5 sequential appends | Sequences are [0, 1, 2, 3, 4] |
| `test_append_invalid_event_type_raises` | Unknown event_type | Raises `LedgerSerializationError`; state unchanged |
| `test_append_missing_required_field_raises` | Missing `timestamp` | Raises `LedgerSerializationError`; state unchanged |
| `test_append_connection_failure_state_unchanged` | SC-010: MockProvider unreachable | Raises `LedgerConnectionError`; `get_tip()` unchanged |
| `test_append_concurrent_no_fork` | SC-011: two threads append simultaneously | Exactly one succeeds, one raises `LedgerSequenceError`; `get_tip().sequence_number` incremented by exactly 1 |
| `test_append_serialization_failure_state_unchanged` | Payload contains non-serializable Python object | Raises `LedgerSerializationError`; Ledger state unchanged |

**read() tests (≥4):**

| Test Method | Description | Expected Behavior |
|-------------|-------------|-------------------|
| `test_read_returns_all_fields` | SC-003: read(5) on 11-event ledger | Returns `LedgerEvent` with all 9 fields present and non-null |
| `test_read_hash_is_stored_value` | read() after append | `event.hash` equals what was stored at append time, not recomputed |
| `test_read_out_of_range_raises` | read(999) with tip at 41 | Raises `LedgerSequenceError` |
| `test_read_negative_raises` | read(-1) | Raises `LedgerSequenceError` |
| `test_read_connection_error` | MockProvider unreachable | Raises `LedgerConnectionError` |

**read_range() tests (≥4):**

| Test Method | Description | Expected Behavior |
|-------------|-------------|-------------------|
| `test_read_range_returns_correct_events` | SC-004: read_range(3, 7) on 11-event ledger | Returns 5 events at sequences [3,4,5,6,7] in ascending order |
| `test_read_range_single_element` | read_range(N, N) | Returns list with exactly one event |
| `test_read_range_end_beyond_tip` | end > tip | Raises `LedgerSequenceError` |
| `test_read_range_start_beyond_tip` | start > tip | Raises `LedgerSequenceError` |

**read_since() tests (≥3):**

| Test Method | Description | Expected Behavior |
|-------------|-------------|-------------------|
| `test_read_since_returns_events_after_sequence` | SC-005: read_since(5) with tip at 10 | Returns events at sequences [6,7,8,9,10] |
| `test_read_since_tip_returns_empty` | read_since(tip) | Returns `[]` |
| `test_read_since_beyond_tip_raises` | read_since(99) with tip at 10 | Raises `LedgerSequenceError` |

**verify_chain() tests (≥8):**

| Test Method | Description | Expected Behavior |
|-------------|-------------|-------------------|
| `test_verify_chain_intact_chain` | SC-007: 6 correct events | `ChainVerificationResult(valid=True, break_at=None)` |
| `test_verify_chain_corruption_at_sequence_3` | SC-008: corrupt event at sequence 3 | `ChainVerificationResult(valid=False, break_at=3)` |
| `test_verify_chain_default_args_uses_full_range` | verify_chain() with no args on 10-event ledger | Walks 0 to 9; returns valid result |
| `test_verify_chain_connection_error_raises` | MockProvider unreachable | Raises `LedgerConnectionError` (NOT `{valid: false}`) |
| `test_verify_chain_empty_ledger_is_valid` | Empty Ledger | `ChainVerificationResult(valid=True, break_at=None)` |
| `test_verify_chain_single_event_is_valid` | One correct event | `valid=True` |
| `test_verify_chain_partial_range` | verify_chain(2, 5) on 10-event chain | Verifies only sequences 2-5 |
| `test_verify_chain_matches_walk_result` | SC-009 (mock): CLI call produces same result as API call | Same `ChainVerificationResult` from both paths |

---

## 7. Existing Code to Reference

| What | Where | Why |
|------|-------|-----|
| platform_sdk.tier0_core.data interface | `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/data.py` | Understand the provider protocol and MockProvider activation |
| platform_sdk.tier0_core.ids interface | `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/ids.py` | UUID v7 generation API |
| platform_sdk.tier0_core.config interface | `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/config.py` | PlatformConfig shape; how to read immudb host/port |
| platform_sdk.tier0_core.secrets interface | `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/secrets.py` | How to retrieve immudb credentials |
| platform_sdk MODULES.md | `/Users/raymondbruni/dopejar/platform_sdk/MODULES.md` | Full module list; MockProvider patterns; env var names |
| Existing LedgerProvider (reference only) | `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/ledger.py` | Prior implementation — read for context but DO NOT copy; this build supersedes it |

---

## 8. E2E Verification

After all tests pass, run these commands and paste the output into RESULTS.md:

```bash
# Full unit test regression
cd staging/FMWK-001-ledger && PLATFORM_ENVIRONMENT=test pytest tests/ -v --tb=short

# Expected: all tests pass, zero failures, total ≥ 55 tests
```

```bash
# Verify test count meets mandatory minimum
cd staging/FMWK-001-ledger && PLATFORM_ENVIRONMENT=test pytest tests/ --collect-only | tail -5

# Expected: "N tests collected" where N >= 55
```

```bash
# Cold-storage CLI smoke (requires: docker-compose up ledger)
cd staging/FMWK-001-ledger && PLATFORM_ENVIRONMENT=local python -m ledger --verify

# Expected output: {"valid": true, "break_at": null, "tip": {"sequence_number": N, "hash": "sha256:..."}}
# Expected exit code: 0
```

```bash
# Verify no direct immudb imports
grep -r "import immudb" ledger/

# Expected: no output (zero matches)
```

```bash
# Verify no direct uuid imports
grep -r "import uuid" ledger/

# Expected: no output (zero matches)
```

---

## 9. Files Summary

| File | Location | Action |
|------|----------|--------|
| `errors.py` | `ledger/errors.py` | CREATE |
| `models.py` | `ledger/models.py` | CREATE |
| `schemas.py` | `ledger/schemas.py` | CREATE |
| `serialization.py` | `ledger/serialization.py` | CREATE |
| `store.py` | `ledger/store.py` | CREATE |
| `verify.py` | `ledger/verify.py` | CREATE |
| `api.py` | `ledger/api.py` | CREATE |
| `__init__.py` | `ledger/__init__.py` | CREATE |
| `__main__.py` | `ledger/__main__.py` | CREATE |
| `conftest.py` | `tests/conftest.py` | CREATE |
| `test_serialization.py` | `tests/test_serialization.py` | CREATE |
| `test_store.py` | `tests/test_store.py` | CREATE |
| `test_verify.py` | `tests/test_verify.py` | CREATE |
| `test_api.py` | `tests/test_api.py` | CREATE |
| `README.md` | `README.md` | CREATE |
| `RESULTS.md` | `sawmill/FMWK-001-ledger/RESULTS.md` | CREATE (after build) |

---

## 10. Design Principles

1. **Single-writer assumption is documented, not assumed.** The in-process mutex prevents sequence forks — but only because there is exactly one kernel process. This assumption is documented in D5 RQ-001 and must appear in the implementation as a comment. Any future multi-process deployment requires replacing the mutex with a server-side transaction.

2. **Storage is storage. Logic is not.** The Ledger stores events. It does not interpret them, filter them, route them, or accumulate them. If you are writing code that inspects a payload field beyond JSON serializability — stop. That logic belongs in FMWK-002, FMWK-005, or another framework.

3. **Fail closed on infrastructure failure.** When immudb is unreachable, the Ledger raises `LedgerConnectionError`. It does not buffer, retry indefinitely, return stale data, or silently continue. The caller (Write Path) decides what to do with the error. The Ledger's built-in retry is one reconnect + one operation retry only.

4. **Canonical bytes are sacred.** The hash chain is only as good as its canonical serialization. Any deviation from `json.dumps(d, sort_keys=True, separators=(',',':'), ensure_ascii=False)` breaks `verify_chain()`. Test with hardcoded vectors. Never change the serialization format without human approval (D1 ASK FIRST boundary).

5. **Platform SDK is not optional.** `platform_sdk.tier0_core.data` is the only permitted path to immudb. Direct imports bypass the MockProvider, making unit tests impossible without live services. This architectural rule is D1 Article 10 — it is a constitutional constraint, not a preference.

6. **DTT is not a process — it is the build.** The test file IS the specification made executable. Writing code before tests means you are implementing to your own interpretation, not the spec. The spec is D2 and D4. Write the test from the spec. Watch it fail. Write the code. Watch it pass. Any other order is wrong.

---

## 11. Verification Discipline

**EVERY "tests pass" claim requires pasted output from THIS session.**

The RESULTS.md MUST include:
- Full test command with flags
- Full test output (not a summary — the actual pytest stdout)
- Test counts: total collected / passed / failed / skipped / error

**Red flags that indicate a claim is NOT verified:**
- "should work"
- "probably passes"
- "I'm confident"
- "tests pass" without pasted output
- Test count stated without running pytest in this session

**If a test fails:** Read the traceback. Identify the specific assertion. Fix the implementation (or the test if it is wrong). Do not delete failing tests to make counts pass.

Reference: `Templates/TDD_AND_DEBUGGING.md`

---

## 12. Mid-Build Checkpoint

After ALL unit tests pass (all Phase 2 tasks complete, before Phase 3):

Record the following evidence BEFORE continuing to Phase 3:

1. Paste full pytest output (show all test names passing)
2. List every file created so far (path + SHA-256)
3. Note any deviations from the spec (D2/D4) made during implementation — if any
4. State: "Checkpoint reached. Continuing to Phase 3."

Do NOT skip the checkpoint. If the orchestrator reviews the checkpoint and escalates, stop and wait for resolution before continuing.

---

## 13. Self-Reflection

Before reporting ANY step complete, answer ALL of these:

1. **Code matches spec?** Compare each implemented method's behavior to D2 scenarios AND D4 postconditions. Not just the happy path — check every postcondition, including failure postconditions.

2. **Edge cases from D8 covered?** SC-001 (genesis), SC-010 (connection failure with state unchanged), SC-011 (concurrent append with no fork), SC-009 (CLI offline). Are all tested?

3. **Code understandable in 6 months?** If you read `store.py` in 6 months, will you know WHY the lock is acquired before the tip read? If not, add a comment.

4. **TDD followed for EVERY behavior?** Check the order: test exists → test fails → code written → test passes. If you cannot confirm this for any behavior, mark it and explain in RESULTS.md.

5. **Code written before tests?** DELETE IT and redo. No exception.

6. **Platform SDK contract held?** Run `grep -r "import immudb" ledger/` and `grep -r "import uuid" ledger/`. Both must return zero matches.

7. **Deferred capabilities excluded?** The snapshot file format (DEF-001) and non-Ledger payload schemas (DEF-002) are NOT in scope for this build. The Ledger accepts deferred payload types as opaque JSON objects. Confirm nothing was added for these.
