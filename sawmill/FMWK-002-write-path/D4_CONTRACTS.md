# D4: Contracts — Write Path (FMWK-002)
Meta: v:1.0.0 (matches D2) | data model: D3 v1.0.0 | status:Final

IDs: IN-NNN (inbound), OUT-NNN (outbound), SIDE-NNN (side-effect), ERR-NNN (error).
Every contract references at least one D2 scenario.

---

## Inbound (IN-###)

### IN-001 — submit_mutation(request) → MutationReceipt

- Caller: FMWK-004 (HO1), FMWK-003 (system-triggered work), FMWK-006 (package events), runtime startup/shutdown logic for system events
- Trigger: Any live state mutation that must become durable and immediately visible
- Scenarios: SC-001, SC-002, SC-003, SC-007, SC-008

**Request Shape**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| event_type | string | yes | One of: `node_creation`, `signal_delta`, `methylation_delta`, `suppression`, `unsuppression`, `mode_change`, `consolidation`, `session_start`, `session_end`, `package_install`, `package_uninstall`, `framework_install`, `snapshot_created`, `intent_transition`, `work_order_transition` |
| schema_version | string | yes | semver string |
| timestamp | string | yes | ISO-8601 UTC with `Z` suffix |
| provenance.framework_id | string | yes | Non-empty framework ID |
| provenance.pack_id | string | no | Non-empty pack ID if present |
| provenance.actor | string | yes | Enum: `system`, `operator`, `agent` |
| payload | object | yes | Must match the payload schema for `event_type` |

**Inline Payload Schemas**

These are restated from FMWK-001 D3 for shared event types and from this D3 for FMWK-002-owned event types.

*node_creation payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| node_id | string | yes | UUID v7 of the new Graph node |
| node_type | string | yes | Non-empty node type |
| initial_methylation | string | yes | Decimal string in `0.0–1.0` |
| base_weight | string | yes | Non-negative decimal string |

*signal_delta payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| node_id | string | yes | UUID v7 of the target Graph node |
| signal_type | string | yes | Enum: `entity`, `mode`, `stimulus`, `regime` |
| delta | string | yes | Signed decimal string |

*methylation_delta payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| node_id | string | yes | UUID v7 of the target Graph node |
| delta | string | yes | Signed decimal string |

*suppression payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| node_id | string | yes | UUID v7 of the target Graph node |
| projection_scope | string | yes | Non-empty projection scope |

*unsuppression payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| node_id | string | yes | UUID v7 of the target Graph node |
| projection_scope | string | yes | Non-empty projection scope |

*mode_change payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| node_id | string | yes | UUID v7 of the target Graph node |
| mode | string | yes | Non-empty mode name |

*consolidation payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| source_node_ids | array[string] | yes | Non-empty array of UUID v7 node IDs |
| consolidated_node_id | string | yes | UUID v7 of the consolidation artifact node |

*session_start payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| session_id | string | yes | UUID v7 |
| actor_id | string | yes | Non-empty actor identifier |
| session_type | string | yes | Enum: `operator`, `user` |

*session_end payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| session_id | string | yes | UUID v7 matching the session |
| reason | string | yes | Enum: `normal`, `timeout`, `error` |

*snapshot_created payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| snapshot_sequence | integer | yes | `>= 0` |
| snapshot_file | string | yes | Absolute `/snapshots/...snapshot` path |
| snapshot_hash | string | yes | `sha256:` + 64 lowercase hex chars |

*package_install payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| package_id | string | yes | Non-empty package identifier |
| framework_id | string | yes | Non-empty framework identifier |
| version | string | yes | semver string |
| manifest_hash | string | yes | `sha256:` + 64 lowercase hex chars |

*package_uninstall, framework_install, intent_transition, work_order_transition payloads:*
- These are accepted and routed through the synchronous append-and-fold contract, but their field ownership belongs to their owning frameworks. The Write Path requires them to be JSON objects and folds them according to event type semantics supplied by the event name and owned schemas.

**Observable Postconditions**
1. The Write Path calls FMWK-001 `append()` exactly once for the request.
2. If append succeeds, the appended event is folded into Graph state before success returns.
3. Success returns `MutationReceipt{sequence_number, event_hash, fold_status:"folded"}`.
4. Immediately after success, Graph reads observe the folded state for the event.
5. For `signal_delta` and `methylation_delta`, the resulting Graph methylation value remains in `0.0–1.0`.
6. For `suppression`, the target node's suppression mask includes `projection_scope`.
7. For `unsuppression`, the target node's suppression mask no longer includes `projection_scope`.
8. For `mode_change`, the target node records the supplied `mode`.
9. For `consolidation`, the consolidated node exists in Graph state and the source nodes remain traceable through Graph relationships.
10. If append fails, no fold occurs and no success receipt is returned.
11. If append succeeds but fold fails, no success receipt is returned and the caller receives `ERR-002 WritePathFoldError`.

**Constraints**
- Callers never append directly to FMWK-001 or write directly to FMWK-005.
- The Write Path performs mechanical folding only; it does not reinterpret payload meaning beyond event-type fold semantics.
- `snapshot_created` must only be submitted after the snapshot artifact metadata exists.

**Example**
```text
Request: {event_type:"signal_delta", schema_version:"1.0.0", timestamp:"2026-03-21T19:40:00Z",
          provenance:{framework_id:"FMWK-004", pack_id:"PC-002-signal", actor:"agent"},
          payload:{node_id:"0195...0042", signal_type:"entity", delta:"0.10"}}
Response: {sequence_number:41, event_hash:"sha256:...", fold_status:"folded"}
```

### IN-002 — create_snapshot() → SnapshotDescriptor

- Caller: FMWK-003 / runtime session-boundary logic
- Trigger: Session boundary or orderly shutdown
- Scenarios: SC-004

**Request Shape:** No caller payload. The current Graph state and Ledger tip are read from dependencies.

**Observable Postconditions**
1. A snapshot artifact is written to disk before success returns.
2. The returned `SnapshotDescriptor` contains the artifact path, artifact hash, and highest included Ledger sequence.
3. A corresponding `snapshot_created` mutation is submitted through `IN-001` using the descriptor fields.
4. If snapshot artifact creation fails, no `snapshot_created` success is returned.

### IN-003 — recover(cursor?) → RecoveryCursor

- Caller: runtime startup logic
- Trigger: Process start after crash, shutdown, or cold boot
- Scenarios: SC-005, SC-009

**Request Shape**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| snapshot_sequence | integer | no | `>= 0` if provided |
| snapshot_file | string | no | Absolute `/snapshots/...snapshot` path if provided |
| snapshot_hash | string | no | `sha256:` + 64 lowercase hex chars if provided |

**Observable Postconditions**
1. If a usable snapshot is provided and loaded, recovery replays exactly the events after `snapshot_sequence`.
2. If no usable snapshot is provided, recovery replays from genesis with `replay_from_sequence = -1`.
3. Replay applies events in ascending sequence order through the current Ledger tip.
4. Success returns a `RecoveryCursor` describing the mode and replay boundaries actually used.

### IN-004 — refold_from_genesis() → RecoveryCursor

- Caller: governed maintenance / operator-authorized maintenance path
- Trigger: Retroactive healing after fold logic change
- Scenarios: SC-006

**Request Shape:** No payload.

**Observable Postconditions**
1. Existing Graph runtime state is discarded or reset before re-fold begins.
2. Ledger history is not modified.
3. Replay begins from genesis (`replay_from_sequence = -1`) and processes all events through tip in ascending order.
4. Success returns `RecoveryCursor{mode:"full_refold", replay_from_sequence:-1, replay_to_sequence:<tip>}`.

## Outbound (OUT-###)

### OUT-001 — MutationReceipt
- Consumer: FMWK-004, FMWK-003, FMWK-006, runtime system paths
- Scenarios: SC-001, SC-002
- Response Shape: D3 E-002 MutationReceipt
- Example success: `{sequence_number:41, event_hash:"sha256:...", fold_status:"folded"}`
- Example failure: typed error instead of partial receipt

### OUT-002 — SnapshotDescriptor
- Consumer: runtime startup/shutdown logic, FMWK-005, FMWK-006
- Scenarios: SC-004
- Response Shape: D3 E-003 SnapshotDescriptor
- Example success: `{snapshot_sequence:41, snapshot_file:"/snapshots/41.snapshot", snapshot_hash:"sha256:..."}`
- Example failure: `ERR-003 SnapshotWriteError`

### OUT-003 — RecoveryCursor
- Consumer: runtime startup logic, maintenance flows
- Scenarios: SC-005, SC-006, SC-009
- Response Shape: D3 E-004 RecoveryCursor
- Example success: `{mode:"post_snapshot_replay", replay_from_sequence:41, replay_to_sequence:47}`
- Example failure: `ERR-004 ReplayRecoveryError`

## Side-Effects (SIDE-###)

### SIDE-001 — Ledger append via FMWK-001
- Target System: FMWK-001 Ledger
- Trigger: `IN-001 submit_mutation`
- Scenarios: SC-001, SC-002, SC-007, SC-008
- Write Shape: `append(event_data)` using the caller-supplied event envelope
- Ordering Guarantee: Append occurs before any Graph fold attempt for the same mutation
- Failure Behavior: If FMWK-001 returns connection, serialization, or sequence failure, the Write Path returns append failure and performs no fold

### SIDE-002 — Graph fold / state mutation
- Target System: FMWK-005 Graph
- Trigger: successful Ledger append during `IN-001`, replay during `IN-003`, or full refold during `IN-004`
- Scenarios: SC-001, SC-003, SC-005, SC-006, SC-008, SC-009
- Write Shape: Apply event-type-specific fold to Graph nodes, edges, suppression masks, modes, and methylation values
- Ordering Guarantee: Live mutation fold happens strictly after durable append and before success return; replay/refold processes events in ascending sequence order
- Failure Behavior: Fold failure after durable append returns `ERR-002 WritePathFoldError`; success is not acknowledged; recovery must use the durable sequence boundary

### SIDE-003 — Snapshot artifact write
- Target System: snapshot storage under `/snapshots/`
- Trigger: `IN-002 create_snapshot`
- Scenarios: SC-004
- Write Shape: Serialize current Graph state to snapshot artifact and compute `snapshot_hash`
- Ordering Guarantee: Artifact creation completes before `snapshot_created` is submitted via `IN-001`
- Failure Behavior: Snapshot artifact write failure returns `ERR-003 SnapshotWriteError`; no successful `snapshot_created` receipt is returned

## Errors (ERR-###)

### ERR-001 — WritePathAppendError
- Condition: FMWK-001 append fails or rejects the mutation
- Scenarios: SC-007
- Caller Action: Treat the mutation as not accepted. Retry only through the Write Path once the Ledger path is healthy.

### ERR-002 — WritePathFoldError
- Condition: Durable append succeeded but Graph fold failed
- Scenarios: SC-008
- Caller Action: Do not retry blindly. Use recovery/replay to restore Graph consistency from the durable sequence boundary before resuming writes.

### ERR-003 — SnapshotWriteError
- Condition: Snapshot artifact cannot be created, hashed, or staged for `snapshot_created`
- Scenarios: SC-004
- Caller Action: Keep operating without reporting snapshot success. Recovery will fall back to older snapshot or full replay.

### ERR-004 — ReplayRecoveryError
- Condition: Snapshot load, post-snapshot replay, or full refold fails
- Scenarios: SC-005, SC-006, SC-009
- Caller Action: Block startup or maintenance completion and surface the failure to the operator/runtime.

## Error Code Enum

| Code | Meaning | Retryable |
|------|---------|-----------|
| WRITE_PATH_APPEND_ERROR | Ledger append failed; mutation not folded | yes, after dependency recovery |
| WRITE_PATH_FOLD_ERROR | Durable append exists but Graph fold failed | no, recover first |
| SNAPSHOT_WRITE_ERROR | Snapshot artifact creation failed | yes |
| REPLAY_RECOVERY_ERROR | Recovery/refold could not complete | no, requires operator/runtime action |

## Testable Surface

| double_id | name | purpose | location (package code only, never tests/) | api_contract | failure_modes | invariants | intentional_simplifications |
|-----------|------|---------|--------------------------------------------|--------------|---------------|------------|-----------------------------|
| TD-001 | LedgerPortDouble | Deterministic append/read_since/get_tip behavior for success and failure paths | package code under write-path doubles module | Exposes `append`, `read_since`, `get_tip` with FMWK-001-compatible shapes | append failure, sequence/tip control, replay stream control | returned sequence boundaries stay monotonic unless explicitly configured to fail | in-memory only; no immudb transport |
| TD-002 | GraphPortDouble | Deterministic fold, snapshot, and reset behavior for live writes and recovery | package code under write-path doubles module | Exposes `fold`, `snapshot`, `load_snapshot`, `reset` | fold failure, snapshot failure, snapshot load failure | fold effects are immediately observable through stored state | simplified in-memory Graph model; no query planner |
