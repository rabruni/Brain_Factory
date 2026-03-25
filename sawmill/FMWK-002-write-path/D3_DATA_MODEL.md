# D3: Data Model — Write Path (FMWK-002)
Meta: v:1.0.0 (matches D2) | status:Final | shared entities:4

---

## Entities

### E-001 — MutationRequest
- Scope: SHARED
- Used By: FMWK-004 (HO1), FMWK-003 (HO2 system-path calls), runtime startup/shutdown logic, FMWK-006 during package events
- Source: SC-001, SC-002, SC-003, SC-007, SC-008
- Description: The caller-visible request envelope submitted to the Write Path for all live mutations. It carries the event type, version, timestamp, provenance, and type-specific payload that will be appended through FMWK-001 and folded into Graph state. The request does not include Ledger-assigned fields such as sequence, previous_hash, or event hash.

Fields:

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| event_type | string | yes | Ledger event category to append and fold | Must be one of the supported values in the Write Path event set: `node_creation`, `signal_delta`, `methylation_delta`, `suppression`, `unsuppression`, `mode_change`, `consolidation`, `session_start`, `session_end`, `package_install`, `package_uninstall`, `framework_install`, `snapshot_created`, `intent_transition`, `work_order_transition` |
| schema_version | string | yes | Schema version for the payload shape | semver string |
| timestamp | string | yes | Creation time for the event | ISO-8601 UTC with `Z` suffix |
| provenance | object | yes | Source framework and actor information | Must match FMWK-001 Provenance shape: `framework_id` required, `actor` required, `pack_id` optional |
| payload | object | yes | Event-type-specific mutation data | Must match the payload schema for the chosen `event_type` |

JSON example:
```json
{
  "event_type": "signal_delta",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-21T19:40:00Z",
  "provenance": {
    "framework_id": "FMWK-004",
    "pack_id": "PC-002-signal",
    "actor": "agent"
  },
  "payload": {
    "node_id": "0195b4e0-4f2a-7000-8000-000000000042",
    "signal_type": "entity",
    "delta": "0.10"
  }
}
```

Invariants:
- `event_type` determines the required payload schema.
- `schema_version`, `timestamp`, and `provenance` are always present.
- Callers never supply Ledger-assigned fields (`event_id`, `sequence`, `previous_hash`, `hash`).

### E-002 — MutationReceipt
- Scope: SHARED
- Used By: FMWK-004, FMWK-003, runtime startup/shutdown logic, FMWK-006
- Source: SC-001, SC-002, SC-004
- Description: The success receipt returned by the Write Path after a mutation has been durably appended and fully folded. It gives callers the durable sequence boundary and resulting event hash they can use for audit and recovery reasoning.

Fields:

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| sequence_number | integer | yes | Ledger sequence assigned to the appended event | `>= 0` |
| event_hash | string | yes | Hash of the appended Ledger event | `sha256:` + 64 lowercase hex chars |
| fold_status | string | yes | Fold completion state for the request | Enum: `folded` |

JSON example:
```json
{
  "sequence_number": 41,
  "event_hash": "sha256:7d5c8f428d3f0a4c24e9c5ab5b8efef7e44603bb66750ab698f3d7c9fc3d2c17",
  "fold_status": "folded"
}
```

Invariants:
- A `MutationReceipt` exists only for successful append-and-fold operations.
- `fold_status` is always `folded`; failed requests return typed errors instead of partial receipts.
- `sequence_number` and `event_hash` correspond to the durable Ledger event created by the request.

### E-003 — SnapshotDescriptor
- Scope: SHARED
- Used By: runtime startup/shutdown logic, FMWK-005 (Graph), FMWK-006 audit/recovery surfaces
- Source: SC-004, SC-005, SC-009
- Description: Metadata for a persisted Graph snapshot coordinated by the Write Path. It identifies the artifact location, the last Ledger sequence included in the snapshot, and the artifact hash recorded in the corresponding `snapshot_created` event.

Fields:

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| snapshot_sequence | integer | yes | Highest Ledger sequence included in the snapshot | `>= 0` |
| snapshot_file | string | yes | Snapshot artifact path | Absolute path under `/snapshots/` ending in `.snapshot` |
| snapshot_hash | string | yes | Hash of the snapshot artifact | `sha256:` + 64 lowercase hex chars |

JSON example:
```json
{
  "snapshot_sequence": 41,
  "snapshot_file": "/snapshots/41.snapshot",
  "snapshot_hash": "sha256:c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
}
```

Invariants:
- Recovery replay starts strictly after `snapshot_sequence`.
- `snapshot_file` and `snapshot_hash` must match the `snapshot_created` payload recorded in the Ledger.
- The descriptor is valid only if the snapshot artifact can be loaded successfully.

### E-004 — RecoveryCursor
- Scope: SHARED
- Used By: runtime startup logic, maintenance/refold flows
- Source: SC-005, SC-006, SC-009
- Description: Internal/external coordination record describing where replay begins and what recovery mode is active. It lets the Write Path expose deterministic recovery boundaries without exposing Graph internals.

Fields:

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| mode | string | yes | Recovery strategy in use | Enum: `post_snapshot_replay`, `full_replay`, `full_refold` |
| replay_from_sequence | integer | yes | Last durable sequence already represented in state before replay begins | `>= -1`; `-1` means replay from genesis |
| replay_to_sequence | integer | yes | Ledger tip targeted for replay/refold completion | `>= replay_from_sequence` |

JSON example:
```json
{
  "mode": "post_snapshot_replay",
  "replay_from_sequence": 41,
  "replay_to_sequence": 47
}
```

Invariants:
- `post_snapshot_replay` starts at `snapshot_sequence`.
- `full_replay` and `full_refold` use `replay_from_sequence = -1`.
- Replay applies events in ascending sequence order from `replay_from_sequence + 1` through `replay_to_sequence`.

## Write-Path-Owned Payload Schemas

These payload schemas are owned by FMWK-002 and fill the gaps deferred by FMWK-001.

### methylation_delta payload
```json
{
  "node_id": "0195b4e0-4f2a-7000-8000-000000000042",
  "delta": "-0.15"
}
```
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| node_id | string | yes | UUID v7 of the target Graph node |
| delta | string | yes | Signed decimal string representing the direct methylation adjustment |

### suppression payload
```json
{
  "node_id": "0195b4e0-4f2a-7000-8000-000000000042",
  "projection_scope": "operator"
}
```
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| node_id | string | yes | UUID v7 of the target Graph node |
| projection_scope | string | yes | Non-empty projection scope name to add to the suppression mask |

### unsuppression payload
```json
{
  "node_id": "0195b4e0-4f2a-7000-8000-000000000042",
  "projection_scope": "operator"
}
```
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| node_id | string | yes | UUID v7 of the target Graph node |
| projection_scope | string | yes | Non-empty projection scope name to remove from the suppression mask |

### mode_change payload
```json
{
  "node_id": "0195b4e0-4f2a-7000-8000-000000000042",
  "mode": "deep-work"
}
```
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| node_id | string | yes | UUID v7 of the target Graph node |
| mode | string | yes | Non-empty mode name to record on the node |

### consolidation payload
```json
{
  "source_node_ids": [
    "0195b4e0-4f2a-7000-8000-000000000010",
    "0195b4e0-4f2a-7000-8000-000000000011"
  ],
  "consolidated_node_id": "0195b4e0-4f2a-7000-8000-000000000099"
}
```
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| source_node_ids | array[string] | yes | Non-empty array of UUID v7 node IDs |
| consolidated_node_id | string | yes | UUID v7 of the consolidation artifact node |

## Entity Relationship Map

```text
MutationRequest (E-001)
  |
  | append + fold success
  v
MutationReceipt (E-002)

SnapshotDescriptor (E-003)
  |
  | establishes replay boundary for
  v
RecoveryCursor (E-004)
```

## Migration Notes

No prior model — greenfield.
