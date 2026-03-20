# D7: Plan — FMWK-001-ledger
Meta: v:1.0.0 (matches D2) | status:Final | constitution: D1 1.0.0 | gap analysis: D6 PASS (0 open)

## Summary
FMWK-001-ledger builds the append-only, hash-chained truth store for DoPeJarMo. The implementation stays mechanically narrow: validate inbound append requests, assign the next sequence inside the ledger boundary, serialize the event into canonical UTF-8 JSON, persist exactly one event synchronously, expose ordered reads and replay, and verify the chain online or offline. First use case: the write path appends a `session_start` or other approved event and receives a durable ledger event with assigned sequence, previous hash, and canonical hash.

## Technical Context
Language/Version | Key Dependencies | Storage | Testing Framework | Platform | Performance Goals | Scale/Scope
Python 3.x | Python stdlib plus `platform_sdk` config/secrets/logging/errors surfaces; immudb reached only through the ledger abstraction boundary | immudb `ledger` database plus offline exported event data for verification | `pytest` | local staging package in `staging/FMWK-001-ledger` | synchronous single-event append with deterministic byte-for-byte hash behavior and single reconnect retry on disconnect | one framework package implementing SC-001 through SC-011 only

## Constitution Check
| Article | Principle | Compliant (YES/NO) | Notes (how architecture satisfies) |
| Article 1 | Splitting | YES | The package contains only ledger-owned contracts, canonical event serialization, persistence, replay, and verification; no other framework behavior is required to author or test it. |
| Article 2 | Merging | YES | Public interfaces stop at append/read/read_range/read_since/get_tip/verify_chain; no graph fold logic, gate execution, work-order logic, or business semantics are introduced. |
| Article 3 | Ownership | YES | The implementation owns the ledger event envelope, sequence assignment, previous-hash linkage, and ordered replay; payload semantics beyond the minimum approved schemas remain external. |
| Article 4 | Source Of Truth | YES | Every acknowledged mutation flows through synchronous append and is returned as a persisted ledger event; reads and verification operate on the stored event stream. |
| Article 5 | Append-Only Immutability | YES | No delete, truncate, compact, or rewrite paths are planned; storage code writes one new event per append and exposes read-only query surfaces otherwise. |
| Article 6 | Separation Of Concerns | YES | Component boundaries isolate request validation, canonical serialization, storage access, and verification; no folding, gate checks, or orchestration state machines appear in the ledger package. |
| Article 7 | Deterministic Hashing And Replay | YES | A dedicated canonical serialization module defines exact JSON bytes, SHA-256 string formatting, genesis previous hash, and ordered replay behavior used by both append and verify paths. |
| Article 8 | Cold-Storage Verifiability And Failure Boundaries | YES | Offline verification reads exported events without runtime services, and explicit ledger errors cover connection, corruption, sequence, and serialization failures. |

## Architecture Overview
```text
append caller
   |
   v
ledger/api.py
   |
   +--> ledger/schemas.py        validates inbound request shape and payload catalog
   +--> ledger/serialization.py  canonical UTF-8 JSON bytes + sha256:<hex>
   +--> ledger/store.py          immudb-backed persistence boundary + reconnect-once
   +--> ledger/verify.py         ordered replay + online/offline chain verification
   |
   v
OUT-001 / OUT-002 / OUT-003 / OUT-004 / OUT-005

offline export file
   |
   v
ledger/verify.py ---> Verification Result
```

### Component Responsibilities
- File: `staging/FMWK-001-ledger/ledger/__init__.py`
  Responsibility | package exports for the builder-facing ledger surface | Implements (D2 SC-001, SC-004, SC-005, SC-006) | Depends On `api.py` | Exposes `Ledger`, `LedgerConnectionError`, `LedgerCorruptionError`, `LedgerSequenceError`, `LedgerSerializationError`
- File: `staging/FMWK-001-ledger/ledger/errors.py`
  Responsibility | framework-local error classes and error-code mapping aligned to D4 ERR-001..ERR-004 | Implements (D2 SC-008, SC-009, SC-010, SC-011) | Depends On stdlib and `platform_sdk` error surface if wrapped | Exposes error classes/constants
- File: `staging/FMWK-001-ledger/ledger/models.py`
  Responsibility | typed event envelope, provenance, tip, and verification result models matching D3 E-001..E-009 | Implements (D2 SC-001, SC-003, SC-005, SC-006, SC-007) | Depends On stdlib dataclasses/typing | Exposes model constructors and serialization helpers
- File: `staging/FMWK-001-ledger/ledger/schemas.py`
  Responsibility | minimum approved event catalog and payload validation rules | Implements (D2 SC-003, SC-007, SC-011) | Depends On `models.py` | Exposes `validate_append_request(...)`, `validate_payload(...)`
- File: `staging/FMWK-001-ledger/ledger/serialization.py`
  Responsibility | canonical JSON normalization, hash input production, SHA-256 formatting, zero-hash constant | Implements (D2 SC-001, SC-002, SC-005, SC-008, SC-011) | Depends On `models.py`, `errors.py` | Exposes `canonical_event_bytes(...)`, `compute_event_hash(...)`
- File: `staging/FMWK-001-ledger/ledger/store.py`
  Responsibility | immudb persistence boundary, sequence/tip reads, atomic append critical section, synchronous write, reconnect-once behavior | Implements (D2 SC-001, SC-002, SC-004, SC-006, SC-009, SC-010) | Depends On `platform_sdk` config/secrets/logging/errors, `models.py`, `serialization.py`, `errors.py` | Exposes `LedgerStore` methods `append_event(...)`, `read(...)`, `read_range(...)`, `read_since(...)`, `get_tip(...)`
- File: `staging/FMWK-001-ledger/ledger/verify.py`
  Responsibility | ordered replay verification for online and offline sources, first-break reporting | Implements (D2 SC-005, SC-008, SC-011) | Depends On `models.py`, `serialization.py`, `errors.py`, `store.py` | Exposes `verify_chain(...)`, `verify_events(...)`
- File: `staging/FMWK-001-ledger/ledger/api.py`
  Responsibility | public orchestration-free ledger facade that wires validation, persistence, and verification together | Implements (D2 SC-001 through SC-011) | Depends On all ledger modules | Exposes `class Ledger` with `append`, `read`, `read_range`, `read_since`, `verify_chain`, `get_tip`
- File: `staging/FMWK-001-ledger/tests/test_serialization.py`
  Responsibility | fixture-level tests for canonical bytes, hash formatting, genesis previous hash, and serialization failure handling | Implements (D2 SC-001, SC-002, SC-005, SC-011) | Depends On `serialization.py`, `models.py` | Exposes pytest tests
- File: `staging/FMWK-001-ledger/tests/test_store.py`
  Responsibility | append/read/tip/range/reconnect/sequence-race tests over the storage boundary using a deterministic fake client or mock provider | Implements (D2 SC-001, SC-002, SC-004, SC-006, SC-009, SC-010) | Depends On `store.py`, `api.py` | Exposes pytest tests
- File: `staging/FMWK-001-ledger/tests/test_verify.py`
  Responsibility | online/offline verification and corruption detection tests | Implements (D2 SC-005, SC-008, SC-011) | Depends On `verify.py`, `store.py` | Exposes pytest tests
- File: `staging/FMWK-001-ledger/tests/test_api.py`
  Responsibility | end-to-end API surface tests for approved event types including snapshot reference event | Implements (D2 SC-003, SC-007, SC-010) | Depends On `api.py` | Exposes pytest tests
- File: `staging/FMWK-001-ledger/README.md`
  Responsibility | local package usage notes and test commands for the staged framework only | Implements documentation only | Depends On D10 | Exposes none

### File Creation Order
```text
staging/FMWK-001-ledger/
├── ledger/
│   ├── __init__.py                  # public package exports
│   ├── errors.py                    # explicit ledger error types/codes
│   ├── models.py                    # D3 envelope, provenance, tip, verification models
│   ├── schemas.py                   # approved event catalog and payload validation
│   ├── serialization.py             # canonical JSON bytes and SHA-256 helpers
│   ├── store.py                     # immudb-facing persistence boundary
│   ├── verify.py                    # online/offline chain verification
│   └── api.py                       # public Ledger facade
├── tests/
│   ├── test_serialization.py        # deterministic byte/hash fixtures
│   ├── test_store.py                # append/read/tip/connection behavior
│   ├── test_verify.py               # corruption + offline verification behavior
│   └── test_api.py                  # approved event-type integration coverage
└── README.md                        # local usage and regression commands
```

### Testing Strategy
- Unit Tests: lock down canonical JSON bytes, hash string formatting, zero-hash genesis behavior, payload validation, and error mapping with deterministic fixtures and no live infrastructure.
- Integration Tests: exercise append/read/read_range/read_since/get_tip/verify_chain against a controlled ledger storage fake that models synchronous writes, single retry, and tip-race rejection without requiring real immudb in every test.
- Smoke Test: `PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests`
  Expected result: all ledger tests pass with no skipped failures for SC-001 through SC-011 coverage.

### Complexity Tracking
| Component | Est. Lines | Risk (Low/Med/High) | Notes |
| errors.py | 40 | Low | Straight error definitions and mapping. |
| models.py | 140 | Medium | Must reflect D3 exactly and preserve serialization invariants. |
| schemas.py | 120 | Medium | Must stay within the approved minimum event catalog only. |
| serialization.py | 140 | High | Byte-level contract; any drift breaks chain verification. |
| store.py | 220 | High | Atomic sequencing, reconnect-once behavior, and append-only safety all live here. |
| verify.py | 120 | High | Must align online and offline verification exactly. |
| api.py | 120 | Medium | Thin facade; risk is accidental scope creep. |
| tests/test_serialization.py | 120 | High | Fixture precision is critical. |
| tests/test_store.py | 180 | High | Needs explicit race and connection-failure coverage. |
| tests/test_verify.py | 120 | High | Must prove corruption detection and offline parity. |
| tests/test_api.py | 120 | Medium | Ensures event catalog and snapshot marker behavior are wired correctly. |
| README.md | 40 | Low | Operator-facing build notes only. |

Totals: source ~900 lines | tests ~540 lines

### Migration Notes
Greenfield in `staging/FMWK-001-ledger`; use the pre-existing `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/ledger.py` only as reference material, not as authority.
