Builder Prompt Contract Version: 1.0.0

# 13Q Comprehension Gate — FMWK-002-write-path (Turn D)

Date: 2026-03-21
Attempt: 2

---

## Q1 — What am I building?

I am building the `write_path` Python package for `FMWK-002-write-path` under `staging/FMWK-002-write-path/`. It is DoPeJarMo's synchronous mutation boundary: it accepts a `MutationRequest`, appends it through the Ledger contract, folds the durable event into Graph state, and returns `MutationReceipt` only after both steps complete. It also owns session-boundary snapshot orchestration, startup recovery from snapshot plus replay, and full-ledger refold for retroactive healing.

Planned build outputs after reviewer PASS:
- `staging/FMWK-002-write-path/write_path/` with `__init__.py`, `errors.py`, `models.py`, `ports.py`, `folds.py`, `system_events.py`, `recovery.py`, `service.py`
- `staging/FMWK-002-write-path/tests/` with `conftest.py`, `test_models.py`, `test_system_events.py`, `test_folds.py`, `test_service_mutations.py`, `test_recovery.py`
- `staging/FMWK-002-write-path/README.md`
- `sawmill/FMWK-002-write-path/RESULTS.md`
- `sawmill/FMWK-002-write-path/builder_evidence.json`

---

## Q2 — What am I NOT building?

- Not a second event store. Durable truth stays in FMWK-001 Ledger.
- Not a query layer for HO2 retrieval, ranking, traversal, or read APIs.
- Not a policy engine. No decay policy, threshold logic, Traveler Rule behavior, or orchestration semantics.
- Not a background queue, daemon, or eventual-consistency write buffer.
- Not direct caller-managed writes to Ledger or Graph.
- Not package gates, package lifecycle policy, LLM execution, or semantic interpretation of user-facing payload meaning.
- Not multi-process writer coordination; D2 defers that explicitly.
- Not snapshot format optimization beyond a recoverable artifact with marker and hash.
- Not any work under `/Users/raymondbruni/dopejar/`; staging only.

---

## Q3 — What are the D1 constitutional boundaries?

**ALWAYS**
- A successful live mutation is append first, fold second, return success last.
- Mechanical folding only. The Write Path updates Graph state from event fields; it does not infer policy or prompt meaning.
- Bounded methylation arithmetic stays in `0.0` through `1.0` inclusive.
- Typed failures only: append failures surface as `WRITE_PATH_APPEND_ERROR`; fold failures after durable append surface as `WRITE_PATH_FOLD_ERROR`; snapshot failures as `SNAPSHOT_WRITE_ERROR`; replay/refold failures as `REPLAY_RECOVERY_ERROR`.
- Snapshot orchestration uses declared contracts and `platform_sdk` for covered infrastructure concerns.
- Test doubles declared in D4 are part of the package surface and must live in package code, not under `tests/`.

**ASK FIRST**
- Any change to append-then-fold acknowledgment ordering.
- Any widening of accepted event types or addition of new public APIs.
- Any change that would move execution logic into HO3 / Graph.
- Any change that rewrites or mutates Ledger history instead of replay/refold.

**NEVER**
- Create a new primitive.
- Add execution or policy logic to HO3 / Graph.
- Write directly to the Ledger outside the declared Ledger port.
- Mutate Graph outside the declared Graph port.
- Read `.holdouts/*` or evaluator artifacts.
- Widen scope into orchestration, query, package gates, or background processing.

---

## Q4 — What are the APIs from D4?

Primary service APIs:
- `submit_mutation(self, request: MutationRequest) -> MutationReceipt`
- `create_snapshot(self) -> SnapshotDescriptor`
- `recover(self, snapshot: SnapshotDescriptor | None = None) -> RecoveryCursor`
- `refold_from_genesis(self) -> RecoveryCursor`

Declared dependency ports:
- `LedgerPort.append(self, request: MutationRequest | dict) -> dict`
- `LedgerPort.read_since(self, sequence_number: int) -> list[dict]`
- `LedgerPort.get_tip(self) -> TipRecord`
- `GraphPort.fold_event(self, event: dict) -> None`
- `GraphPort.export_snapshot(self) -> bytes`
- `GraphPort.load_snapshot(self, payload: bytes) -> None`
- `GraphPort.reset_state(self) -> None`

Supporting module APIs:
- `fold_live_event(graph: GraphPort, event: dict) -> None`
- `clamp_methylation(value: Decimal) -> Decimal`
- `create_snapshot(...) -> SnapshotDescriptor`
- `recover_graph(...) -> RecoveryCursor`
- `refold_from_genesis(...) -> RecoveryCursor`
- `build_session_start_request(...) -> MutationRequest`
- `build_session_end_request(...) -> MutationRequest`
- `build_snapshot_created_request(...) -> MutationRequest`

---

## Q5 — What are the file locations from D3/D4?

Package source files:
- `staging/FMWK-002-write-path/write_path/__init__.py`
- `staging/FMWK-002-write-path/write_path/errors.py`
- `staging/FMWK-002-write-path/write_path/models.py`
- `staging/FMWK-002-write-path/write_path/ports.py`
- `staging/FMWK-002-write-path/write_path/folds.py`
- `staging/FMWK-002-write-path/write_path/system_events.py`
- `staging/FMWK-002-write-path/write_path/recovery.py`
- `staging/FMWK-002-write-path/write_path/service.py`

Test files:
- `staging/FMWK-002-write-path/tests/conftest.py`
- `staging/FMWK-002-write-path/tests/test_models.py`
- `staging/FMWK-002-write-path/tests/test_system_events.py`
- `staging/FMWK-002-write-path/tests/test_folds.py`
- `staging/FMWK-002-write-path/tests/test_service_mutations.py`
- `staging/FMWK-002-write-path/tests/test_recovery.py`

Required Sawmill artifacts:
- `sawmill/FMWK-002-write-path/13Q_ANSWERS.md`
- `sawmill/FMWK-002-write-path/RESULTS.md`
- `sawmill/FMWK-002-write-path/builder_evidence.json`

[CRITICAL_REVIEW_REQUIRED]: D4's Testable Surface says `TD-001 LedgerPortDouble` and `TD-002 GraphPortDouble` must live in package code, but the handoff step list places doubles in `tests/conftest.py` and D10 says "declared doubles live in `tests/conftest.py`." My current interpretation is that evaluator-visible doubles must be created under package code and may also be wrapped by test fixtures in `tests/conftest.py`. If that reading is wrong, the reviewer should resolve the location conflict before implementation.

---

## Q6 — What are the data formats from D3/D4?

Core entities:
- `MutationRequest`: `event_type`, `schema_version`, `timestamp`, `provenance`, `payload`
- `MutationReceipt`: `sequence_number`, `event_hash`, `fold_status="folded"`
- `SnapshotDescriptor`: `snapshot_sequence`, `snapshot_file`, `snapshot_hash`
- `RecoveryCursor`: `mode`, `replay_from_sequence`, `replay_to_sequence`

Key format constraints:
- `event_type` must be one of the accepted Write Path event types from D4 IN-001
- `timestamp` is ISO-8601 UTC with `Z`
- `provenance.framework_id` required, `pack_id` optional, `actor` in `system|operator|agent`
- Decimal payload values use decimal strings, not binary floats
- `snapshot_file` must be an absolute `/snapshots/...snapshot` path
- `snapshot_hash` and `event_hash` are `sha256:` plus 64 lowercase hex chars
- `RecoveryCursor.mode` is one of `post_snapshot_replay`, `full_replay`, `full_refold`
- `replay_from_sequence = -1` means replay from genesis

Write-path-owned payload schemas I must support explicitly:
- `methylation_delta`: `node_id`, `delta`
- `suppression`: `node_id`, `projection_scope`
- `unsuppression`: `node_id`, `projection_scope`
- `mode_change`: `node_id`, `mode`
- `consolidation`: `source_node_ids`, `consolidated_node_id`

---

## Q7 — What are the manifest and packaging requirements?

- Package ID: `FMWK-002-write-path`
- Framework ID: `FMWK-002`
- Version: `1.0.0`
- Staging root is authoritative: `staging/FMWK-002-write-path/`
- The package must be importable through a clean `write_path/__init__.py`
- `RESULTS.md` must record hashes for every created file
- `builder_evidence.json` must include `run_id`, active `attempt`, red->green evidence, full test command/result, changed files, plus the orchestrator-provided `handoff_hash` and `q13_answers_hash` copied verbatim when implementation happens

[CRITICAL_REVIEW_REQUIRED]: The current prompt for this turn did not inject `handoff_hash` or `q13_answers_hash`, even though the finalize step says they will be provided in the prompt. My assumption is that this omission does not block the 13Q gate and only matters after reviewer PASS, but the reviewer/orchestrator should confirm how those values will be supplied on the build turn.

---

## Q8 — What are the dependencies?

External/contracts:
- FMWK-001 Ledger contracts for `append`, `read_since`, `get_tip`
- FMWK-005 Graph contracts for `fold_event`, `export_snapshot`, `load_snapshot`, `reset_state`
- `platform_sdk.tier0_core.config`
- `platform_sdk.tier0_core.secrets`
- `platform_sdk.tier0_core.logging`
- `platform_sdk.tier0_core.errors`
- `platform_sdk` storage/filesystem helpers

Stdlib dependencies called out in the handoff/context:
- `dataclasses`
- `typing`
- `decimal`
- `hashlib`
- `json`
- `pathlib`

Quality bar reference:
- Align package structure and evidence rigor with `staging/FMWK-001-ledger/ledger/` and its Turn B artifacts

---

## Q9 — What is the testing obligation?

Minimum package target is `40+` tests, with a handoff target of `45-55`.

Per-file minimums from the handoff:
- `tests/test_models.py`: 6
- `tests/test_system_events.py`: 6
- `tests/test_folds.py`: 12
- `tests/test_service_mutations.py`: 14
- `tests/test_recovery.py`: 12

Required named behaviors include:
- `test_submit_mutation_success_returns_receipt_after_fold`
- `test_submit_mutation_append_failure_no_fold`
- `test_submit_mutation_fold_failure_returns_typed_error_and_boundary`
- `test_signal_delta_clamps_at_upper_bound`
- `test_signal_delta_clamps_at_lower_bound`
- `test_create_snapshot_writes_artifact_before_snapshot_created`
- `test_recover_uses_post_snapshot_replay_only`
- `test_recover_without_snapshot_replays_from_genesis`
- `test_refold_from_genesis_resets_graph_and_preserves_ledger`

Verification commands eventually required:
- `PLATFORM_ENVIRONMENT=test pytest tests/test_models.py -v`
- `PLATFORM_ENVIRONMENT=test pytest tests/test_system_events.py -v`
- `PLATFORM_ENVIRONMENT=test pytest tests/test_folds.py -v`
- `PLATFORM_ENVIRONMENT=test pytest tests/test_service_mutations.py -v`
- `PLATFORM_ENVIRONMENT=test pytest tests/test_recovery.py -v`
- `PLATFORM_ENVIRONMENT=test pytest tests/ -v --tb=short`

TDD rule is strict: for each D8 behavior, design comment first, then failing test, then minimal implementation, then green refactor.

---

## Q10 — How does this integrate with existing components?

- HO1, HO2/runtime, and FMWK-006 submit mutations through `WritePathService.submit_mutation()`
- `submit_mutation()` calls the Ledger port to durably append first
- After durable append, the same event is folded into Graph through the Graph port
- Snapshot creation reads Graph state via `export_snapshot()`, writes the artifact, then routes a `snapshot_created` request back through the same append/fold path
- Recovery uses a provided or discovered `SnapshotDescriptor`, loads snapshot state into Graph, then replays only events after `snapshot_sequence` using `LedgerPort.read_since()`
- Full refold discards/reset Graph state, then replays the full Ledger from genesis without rewriting history
- The package depends on FMWK-001 and FMWK-005 contracts but does not absorb their ownership

---

## Q11 — Adversarial: what is the main failure mode I must preserve exactly?

The critical infrastructure failure is SC-008: durable Ledger append succeeds, then Graph fold fails. The correct behavior is not rollback, not partial success, and not silent retry. It must return `WritePathFoldError`, preserve the durable sequence boundary, and require deterministic recovery before more writes proceed.

Likely evaluator probes:
- append succeeds but `fold_event()` raises
- service accidentally returns a receipt anyway
- service allows another write after the fold failure without recovery
- recovery replays from the wrong boundary or replays the failed event twice out of order

---

## Q12 — Adversarial: what shortcut am I forbidden to take?

I cannot add a hidden fast path for system events, snapshots, or recovery that bypasses the normal append/fold contract. `session_start`, `session_end`, and `snapshot_created` may be authored without HO1, but they still have to go through the same `submit_mutation()` path. I also cannot bypass the declared ports with direct Graph mutation or direct Ledger writes, even in tests.

Likely shortcut failures:
- special-casing `snapshot_created` without durable append
- folding system events directly into Graph without Ledger append
- using tests-only helpers as the real package surface instead of declared doubles in package code

---

## Q13 — Adversarial: what semantic drift would mean I misunderstood the framework?

Semantic drift would be treating the Write Path as a smart governance engine instead of a synchronous consistency layer. If I add query APIs, policy decisions, orchestration semantics, or background work, I have crossed the boundary. If I put execution into Graph, or if I let caller success mean anything less than durable append plus completed fold, I have broken the primitive assembly model.

The semantic audit I should hold against every implementation choice:
- Does this preserve Ledger as durable truth and Graph as derived state?
- Is the Write Path only sequencing append/fold/snapshot/replay mechanics?
- Would this still be explainable as infrastructure six months later, without hidden policy?
- Does every success receipt still mean "durable append + completed fold"?
