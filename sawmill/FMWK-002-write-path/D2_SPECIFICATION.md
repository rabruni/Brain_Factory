# D2: Specification — Write Path (FMWK-002)
Meta: pkg:FMWK-002-write-path | v:1.0.0 | status:Final | author:spec-agent | sources:NORTH_STAR.md v3.0, BUILDER_SPEC.md v3.0, OPERATIONAL_SPEC.md v3.0, FWK-0-DRAFT.md v1.0.0, BUILD-PLAN.md v1.0, TASK.md | constitution:D1 v1.0.0

---

## Purpose

The Write Path is the synchronous infrastructure service that maintains consistency between the Ledger on disk and the Graph in memory. It is the sole mutation path in DoPeJarMo: callers submit an event to the Write Path, the Write Path appends it through FMWK-001, immediately folds it into Graph state, and only then acknowledges success. The same framework also coordinates session-boundary snapshots, startup replay from snapshot marker, and full re-fold of the Ledger during governed maintenance.

## NOT

- The Write Path is NOT a second event store. It does not own durable truth; the Ledger does.
- The Write Path is NOT a query engine. It does not serve HO2 retrieval, ranking, or traversal APIs.
- The Write Path is NOT a policy engine. It does not decide thresholds, decay, Traveler Rule behavior, or orchestration policy.
- The Write Path is NOT a background queue or daemon. It does not buffer writes for eventual fold.
- The Write Path is NOT allowed to write directly around FMWK-001 or accept direct caller-managed writes to Graph.
- The Write Path is NOT responsible for package gates, LLM execution, or semantic interpretation of human-relatable payloads.

## Scenarios

### Primary

#### SC-001 — Synchronous append-and-fold for caller-submitted mutation
- Priority: P0 (blocker)
- Source: BUILDER_SPEC.md "The Data Pattern", TASK.md "What to Spec"
- GIVEN HO1 or another declared caller submits a valid mutation request WHEN the Write Path processes it THEN it appends the event to the Ledger through FMWK-001 AND immediately folds the same event into Graph state AND returns success only after both steps complete AND the new state is available for immediate Graph reads
- Testing Approach: Unit/integration test with doubles for Ledger and Graph. Assert append happens before fold, success returns once, and folded state is visible at return time.

#### SC-002 — Direct system-event authoring
- Priority: P1 (must)
- Source: BUILDER_SPEC.md "Exception — System Events", TASK.md constraints
- GIVEN the runtime invokes a system-path operation for `session_start`, `session_end`, or `snapshot_created` WHEN the Write Path processes it THEN it authors the system event without routing through HO1 AND appends/folds it through the same synchronous path as any other mutation
- Testing Approach: Submit each supported system event through the system-path contract. Assert no HO1 dependency exists and the resulting event is durably appended and folded.

#### SC-003 — Signal accumulator fold
- Priority: P0 (blocker)
- Source: BUILDER_SPEC.md §Signal Accumulator, TASK.md constraints
- GIVEN a `signal_delta` event targeting an existing Graph node WHEN the Write Path folds it THEN the node's methylation value is updated immediately AND the resulting value remains within `0.0` through `1.0` inclusive AND no higher-layer decay or threshold policy is applied by the Write Path
- Testing Approach: Apply positive and negative deltas near both bounds. Assert immediate update, clamped range, and no extra framework-policy side effects.

#### SC-004 — Session-boundary snapshot
- Priority: P1 (must)
- Source: BUILDER_SPEC.md "Snapshotting", OPERATIONAL_SPEC.md shutdown/startup sections, TASK.md owns list
- GIVEN HO2 or runtime session logic signals a session boundary WHEN the Write Path creates a snapshot THEN it serializes current Graph state to disk AND records a snapshot sequence marker that identifies the last included Ledger event AND appends/folds a `snapshot_created` event that references the snapshot artifact
- Testing Approach: Drive snapshot creation against a non-empty Graph. Assert snapshot artifact exists, includes a sequence marker, and `snapshot_created` is appended after artifact creation metadata is available.

#### SC-005 — Startup recovery from snapshot marker
- Priority: P0 (blocker)
- Source: BUILDER_SPEC.md "Snapshotting", OPERATIONAL_SPEC.md Q1/Q3/startup, TASK.md owns list
- GIVEN a persisted snapshot with marker sequence `S` and a Ledger tip greater than `S` WHEN the Write Path performs startup recovery THEN it loads the snapshot state AND replays exactly the events after `S` in ascending sequence order AND reconstructs a Graph state equivalent to replaying the full Ledger through the same fold logic
- Testing Approach: Create events, snapshot at `S`, append additional events, then recover. Assert only post-`S` events are replayed and the recovered Graph matches a full replay reference.

#### SC-006 — Retroactive healing by full re-fold
- Priority: P1 (must)
- Source: BUILDER_SPEC.md "Retroactive Healing", OPERATIONAL_SPEC.md Q7, TASK.md owns list
- GIVEN governed maintenance is authorized and fold logic has changed WHEN the Write Path performs retroactive healing THEN it rebuilds Graph state by replaying the Ledger from genesis without modifying historical Ledger events AND produces state according to the new fold logic
- Testing Approach: Build Graph under fold rule A, switch to fold rule B in a controlled test, refold from genesis, and assert Ledger contents stay unchanged while Graph state reflects rule B.

### Edge Cases

#### SC-007 — Ledger append failure
- Priority: P0 (blocker)
- Source: OPERATIONAL_SPEC.md failure matrix, TASK.md constraints, FMWK-001 D4 ERR-001
- GIVEN the Ledger is unreachable or rejects the append WHEN the Write Path processes a mutation THEN it returns a typed append failure AND does not fold the event into Graph AND does not acknowledge success
- Testing Approach: Configure Ledger double to fail append. Assert Graph double receives no fold call and caller receives append failure immediately.

#### SC-008 — Fold failure after durable append
- Priority: P1 (must)
- Source: TASK.md atomicity requirement, OPERATIONAL_SPEC.md "block rather than guess"
- GIVEN the Ledger append succeeds but Graph fold fails WHEN the Write Path processes the mutation THEN it does not acknowledge success AND returns a typed fold failure AND records the durable sequence boundary needed for deterministic recovery before further writes proceed
- Testing Approach: Ledger double succeeds, Graph double fails fold. Assert no success receipt is returned, failure is surfaced, and recovery can replay from the durable sequence.

#### SC-009 — Recovery with no usable snapshot
- Priority: P1 (must)
- Source: BUILDER_SPEC.md "destroy it and rebuild", OPERATIONAL_SPEC.md startup
- GIVEN startup finds no snapshot or finds an unusable snapshot marker WHEN recovery begins THEN the Write Path builds Graph state by replaying the full Ledger from genesis and still reaches a valid runtime state
- Testing Approach: Run recovery with no snapshot present, then with snapshot load failure. Assert both paths replay from sequence 0 and converge on the expected Graph state.

## Deferred Capabilities

**DEF-001 — Multi-process writer coordination**
- What: Replacing the single-process mutation assumption with cross-process transactional append/fold coordination
- Why Deferred: KERNEL architecture assumes one kernel process and one Write Path instance
- Trigger to add: Deployment model changes to multiple kernel processes sharing one Ledger
- Impact if never added: Write Path remains correct only under single-process deployment

**DEF-002 — Snapshot binary format optimization**
- What: Choosing and optimizing a compact snapshot serialization format
- Why Deferred: Authority requires a sequence marker and recoverability, but not a particular binary format
- Trigger to add: Graph size or startup latency makes the initial format insufficient
- Impact if never added: Startup still works; snapshots may be larger or slower than ideal

## Success Criteria

- [ ] Every successful mutation goes through append then fold then success return, in that order
- [ ] No success is returned if the Ledger append fails
- [ ] No success is returned if Graph fold fails
- [ ] `signal_delta` folds keep methylation in `0.0–1.0`
- [ ] `session_start`, `session_end`, and `snapshot_created` can be authored by the system path without HO1
- [ ] Snapshot artifacts carry a sequence marker sufficient for post-snapshot replay
- [ ] Startup recovery replays only events after the snapshot marker when a usable snapshot exists
- [ ] Startup recovery replays from genesis when no usable snapshot exists
- [ ] Retroactive healing changes Graph state only through re-fold, never by rewriting Ledger history
- [ ] All access uses declared dependency contracts and `platform_sdk`

## Clarifications

All clarifications live in D6. Use pointers only:
- See D6 CLR-001 (methylation fold rule)
- See D6 CLR-002 (fold failure after durable append)
- See D6 CLR-003 (snapshot orchestration vs Graph ownership boundary)
