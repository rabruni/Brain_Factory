# D9: Holdout Scenarios — Write Path (FMWK-002)
Meta: v:1.0.0 | contracts:D4 1.0.0 | status:Final | author:holdout-agent | last run:Not yet executed
CRITICAL: Builder MUST NOT see these scenarios before completing work.

## Purpose
Behavioral holdout scenarios only. No executable code. Evaluator later discovers API surface from staged code and writes tests.

```yaml
scenario_id: "HS-001"
title: "Live mutation becomes durable, folded, and immediately visible"
priority: P0
authority:
  d2_scenarios: [SC-001, SC-003]
  d4_contracts: [IN-001, OUT-001, SIDE-001, SIDE-002]
category: happy-path
setup:
  description: "A caller prepares a valid live mutation that targets an existing Graph node."
  preconditions:
    - "A Graph node already exists and is observable through Graph reads."
    - "The caller has a valid mutation request for a `signal_delta` event."
    - "The requested delta would change the node's methylation value."
action:
  description: "The caller submits the mutation through the Write Path."
  steps:
    - "Submit the valid mutation request."
    - "Wait for the Write Path to return its caller-visible result."
    - "Read Graph state for the targeted node immediately after success returns."
expected_outcome:
  description: "The mutation is appended, folded, and visible by the time success is reported."
  assertions:
    - subject: "Mutation submission"
      condition: "The request succeeds"
      observable: "The caller receives a success receipt containing a sequence number, an event hash, and `fold_status` equal to `folded`."
    - subject: "Graph state"
      condition: "Immediately after success returns"
      observable: "Graph reads observe the folded state for the submitted event."
    - subject: "Target node methylation"
      condition: "After the `signal_delta` fold completes"
      observable: "The resulting methylation value remains within `0.0` through `1.0` inclusive."
  negative_assertions:
    - "The caller does not receive success before the folded state is observable."
    - "The resulting methylation value does not fall below `0.0` or exceed `1.0`."
    - "The Write Path does not apply higher-layer decay or threshold policy as part of this fold."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "The returned success receipt."
  - "Graph read output captured immediately after success."
  - "The observed methylation value before and after the mutation."
```

Authority Basis:
- D2 SC-001: "it appends the event to the Ledger through FMWK-001 AND immediately folds the same event into Graph state AND returns success only after both steps complete AND the new state is available for immediate Graph reads"
- D2 SC-003: "the node's methylation value is updated immediately AND the resulting value remains within `0.0` through `1.0` inclusive AND no higher-layer decay or threshold policy is applied by the Write Path"
- D4 IN-001 Observable Postcondition 3: "Success returns `MutationReceipt{sequence_number, event_hash, fold_status:\"folded\"}`."
- D4 IN-001 Observable Postcondition 4: "Immediately after success, Graph reads observe the folded state for the event."
- D4 IN-001 Observable Postcondition 5: "For `signal_delta` and `methylation_delta`, the resulting Graph methylation value remains in `0.0–1.0`."
- D4 SIDE-001: "Append occurs before any Graph fold attempt for the same mutation"
- D4 SIDE-002: "Live mutation fold happens strictly after durable append and before success return"

Notes for Evaluator:
- Use any caller-discoverable path that maps to live mutation submission, but keep the expectation limited to the receipt and immediate read visibility described above.

```yaml
scenario_id: "HS-002"
title: "Session-boundary snapshot creates an artifact and records snapshot creation through the same synchronous path"
priority: P1
authority:
  d2_scenarios: [SC-002, SC-004]
  d4_contracts: [IN-001, IN-002, OUT-002, SIDE-003, ERR-003]
category: lifecycle
setup:
  description: "Runtime session-boundary logic prepares to create a snapshot from a non-empty Graph."
  preconditions:
    - "Current Graph state is non-empty."
    - "A session boundary or orderly shutdown condition exists."
    - "Snapshot storage is available."
action:
  description: "The runtime session-boundary caller requests snapshot creation."
  steps:
    - "Initiate snapshot creation from the session-boundary path."
    - "Wait for the snapshot operation to return its caller-visible result."
    - "Observe the returned snapshot descriptor and the caller-visible effects of the recorded snapshot creation."
expected_outcome:
  description: "The snapshot artifact is created first, then a corresponding snapshot creation event is recorded through the Write Path."
  assertions:
    - subject: "Snapshot operation"
      condition: "Artifact creation succeeds"
      observable: "The caller receives a snapshot descriptor containing the artifact path, artifact hash, and highest included Ledger sequence."
    - subject: "Snapshot artifact"
      condition: "Before success returns"
      observable: "A snapshot artifact has been written to disk."
    - subject: "Recorded snapshot creation"
      condition: "After descriptor creation"
      observable: "A corresponding `snapshot_created` mutation is submitted using the descriptor fields and becomes part of the same governed append-and-fold behavior."
  negative_assertions:
    - "The operation does not report snapshot success before the artifact exists."
    - "If artifact creation fails, no successful `snapshot_created` result is reported."
    - "The runtime caller is not required to route this system event through HO1 to complete the session-boundary operation."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "The returned snapshot descriptor."
  - "The written snapshot artifact path and hash."
  - "Caller-visible evidence that a corresponding `snapshot_created` mutation was recorded."
```

Authority Basis:
- D2 SC-002: "WHEN the Write Path processes it THEN it authors the system event without routing through HO1 AND appends/folds it through the same synchronous path as any other mutation"
- D2 SC-004: "it serializes current Graph state to disk AND records a snapshot sequence marker that identifies the last included Ledger event AND appends/folds a `snapshot_created` event that references the snapshot artifact"
- D4 IN-002 Observable Postcondition 1: "A snapshot artifact is written to disk before success returns."
- D4 IN-002 Observable Postcondition 2: "The returned `SnapshotDescriptor` contains the artifact path, artifact hash, and highest included Ledger sequence."
- D4 IN-002 Observable Postcondition 3: "A corresponding `snapshot_created` mutation is submitted through `IN-001` using the descriptor fields."
- D4 IN-002 Observable Postcondition 4: "If snapshot artifact creation fails, no `snapshot_created` success is returned."
- D4 SIDE-003: "Artifact creation completes before `snapshot_created` is submitted via `IN-001`"
- D4 IN-001 Constraints: "`snapshot_created` must only be submitted after the snapshot artifact metadata exists."

Notes for Evaluator:
- This scenario is about caller-visible sequencing and outcomes. Do not require internal knowledge of how the artifact is serialized.

```yaml
scenario_id: "HS-003"
title: "Startup recovery chooses post-snapshot replay when usable and full replay when not"
priority: P0
authority:
  d2_scenarios: [SC-005, SC-009]
  d4_contracts: [IN-003, OUT-003, SIDE-002, ERR-004]
category: lifecycle
setup:
  description: "Two startup recovery situations are prepared: one with a usable snapshot and one without a usable snapshot."
  preconditions:
    - "There is a Ledger tip beyond at least one earlier sequence boundary."
    - "Case A has a persisted snapshot with a valid marker sequence below the current Ledger tip."
    - "Case B has either no snapshot or an unusable snapshot marker."
action:
  description: "The runtime startup path performs recovery in both cases."
  steps:
    - "Start recovery with the usable snapshot inputs from Case A."
    - "Observe the returned recovery cursor and the reconstructed Graph state for Case A."
    - "Start recovery again with no usable snapshot inputs from Case B."
    - "Observe the returned recovery cursor and the reconstructed Graph state for Case B."
expected_outcome:
  description: "Recovery replays only the required range when a usable snapshot exists and replays from genesis when it does not."
  assertions:
    - subject: "Case A recovery"
      condition: "A usable snapshot is provided and loaded"
      observable: "Recovery replays exactly the events after the snapshot sequence in ascending order through the current tip."
    - subject: "Case A result"
      condition: "Recovery succeeds with a usable snapshot"
      observable: "The returned recovery cursor describes the replay boundaries actually used."
    - subject: "Case B recovery"
      condition: "No usable snapshot is provided"
      observable: "Recovery replays from genesis with `replay_from_sequence = -1` in ascending order through the current tip."
    - subject: "Recovered Graph state"
      condition: "Each recovery completes successfully"
      observable: "The reconstructed Graph state is valid for runtime use, and the usable-snapshot case is equivalent to replaying the full Ledger through the same fold logic."
  negative_assertions:
    - "Case A does not replay events at or before the usable snapshot sequence."
    - "Case B does not depend on a snapshot to reach a valid runtime state."
    - "Neither recovery path reports success with replay boundaries that differ from the boundaries actually used."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "The recovery cursor returned for Case A."
  - "The recovery cursor returned for Case B."
  - "Observed replay boundaries and resulting Graph state for both cases."
```

Authority Basis:
- D2 SC-005: "it loads the snapshot state AND replays exactly the events after `S` in ascending sequence order AND reconstructs a Graph state equivalent to replaying the full Ledger through the same fold logic"
- D2 SC-009: "startup finds no snapshot or finds an unusable snapshot marker ... THEN the Write Path builds Graph state by replaying the full Ledger from genesis and still reaches a valid runtime state"
- D4 IN-003 Observable Postcondition 1: "If a usable snapshot is provided and loaded, recovery replays exactly the events after `snapshot_sequence`."
- D4 IN-003 Observable Postcondition 2: "If no usable snapshot is provided, recovery replays from genesis with `replay_from_sequence = -1`."
- D4 IN-003 Observable Postcondition 3: "Replay applies events in ascending sequence order through the current Ledger tip."
- D4 IN-003 Observable Postcondition 4: "Success returns a `RecoveryCursor` describing the mode and replay boundaries actually used."
- D4 SIDE-002: "replay/refold processes events in ascending sequence order"

Notes for Evaluator:
- Treat this as two concrete startup conditions within one scenario so both recovery modes are exercised under one D9 entry.

```yaml
scenario_id: "HS-004"
title: "Governed retroactive healing rebuilds Graph state from genesis without altering Ledger history"
priority: P1
authority:
  d2_scenarios: [SC-006]
  d4_contracts: [IN-004, OUT-003, SIDE-002, ERR-004]
category: integrity
setup:
  description: "A governed maintenance path is authorized after fold logic has changed."
  preconditions:
    - "Ledger history already exists."
    - "Graph state currently reflects earlier fold logic."
    - "Operator-authorized maintenance is available."
action:
  description: "The authorized maintenance path triggers a full re-fold from genesis."
  steps:
    - "Initiate governed full re-fold."
    - "Wait for the caller-visible recovery result."
    - "Observe the resulting Graph state and the replay boundaries used."
expected_outcome:
  description: "The operation resets runtime state, replays the entire Ledger from genesis, and returns boundaries that describe a full refold."
  assertions:
    - subject: "Graph runtime state"
      condition: "Before replay begins"
      observable: "Existing runtime state is discarded or reset before the re-fold starts."
    - subject: "Replay boundaries"
      condition: "The full re-fold succeeds"
      observable: "Replay begins from genesis with `replay_from_sequence = -1` and processes all events through the current tip in ascending order."
    - subject: "Returned recovery result"
      condition: "The full re-fold succeeds"
      observable: "The caller receives a recovery cursor with mode `full_refold`, `replay_from_sequence:-1`, and the replay tip used."
    - subject: "Post-refold Graph state"
      condition: "Replay completes under the new fold logic"
      observable: "Graph state reflects the new fold logic."
  negative_assertions:
    - "Historical Ledger events are not modified during retroactive healing."
    - "The operation does not report success without replaying through the current tip."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "The returned recovery cursor for the full refold."
  - "Observed replay boundaries and ordering."
  - "Evidence that Ledger history remains unchanged while Graph state changes."
```

Authority Basis:
- D2 SC-006: "it rebuilds Graph state by replaying the Ledger from genesis without modifying historical Ledger events AND produces state according to the new fold logic"
- D4 IN-004 Observable Postcondition 1: "Existing Graph runtime state is discarded or reset before re-fold begins."
- D4 IN-004 Observable Postcondition 2: "Ledger history is not modified."
- D4 IN-004 Observable Postcondition 3: "Replay begins from genesis (`replay_from_sequence = -1`) and processes all events through tip in ascending order."
- D4 IN-004 Observable Postcondition 4: "Success returns `RecoveryCursor{mode:\"full_refold\", replay_from_sequence:-1, replay_to_sequence:<tip>}`."
- D4 SIDE-002: "replay/refold processes events in ascending sequence order"

Notes for Evaluator:
- This scenario is about governed behavior and caller-visible outcomes, not about how fold logic changes are injected.

```yaml
scenario_id: "HS-005"
title: "Mutation failures distinguish append rejection from fold failure after durable append"
priority: P0
authority:
  d2_scenarios: [SC-007, SC-008]
  d4_contracts: [IN-001, SIDE-001, SIDE-002, ERR-001, ERR-002]
category: failure-injection
setup:
  description: "Two failure conditions are prepared for the same kind of caller-visible mutation request."
  preconditions:
    - "A valid mutation request is available."
    - "Case A can force the Ledger append step to fail."
    - "Case B can allow append to succeed but cause the Graph fold step to fail."
action:
  description: "The caller submits the mutation once under each failure condition."
  steps:
    - "Submit the mutation under Case A where append is rejected."
    - "Observe the caller-visible result and Graph state for Case A."
    - "Submit the mutation under Case B where append succeeds and fold fails."
    - "Observe the caller-visible result and the recovery boundary information available for Case B."
expected_outcome:
  description: "Append rejection leaves Graph untouched, while fold failure after durable append returns a distinct failure and requires recovery from the durable boundary."
  assertions:
    - subject: "Case A mutation"
      condition: "Ledger append fails"
      observable: "The caller receives a typed append failure and no success receipt."
    - subject: "Case A Graph state"
      condition: "Ledger append fails"
      observable: "No fold occurs for the submitted event."
    - subject: "Case B mutation"
      condition: "Ledger append succeeds but fold fails"
      observable: "The caller receives a typed fold failure and no success receipt."
    - subject: "Case B recovery state"
      condition: "Fold fails after durable append"
      observable: "The durable sequence boundary needed for deterministic recovery is recorded before further writes proceed."
  negative_assertions:
    - "Case A does not acknowledge success."
    - "Case B does not acknowledge success."
    - "Case B is not treated as an append failure."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "The caller-visible error returned for Case A."
  - "The caller-visible error returned for Case B."
  - "Observed evidence that no fold occurred in Case A."
  - "Observed evidence of the durable recovery boundary in Case B."
```

Authority Basis:
- D2 SC-007: "it returns a typed append failure AND does not fold the event into Graph AND does not acknowledge success"
- D2 SC-008: "it does not acknowledge success AND returns a typed fold failure AND records the durable sequence boundary needed for deterministic recovery before further writes proceed"
- D4 IN-001 Observable Postcondition 10: "If append fails, no fold occurs and no success receipt is returned."
- D4 IN-001 Observable Postcondition 11: "If append succeeds but fold fails, no success receipt is returned and the caller receives `ERR-002 WritePathFoldError`."
- D4 SIDE-001 Failure Behavior: "If FMWK-001 returns connection, serialization, or sequence failure, the Write Path returns append failure and performs no fold"
- D4 SIDE-002 Failure Behavior: "Fold failure after durable append returns `ERR-002 WritePathFoldError`; success is not acknowledged; recovery must use the durable sequence boundary"
- D4 ERR-001: "Condition: FMWK-001 append fails or rejects the mutation"
- D4 ERR-002: "Condition: Durable append succeeded but Graph fold failed"

Notes for Evaluator:
- Keep the two failure cases behaviorally distinct. The expected difference is the error class and whether the durable recovery boundary exists.

## Coverage Matrix
All D2 P0 and P1 scenarios MUST have holdout coverage. Zero gaps allowed.

| D2 Scenario | Priority | Holdout Coverage | Notes |
|-------------|----------|------------------|-------|
| SC-001 | P0 | HS-001 | Live append-and-fold with immediate visibility |
| SC-002 | P1 | HS-002 | System-authored snapshot path without HO1 routing |
| SC-003 | P0 | HS-001 | Methylation update is immediate and clamped |
| SC-004 | P1 | HS-002 | Snapshot artifact and `snapshot_created` recording |
| SC-005 | P0 | HS-003 | Usable snapshot recovery path |
| SC-006 | P1 | HS-004 | Full re-fold from genesis under governed maintenance |
| SC-007 | P0 | HS-005 | Append rejection behavior |
| SC-008 | P1 | HS-005 | Fold failure after durable append |
| SC-009 | P1 | HS-003 | No usable snapshot falls back to genesis replay |

## Evaluator Contract
Evaluator writes, per scenario per attempt:
- `eval_tests/attemptN/HS-NNN.py`
- `eval_tests/attemptN/HS-NNN.mapping.md`
- `eval_tests/attemptN/HS-NNN.run{1,2,3}.json`
Mapping file MUST cite D9 fields used + staged code paths used for API discovery.
Evaluator may use code to learn HOW to call the implementation, never WHAT behavior to expect.

## Run Protocol
Order: P0 first, then P1, then P2.
Scenario pass: 2 of 3 runs.
Overall pass: all P0 pass, all P1 pass, overall >= 90%.
