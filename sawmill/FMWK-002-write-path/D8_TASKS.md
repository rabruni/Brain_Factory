# D8: Tasks — Write Path (FMWK-002)
Meta: plan: D7 v1.0.0 | status:Final | total tasks:10 | parallel opportunities:3

---

## MVP Scope

All D2 scenarios are in scope for this build. No D2 scenario is deferred.

| D2 Scenario | Priority | Scope |
|------------|----------|-------|
| SC-001 — Synchronous append-and-fold for caller-submitted mutation | P0 (blocker) | IN |
| SC-003 — Signal accumulator fold | P0 (blocker) | IN |
| SC-005 — Startup recovery from snapshot marker | P0 (blocker) | IN |
| SC-002 — Direct system-event authoring | P1 (must) | IN |
| SC-004 — Session-boundary snapshot | P1 (must) | IN |
| SC-006 — Retroactive healing by full re-fold | P1 (must) | IN |
| SC-007 — Ledger append failure | P0 (blocker) | IN |
| SC-008 — Fold failure after durable append | P1 (must) | IN |
| SC-009 — Recovery with no usable snapshot | P1 (must) | IN |

Deferred capabilities remain exactly as declared in D2:
- DEF-001 — Multi-process writer coordination
- DEF-002 — Snapshot binary format optimization

---

## Tasks (T-### IDs, phased)

Phases: 0=Foundation, 1=Fold Logic, 2=Service + Recovery, 3=Validation

---

### Phase 0 — Foundation

#### T-001 — Errors, entities, and dependency ports

- Parallel/Serial: Serial
- Dependency: None
- Scope: M
- Scenarios Satisfied: SC-001, SC-002, SC-004, SC-005, SC-006, SC-007, SC-008, SC-009
- Contracts Implemented: D4 OUT-001, OUT-002, OUT-003, ERR-001, ERR-002, ERR-003, ERR-004
- Acceptance Criteria:
  1. `write_path/errors.py` exists with `WritePathAppendError`, `WritePathFoldError`, `SnapshotWriteError`, and `ReplayRecoveryError`.
  2. `write_path/models.py` exists with `MutationRequest`, `MutationReceipt`, `SnapshotDescriptor`, and `RecoveryCursor` matching D3 E-001 through E-004.
  3. `write_path/ports.py` defines package-local `LedgerPort` and `GraphPort` protocols covering the D4 dependency surface.
  4. `tests/conftest.py` defines `TD-001 LedgerPortDouble` and `TD-002 GraphPortDouble` with deterministic failure injection for append, fold, snapshot, and replay scenarios.
  5. Tests prove the D3 JSON examples instantiate cleanly and that the doubles can express every D2 scenario without inventing extra substitutes.

#### T-002 — System-event request builders

- Parallel/Serial: Parallel with T-003
- Dependency: T-001 (needs models)
- Scope: S
- Scenarios Satisfied: SC-002, SC-004
- Contracts Implemented: D4 IN-001, IN-002
- Acceptance Criteria:
  1. `write_path/system_events.py` exists with builders for `session_start`, `session_end`, and `snapshot_created`.
  2. Builders emit `MutationRequest` values using only the allowed system event types.
  3. `snapshot_created` requests require an existing `SnapshotDescriptor` and copy `snapshot_sequence`, `snapshot_file`, and `snapshot_hash` verbatim.
  4. `tests/test_system_events.py` includes at least 6 tests covering valid builders, unsupported event rejection, and descriptor-to-request mapping.

#### T-003 — Fold primitives and bounded methylation helpers

- Parallel/Serial: Parallel with T-002
- Dependency: T-001 (needs models and ports)
- Scope: M
- Scenarios Satisfied: SC-001, SC-003, SC-008
- Contracts Implemented: D4 SIDE-002, ERR-002
- Acceptance Criteria:
  1. `write_path/folds.py` exists with `clamp_methylation()` and `fold_live_event()`.
  2. `signal_delta` and `methylation_delta` folds use additive arithmetic then clamp to the closed range `0.0–1.0`.
  3. `suppression`, `unsuppression`, `mode_change`, `consolidation`, `session_start`, `session_end`, `package_install`, `package_uninstall`, `framework_install`, `intent_transition`, and `work_order_transition` route to mechanical Graph mutations only.
  4. Fold helpers do not call Ledger APIs, prompt systems, or HO2 policy logic.
  5. `tests/test_folds.py` includes at least 12 tests covering upper/lower clamp behavior, event-type routing, and fold-error propagation.

---

### Phase 1 — Fold Logic

#### T-004 — Core synchronous mutation service

- Parallel/Serial: Serial
- Dependency: T-001, T-003
- Scope: L
- Scenarios Satisfied: SC-001, SC-003, SC-007, SC-008
- Contracts Implemented: D4 IN-001, OUT-001, SIDE-001, SIDE-002, ERR-001, ERR-002
- Acceptance Criteria:
  1. `write_path/service.py` defines `WritePathService.submit_mutation(self, request: MutationRequest) -> MutationReceipt`.
  2. `submit_mutation()` calls Ledger append exactly once, then folds the appended event exactly once, then returns `MutationReceipt`.
  3. No success receipt is returned if append fails.
  4. No success receipt is returned if fold fails after durable append; instead the service raises `WritePathFoldError` with the durable sequence boundary needed for recovery.
  5. Immediate Graph reads through `TD-002 GraphPortDouble` observe folded state before `submit_mutation()` returns.
  6. `tests/test_service_mutations.py` includes at least 10 tests for success ordering, append failure, fold failure, and immediate visibility.

#### T-005 — System-path mutation coverage in service

- Parallel/Serial: Serial
- Dependency: T-002, T-004
- Scope: S
- Scenarios Satisfied: SC-002
- Contracts Implemented: D4 IN-001, OUT-001
- Acceptance Criteria:
  1. `WritePathService.submit_mutation()` accepts system-built requests for `session_start`, `session_end`, and `snapshot_created`.
  2. No HO1 dependency is required to author these system events.
  3. `tests/test_service_mutations.py` adds at least 4 tests proving all three supported system events append and fold through the same path as caller mutations.

#### T-006 — Snapshot creation orchestration

- Parallel/Serial: Serial
- Dependency: T-002, T-004
- Scope: M
- Scenarios Satisfied: SC-004
- Contracts Implemented: D4 IN-002, OUT-002, SIDE-003, ERR-003
- Acceptance Criteria:
  1. `write_path/recovery.py` defines `create_snapshot(...) -> SnapshotDescriptor`.
  2. Snapshot artifact creation occurs before `snapshot_created` is submitted.
  3. The returned descriptor includes `snapshot_sequence`, `snapshot_file`, and `snapshot_hash`.
  4. Snapshot failure raises `SnapshotWriteError` and does not return a success descriptor.
  5. `tests/test_recovery.py` includes at least 6 tests covering successful snapshot creation, descriptor correctness, and snapshot artifact failure.

#### T-007 — Startup recovery from snapshot marker

- Parallel/Serial: Serial
- Dependency: T-006
- Scope: M
- Scenarios Satisfied: SC-005, SC-009
- Contracts Implemented: D4 IN-003, OUT-003, ERR-004
- Acceptance Criteria:
  1. `write_path/recovery.py` defines `recover_graph(...) -> RecoveryCursor`.
  2. With a usable snapshot, recovery loads the snapshot and replays exactly the events after `snapshot_sequence` in ascending order.
  3. With no usable snapshot, recovery replays from genesis with `replay_from_sequence = -1`.
  4. Returned `RecoveryCursor.mode` is `post_snapshot_replay` or `full_replay` as appropriate.
  5. `tests/test_recovery.py` includes at least 8 tests covering usable snapshot recovery, missing snapshot recovery, unusable snapshot fallback, and replay ordering.

#### T-008 — Full-ledger refold for retroactive healing

- Parallel/Serial: Serial
- Dependency: T-007
- Scope: M
- Scenarios Satisfied: SC-006
- Contracts Implemented: D4 IN-004, OUT-003, ERR-004
- Acceptance Criteria:
  1. `write_path/recovery.py` defines `refold_from_genesis(...) -> RecoveryCursor`.
  2. The Graph state is reset before replay starts.
  3. Ledger history is read-only throughout the operation.
  4. Returned `RecoveryCursor` is `mode="full_refold"`, `replay_from_sequence=-1`, `replay_to_sequence=<tip>`.
  5. `tests/test_recovery.py` includes at least 4 tests proving Graph reset, replay order, unchanged Ledger history, and cursor shape.

---

### Phase 2 — Service + Recovery

### Phase 3 — Validation

#### T-009 — Package assembly and public exports

- Parallel/Serial: Parallel with T-010
- Dependency: T-005, T-008
- Scope: S
- Scenarios Satisfied: Supports SC-001 through SC-009 by exposing the package cleanly
- Contracts Implemented: D4 IN-001 through IN-004, OUT-001 through OUT-003, ERR-001 through ERR-004
- Acceptance Criteria:
  1. `write_path/__init__.py` exports `WritePathService`, the D3 entity types, and the typed errors.
  2. `README.md` summarizes live mutation, snapshot, recovery, and refold responsibilities without expanding scope.
  3. Import smoke tests pass: `from write_path import WritePathService, MutationRequest, MutationReceipt`.

#### T-010 — Full regression and evidence capture

- Parallel/Serial: Parallel with T-009
- Dependency: T-005, T-008
- Scope: M
- Scenarios Satisfied: SC-001 through SC-009
- Contracts Implemented: Validation of all implemented D4 contracts
- Acceptance Criteria:
  1. Full unit suite runs from the package root with `PLATFORM_ENVIRONMENT=test pytest tests/ -v --tb=short`.
  2. Test count is at least 40, satisfying the handoff standard for a 6+ file package.
  3. Results are recorded in `sawmill/FMWK-002-write-path/RESULTS.md` with full command output pasted from the build session.
  4. Baseline snapshot and full regression sections are completed per handoff standard.

---

## Task Dependency Graph

```text
T-001
  ├── T-002 ──┐
  └── T-003 ──┴── T-004 ── T-005 ── T-006 ── T-007 ── T-008 ──┬── T-009
                                                                └── T-010
```

Parallel opportunities:
- `T-002` with `T-003`
- `T-009` with `T-010`
- Test writing inside `T-006` and `T-007` can proceed alongside package export cleanup once core behavior is stable

## Summary

| Task | Phase | Scope | Serial/Parallel | Scenarios |
|------|-------|-------|-----------------|-----------|
| T-001 | 0 | M | Serial | SC-001, SC-002, SC-004, SC-005, SC-006, SC-007, SC-008, SC-009 |
| T-002 | 0 | S | Parallel | SC-002, SC-004 |
| T-003 | 0 | M | Parallel | SC-001, SC-003, SC-008 |
| T-004 | 2 | L | Serial | SC-001, SC-003, SC-007, SC-008 |
| T-005 | 2 | S | Serial | SC-002 |
| T-006 | 2 | M | Serial | SC-004 |
| T-007 | 2 | M | Serial | SC-005, SC-009 |
| T-008 | 2 | M | Serial | SC-006 |
| T-009 | 3 | S | Parallel | SC-001 through SC-009 |
| T-010 | 3 | M | Parallel | SC-001 through SC-009 |

Total: 10 tasks, 4 phases, 3 parallelizable opportunities, 7 serial waves.
MVP Tasks: T-001 through T-010.
