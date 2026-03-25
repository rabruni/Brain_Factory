# D10: Agent Context — Write Path (FMWK-002)
Meta: pkg:FMWK-002-write-path | updated:2026-03-21

---

## What This Project Does

The `write_path` package is DoPeJarMo's synchronous consistency layer. It accepts live mutation requests from HO1, HO2 system paths, runtime startup/shutdown logic, and package lifecycle flows; appends them through the Ledger contract; folds them immediately into Graph state; and returns success only after both steps complete. It also coordinates snapshot creation at session boundaries, startup recovery from a snapshot marker plus post-snapshot replay, and full-ledger refold for governed retroactive healing. It is not a query layer, not a policy engine, and not a background queue.

---

## Architecture Overview

```text
Callers
  ├── HO1 live mutations
  ├── HO2/runtime system events
  ├── runtime startup recovery
  └── governed maintenance refold
              |
              v
      WritePathService (service.py)
        ├── submit_mutation()
        ├── create_snapshot()
        ├── recover()
        └── refold_from_genesis()
              |
      +-------+--------+
      |                |
      v                v
 LedgerPort         GraphPort
 append()           fold_event()
 read_since()       export_snapshot()
 get_tip()          load_snapshot()
                    reset_state()
              |
              v
       recovery.py + folds.py
```

Directory structure:
```text
staging/FMWK-002-write-path/
├── write_path/
│   ├── __init__.py
│   ├── errors.py
│   ├── models.py
│   ├── ports.py
│   ├── folds.py
│   ├── system_events.py
│   ├── recovery.py
│   └── service.py
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_system_events.py
│   ├── test_folds.py
│   ├── test_service_mutations.py
│   └── test_recovery.py
└── README.md
```

---

## Key Patterns

**1. Append Then Fold Then Return** [D1 Article 4, D5 RQ-001]
`submit_mutation()` succeeds only after Ledger append is durable and Graph fold completes; never acknowledge earlier.

**2. Mechanical Fold Only** [D1 Article 6]
Fold helpers transform Graph state from event fields only; they do not infer policy, prompt meaning, or orchestration decisions.

**3. Bounded Methylation Arithmetic** [D1 Article 7, D6 CLR-001]
Signal and methylation deltas use additive arithmetic followed by clamping to `0.0–1.0`.

**4. Durable Boundary on Fold Failure** [D5 RQ-002, D6 CLR-002]
If append succeeds and fold fails, return `WRITE_PATH_FOLD_ERROR`, preserve the durable boundary, and require recovery before more writes proceed.

**5. Snapshot Orchestration Split from Graph Ownership** [D5 RQ-004, D6 CLR-003]
The Write Path owns when snapshotting happens and what Ledger sequence boundary it represents; Graph owns the save/load mechanics behind a declared interface.

**6. Declared Doubles Are Part of the Spec Surface** [D6 Testable Surface Completeness]
`TD-001 LedgerPortDouble` and `TD-002 GraphPortDouble` are mandatory so Turn E can express append, fold, snapshot, and replay outcomes without inventing replacement dependencies.

---

## Commands

```bash
# Run full unit suite
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/ -v

# Run mutation-path tests only
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/test_service_mutations.py -v

# Run recovery-path tests only
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/test_recovery.py -v

# Run one specific failure-path test
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/test_service_mutations.py::test_submit_mutation_fold_failure_returns_typed_error -v

# Full regression with output capture for RESULTS.md
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/ -v --tb=short 2>&1 | tee regression_output.txt
```

---

## Tool Rules

| USE THIS | NOT THIS | WHY |
|----------|----------|-----|
| FMWK-001 contracts through `platform_sdk` | Direct immudb client usage | Matches D1: Ledger access stays behind the declared contract and SDK-covered path. |
| Declared FMWK-005 interface/double | Ad hoc shared-memory mutation outside contract | Matches D1: Graph writes stay behind the declared interface. |
| `platform_sdk` storage/filesystem modules | Raw uncontrolled filesystem helpers | Matches D1: snapshot file I/O stays governed and mockable. |
| `platform_sdk.tier0_core.logging` | `print()`, raw logging libraries | Matches D1: logging is SDK-covered. |
| `platform_sdk.tier0_core.errors` | Raw `Exception` trees only | Matches D1: error handling is SDK-covered. |
| `platform_sdk.tier0_core.config` | scattered `os.getenv()` | Matches D1: configuration is SDK-covered. |
| `platform_sdk.tier0_core.secrets` | hardcoded credentials | Matches D1: secrets never live in source. |
| Declared package-code doubles and MockProvider | live immudb or live kernel required for unit tests | Matches D1: unit tests use declared doubles, not live services. |

---

## Coding Conventions

- Python 3.11+
- Prefer stdlib plus `platform_sdk`; do not introduce new infrastructure libraries unless already required by a declared dependency
- Full type hints on public methods and dataclasses
- Use `@dataclass` for D3 entities
- Use `Decimal` for bounded methylation arithmetic rather than binary float math in fold code
- Raise typed write-path errors; never swallow failures or silently continue after append/fold/snapshot/replay problems
- `pytest` is the test framework; declared doubles live in `tests/conftest.py`
- TDD is mandatory: write the test first, run it failing, then implement

---

## Submission Protocol

1. Read `sawmill/FMWK-002-write-path/BUILDER_HANDOFF.md` completely.
2. Answer all 13 questions in `sawmill/FMWK-002-write-path/13Q_ANSWERS.md`; first line MUST be: `Builder Prompt Contract Version: 1.0.0`
3. STOP. Do not implement before reviewer PASS.
4. After reviewer PASS, execute D8 in order using DTT for every behavior.
5. After all unit tests pass, record the mid-build checkpoint evidence required by the handoff.
6. Run full regression: `PLATFORM_ENVIRONMENT=test pytest tests/ -v --tb=short`
7. Write `sawmill/FMWK-002-write-path/RESULTS.md` with hashes, full pasted test output, baseline snapshot, regression status, issues, and session log.

Branch naming: `feature/fmwk-002-write-path`
Commit format: `feat(fmwk-002): <description>`
Results file path: `sawmill/FMWK-002-write-path/RESULTS.md`

---

## Active Components

| Component | Where | Interface (signature) |
|-----------|-------|-----------------------|
| WritePathService | `write_path/service.py` | `submit_mutation(self, request: MutationRequest) -> MutationReceipt`; `create_snapshot(self) -> SnapshotDescriptor`; `recover(self, snapshot: SnapshotDescriptor | None = None) -> RecoveryCursor`; `refold_from_genesis(self) -> RecoveryCursor` |
| LedgerPort | `write_path/ports.py` | `append(self, request: MutationRequest | dict) -> dict`; `read_since(self, sequence_number: int) -> list[dict]`; `get_tip(self) -> TipRecord` |
| GraphPort | `write_path/ports.py` | `fold_event(self, event: dict) -> None`; `export_snapshot(self) -> bytes`; `load_snapshot(self, payload: bytes) -> None`; `reset_state(self) -> None` |
| Fold helpers | `write_path/folds.py` | `fold_live_event(graph: GraphPort, event: dict) -> None`; `clamp_methylation(value: Decimal) -> Decimal` |
| Recovery coordinator | `write_path/recovery.py` | `create_snapshot(...) -> SnapshotDescriptor`; `recover_graph(...) -> RecoveryCursor`; `refold_from_genesis(...) -> RecoveryCursor` |
| System-event builders | `write_path/system_events.py` | `build_session_start_request(...) -> MutationRequest`; `build_session_end_request(...) -> MutationRequest`; `build_snapshot_created_request(...) -> MutationRequest` |

---

## Links to Deeper Docs

- **D1** — Constitution: framework boundary, synchronous acknowledgment rule, no dual writes, bounded methylation, deterministic failure posture, SDK-only tooling constraints
- **D2** — Specification: the 9 build scenarios and the deferred capabilities that remain out of scope
- **D3** — Data Model: `MutationRequest`, `MutationReceipt`, `SnapshotDescriptor`, `RecoveryCursor`, and FMWK-002-owned payload schemas
- **D4** — Contracts: inbound methods, side effects, error semantics, and caller-visible observable postconditions
- **D5** — Research: rationale for append-then-fold success, fold-failure posture, bounded methylation arithmetic, and snapshot ownership split
- **D6** — Gap Analysis: the resolved assumptions and the declared evaluator-visible doubles
- **D9** — Holdout Scenarios: kept separate from builders during active build
