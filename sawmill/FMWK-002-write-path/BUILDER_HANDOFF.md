# Builder Handoff — Write Path (FMWK-002)
Prompt Contract Version: 1.0.0

---

## 1. Mission

Build the `write_path` Python package for FMWK-002-write-path. This package is DoPeJarMo's synchronous mutation boundary: it accepts `MutationRequest` inputs, appends through the Ledger contract, folds immediately into Graph state, and returns `MutationReceipt` only after both steps complete. It also owns session-boundary snapshot orchestration, startup recovery from a snapshot marker plus post-snapshot replay, and full-ledger refold for governed retroactive healing. Package ID: `FMWK-002-write-path`.

---

## 2. Critical Constraints

1. **Staging only.** All code is written under `staging/FMWK-002-write-path/`. Do NOT write to `/Users/raymondbruni/dopejar/`.
2. **DTT per behavior.** For every D8 task: write tests first, run them failing, then implement, then rerun passing. If code was written before tests, delete it and redo. Reference: `Templates/TDD_AND_DEBUGGING.md`.
3. **Package everything.** `write_path/` must be an importable Python package with a clean `__init__.py`.
4. **E2E verify before declaring done.** Run `PLATFORM_ENVIRONMENT=test pytest tests/ -v --tb=short` and paste full output into `RESULTS.md`.
5. **No hardcoding.** Config, secrets, logging, error capture, and snapshot filesystem access must go through `platform_sdk`.
6. **No file replacement.** Edit incrementally. If a full rewrite becomes necessary, explain it in `RESULTS.md`.
7. **Deterministic archives.** Any artifact or snapshot helper output must be reproducible from the same inputs.
8. **Results file is mandatory.** Write `sawmill/FMWK-002-write-path/RESULTS.md` with every required section before reporting completion.
9. **Full regression before done.** Run the complete package test suite, not only touched tests.
10. **Baseline snapshot.** `RESULTS.md` must include packages installed and starting test count at session start.
11. **TDD discipline is enforced.** Every "tests pass" claim requires pasted output from this session.
12. **No direct infrastructure bypass.** No direct immudb imports, no ad hoc Graph mutation outside the declared port, no raw filesystem helpers for snapshots.
13. **No scope widening.** Do not add query APIs, daemons, orchestration policy, prompt execution, package gates, or multi-process writer coordination.

---

## 3. Architecture/Design

```text
Callers
  ├── HO1 live mutation requests
  ├── HO2/runtime system events
  ├── runtime startup recovery
  └── governed maintenance refold
              |
              v
      +--------------------------------------+
      | WritePathService                      |
      | submit_mutation()                     |
      | create_snapshot()                     |
      | recover()                             |
      | refold_from_genesis()                 |
      +------------------+-------------------+
                         |
            +------------+-------------+
            |                          |
            v                          v
       LedgerPort                 GraphPort
       append()                   fold_event()
       read_since()               export_snapshot()
       get_tip()                  load_snapshot()
                                  reset_state()
            |                          |
            +------------+-------------+
                         |
                         v
              recovery.py + folds.py
```

Data-flow boundaries:
- Live mutation path: validate request -> Ledger append -> Graph fold -> success receipt
- System-event path: build allowed system request -> same live mutation path
- Snapshot path: Graph snapshot export -> hash/write artifact -> submit `snapshot_created`
- Recovery path: load usable snapshot if present -> replay `read_since(snapshot_sequence)` -> return cursor
- Full refold path: reset Graph -> replay full Ledger from genesis -> return cursor

Every boundary is mechanical:
- Ledger remains durable truth
- Graph remains in-memory derived state
- Write Path remains the sole sequencer of append + fold + replay coordination
- No business policy or semantic interpretation inside fold logic

---

## 4. Implementation Steps

Follow D8 order exactly. Every step is tests first, then implementation.

1. **Implement errors, entities, and ports.**
   Files: `write_path/errors.py`, `write_path/models.py`, `write_path/ports.py`, `tests/conftest.py`, `tests/test_models.py`
   Signatures:
   - `class WritePathAppendError(Exception)`
   - `class WritePathFoldError(Exception)`
   - `class SnapshotWriteError(Exception)`
   - `class ReplayRecoveryError(Exception)`
   - `class LedgerPort(Protocol): ...`
   - `class GraphPort(Protocol): ...`
   Why: the rest of the package depends on stable types and evaluator-visible doubles.

2. **Implement allowed system-event builders.**
   Files: `write_path/system_events.py`, `tests/test_system_events.py`
   Signatures:
   - `build_session_start_request(...) -> MutationRequest`
   - `build_session_end_request(...) -> MutationRequest`
   - `build_snapshot_created_request(descriptor: SnapshotDescriptor, ...) -> MutationRequest`
   Why: SC-002 and SC-004 require a controlled system path with no HO1 dependency.

3. **Implement fold primitives and bounded arithmetic.**
   Files: `write_path/folds.py`, `tests/test_folds.py`
   Signatures:
   - `clamp_methylation(value: Decimal) -> Decimal`
   - `fold_live_event(graph: GraphPort, event: dict) -> None`
   Why: SC-003 and SC-008 depend on explicit, mechanical, replay-safe fold semantics.

4. **Implement the core synchronous service.**
   Files: `write_path/service.py`, `tests/test_service_mutations.py`
   Signatures:
   - `class WritePathService`
   - `submit_mutation(self, request: MutationRequest) -> MutationReceipt`
   Why: this is the constitutional center of the framework; success means append and fold both completed.

5. **Wire system-event requests through the same service path.**
   Files: `write_path/service.py`, `tests/test_service_mutations.py`
   Signatures:
   - same `submit_mutation(...)`
   Why: SC-002 forbids a special hidden path; system events must use the same append/fold contract.

6. **Implement snapshot creation orchestration.**
   Files: `write_path/recovery.py`, `tests/test_recovery.py`
   Signatures:
   - `create_snapshot(graph: GraphPort, ledger: LedgerPort, ...) -> SnapshotDescriptor`
   Why: SC-004 requires artifact-first snapshot creation followed by `snapshot_created`.

7. **Implement startup recovery.**
   Files: `write_path/recovery.py`, `tests/test_recovery.py`
   Signatures:
   - `recover_graph(graph: GraphPort, ledger: LedgerPort, snapshot: SnapshotDescriptor | None) -> RecoveryCursor`
   Why: SC-005 and SC-009 require deterministic rebuild from snapshot+replay or full replay.

8. **Implement full refold for retroactive healing.**
   Files: `write_path/recovery.py`, `tests/test_recovery.py`
   Signatures:
   - `refold_from_genesis(graph: GraphPort, ledger: LedgerPort) -> RecoveryCursor`
   Why: SC-006 requires Graph healing without rewriting Ledger history.

9. **Assemble package exports and docs.**
   Files: `write_path/__init__.py`, `README.md`
   Why: builder output must be importable and legible without widening the public surface.

10. **Run full regression and write evidence.**
    Files: `sawmill/FMWK-002-write-path/RESULTS.md`
    Why: completion is not credible without pasted output, hashes, and regression evidence from this session.

---

## 5. Package Plan

**Package ID:** `FMWK-002-write-path`  
**Layer:** KERNEL

| File | Type | Action |
|------|------|--------|
| `write_path/__init__.py` | Source | CREATE |
| `write_path/errors.py` | Source | CREATE |
| `write_path/models.py` | Source | CREATE |
| `write_path/ports.py` | Source | CREATE |
| `write_path/folds.py` | Source | CREATE |
| `write_path/system_events.py` | Source | CREATE |
| `write_path/recovery.py` | Source | CREATE |
| `write_path/service.py` | Source | CREATE |
| `tests/conftest.py` | Test | CREATE |
| `tests/test_models.py` | Test | CREATE |
| `tests/test_system_events.py` | Test | CREATE |
| `tests/test_folds.py` | Test | CREATE |
| `tests/test_service_mutations.py` | Test | CREATE |
| `tests/test_recovery.py` | Test | CREATE |
| `README.md` | Docs | CREATE |

Dependencies:
- FMWK-001 package contracts for Ledger append/read tip/replay
- FMWK-005 package contracts for Graph fold/snapshot/load/reset
- `platform_sdk.tier0_core.config`
- `platform_sdk.tier0_core.secrets`
- `platform_sdk.tier0_core.logging`
- `platform_sdk.tier0_core.errors`
- `platform_sdk` storage/filesystem helpers
- stdlib `dataclasses`, `typing`, `decimal`, `hashlib`, `json`, `pathlib`

Manifest notes:
- `package_id`: `FMWK-002-write-path`
- `framework_id`: `FMWK-002`
- `version`: `1.0.0`
- Record hashes for every created file in `RESULTS.md`

---

## 6. Test Plan

Mandatory minimum for a 6+ file package: **40+ tests**. Target: **45-55 tests**.

| Test File | Minimum | Coverage |
|-----------|---------|----------|
| `tests/test_models.py` | 6 | D3 entity construction, field preservation, descriptor/cursor shapes |
| `tests/test_system_events.py` | 6 | Allowed system events, unsupported event rejection, descriptor propagation |
| `tests/test_folds.py` | 12 | clamp upper/lower bounds, signal delta, methylation delta, suppression, unsuppression, mode change, consolidation, no policy logic |
| `tests/test_service_mutations.py` | 14 | append then fold ordering, immediate visibility, append failure, fold failure, durable boundary capture, system-event routing |
| `tests/test_recovery.py` | 12 | snapshot success, snapshot failure, post-snapshot replay, full replay fallback, unusable snapshot, full refold, unchanged Ledger history |

Specific required behaviors:
- `test_submit_mutation_success_returns_receipt_after_fold`
- `test_submit_mutation_append_failure_no_fold`
- `test_submit_mutation_fold_failure_returns_typed_error_and_boundary`
- `test_signal_delta_clamps_at_upper_bound`
- `test_signal_delta_clamps_at_lower_bound`
- `test_create_snapshot_writes_artifact_before_snapshot_created`
- `test_recover_uses_post_snapshot_replay_only`
- `test_recover_without_snapshot_replays_from_genesis`
- `test_refold_from_genesis_resets_graph_and_preserves_ledger`

---

## 7. Existing Code to Reference

| What | Where | Why |
|------|-------|-----|
| Turn B artifact style and level of specificity | `sawmill/FMWK-001-ledger/D7_PLAN.md`, `sawmill/FMWK-001-ledger/D8_TASKS.md`, `sawmill/FMWK-001-ledger/D10_AGENT_CONTEXT.md` | Use the same rigor and evidence standard |
| Existing staged Ledger package structure | `staging/FMWK-001-ledger/ledger/` | The Write Path depends on Ledger contracts and should align with its package quality bar |
| Turn A write-path requirements | `sawmill/FMWK-002-write-path/D2_SPECIFICATION.md`, `sawmill/FMWK-002-write-path/D4_CONTRACTS.md`, `sawmill/FMWK-002-write-path/D6_GAP_ANALYSIS.md` | These are the authoritative build inputs |

---

## 8. E2E Verification

Run these exactly and paste the output into `RESULTS.md`:

```bash
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/test_models.py -v
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/test_system_events.py -v
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/test_folds.py -v
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/test_service_mutations.py -v
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/test_recovery.py -v
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/ -v --tb=short
```

Expected outcome:
- All tests pass
- No live immudb dependency in unit tests
- Failure-path tests prove typed errors for append, fold, snapshot, and replay problems

---

## 9. Files Summary

| File | Location | Action |
|------|----------|--------|
| `__init__.py` | `write_path/__init__.py` | CREATE |
| `errors.py` | `write_path/errors.py` | CREATE |
| `models.py` | `write_path/models.py` | CREATE |
| `ports.py` | `write_path/ports.py` | CREATE |
| `folds.py` | `write_path/folds.py` | CREATE |
| `system_events.py` | `write_path/system_events.py` | CREATE |
| `recovery.py` | `write_path/recovery.py` | CREATE |
| `service.py` | `write_path/service.py` | CREATE |
| `conftest.py` | `tests/conftest.py` | CREATE |
| `test_models.py` | `tests/test_models.py` | CREATE |
| `test_system_events.py` | `tests/test_system_events.py` | CREATE |
| `test_folds.py` | `tests/test_folds.py` | CREATE |
| `test_service_mutations.py` | `tests/test_service_mutations.py` | CREATE |
| `test_recovery.py` | `tests/test_recovery.py` | CREATE |
| `README.md` | `README.md` | CREATE |
| `RESULTS.md` | `sawmill/FMWK-002-write-path/RESULTS.md` | CREATE |

---

## 10. Design Principles

1. Success means durable append plus completed fold, never less.
2. The Write Path is a consistency layer, not a semantic or policy layer.
3. Replay and refold must reconstruct state only from Ledger truth and declared snapshot artifacts.
4. Bounded methylation arithmetic is primitive behavior; higher-layer regulation stays out.
5. Typed failures are better than ambiguous state; block rather than guess.
6. All covered infrastructure concerns stay behind `platform_sdk` and declared ports.

---

## 11. Verification Discipline

Every "pass" statement in `RESULTS.md` must include pasted output from this session. Do not summarize with counts only. Include:
- the exact command
- the exact output
- total/passed/failed/skipped counts
- any failures encountered and how they were fixed

Red flags:
- "should work"
- "probably passes"
- "I’m confident"
- "tests were green earlier"

If the output is not pasted, it does not count as verified.

---

## 12. Mid-Build Checkpoint

After all unit tests pass but before final reporting:
- record total test count and pasted output
- list files created so far
- note any deviations from D8 or D4
- confirm whether all P0 and P1 scenarios are covered by tests

Continue unless the orchestrator escalates.

---

## 13. Self-Reflection

Before reporting any step complete, verify:
- the code still matches D2 and D4 exactly
- SC-001 through SC-009 are covered with explicit tests
- fold failure after durable append is surfaced, not hidden
- replay/refold behavior is deterministic and explainable six months from now
- TDD was followed for every behavior; if not, delete the premature code and redo it
