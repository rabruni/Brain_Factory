# D10: Agent Context — FMWK-001-ledger
Meta: pkg:FMWK-001-ledger | updated:2026-03-01

---

## What This Project Does

You are building the Ledger — the append-only, hash-chained event store at the foundation of
DoPeJarMo. Every state mutation in the system gets recorded here as an immutable event. You wrap
immudb (a hash-verified key-value store) behind a stable six-method interface, assign monotonic
sequence numbers and SHA-256 hash-chain links internally on every write so no caller can produce
a forked or non-monotonic sequence, and guarantee that a CLI tool connecting directly to immudb
on :3322 with the kernel stopped can verify the entire chain with no other runtime services.
Your output is consumed first by FMWK-002 (write-path), which calls `append()` for every state
mutation and `read_since()` to reconstruct the Graph after a snapshot. You also add an immudb
adapter to `platform_sdk.tier0_core.data` (the only place immudb SDK may be imported) before
wiring it into the Ledger class.

---

## Architecture Overview

```
Callers ──→ Ledger.append(event: dict) ──→ int (sequence assigned)
         ──→ Ledger.read(seq) ──→ LedgerEvent
         ──→ Ledger.read_range(start, end) ──→ list[LedgerEvent]
         ──→ Ledger.read_since(seq) ──→ list[LedgerEvent]
         ──→ Ledger.get_tip() ──→ LedgerTip
         ──→ Ledger.verify_chain(start?, end?) ──→ VerifyChainResult
         ──→ Ledger.connect(config) ──→ None (or LedgerConnectionError)

staging/FMWK-001-ledger/
├── ledger/
│   ├── __init__.py          exports: Ledger, LedgerConfig, LedgerEvent, LedgerTip,
│   │                                 VerifyChainResult, Ledger*Error
│   ├── errors.py            LedgerConnectionError, LedgerCorruptionError,
│   │                        LedgerSequenceError, LedgerSerializationError
│   ├── schemas.py           LedgerEvent (E-001), LedgerTip (E-003),
│   │                        VerifyChainResult (E-004), payload schemas (E-005..E-008),
│   │                        EVENT_TYPE_CATALOG (E-009, frozenset of 15 types)
│   ├── serializer.py        compute_hash(), check_no_floats(), canonical_bytes(),
│   │                        GENESIS_SENTINEL constant
│   └── ledger.py            Ledger class — all 7 public methods, threading.Lock mutex
├── platform_sdk/tier0_core/data/
│   └── immudb_adapter.py    ImmudbAdapter (Protocol), MockImmudbAdapter,
│                            RealImmudbAdapter, get_adapter()
└── tests/
    ├── unit/
    │   ├── test_serializer.py   12 tests — pure serializer contract
    │   └── test_ledger_unit.py  30 tests — all scenarios via MockProvider
    └── integration/
        ├── test_ledger_integration.py  6 tests — Docker immudb on :3322
        └── test_cold_storage.py        2 tests — SC-005 offline verify
```

---

## Key Patterns

**1. Canonical Serialization Contract (E-002 / SIDE-002)** — D3 E-002, D5 RQ-005
Every hash is computed from: `json.dumps(event_minus_hash_field, sort_keys=True, separators=(',',':'), ensure_ascii=False)` → UTF-8 encode → SHA-256 → lowercase hex → prefix `"sha256:"`. This exact algorithm must be reproduced by any verifier in any language. Never deviate.

**2. Float Prohibition at Input Boundary** — D1 NEVER, D5 RQ-005
Before any serialization, `check_no_floats()` recursively walks the event dict and raises `LedgerSerializationError` if any Python `float` is found anywhere. This is enforced at `append()` time — not at read time or verify time — so the bug is caught at the caller, not during chain verification.

**3. Mutex Atomicity for Append (CLR-001)** — D5 RQ-001, D6 CLR-001
`append()` acquires `threading.Lock()` before reading the tip. The sequence is: lock → get_tip() → compute_seq → assign fields → kv_set → release. This prevents sequence gaps if (design violation) two threads call append concurrently. `LedgerSequenceError` is the catch if the lock fails.

**4. Infrastructure Separation on Connect (D1 Article 9)** — D2 SC-EC-004
`connect()` calls `list_databases()` on the adapter. If `"ledger"` is not in the result, it raises `LedgerConnectionError` immediately with zero admin calls. It NEVER calls `CreateDatabaseV2`. GENESIS is the only place that creates the database.

**5. Cold-Storage Verifiability (D1 Article 8)** — D2 SC-005
`verify_chain()` uses only the adapter connection (immudb gRPC :3322). It imports nothing from ledger/, Graph, HO1, HO2, or kernel. The CLI tool and the in-process call path produce identical results.

**6. Platform SDK Abstraction (D1 Article 7)** — D5 RQ-004
The only file permitted to import `immudb` SDK is `immudb_adapter.py` (RealImmudbAdapter class). All other FMWK-001 code imports from `platform_sdk.tier0_core.data`. Static analysis gate T-012 enforces this.

---

## Commands

```bash
# Working directory: staging/FMWK-001-ledger/ (relative to Brain_Factory repo root)

# Install dev dependencies (Python 3.12+ required)
pip install pytest immudb-py uuid7

# Run all unit tests (no Docker needed)
python -m pytest tests/unit/ -v

# Run one specific test
python -m pytest tests/unit/test_serializer.py::test_canonical_json_sorted_keys -v

# Run full unit regression (expected: 42 passed)
python -m pytest tests/unit/ -v --tb=short

# Start Docker immudb (required for integration tests only)
cd ../../  # repo root
docker-compose up -d ledger

# Run integration tests (Docker immudb must be up on :3322)
cd staging/FMWK-001-ledger
python -m pytest tests/integration/test_ledger_integration.py -v

# Run cold-storage test (stops kernel container mid-test — Docker required)
python -m pytest tests/integration/test_cold_storage.py -v

# Full regression (all 50 tests — Docker required for integration)
python -m pytest tests/ -v --tb=short

# Static analysis gate (must exit 0)
bash scripts/static_analysis.sh

# Check serializer output manually
python -c "
from ledger.serializer import compute_hash, GENESIS_SENTINEL
event = {'event_id': 'test', 'event_type': 'session_start', 'schema_version': '1.0.0',
         'timestamp': '2026-03-01T00:00:00Z', 'provenance': {'framework_id': 'FMWK-001',
         'pack_id': 'PC-001', 'actor': 'system'}, 'payload': {}, 'sequence': 0,
         'previous_hash': GENESIS_SENTINEL}
print(compute_hash(event))
"
```

---

## Tool Rules

| USE THIS | NOT THIS | WHY |
|----------|----------|-----|
| `platform_sdk.tier0_core.data.get_adapter()` | `import immudb` directly | D1 Article 7; adapter is the only permitted immudb import boundary |
| `platform_sdk.tier0_core.config` | `os.getenv()` for config | Platform SDK contract (AGENT_BOOTSTRAP.md) — non-negotiable |
| `platform_sdk.tier0_core.secrets.get_secret()` | hardcoded credentials or `os.getenv()` for secrets | Same contract; secrets never in source |
| `platform_sdk.tier0_core.errors` base class | bare `raise Exception(...)` | D1 Tooling Constraints; error reporting contract |
| `platform_sdk.tier0_core.logging` | `print()`, raw `structlog`, `logging.basicConfig()` | D1 Tooling Constraints |
| `platform_sdk.tier2_reliability.health` | custom `/health` logic | D1 Tooling Constraints |
| `platform_sdk.tier2_reliability` metrics module | raw Prometheus client | D1 Tooling Constraints |
| `json.dumps(obj, sort_keys=True, separators=(',',':'), ensure_ascii=False)` | any JSON lib with different defaults | E-002 byte-level contract; alternative args produce different bytes |
| `hashlib.sha256(utf8_bytes).hexdigest()` prefixed `"sha256:"` | base64, uppercase, `0x` prefix | D1 Article 5; case and format are a byte-level contract |
| `MockImmudbAdapter` in all unit tests | real immudb in unit tests | D1 Dev Workflow Constraint 5; unit tests never spin up real services |
| `uuid.uuid7()` (Python 3.12+ stdlib) | `uuid.uuid4()` or any other UUID version | D5 RQ-002; time-ordered UUID required per D3 E-001 |

---

## Coding Conventions

| Convention | Rule |
|------------|------|
| Python version | 3.12+ required (uses `uuid.uuid7()`, `X \| Y` type union syntax) |
| Stdlib-first | Check `platform_sdk/MODULES.md` before adding any external package |
| Type hints | Required on all public method signatures; `from __future__ import annotations` at top of files that use forward refs |
| Dataclasses | Use `@dataclass(frozen=True)` for schema types (LedgerEvent, LedgerTip, VerifyChainResult, payload schemas) |
| Error handling | All errors from `platform_sdk.tier0_core.errors` base — never bare `Exception` |
| Exit codes | `pytest` controls test exit codes; scripts exit 0 on success, 1 on failure |
| Test framework | `pytest` only — no `unittest.TestCase` |
| Decimal fields | All decimal values are `str` type — never `float`. Enforced at `check_no_floats()` and at dataclass field types. |
| Null fields | Included in canonical JSON as `"key": null` — never omitted |
| Zero admin ops | Never call `DatabaseDelete`, `DropDatabase`, `CompactIndex`, `TruncateDatabase`, `CleanIndex` in any FMWK-001 code |
| No caller sequence | `append()` signature: `def append(self, event: dict) -> int` — sequence is NEVER a parameter |

---

## Submission Protocol

1. **Answer all 13 Questions** in your first response to the handoff. STOP. Do not write any code.
2. **Wait for human greenlight** before starting implementation.
3. **Per-behavior DTT**: For each acceptance criterion in D8, write the failing test first, then implement the behavior, then confirm the test passes. Never implement without a test.
4. **Run unit tests after every task**: `python -m pytest tests/unit/ -v` — all must pass before moving to the next task.
5. **Run static analysis gate** (`bash scripts/static_analysis.sh`) after T-012 is complete. Fix any violations before proceeding.
6. **Run full regression** before generating the results file: `python -m pytest tests/ -v --tb=short`. Must exit 0.
7. **Generate RESULTS.md** at `staging/FMWK-001-ledger/RESULTS.md` per `BUILDER_HANDOFF_STANDARD.md`. Include SHA-256 hashes for every file using `sha256:<64hex>` format.
8. **Branch naming**: `feature/FMWK-001-ledger`
9. **Commit format**: `feat(FMWK-001): <imperative description>` (e.g., `feat(FMWK-001): add canonical serializer and hash computation`)
10. **Results file path**: `staging/FMWK-001-ledger/RESULTS.md`
11. **Flag CRITICAL_REVIEW_REQUIRED** on any 13Q answer where your interpretation feels loose.

---

## Active Components

| Component | Where | Interface (signature) |
|-----------|-------|----------------------|
| `Ledger` class | `ledger/ledger.py` | `connect(config: LedgerConfig) -> None` |
| | | `append(event: dict) -> int` |
| | | `read(sequence_number: int) -> LedgerEvent` |
| | | `read_range(start: int, end: int) -> list[LedgerEvent]` |
| | | `read_since(sequence_number: int) -> list[LedgerEvent]` |
| | | `get_tip() -> LedgerTip` |
| | | `verify_chain(start: int = 0, end: int \| None = None) -> VerifyChainResult` |
| `compute_hash` | `ledger/serializer.py` | `compute_hash(event: dict) -> str` |
| `check_no_floats` | `ledger/serializer.py` | `check_no_floats(obj: Any) -> None` |
| `canonical_bytes` | `ledger/serializer.py` | `canonical_bytes(event: dict) -> bytes` |
| `GENESIS_SENTINEL` | `ledger/serializer.py` | `str` constant = `"sha256:" + "0" * 64` |
| `ImmudbAdapter` | `platform_sdk/tier0_core/data/immudb_adapter.py` | Protocol (see T-004 AC) |
| `MockImmudbAdapter` | same | `connect()`, `kv_set()`, `kv_get()`, `kv_scan()`, `list_databases()`, `set_failure_on_next_write()` |
| `get_adapter` | same | `get_adapter() -> ImmudbAdapter` |
| `LedgerEvent` | `ledger/schemas.py` | frozen dataclass (D3 E-001 fields) |
| `LedgerTip` | `ledger/schemas.py` | frozen dataclass (`sequence_number: int`, `hash: str`) |
| `VerifyChainResult` | `ledger/schemas.py` | frozen dataclass (`valid: bool`, `break_at: int \| None = None`) |
| `EVENT_TYPE_CATALOG` | `ledger/schemas.py` | `frozenset[str]` — exactly 15 event types from D3 E-009 |

---

## Links to Deeper Docs

| Doc | What to Find There |
|-----|--------------------|
| `D1_CONSTITUTION.md` | 9 articles defining NEVER boundaries; ALWAYS/ASK FIRST/NEVER permission tiers; tooling constraints table |
| `D2_SPECIFICATION.md` | All 9 primary scenarios + 4 edge cases with GIVEN/WHEN/THEN; success criteria; NOT boundaries |
| `D3_DATA_MODEL.md` | Entity schemas E-001 through E-009; canonical JSON algorithm; entity relationship map |
| `D4_CONTRACTS.md` | All 7 inbound contracts (IN-001..007); 4 outbound (OUT-001..004); 3 side-effects (SIDE-001..003); 4 error contracts (ERR-001..004) |
| `D5_RESEARCH.md` | RQ-001 (mutex decision rationale), RQ-002 (UUID v7), RQ-005 (float prohibition rationale), RQ-006 (zero-padded key format) |
| `D6_GAP_ANALYSIS.md` | 4 gaps (all RESOLVED/ASSUMED); 3 CLRs (all RESOLVED); self-check tables |
| `D7_PLAN.md` | Constitution Check (all 9 articles); architecture diagram; component responsibilities; file creation order; test strategy; complexity estimate |
| `D8_TASKS.md` | 12 tasks with acceptance criteria, dependency graph, scenario tracing, contract tracing |
| D9 (holdout scenarios) | **NOT AVAILABLE TO BUILDER.** Evaluator-only. Do not ask for it. |
