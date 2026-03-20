# D7: Plan — FMWK-001-ledger
Meta: v:1.0.0 (matches D2) | status:Final | constitution: D1 1.0.0 | gap analysis: D6 PASS (0 open)

## Summary
FMWK-001-ledger will be built as a narrow Python ledger package that owns exactly four things: canonical event models, canonical serialization and hash computation, a Ledger-owned immudb storage adapter, and a public Ledger service that appends, reads, replays, and verifies events. The first use case is the write-path appending a genesis event and subsequent events without caller-controlled sequencing while preserving exact replay and offline verification behavior.

## Technical Context
Language/Version | Python 3.11+ | Key Dependencies | `platform_sdk` for config/secrets/logging, `pytest` for tests, immudb client only behind the Ledger storage boundary if required by the runtime | Storage | immudb `ledger` database over gRPC plus offline exported event bytes | Testing Framework | `pytest` with fake backend unit tests and opt-in immudb integration tests | Platform | macOS/Linux dev, single-writer DoPeJarMo kernel runtime | Performance Goals | synchronous single-event append, deterministic replay, exact hash reproducibility | Scale/Scope | one framework package, one public ledger interface, no fold/graph/gate logic

## Constitution Check
| Article | Principle | Compliant (YES/NO) | Notes (how architecture satisfies) |
| Article 1 | Splitting | YES | Components stop at event storage, schema ownership, chain verification, ordered retrieval, and storage abstraction. No fold or graph code is planned. |
| Article 2 | Merging | YES | Write-path, graph, orchestration, and package-lifecycle logic are excluded from the file plan and public interfaces. |
| Article 3 | Ownership | YES | `models.py` owns `LedgerEvent`, `LedgerTip`, and `ChainVerificationResult`; callers consume those via the public ledger interface only. |
| Article 4 | Append-Only Truth | YES | No delete, rewrite, truncate, or admin mutation interfaces are created; append persists exactly one new event or fails closed. |
| Article 5 | Deterministic Hash Chain | YES | `serialization.py` centralizes canonical JSON bytes and exact `sha256:<64 hex>` formatting for append and verify flows. |
| Article 6 | Interface Isolation | YES | Only the Ledger package exposes storage operations; configuration comes through `platform_sdk`, and callers never pass sequence numbers or touch immudb APIs. |
| Article 7 | Cold-Storage Verifiability | YES | `verify_chain` operates on online reads and offline exported bytes with the same serializer and comparison path. |
| Article 8 | Fail Closed | YES | Explicit error types for connection, serialization, sequence conflict, and corruption halt the operation with no silent repair or hidden retry loop. |

## Architecture Overview
```text
Append caller
    |
    v
Ledger service ------------------------> models / contract validation
    |                                        |
    | append/read/replay/verify              v
    +-------------------------------> canonical serialization + hashing
    |                                        |
    v                                        v
Ledger storage adapter --------------> immudb event bytes / offline export bytes
    |
    v
ordered Ledger events / tip / verification result
```

### Component Responsibilities
- File: `ledger/__init__.py`
  Responsibility | package exports only | Implements (D2 SC-003) | Depends On | `service.py`, `models.py`, `errors.py` | Exposes (public interface/signatures) | `Ledger`, `LedgerEvent`, `LedgerTip`, `ChainVerificationResult`
- File: `ledger/errors.py`
  Responsibility | typed failure boundary | Implements (D2 SC-007, SC-008, SC-009, SC-010) | Depends On | stdlib only | Exposes (public interface/signatures) | `LedgerConnectionError`, `LedgerSerializationError`, `LedgerSequenceError`, `LedgerCorruptionError`
- File: `ledger/models.py`
  Responsibility | canonical request/response/event structures and validators | Implements (D2 SC-005, SC-006) | Depends On | stdlib dataclasses/typing | Exposes (public interface/signatures) | `LedgerEvent`, `EventProvenance`, payload dataclasses, `LedgerTip`, `ChainVerificationResult`
- File: `ledger/serialization.py`
  Responsibility | canonical JSON byte generation and SHA-256 helpers for append and verify | Implements (D2 SC-001, SC-002, SC-004, SC-008, SC-010) | Depends On | `models.py`, `errors.py`, stdlib `json`/`hashlib` | Exposes (public interface/signatures) | `canonical_event_bytes(event) -> bytes`, `compute_event_hash(event) -> str`, `event_key(sequence: int) -> str`
- File: `ledger/backend.py`
  Responsibility | Ledger-owned storage boundary, reconnect-once behavior, ordered byte retrieval | Implements (D2 SC-002, SC-003, SC-009) | Depends On | `platform_sdk`, `errors.py`, runtime immudb client boundary | Exposes (public interface/signatures) | `connect()`, `append_bytes(key: str, value: bytes) -> None`, `read_bytes(sequence: int) -> bytes`, `read_range_bytes(start: int, end: int) -> list[bytes]`, `read_since_bytes(sequence_number: int) -> list[bytes]`, `get_tip_bytes() -> tuple[int, bytes] | None`
- File: `ledger/service.py`
  Responsibility | public Ledger contract implementation with internal sequence assignment, append-only behavior, replay, and online/offline verification | Implements (D2 SC-001 through SC-010) | Depends On | `models.py`, `serialization.py`, `backend.py`, `errors.py` | Exposes (public interface/signatures) | `class Ledger`, `append(request) -> tuple[int, LedgerEvent]`, `read(sequence_number: int) -> LedgerEvent`, `read_range(start: int, end: int) -> list[LedgerEvent]`, `read_since(sequence_number: int) -> list[LedgerEvent]`, `verify_chain(start: int | None = None, end: int | None = None, source_mode: str = "online", offline_events: list[LedgerEvent] | None = None) -> ChainVerificationResult`, `get_tip() -> LedgerTip | None`
- File: `tests/test_models.py`
  Responsibility | envelope and payload validation coverage | Implements (D2 SC-005, SC-006) | Depends On | `models.py` | Exposes (public interface/signatures) | pytest test functions only
- File: `tests/test_serialization.py`
  Responsibility | exact canonical bytes, genesis hash input, Unicode/null handling, corruption-detection helpers | Implements (D2 SC-001, SC-004, SC-008, SC-010) | Depends On | `serialization.py`, `models.py` | Exposes (public interface/signatures) | pytest test functions only
- File: `tests/test_append_and_read.py`
  Responsibility | append sequencing, read, range, since, and tip behavior against a fake backend | Implements (D2 SC-001, SC-002, SC-003, SC-005, SC-006, SC-007) | Depends On | `service.py`, fake backend fixture | Exposes (public interface/signatures) | pytest test functions only
- File: `tests/test_verification.py`
  Responsibility | online/offline verification parity and first-break detection | Implements (D2 SC-004, SC-010) | Depends On | `service.py`, exported fixture bytes | Exposes (public interface/signatures) | pytest test functions only
- File: `tests/test_connection_failures.py`
  Responsibility | reconnect-once and fail-closed connection-path coverage | Implements (D2 SC-009) | Depends On | `backend.py`, `service.py` | Exposes (public interface/signatures) | pytest test functions only
- File: `tests/test_integration_immudb.py`
  Responsibility | opt-in real immudb contract verification | Implements (D2 SC-001, SC-002, SC-003, SC-004, SC-009) | Depends On | runtime immudb availability | Exposes (public interface/signatures) | pytest integration tests only

### File Creation Order
```text
framework-root/
  ledger/
    __init__.py                 # public exports only
    errors.py                   # typed ledger failure surface
    models.py                   # canonical event/request/response structures
    serialization.py            # canonical bytes, hash helpers, sequence key formatting
    backend.py                  # Ledger-owned storage adapter and reconnect behavior
    service.py                  # public Ledger contract implementation
  tests/
    conftest.py                 # fake backend and shared fixtures
    test_models.py              # envelope and payload schema tests
    test_serialization.py       # canonical JSON and hash-chain tests
    test_append_and_read.py     # append, read, replay, and tip tests
    test_verification.py        # online/offline verification parity tests
    test_connection_failures.py # connection and retry behavior tests
    test_integration_immudb.py  # opt-in real immudb tests
```

### Testing Strategy
- Unit Tests: validate event and payload constraints, exact canonical byte output, sequence assignment, append-only behavior, replay ordering, corruption detection, and reconnect-once logic using a fake backend. No live immudb in the default test loop.
- Integration Tests: run against a real immudb instance only when the environment provides it; verify append/read/verify/get_tip behavior matches the fake-backend contract and that missing-database handling fails with `LedgerConnectionError`.
- Smoke Test: `python -m pytest -q tests/test_verification.py -k online_offline_parity` should report one passing verification-parity test with no failures.

### Complexity Tracking
| Component | Est. Lines | Risk (Low/Med/High) | Notes |
| `ledger/errors.py` | 20 | Low | Straight typed exceptions. |
| `ledger/models.py` | 160 | Medium | Holds canonical schema boundaries and field validation. |
| `ledger/serialization.py` | 120 | High | Byte-level correctness governs hash-chain determinism. |
| `ledger/backend.py` | 140 | High | Connection and retry behavior can violate fail-closed semantics if loose. |
| `ledger/service.py` | 220 | High | Central contract enforcement for append/replay/verify. |
| `tests/` | 420 | Medium | Needs scenario-for-scenario coverage plus integration guards. |
| Total source | 660 | High | Hash/sequence correctness is the primary implementation risk. |
| Total tests | 420 | Medium | Coverage breadth is intentional because D2/D4 are contract-heavy. |

### Migration Notes
Greenfield — no migration.
