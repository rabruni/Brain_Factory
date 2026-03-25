# D7: Plan — Write Path (FMWK-002)
Meta: v:1.0.0 (matches D2) | status:Final | constitution: D1 v1.0.0 | gap analysis: D6 PASS (0 open)

---

## Summary

The Write Path package implements DoPeJarMo's synchronous mutation boundary: callers submit a `MutationRequest`, the service appends it through the Ledger contract, immediately folds it into the Graph contract, and only then returns a `MutationReceipt`. The same package coordinates session-boundary snapshot creation, startup recovery from a snapshot marker plus post-snapshot replay, and full-ledger refold for governed retroactive healing. The first concrete use case is a live `signal_delta` mutation from HO1: the service validates the request, calls the Ledger append contract exactly once, folds the appended event into Graph state, clamps methylation to `0.0–1.0`, and returns success only after the new state is visible to immediate Graph reads.

---

## Technical Context

| Dimension | Value |
|-----------|-------|
| Language | Python 3.11+ |
| Key Dependencies | `platform_sdk` (tier0_core: config, secrets, logging, errors, storage/filesystem; tier1_runtime as needed for validation wiring); FMWK-001 Ledger package contracts; FMWK-005 Graph package contracts; stdlib `dataclasses`, `typing`, `decimal`, `hashlib`, `json`, `pathlib` |
| Storage | Ledger durability owned by FMWK-001; Graph state owned by FMWK-005 in memory; snapshot artifacts under `/snapshots/` via `platform_sdk` storage/filesystem modules |
| Testing Framework | `pytest`; declared doubles `TD-001 LedgerPortDouble` and `TD-002 GraphPortDouble`; platform_sdk MockProvider for filesystem/config/logging concerns |
| Platform | Single kernel process, synchronous write path, no background queue or daemon |
| Performance Goals | Live mutation path remains synchronous; recovery replays only post-snapshot events when a usable snapshot exists; full replay/refold remains deterministic rather than optimized |
| Scale / Scope | KERNEL framework; initial deployment assumes one process and one Write Path instance; no multi-process writer coordination in scope |

---

## Constitution Check

| Article | Principle | Compliant | Notes |
|---------|-----------|-----------|-------|
| 1 — Splitting Test | Independently authorable from spec pack + FWK-0 alone | YES | Package boundaries stay inside synchronous mutation, snapshot orchestration, and replay/refold control. Ledger and Graph are consumed only through declared ports. |
| 2 — Merging Test | No separate capabilities absorbed | YES | No query API, no immudb administration, no HO2 orchestration policy, no HO1 prompt execution, and no package gate logic appear in scope. |
| 3 — Ownership Test | Exclusive ownership of synchronous mutation sequencing and replay coordination | YES | Only the Write Path service calls live Ledger append, only it initiates live fold, and only it starts snapshot/recover/refold flows. |
| 4 — Synchronous Acknowledgment | Success only after durable append and completed fold | YES | `submit_mutation()` returns `MutationReceipt` only after Ledger append succeeds and Graph fold finishes. |
| 5 — No Dual Writes | Callers submit one mutation request only | YES | Public surface exposes mutation, snapshot, recovery, and refold methods only; callers never write Ledger and Graph separately. |
| 6 — Fold, Don’t Interpret | Mechanical fold only | YES | Fold handlers map event fields to Graph state changes without retrieval policy, semantic interpretation, or work-order logic. |
| 7 — Range-Bounded Signal Accumulation | Methylation always stays in `0.0–1.0` | YES | Signal and methylation folds use additive arithmetic with clamping per D6 CLR-001. |
| 8 — Replayability Over Time | Rebuild from snapshot marker + replay or full replay | YES | Recovery and refold use Ledger sequence boundaries and Graph save/load/reset interfaces only; no hidden side state. |
| 9 — Deterministic Failure Posture | Block and surface typed errors | YES | Append, fold, snapshot, and replay failures return typed errors; fold failure after durable append blocks further progress until recovery. |
| 10 — Platform SDK Contract | Covered concerns use `platform_sdk` only | YES | Storage/filesystem, config, secrets, logging, and errors route through `platform_sdk`; no raw immudb or uncontrolled filesystem helpers appear in plan. |

---

## Architecture Overview

```text
Callers
  HO1 / HO2 system path / runtime startup-shutdown / FMWK-006
                |
                | MutationRequest / create_snapshot / recover / refold_from_genesis
                v
      +--------------------------------------+
      | WritePathService (service.py)        |
      | - submit_mutation()                  |
      | - create_snapshot()                  |
      | - recover()                          |
      | - refold_from_genesis()              |
      +------------------+-------------------+
                         | live append/fold
            +------------+-------------+
            |                          |
            v                          v
  LedgerPort (ports.py)         GraphPort (ports.py)
  append / read_since /         fold_event / snapshot /
  get_tip                       load_snapshot / reset_graph
            |                          |
            +------------+-------------+
                         |
                         v
              RecoveryCoordinator (recovery.py)
              - replay after snapshot
              - full replay from genesis
              - durable boundary tracking

Support modules:
  models.py   -> MutationRequest, MutationReceipt, SnapshotDescriptor, RecoveryCursor
  errors.py   -> WritePathAppendError, WritePathFoldError, SnapshotWriteError, ReplayRecoveryError
  folds.py    -> event-type fold handlers + methylation clamp
  system_events.py -> system-event request builders
```

### Component Responsibilities

**errors.py**
- File: `write_path/errors.py`
- Responsibility: Define the four typed write-path errors with stable codes and messages.
- Implements: D4 ERR-001, ERR-002, ERR-003, ERR-004
- Depends On: stdlib only
- Exposes: `WritePathAppendError`, `WritePathFoldError`, `SnapshotWriteError`, `ReplayRecoveryError`

**models.py**
- File: `write_path/models.py`
- Responsibility: Dataclasses for D3 entities and typed helper records used by the service layer.
- Implements: D3 E-001, E-002, E-003, E-004
- Depends On: `dataclasses`, `typing`
- Exposes: `MutationRequest`, `MutationReceipt`, `SnapshotDescriptor`, `RecoveryCursor`

**ports.py**
- File: `write_path/ports.py`
- Responsibility: Declare the package-local dependency interfaces and test-double contracts.
- Implements: D4 inbound/outbound dependency expectations; D6 testable surface assumptions
- Depends On: `typing`, `models.py`
- Exposes:
  - `class LedgerPort(Protocol): append(...), read_since(...), get_tip()`
  - `class GraphPort(Protocol): fold_event(...), export_snapshot(...), load_snapshot(...), reset_state()`

**folds.py**
- File: `write_path/folds.py`
- Responsibility: Mechanical fold functions for supported event types, including bounded methylation arithmetic.
- Implements: SC-001, SC-002, SC-003, SC-008; D4 SIDE-002
- Depends On: `decimal`, `models.py`, `errors.py`
- Exposes:
  - `fold_live_event(graph: GraphPort, event: dict) -> None`
  - `clamp_methylation(value: Decimal) -> Decimal`

**system_events.py**
- File: `write_path/system_events.py`
- Responsibility: Build allowed system-path requests for `session_start`, `session_end`, and `snapshot_created`.
- Implements: SC-002, SC-004
- Depends On: `models.py`
- Exposes:
  - `build_session_start_request(...) -> MutationRequest`
  - `build_session_end_request(...) -> MutationRequest`
  - `build_snapshot_created_request(descriptor: SnapshotDescriptor, ...) -> MutationRequest`

**recovery.py**
- File: `write_path/recovery.py`
- Responsibility: Snapshot, replay, and full-refold orchestration against Ledger and Graph ports.
- Implements: SC-004, SC-005, SC-006, SC-009; D4 IN-002, IN-003, IN-004
- Depends On: `ports.py`, `models.py`, `system_events.py`, `errors.py`, `platform_sdk` storage/filesystem helpers
- Exposes:
  - `create_snapshot(graph: GraphPort, ledger: LedgerPort, ...) -> SnapshotDescriptor`
  - `recover_graph(graph: GraphPort, ledger: LedgerPort, snapshot: SnapshotDescriptor | None) -> RecoveryCursor`
  - `refold_from_genesis(graph: GraphPort, ledger: LedgerPort) -> RecoveryCursor`

**service.py**
- File: `write_path/service.py`
- Responsibility: Public Write Path service coordinating validation, append-then-fold sequencing, and failure posture.
- Implements: SC-001 through SC-009; D4 IN-001 through IN-004
- Depends On: `ports.py`, `models.py`, `folds.py`, `recovery.py`, `errors.py`, `platform_sdk` logging/config/errors
- Exposes:
  - `class WritePathService`
  - `submit_mutation(self, request: MutationRequest) -> MutationReceipt`
  - `create_snapshot(self) -> SnapshotDescriptor`
  - `recover(self, snapshot: SnapshotDescriptor | None = None) -> RecoveryCursor`
  - `refold_from_genesis(self) -> RecoveryCursor`

**__init__.py**
- File: `write_path/__init__.py`
- Responsibility: Clean public exports for the package.
- Exposes: service, models, and typed errors only

### File Creation Order

```text
staging/FMWK-002-write-path/
├── write_path/
│   ├── errors.py            Phase 0 — error vocabulary first
│   ├── models.py            Phase 0 — D3 entities
│   ├── ports.py             Phase 0 — dependency contracts and doubles
│   ├── folds.py             Phase 1 — mechanical fold logic
│   ├── system_events.py     Phase 1 — allowed system-event builders
│   ├── recovery.py          Phase 2 — snapshot/replay/refold orchestration
│   ├── service.py           Phase 2 — public synchronous service
│   └── __init__.py          Phase 3 — exports
├── tests/
│   ├── conftest.py                Phase 0 — doubles and shared fixtures
│   ├── test_models.py             Phase 0 — D3 entity coverage
│   ├── test_folds.py              Phase 1 — bounded arithmetic and event folds
│   ├── test_service_mutations.py  Phase 2 — live mutation sequencing and failures
│   ├── test_recovery.py           Phase 2 — snapshot/replay/refold paths
│   └── test_system_events.py      Phase 1 — allowed system-path requests
└── README.md
```

### Testing Strategy

- Unit Tests: use `TD-001 LedgerPortDouble` and `TD-002 GraphPortDouble` from `tests/conftest.py`. Cover live mutation sequencing, append failure, fold failure after durable append, bounded methylation arithmetic, snapshot artifact creation, post-snapshot replay, full replay fallback, and full refold behavior.
- Integration Tests: optional package-level integration against staged FMWK-001 Ledger package and staged FMWK-005 Graph package once both exist. No live kernel or live immudb required for the unit suite.
- Smoke Test: `cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/ -v`
  Expected result: all write-path tests pass, including append/fold, snapshot, recovery, and refold scenarios.

### Complexity Tracking

| Component | Est. Lines | Risk | Notes |
|-----------|-----------|------|-------|
| errors.py | 40 | Low | Typed error classes only |
| models.py | 110 | Low | D3 entities and helper parsing |
| ports.py | 70 | Low | Protocols and test-double interfaces |
| folds.py | 160 | Medium | Event-type fold behavior and clamping |
| system_events.py | 80 | Low | Restricted request builders |
| recovery.py | 180 | Medium | Snapshot/replay boundary logic |
| service.py | 180 | High | Append/fold sequencing and failure posture |
| __init__.py | 20 | Low | Exports only |
| **Total Source** | **~840** | — | |
| conftest.py | 90 | Low | Doubles and fixtures |
| test_models.py | 70 | Low | Entity/schema coverage |
| test_folds.py | 140 | Medium | Event folds and bounds |
| test_system_events.py | 70 | Low | System-event surface |
| test_service_mutations.py | 220 | High | Core sequencing + failure cases |
| test_recovery.py | 220 | Medium | Snapshot/replay/refold |
| **Total Tests** | **~810** | — | |
| **Combined** | **~1650** | — | |

### Migration Notes

Greenfield — no migration.
