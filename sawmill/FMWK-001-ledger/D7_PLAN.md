# D7: Plan — Ledger (FMWK-001)
Meta: v:1.0.0 (matches D2) | status:Final | constitution: D1 v1.0.0 | gap analysis: D6 PASS (0 open)

---

## Summary

The Ledger (FMWK-001) implements the append-only, hash-chained event store primitive for DoPeJarMo. It provides six interface methods backed by immudb through the platform_sdk: `append`, `read`, `read_range`, `read_since`, `verify_chain`, and `get_tip`. The LedgerClient wraps an ImmudbStore (which uses `platform_sdk.tier0_core.data`), assigns monotonic sequence numbers, computes SHA-256 hash chains using a deterministic canonical JSON serialization, and enforces single-writer discipline via an in-process threading.Lock. The first concrete use case is genesis: the Write Path calls `get_tip()` (returns the empty-ledger sentinel), then calls `append()` with a `node_creation` event, and the Ledger assigns `sequence=0`, sets `previous_hash="sha256:"+64zeros`, computes the chain hash, and persists to immudb. All unit tests run against platform_sdk MockProvider — no live immudb is required for the unit test suite.

---

## Technical Context

| Dimension | Value |
|-----------|-------|
| Language | Python 3.11+ |
| Key Dependencies | `platform_sdk` (tier0_core: data, ids, config, secrets, logging, errors, metrics); `hashlib` (stdlib); `json` (stdlib); `threading` (stdlib) |
| Storage | immudb gRPC on port 3322 (config-driven via platform_sdk.tier0_core.config), database `"ledger"`, key=zero-padded sequence string (20-char, e.g. `"00000000000000000005"`), value=canonical JSON bytes of full LedgerEvent |
| Testing Framework | `pytest`; platform_sdk MockProvider (PLATFORM_ENVIRONMENT=test); integration tests marked `@pytest.mark.integration` |
| Platform | Single kernel process (Docker), single Write Path caller per deployment |
| Performance Goals | append latency < 100ms (single event, non-integration); `verify_chain(0, 1000)` < 5s on warm immudb |
| Scale / Scope | KERNEL build; initial deployment ≪ 1M events; no read-path optimization required at this scale (D2 DEF-003 deferred) |

---

## Constitution Check

| Article | Principle | Compliant | Notes |
|---------|-----------|-----------|-------|
| 1 — Splitting Test | Independently authorable from spec pack + FWK-0 alone | YES | Builder receives only Ledger spec pack + FWK-0. All six methods are fully specifiable without Write Path, Graph, or Package Lifecycle internals. |
| 2 — Merging Test | No capabilities from separate frameworks absorbed | YES | Zero fold logic, graph construction, methylation computation, gate validation, or work order state management in scope. These are explicitly excluded in D2 NOT section. |
| 3 — Ownership Test | Exclusive ownership of event store, base schema, hash chain, canonical serialization | YES | Only this package imports immudb via platform_sdk. Canonical JSON contract is defined in D3/D4 SIDE-002 and enforced only in `serialization.py`. |
| 4 — Append-Only Immutability | No delete/modify/overwrite/truncate capability | YES | No delete methods in LedgerClient or ImmudbStore interface. immudb append-only design enforces at storage level. Forbidden admin methods listed in D1 NEVER boundary. |
| 5 — No Business Logic | Six methods: storage and retrieval only | YES | No payload field inspection beyond JSON serializability. No routing, filtering, accumulation, or graph operations. |
| 6 — Self-Describing Events | Required fields enforced on every append | YES | `validate_event_data()` in schemas.py raises LedgerSerializationError if event_type, schema_version, timestamp, or provenance fields are missing or invalid. |
| 7 — Hash Chain Integrity | SHA-256 hash chain on every append; verify_chain walks entire range | YES | `canonical_hash()` computed in serialization.py; previous_hash threaded through chain in append(); verify.py `walk_chain()` validates both hash and linkage. |
| 8 — Cold-Storage Verifiability | CLI tool connects directly to immudb; no kernel required | YES | `python -m ledger --verify` connects to immudb on config-driven port. `verify_chain()` has no kernel dependency. |
| 9 — immudb Abstraction | Public interface exposes no immudb types | YES | All public return types are LedgerEvent, TipRecord, ChainVerificationResult (defined in models.py). No immudb gRPC types in any public method signature. |
| 10 — Platform SDK Contract | All immudb access via platform_sdk | YES | store.py uses `platform_sdk.tier0_core.data` exclusively. MockProvider activated via PLATFORM_ENVIRONMENT=test. No direct `import immudb` anywhere in the package. |

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│  Callers: Write Path (FMWK-002), Graph (FMWK-005), CLI     │
└───────────────────────┬────────────────────────────────────┘
                        │ append / read / read_range /
                        │ read_since / verify_chain / get_tip
                        ▼
┌────────────────────────────────────────────────────────────┐
│  api.py — LedgerClient                                      │
│  Public 6-method interface                                   │
│  Assigns: event_id (ids), sequence (tip+1), hashes          │
│  Delegates to: store.py · serialization.py · verify.py      │
└──────┬────────────────────┬──────────────────────────────  ┘
       │                    │
       ▼                    ▼
┌──────────────┐   ┌────────────────────────────────────────┐
│  store.py    │   │  serialization.py                       │
│  ImmudbStore │   │  canonical_json(event_dict) -> str      │
│  threading   │   │  canonical_hash(event_dict) -> str      │
│  .Lock mutex │   │  stdlib: json + hashlib only            │
│  1-reconnect │   └───────────────────────────┬────────────┘
│  retry       │                               │
└──────┬───────┘                               │
       │                               ┌───────▼─────────────┐
       │ platform_sdk.tier0_core.data  │  verify.py          │
       ▼                               │  walk_chain(events)  │
┌──────────────────────────────────┐   └─────────────────────┘
│  immudb gRPC :3322 (config)      │
│  database "ledger"               │
│  key  = zero-padded seq string   │
│  value = canonical JSON bytes    │
└──────────────────────────────────┘

Support modules (no external deps beyond platform_sdk):
  models.py   — LedgerEvent, Provenance, TipRecord,
                ChainVerificationResult, EventType enum
  schemas.py  — validate_event_data()
  errors.py   — LedgerConnectionError, LedgerCorruptionError,
                LedgerSequenceError, LedgerSerializationError
```

---

### Component Responsibilities

**errors.py**
- File: `ledger/errors.py`
- Responsibility: Define all four Ledger error classes with no external dependencies.
- Implements: ERR-001, ERR-002, ERR-003, ERR-004
- Depends On: Python stdlib only
- Exposes: `LedgerConnectionError`, `LedgerCorruptionError`, `LedgerSequenceError`, `LedgerSerializationError` — all subclass `Exception`; each carries a `code` attribute matching the D4 Error Code Enum value

---

**models.py**
- File: `ledger/models.py`
- Responsibility: Dataclass definitions for all four entities and the EventType enum.
- Implements: D3 E-001 (LedgerEvent), E-002 (Provenance), E-003 (TipRecord), E-004 (ChainVerificationResult), EventType enum (15 values)
- Depends On: `dataclasses`, `typing` (stdlib); `errors.py`
- Exposes: `LedgerEvent`, `Provenance`, `TipRecord`, `ChainVerificationResult`, `EventType`

---

**schemas.py**
- File: `ledger/schemas.py`
- Responsibility: Field-level validation of append() input before any write occurs.
- Implements: D4 IN-001 constraints, D1 Article 6 (self-describing events)
- Depends On: `models.py`, `errors.py`
- Exposes: `validate_event_data(event_data: dict) -> None` — raises `LedgerSerializationError` on missing/invalid required fields or non-JSON-serializable payload

---

**serialization.py**
- File: `ledger/serialization.py`
- Responsibility: Canonical JSON serialization (SIDE-002) and SHA-256 hash computation (D1 Article 7).
- Implements: D3 Canonical JSON Serialization Constraint, D4 SIDE-002
- Depends On: `json`, `hashlib` (stdlib only — zero additional deps)
- Exposes:
  - `canonical_json(event_dict: dict) -> str` — sorts keys, no whitespace, ensure_ascii=False, excludes nothing
  - `canonical_hash(event_dict: dict) -> str` — excludes `hash` field, returns `"sha256:" + 64 lowercase hex chars`

---

**store.py**
- File: `ledger/store.py`
- Responsibility: Thin immudb wrapper via platform_sdk; in-process mutex; one-reconnect-one-retry connection policy.
- Implements: D4 SIDE-001, ERR-001, D5 RQ-001 (mutex), D5 RQ-005 (retry), D6 CLR-001 (fail-fast if DB missing)
- Depends On: `platform_sdk.tier0_core.data`, `platform_sdk.tier0_core.config`, `platform_sdk.tier0_core.secrets`, `platform_sdk.tier0_core.logging`; `threading` (stdlib)
- Exposes:
  - `ImmudbStore.__init__(config: PlatformConfig)`
  - `ImmudbStore.connect() -> None` — fails fast with LedgerConnectionError if "ledger" DB absent (CLR-001)
  - `ImmudbStore.set(key: str, value: bytes) -> None` — acquires `_lock`; 1-reconnect + 1-retry on failure
  - `ImmudbStore.get(key: str) -> bytes` — raises LedgerSequenceError if key not found
  - `ImmudbStore.scan(start_key: str, end_key: str) -> list[bytes]` — ascending order
  - `ImmudbStore.get_count() -> int` — number of stored keys
  - `ImmudbStore._lock: threading.Lock`

---

**verify.py**
- File: `ledger/verify.py`
- Responsibility: Hash chain walk algorithm — pure function, no storage access.
- Implements: D4 IN-005, OUT-005, SC-007, SC-008, SC-009
- Depends On: `serialization.py`, `models.py`, `errors.py`
- Exposes: `walk_chain(events: list[LedgerEvent]) -> ChainVerificationResult`

---

**api.py**
- File: `ledger/api.py`
- Responsibility: LedgerClient — the sole public interface. Assembles all modules. Assigns event_id, sequence, previous_hash, hash.
- Implements: D4 IN-001 through IN-006, OUT-001 through OUT-005
- Depends On: `store.py`, `serialization.py`, `verify.py`, `models.py`, `schemas.py`, `errors.py`; `platform_sdk.tier0_core.ids`, `platform_sdk.tier0_core.logging`
- Exposes:
  - `LedgerClient.__init__(config: PlatformConfig)`
  - `LedgerClient.connect() -> None`
  - `LedgerClient.append(event_data: dict) -> int`
  - `LedgerClient.read(sequence_number: int) -> LedgerEvent`
  - `LedgerClient.read_range(start: int, end: int) -> list[LedgerEvent]`
  - `LedgerClient.read_since(sequence_number: int) -> list[LedgerEvent]`
  - `LedgerClient.verify_chain(start: int = 0, end: int | None = None) -> ChainVerificationResult`
  - `LedgerClient.get_tip() -> TipRecord`

---

**__init__.py**
- File: `ledger/__init__.py`
- Responsibility: Clean public exports for the `ledger` package.
- Exposes: `LedgerClient`, `LedgerEvent`, `Provenance`, `TipRecord`, `ChainVerificationResult`, `EventType`, `LedgerConnectionError`, `LedgerCorruptionError`, `LedgerSequenceError`, `LedgerSerializationError`

---

### File Creation Order

```
staging/FMWK-001-ledger/
├── ledger/
│   ├── errors.py           Phase 0 — no dependencies; error classes first
│   ├── models.py           Phase 0 — depends on errors only
│   ├── schemas.py          Phase 0 — depends on models + errors
│   ├── serialization.py    Phase 0 — stdlib only (parallel with models)
│   ├── store.py            Phase 1 — platform_sdk.tier0_core.data
│   ├── verify.py           Phase 1 — depends on serialization + models (parallel with store)
│   ├── api.py              Phase 2 — assembles all modules
│   └── __init__.py         Phase 2 — exports (after api.py)
├── tests/
│   ├── conftest.py              Phase 0 — MockProvider fixtures
│   ├── test_serialization.py    Phase 0 — test vectors, no deps
│   ├── test_store.py            Phase 1 — MockProvider-based
│   ├── test_verify.py           Phase 1 — pure function tests
│   └── test_api.py              Phase 2 — full LedgerClient scenarios
└── README.md
```

---

### Testing Strategy

**Unit Tests** (all use platform_sdk MockProvider — no live immudb):
- `tests/conftest.py`: Sets PLATFORM_ENVIRONMENT=test. Provides fixtures: `mock_config`, `mock_ledger_client`, `sample_node_creation_event`, `sample_session_start_event`.
- `tests/test_serialization.py`: Test vectors — given a known event dict, assert `canonical_hash()` equals a pre-computed expected value. Tests: key sort, whitespace-free, ensure_ascii=False, hash-field exclusion, null inclusion, float-as-string requirement, nested key sort.
- `tests/test_store.py`: MockProvider simulates connection failure, missing database, key-not-found, retry success, retry failure, concurrent lock serialization.
- `tests/test_verify.py`: Pure function tests — empty list, single intact event, multi-event intact chain, corruption at position N, broken linkage, lowest-failure precedence.
- `tests/test_api.py`: All 11 D2 scenarios (SC-001 through SC-011). Covers each of the 6 LedgerClient methods.

**Integration Tests** (marked `@pytest.mark.integration` — require live immudb on port 3322):
- Append 100 events sequentially; verify chain; read range; cold-storage CLI verify.
- Run only in CI with `docker-compose up ledger`.

**Smoke Test** (no kernel process required):
```bash
PLATFORM_ENVIRONMENT=local python -m ledger --verify
```
Expected output: `{"valid": true, "break_at": null, "tip": {"sequence_number": N, "hash": "sha256:..."}}`
Expected exit code: `0`

---

### Complexity Tracking

| Component | Est. Lines | Risk | Notes |
|-----------|-----------|------|-------|
| errors.py | 40 | Low | 4 error classes, no logic |
| models.py | 120 | Low | Dataclasses + enum |
| schemas.py | 60 | Low | Validation functions |
| serialization.py | 60 | Low | Pure stdlib functions |
| store.py | 180 | Medium | Mutex + retry + platform_sdk integration |
| verify.py | 80 | Low | Pure function, well-specified |
| api.py | 160 | Medium | Coordinates all modules; tip logic; mutex threading |
| __init__.py | 20 | Low | Exports only |
| **Total Source** | **~720** | — | |
| conftest.py | 50 | Low | Fixtures |
| test_serialization.py | 90 | Low | Test vectors |
| test_store.py | 110 | Low | MockProvider-based |
| test_verify.py | 110 | Low | Corrupt event injection |
| test_api.py | 280 | Medium | 11 scenarios, 35 test methods |
| **Total Tests** | **~640** | — | |
| **Combined** | **~1360** | — | |

---

### Migration Notes

Greenfield — no migration. FMWK-001-ledger is a KERNEL framework built from scratch. No prior data model exists to migrate from.
