# D7: Plan — FMWK-001-ledger
Meta: v:1.0.0 (matches D2) | status:Draft | constitution:D1 v1.0.0 | gap_analysis:D6 PASS (0 open)

---

## Summary

FMWK-001-ledger is the append-only, hash-chained event store for DoPeJarMo. It wraps immudb
behind a stable seven-method interface (`connect`, `append`, `read`, `read_range`, `read_since`,
`get_tip`, `verify_chain`), assigns sequence numbers and hash-chain links internally so callers
cannot corrupt the ordering invariant, and guarantees that any tool connecting directly to immudb
on :3322 can verify the full chain without a running kernel. The first consumer after GENESIS is
FMWK-002 (write-path), which calls `append()` for every state mutation and `read_since()` to
replay events after a snapshot load. The build adds an immudb adapter to platform_sdk (satisfying
D1 Article 7), implements the Ledger class in the FMWK-001 staging package, and produces 50
tests spanning unit (MockProvider), integration (Docker immudb), and cold-storage verification
(SC-005: kernel stopped, CLI connects directly).

---

## Technical Context

| Item | Value |
|------|-------|
| Language / Version | Python 3.12+ |
| Key Dependencies | `platform_sdk.tier0_core.data` (immudb adapter, added by this build), `platform_sdk.tier0_core.{config,secrets,errors,logging}`, `platform_sdk.tier2_reliability.{health,metrics}`, `hashlib` (stdlib), `json` (stdlib), `threading` (stdlib mutex), `uuid` (stdlib, 3.12+ for `uuid.uuid7()`) |
| Storage | immudb gRPC :3322 (Docker service `ledger`), `ledger_data` volume |
| Testing Framework | `pytest` (unit with MockProvider; integration with Docker immudb) |
| Platform | Brain_Factory repo, `staging/FMWK-001-ledger/` (never touches governed filesystem during authoring) |
| Performance Goals | `append()` p99 < 50ms on local Docker; `verify_chain()` over 1000 events < 5s |
| Scale / Scope | KERNEL phase: single writer (FMWK-002 Write Path), single persistent gRPC connection |

---

## Constitution Check

| Article | Principle | Compliant | Notes |
|---------|-----------|-----------|-------|
| 1: SPLITTING | Independently authorable with only FMWK-000 installed | YES | All FMWK-001 code lives in `staging/FMWK-001-ledger/`. Static analysis gate (T-012) confirms zero cross-framework imports. Gate passes with only FMWK-000 present. |
| 2: MERGING | No fold, signal, gate, or Graph logic; stores events only | YES | `ledger.py` contains only `connect/append/read/read_range/read_since/get_tip/verify_chain`. T-012 static check confirms zero FMWK-002 through FMWK-006 imports. |
| 3: OWNERSHIP | Sole owner of base schema fields: `event_id`, `previous_hash`, `sequence`, `schema_version`, `hash` | YES | `schemas.py` is the sole definition point. T-012 greps all non-FMWK-001 files for these fields — zero matches required. |
| 4: APPEND-ONLY IMMUTABILITY | Zero admin operation calls (`DatabaseDelete`, `DropDatabase`, etc.) | YES | `immudb_adapter.py` RealProvider exposes no admin methods. T-012 static analysis fails build if any admin op string found in FMWK-001 code. |
| 5: DETERMINISTIC HASH CHAIN | Every event links to predecessor via `sha256:<64 lowercase hex>` | YES | `serializer.py` implements E-002 byte-level contract. SC-006 (genesis sentinel exact match), SC-007 (5-event chain linkage), and SC-004 (verify_chain) provide coverage. |
| 6: SEQUENCE MONOTONICITY | `append()` accepts no `sequence` param; Ledger assigns; conflict → `LedgerSequenceError` | YES | `IN-001` contract: caller supplies no sequence. Mutex (CLR-001) + immudb atomicity. T-010 verifies signature and SC-EC-002 behavior. |
| 7: IMMUDB ABSTRACTION | All immudb access through `platform_sdk.tier0_core.data` | YES | This build adds the immudb adapter to platform_sdk. `ledger.py` imports only from `platform_sdk`. T-012 greps for direct immudb SDK imports — zero permitted. |
| 8: COLD-STORAGE VERIFIABILITY | `verify_chain()` runs with kernel stopped, immudb only | YES | `verify_chain()` takes only an immudb adapter connection. T-011 `test_cold_storage.py` stops kernel container, connects CLI directly, asserts identical result. |
| 9: INFRASTRUCTURE SEPARATION | `connect()` fails immediately if `ledger` DB missing; zero admin calls | YES | `connect()` reads existing databases; if `ledger` not found, raises `LedgerConnectionError` immediately. SC-EC-004 unit test: mock reports no `ledger` DB → asserts error + zero admin calls. |

---

## Architecture Overview

```
                Callers (FMWK-002, FMWK-006, kernel bootstrap, CLI tools)
                        │
                        │ append() / read() / verify_chain() / get_tip()
                        ▼
        ┌───────────────────────────────────────┐
        │            ledger.py                  │
        │          Ledger class                 │
        │                                       │
        │  connect()        append()            │
        │  read()           read_range()        │
        │  read_since()     get_tip()           │
        │  verify_chain()                       │
        │         │    │                        │
        │  threading.Lock (mutex)               │
        └──────────┼────┼───────────────────────┘
                   │    │
         ┌─────────┘    └──────────────┐
         │                             │
         ▼                             ▼
┌─────────────────┐         ┌─────────────────────┐
│  serializer.py  │         │     schemas.py       │
│  compute_hash() │         │  LedgerEvent (E-001) │
│  check_no_float │         │  LedgerTip (E-003)   │
│  E-002 contract │         │  VerifyChainResult   │
└────────┬────────┘         │  Payload E-005..E-008│
         │                  │  EventTypeCatalog     │
         └─────────┐        │  (E-009)             │
                   │        └─────────────────────-┘
                   │
                   ▼
         ┌─────────────────┐
         │    errors.py    │
         │  Ledger*Error   │
         │  ERR-001..004   │
         └────────┬────────┘
                  │
                  ▼
┌──────────────────────────────────────────────────┐
│   platform_sdk.tier0_core.data.ImmudbAdapter     │
│   Protocol + MockProvider + RealProvider         │
│   (added by this build)                          │
└────────────────────┬─────────────────────────────┘
                     │ gRPC :3322
                     ▼
          ┌──────────────────────┐
          │   immudb (Docker)    │
          │   ledger_data volume │
          └──────────────────────┘
```

### Append Data Flow

```
Caller → append(event_without_seq_or_hash)
  → check_no_floats(event)              [raises LedgerSerializationError if float found]
  → mutex.acquire()
  → tip = get_tip()
  → seq = tip.sequence_number + 1 (or 0 if tip.sequence_number == -1)
  → previous_hash = tip.hash  (or genesis_sentinel if seq == 0)
  → event.sequence = seq
  → event.previous_hash = previous_hash
  → canonical_bytes = serialize(event_without_hash_field)
  → event.hash = "sha256:" + sha256(canonical_bytes).hexdigest()
  → adapter.kv_set(key=zero_pad(seq, 12), value=canonical_json(event))  [synchronous gRPC]
  → mutex.release()
  → return seq
```

### Verify Chain Data Flow

```
Caller → verify_chain(start=0, end=N)
  → prev_hash = None
  → for seq in range(start, end+1):
      raw = adapter.kv_get(key=zero_pad(seq, 12))
      event = deserialize(raw)
      expected_hash = compute_hash(event)          [hash field excluded from input]
      if event.hash != expected_hash:
          return VerifyChainResult(valid=False, break_at=seq)
      expected_prev = genesis_sentinel if seq == 0 else prev_hash
      if event.previous_hash != expected_prev:
          return VerifyChainResult(valid=False, break_at=seq)
      prev_hash = event.hash
  → return VerifyChainResult(valid=True)
[No kernel, Graph, HO1, HO2, or any cognitive runtime required — immudb only]
```

---

### Component Responsibilities

**`ledger/errors.py`**
- Responsibility: Defines all four Ledger error classes. No logic, no imports beyond stdlib.
- Implements: ERR-001 through ERR-004
- Depends On: nothing
- Exposes: `LedgerConnectionError`, `LedgerCorruptionError`, `LedgerSequenceError`, `LedgerSerializationError`

**`ledger/schemas.py`**
- Responsibility: Dataclass definitions for all entities (E-001 through E-009). No business logic. Pure data shapes.
- Implements: D3 E-001 (LedgerEvent), E-003 (LedgerTip), E-004 (VerifyChainResult), E-005 through E-008 (payload schemas), E-009 (EventTypeCatalog)
- Depends On: `errors.py`
- Exposes: `LedgerEvent`, `LedgerTip`, `VerifyChainResult`, `SnapshotCreatedPayload`, `NodeCreationPayload`, `SessionStartPayload`, `SessionEndPayload`, `PackageInstallPayload`, `EVENT_TYPE_CATALOG: frozenset[str]`

**`ledger/serializer.py`**
- Responsibility: Byte-level canonical JSON serialization and SHA-256 hash computation (E-002 / SIDE-002). Pure functions only — no I/O, no state.
- Implements: E-002, SIDE-002, float detection for ERR-004
- Depends On: `errors.py`, `json` (stdlib), `hashlib` (stdlib)
- Exposes: `compute_hash(event: dict) -> str`, `check_no_floats(obj: Any) -> None`, `canonical_bytes(event: dict) -> bytes`, `GENESIS_SENTINEL: str`

**`platform_sdk/tier0_core/data/__init__.py` + `platform_sdk/tier0_core/data/immudb_adapter.py`** (added in staging)
- Staging creates a `data/` package even though the live SDK currently has a single-file `data.py`.
- The staging package is independent of the live SDK layout and re-exports the existing `data.py` functionality needed by the packet, plus the new immudb adapter.
- Responsibility: immudb gRPC adapter following platform_sdk Protocol + MockProvider + RealProvider pattern. MockProvider is a dict-backed in-memory KV store. RealProvider wraps immudb SDK.
- Implements: D4 SIDE-001, IN-007 (connect contract), SIDE-003 (reconnect)
- Depends On: `platform_sdk.tier0_core.{config, secrets}`, immudb SDK (RealProvider only — isolated inside adapter)
- Exposes: `ImmudbAdapter` (Protocol), `MockImmudbAdapter`, `RealImmudbAdapter`, `get_adapter() -> ImmudbAdapter` (env-var selected)

**`ledger/ledger.py`**
- Responsibility: The Ledger class — orchestrates all six public methods using serializer + adapter + schemas + errors. Owns the threading.Lock mutex for append atomicity (CLR-001).
- Implements: IN-001 through IN-007, OUT-001 through OUT-004, SIDE-001 through SIDE-003, SC-001 through SC-009, SC-EC-001 through SC-EC-004
- Depends On: `serializer.py`, `schemas.py`, `errors.py`, `platform_sdk.tier0_core.data` (ImmudbAdapter), `platform_sdk.tier0_core.logging`
- Exposes:
  ```python
  class Ledger:
      def connect(self, config: LedgerConfig) -> None
      def append(self, event: dict) -> int
      def read(self, sequence_number: int) -> LedgerEvent
      def read_range(self, start: int, end: int) -> list[LedgerEvent]
      def read_since(self, sequence_number: int) -> list[LedgerEvent]
      def get_tip(self) -> LedgerTip
      def verify_chain(self, start: int = 0, end: int | None = None) -> VerifyChainResult
  ```

---

### File Creation Order

```
staging/FMWK-001-ledger/
│
├── ledger/                         # FMWK-001 package
│   ├── __init__.py                 # Exports: Ledger, LedgerConfig, LedgerEvent, VerifyChainResult, LedgerTip, errors
│   ├── errors.py                   # Phase 0: ERR-001..004 error classes
│   ├── schemas.py                  # Phase 0: E-001..E-009 dataclasses + EventTypeCatalog + LedgerConfig.from_env()
│   ├── serializer.py               # Phase 0: canonical JSON + hash + float detection
│   └── ledger.py                   # Phase 2: Ledger class (connect + all 6 methods)
│
├── platform_sdk/                   # SDK additions (contributed to platform_sdk)
│   └── tier0_core/
│       └── data/
│           ├── __init__.py         # Phase 1: staging-only re-export shim
│           └── immudb_adapter.py   # Phase 1: Protocol + MockProvider + RealProvider
│
└── tests/
    ├── unit/
    │   ├── __init__.py
    │   ├── test_serializer.py      # Phase 0: 12 tests — serializer contract
    │   └── test_ledger_unit.py     # Phase 2: 33 tests — all scenarios via MockProvider
    └── integration/
        ├── __init__.py
        ├── test_ledger_integration.py  # Phase 3: 6 tests — real Docker immudb
        └── test_cold_storage.py        # Phase 3: 2 tests — SC-005 cold verification
```

---

### Testing Strategy

**Unit Tests (MockProvider — no Docker required)**

`test_serializer.py` (12 tests):
- What: canonical JSON output format, float detection at all nesting depths, null field inclusion, integer no-decimal, unicode literal output, genesis sentinel exact string, hash regex.
- Mocking: None — pure functions.

`test_ledger_unit.py` (33 tests):
- What: all P0 and P1 scenarios against MockProvider. connect/append/read/get_tip/verify_chain error and success paths.
- Mocking: `MockImmudbAdapter` (dict-backed in-memory KV, admin-call tracking, failure injection via pytest monkeypatch or mock failure flag).

**Integration Tests (real Docker immudb)**

`test_ledger_integration.py` (6 tests):
- What: SC-001 through SC-009 with actual immudb. 1000-event chain write + verify. read_since after snapshot position.
- Environment: Docker Compose `ledger` service on :3322. Teardown flushes DB (GENESIS re-provision per test that needs clean state, or use immudb db isolation).
- Note: These tests document the expected result; CI should gate on them.

`test_cold_storage.py` (2 tests):
- What: SC-005 — write events with kernel running, then stop kernel container, run verify_chain via CLI adapter directly. Assert identical result to online run.
- Environment: Docker. Test uses subprocess or direct adapter connect without kernel.

**Smoke Test (copy-paste verify)**

```bash
cd staging/FMWK-001-ledger
python3 -m pytest tests/unit/ -v --tb=short
# Expected final line: "45 passed in <Xs>"
```

---

### Complexity Tracking

| Component | Est. Lines | Risk | Notes |
|-----------|-----------|------|-------|
| `errors.py` | ~40 | Low | Pure class definitions, no logic |
| `schemas.py` | ~180 | Low | Dataclasses + E-009 catalog frozenset |
| `serializer.py` | ~80 | Medium | Byte-level contract; float detection recursive walk |
| `immudb_adapter.py` | ~200 | Medium | Three classes (Protocol, Mock, Real); RealProvider uses immudb gRPC SDK |
| `ledger.py` | ~280 | High | append() mutex + atomicity; reconnect logic; verify_chain walk; all error paths |
| `__init__.py` files | ~30 | Low | Exports only |
| `test_serializer.py` | ~150 | Low | Pure function tests |
| `test_ledger_unit.py` | ~500 | Medium | 33 tests; MockProvider failure injection |
| `test_ledger_integration.py` | ~200 | Medium | Requires Docker; test isolation |
| `test_cold_storage.py` | ~100 | Medium | Subprocess kernel stop/start |
| **Source total** | **~810** | | |
| **Test total** | **~900** | | |

---

### Migration Notes

Greenfield — no prior FMWK-001 implementation exists. No migration path required.

The immudb adapter contributed in staging is additive — existing live platform_sdk modules are not modified. The live SDK's `platform_sdk/tier0_core/ledger.py` may be used as a structural Protocol example only; its `CreateDatabaseV2` connection behavior is prohibited by this packet.
