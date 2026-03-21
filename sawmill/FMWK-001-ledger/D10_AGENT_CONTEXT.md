# D10: Agent Context — Ledger (FMWK-001)
Meta: pkg:FMWK-001-ledger | updated:2026-03-21

---

## What This Project Does

The `ledger` package implements the Ledger primitive for DoPeJarMo — an append-only, hash-chained event store backed by immudb. It exposes 6 methods on `LedgerClient`: `append`, `read`, `read_range`, `read_since`, `verify_chain`, and `get_tip`. Every state mutation in the system (node creation, session boundaries, signal deltas, package installs) enters as a call to `append()` from the Write Path (FMWK-002). The Ledger assigns monotonic sequence numbers, computes SHA-256 hashes using deterministic canonical JSON serialization, threads each event's `previous_hash` from its predecessor's `hash`, and writes to immudb via `platform_sdk.tier0_core.data`. An in-process `threading.Lock` prevents sequence forks in the single-writer architecture. All unit tests use platform_sdk's MockProvider — no live immudb is required. A CLI entry point (`python -m ledger --verify`) lets operators verify the chain directly from immudb with no kernel process running.

---

## Architecture Overview

```
Caller (Write Path / Graph / CLI)
         │ append / read / read_range /
         │ read_since / verify_chain / get_tip
         ▼
 ┌───────────────────────────────────────┐
 │ api.py — LedgerClient                 │
 │  ├── validate_event_data()  [schemas] │
 │  ├── platform_sdk.tier0_core.ids      │ ← UUID v7 event_id
 │  ├── canonical_hash()  [serialization]│ ← hash computation
 │  ├── ImmudbStore       [store]        │ ← read/write immudb
 │  └── walk_chain()      [verify]       │ ← chain integrity
 └───────────────────────────────────────┘
         │ (store)
         ▼
 ┌─────────────────────────────────┐
 │ platform_sdk.tier0_core.data    │ ← gRPC abstraction + MockProvider
 └─────────────────┬───────────────┘
                   ▼
 immudb :3322 (config-driven)
 database "ledger"
 key  = zero-padded seq (e.g. "00000000000000000005")
 value = canonical JSON bytes of full LedgerEvent

Support modules (no immudb or platform_sdk deps except errors):
  errors.py       → LedgerConnectionError, LedgerCorruptionError,
                    LedgerSequenceError, LedgerSerializationError
  models.py       → LedgerEvent, Provenance, TipRecord,
                    ChainVerificationResult, EventType
  schemas.py      → validate_event_data()
  serialization.py→ canonical_json(), canonical_hash()
  verify.py       → walk_chain()
```

Directory structure:
```
staging/FMWK-001-ledger/
├── ledger/
│   ├── __init__.py          public exports (all public symbols)
│   ├── api.py               LedgerClient — 6-method public interface
│   ├── errors.py            4 error classes
│   ├── models.py            4 dataclasses + EventType enum (15 values)
│   ├── schemas.py           validate_event_data()
│   ├── serialization.py     canonical_json() + canonical_hash()
│   ├── store.py             ImmudbStore (mutex + retry + platform_sdk)
│   ├── verify.py            walk_chain()
│   └── __main__.py          CLI: python -m ledger --verify
├── tests/
│   ├── conftest.py          MockProvider fixtures
│   ├── test_serialization.py  canonical hash test vectors (≥8 tests)
│   ├── test_store.py        ImmudbStore unit tests (≥10 tests)
│   ├── test_verify.py       chain walk unit tests (≥8 tests)
│   └── test_api.py          LedgerClient full scenarios (≥35 tests)
└── README.md
```

---

## Key Patterns

**1. In-Process Mutex (threading.Lock)** [D5 RQ-001]
`store._lock` is acquired for the entire read-tip → compute-sequence → write sequence in `append()`. This prevents two concurrent callers from computing the same next sequence number. ASSUMPTION: single kernel process per deployment. If multi-process deployment is ever added, this must be replaced with a server-side transaction (e.g. immudb ExecAll or VerifiedSet).

**2. Canonical JSON for Hash Computation** [D3 Canonical JSON Constraint, D4 SIDE-002]
Every hash is computed from `json.dumps(event_without_hash, sort_keys=True, separators=(',',':'), ensure_ascii=False).encode('utf-8')`. Any deviation — extra whitespace, different key order, escaped unicode — produces a different hash and breaks chain verification. Never use `json.dumps` with defaults, `ujson`, or `orjson` for hash input.

**3. Floats as Strings in Payloads** [D5 RQ-003]
All float values in event payloads (`initial_methylation`, `base_weight`, `delta`) MUST be strings (`"0.1"`) never raw JSON numbers (`0.1`). IEEE 754 float64 representations differ across Python, Go, and JavaScript, producing different canonical bytes and therefore different hashes. This is enforced in D3 payload schemas — check them before setting any numeric field.

**4. Empty Ledger Sentinel** [D5 RQ-004, D6 CLR-002]
`get_tip()` on an empty Ledger returns `TipRecord(sequence_number=-1, hash="sha256:"+64zeros)`. The Write Path computes `next_sequence = tip.sequence_number + 1 = 0` (genesis). The returned `hash` becomes the genesis event's `previous_hash` directly. This eliminates a special case in the Write Path's append loop — the logic is uniform for genesis and all subsequent events.

**5. Platform SDK Contract** [D1 Article 10, AGENT_BOOTSTRAP.md]
ALL immudb access goes through `platform_sdk.tier0_core.data`. ALL ID generation goes through `platform_sdk.tier0_core.ids`. ALL config reads go through `platform_sdk.tier0_core.config`. NEVER import `immudb`, `uuid`, or `os.getenv` directly. The MockProvider mechanism only activates when access goes through the SDK — direct imports make unit tests require a live immudb instance.

---

## Commands

```bash
# Run all unit tests (no live immudb required)
cd staging/FMWK-001-ledger && PLATFORM_ENVIRONMENT=test pytest tests/ -v

# Run a single test
cd staging/FMWK-001-ledger && PLATFORM_ENVIRONMENT=test pytest tests/test_api.py::test_append_genesis_sequence_zero -v

# Run with short tracebacks for RESULTS.md
cd staging/FMWK-001-ledger && PLATFORM_ENVIRONMENT=test pytest tests/ -v --tb=short 2>&1 | tee regression_output.txt

# Run integration tests only (requires: docker-compose up ledger)
cd staging/FMWK-001-ledger && PLATFORM_ENVIRONMENT=local pytest tests/ -v -m integration

# Cold-storage CLI verification (kernel NOT required — connects to immudb directly)
cd staging/FMWK-001-ledger && PLATFORM_ENVIRONMENT=local python -m ledger --verify

# Collect all tests (verify scenario coverage)
cd staging/FMWK-001-ledger && PLATFORM_ENVIRONMENT=test pytest tests/ --collect-only
```

---

## Tool Rules

| USE THIS | NOT THIS | WHY |
|----------|----------|-----|
| `platform_sdk.tier0_core.data` | `import immudb` / `from immudb import ...` | MockProvider requires all immudb access through SDK; direct import breaks unit tests |
| `platform_sdk.tier0_core.ids` | `import uuid` / `uuid.uuid4()` / `uuid.uuid7()` | Platform SDK contract; ID generation is a covered concern |
| `platform_sdk.tier0_core.config` | `os.getenv()` directly | Config contract; centralizes config reads |
| `platform_sdk.tier0_core.secrets` | Hardcoded credentials, `os.getenv()` for secrets | Secrets never in source code |
| `platform_sdk.tier0_core.logging` | `print()`, raw `structlog`, `logging.getLogger()` | Structured logging contract |
| `json.dumps(d, sort_keys=True, separators=(',',':'), ensure_ascii=False)` | `json.dumps` with defaults / `ujson` / `orjson` | Canonical bytes required for hash chain — any deviation breaks verification |
| `hashlib.sha256` (stdlib) | External crypto libraries | Stdlib only; no new dependencies |
| `threading.Lock()` | `asyncio.Lock()` / no lock at all | Synchronous single-writer model (D5 RQ-001); async lock is wrong model here |
| `"0.1"` (string) for float payload fields | `0.1` (JSON number) | Cross-language hash safety; IEEE 754 divergence breaks hash matching (D5 RQ-003) |
| `{"field": null}` in canonical JSON | Omit null fields | Null fields are included in canonical serialization per D3 constraint |

---

## Coding Conventions

- **Python**: 3.11+
- **Stdlib policy**: Use `hashlib`, `json`, `threading`, `dataclasses`, `typing`, `time` from stdlib. All other concerns go through `platform_sdk`.
- **Type hints**: Full type hints on all public methods and `@dataclass` fields. `Optional[X]` for nullable fields (not `X | None` if Python 3.9 compat needed).
- **Dataclasses**: Use `@dataclass` for all four entity classes (LedgerEvent, Provenance, TipRecord, ChainVerificationResult). Do NOT use Pydantic unless platform_sdk already depends on it.
- **Error handling**: Raise typed Ledger errors from `errors.py`. Never raise raw `Exception`. Never suppress exceptions silently. Error codes must match D4 Error Code Enum exactly.
- **Exit codes** (CLI): `0` = chain valid, `1` = invalid or any error
- **Test framework**: `pytest`. Activate MockProvider by setting `PLATFORM_ENVIRONMENT=test` in the test environment (via `conftest.py` or env var). Mark integration tests with `@pytest.mark.integration`.
- **TDD discipline**: Every behavior defined in D2/D4 must have tests WRITTEN BEFORE implementation. If you wrote code before tests — delete the code and redo. No exceptions. See BUILDER_HANDOFF.md Section 11 (Verification Discipline).

---

## Submission Protocol

1. Read `BUILDER_HANDOFF.md` completely (located in `sawmill/FMWK-001-ledger/`)
2. Answer all 13 questions in `sawmill/FMWK-001-ledger/13Q_ANSWERS.md`; first line MUST be: `Builder Prompt Contract Version: 1.0.0`
3. **STOP.** Do not write any code. Wait for Reviewer PASS on 13Q.
4. After Reviewer PASS: implement using DTT — task order T-001 → T-012 per D8
   - For each task: write all test methods first → run pytest and watch them fail → implement → run pytest and watch them pass
5. After all Phase 2 tasks complete and all unit tests pass: record Mid-Build Checkpoint (paste full pytest output to `13Q_ANSWERS.md` or a checkpoint note)
6. Run full regression: `PLATFORM_ENVIRONMENT=test pytest tests/ -v --tb=short`
7. Write `sawmill/FMWK-001-ledger/RESULTS.md` with ALL mandatory sections:
   - Status (PASS / FAIL / PARTIAL)
   - Files Created (path + SHA-256 for every file)
   - Test Results (full command + full pasted output + counts: total / passed / failed / skipped)
   - Full Regression (same)
   - Baseline Snapshot
   - Clean-Room Verification steps
   - Issues Encountered
   - Notes for Reviewer
   - Session Log

Branch naming: `feature/fmwk-001-ledger`
Commit format: `feat(fmwk-001): <description>`
Results file path: `sawmill/FMWK-001-ledger/RESULTS.md`

---

## Active Components

| Component | Where | Interface (signature) |
|-----------|-------|-----------------------|
| LedgerClient | `ledger/api.py` | `LedgerClient(config: PlatformConfig)`; `.connect()`; `.append(event_data: dict) -> int`; `.read(sequence_number: int) -> LedgerEvent`; `.read_range(start: int, end: int) -> list[LedgerEvent]`; `.read_since(sequence_number: int) -> list[LedgerEvent]`; `.verify_chain(start: int = 0, end: int | None = None) -> ChainVerificationResult`; `.get_tip() -> TipRecord` |
| ImmudbStore | `ledger/store.py` | `ImmudbStore(config: PlatformConfig)`; `.connect()`; `.set(key: str, value: bytes) -> None`; `.get(key: str) -> bytes`; `.scan(start_key: str, end_key: str) -> list[bytes]`; `.get_count() -> int`; `._lock: threading.Lock` |
| canonical_hash | `ledger/serialization.py` | `canonical_hash(event_dict: dict) -> str` — excludes `hash` field; returns `"sha256:"+64hex |
| canonical_json | `ledger/serialization.py` | `canonical_json(event_dict: dict) -> str` — sort_keys, no whitespace, ensure_ascii=False |
| walk_chain | `ledger/verify.py` | `walk_chain(events: list[LedgerEvent]) -> ChainVerificationResult` |
| validate_event_data | `ledger/schemas.py` | `validate_event_data(event_data: dict) -> None` — raises LedgerSerializationError on invalid input |

---

## Links to Deeper Docs

- **D1** — Constitution: 10 articles (Splitting Test, Merging Test, Ownership, Append-Only, No Business Logic, Self-Describing Events, Hash Chain Integrity, Cold-Storage Verifiability, immudb Abstraction, Platform SDK Contract); ALWAYS/ASK FIRST/NEVER boundaries; tooling constraints
- **D2** — Specification: 11 scenarios (SC-001..011); NOT section (what the Ledger is NOT); 3 deferred capabilities; 15 success criteria
- **D3** — Data Model: 4 entities (E-001 LedgerEvent with 9 fields, E-002 Provenance, E-003 TipRecord, E-004 ChainVerificationResult); 6 Ledger-owned payload schemas; canonical JSON constraint with Python reference implementation; EventType enum (15 values)
- **D4** — Contracts: 6 inbound contracts (IN-001..006) with request shapes and observable postconditions; 5 outbound return types (OUT-001..005); 2 side-effect contracts (SIDE-001 immudb write mapping, SIDE-002 canonical JSON); 4 error types (ERR-001..004); Error Code Enum; EventType Enum restated for Turn C
- **D5** — Research: RQ-001 (in-process mutex decision — Option B); RQ-002 (UUID v7 via platform_sdk.ids); RQ-003 (canonical JSON cross-language compatibility); RQ-004 (empty Ledger get_tip sentinel); RQ-005 (connection retry policy — 1 reconnect + 1 retry)
- **D6** — Gap Analysis: 4 clarifications resolved (CLR-001 fail-fast connect; CLR-002 empty tip sentinel; CLR-003 floats-as-strings; CLR-004 inclusive read_range bounds); 5 gaps all resolved; isolation checks PASS for Turn C, Turn D, Turn E
- **D9** — Holdout Scenarios: **NOT shown to builder agents.** Contains adversarial test cases generated independently from D2+D4. The evaluator runs these after the build is complete.
