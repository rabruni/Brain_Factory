# D3: Data Model — FMWK-001-ledger
Meta: v:1.0.0 (matches D2) | status:Final | shared entities:9

## Entities
### E-001 — Ledger Event
- Scope: SHARED
- Used By: FMWK-002 write-path, FMWK-003 orchestration, FMWK-005 graph, FMWK-006 package-lifecycle, cold-storage validation tools
- Source: SC-001, SC-002, SC-003, SC-004, SC-005, SC-007, SC-008, SC-011
- Description: The canonical append-only event envelope stored by the ledger. It is self-describing, globally ordered, hash-linked to the previous event, and serialized deterministically for persistence and verification.

| Field | Type | Required | Description | Constraints |
| event_id:string | Type:uuid-v7 | Req:yes | Stable event identifier | Constraint:UUIDv7 string |
| sequence:number | Type:integer | Req:yes | Global monotonic ledger sequence | Constraint:`>= 0`; assigned only by ledger |
| event_type:string | Type:string | Req:yes | Event type discriminator | Constraint:non-empty; must be in approved catalog |
| schema_version:string | Type:semver | Req:yes | Payload/schema version | Constraint:`1.0.0` for this spec version |
| timestamp:string | Type:ISO-8601 UTC | Req:yes | Event creation time | Constraint:UTC timestamp with `Z` suffix |
| provenance:object | Type:Provenance | Req:yes | Framework, pack, and actor origin | Constraint:see nested constraints |
| previous_hash:string | Type:hash | Req:yes | Hash of prior event in chain | Constraint:`sha256:<64 lowercase hex>`; genesis uses zero hash |
| payload:object | Type:object | Req:yes | Event-type-specific payload | Constraint:validated by event type schema |
| hash:string | Type:hash | Req:yes | Hash of canonical serialized event excluding `hash` field | Constraint:`sha256:<64 lowercase hex>` |

```json
{
  "event_id": "0195b8d1-6d8d-7ef9-9c6a-4bd29ca2dce4",
  "sequence": 2,
  "event_type": "package_install",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:15:32Z",
  "provenance": {
    "framework_id": "FMWK-006",
    "pack_id": "PC-006-kernel-package",
    "actor": "system"
  },
  "previous_hash": "sha256:2ddcbf0b9a9120cc1d72fe073dc372f976922a0b7d20c0f5fd43589e3c56231d",
  "payload": {
    "package_id": "PKG-0001-kernel",
    "framework_id": "FMWK-001-ledger",
    "version": "1.0.0",
    "install_scope": "kernel",
    "manifest_hash": "sha256:06dfb23ab8cf9c6621fe58f465bf6f6a2e4698af1c8d8de7c093b2b26a3e5fb7"
  },
  "hash": "sha256:8c9c546d9fea3a48d36c1318bd91bc35499808722d2bb4f2e0eb342d6b3de4d7"
}
```

Invariants:
- `sequence` is unique and strictly increasing by 1 from genesis.
- `previous_hash` of sequence `0` is exactly `sha256:` plus 64 lowercase zeroes.
- `hash` is computed from canonical JSON serialization of the event excluding the `hash` field.
- The stored event bytes must round-trip without changing field meanings or order-independent hash outcome.

### E-002 — Verification Result
- Scope: SHARED
- Used By: cold-storage validation tools, FMWK-006 package-lifecycle, operators via DoPeJarMo diagnostics
- Source: SC-005, SC-008
- Description: Mechanical result of replaying and recomputing the ledger hash chain over a requested sequence interval.

| Field | Type | Required | Description | Constraints |
| valid:boolean | Type:boolean | Req:yes | Whether every checked event matched its stored hash and prior hash linkage | Constraint:true or false |
| start_sequence:number | Type:integer | Req:yes | Inclusive verification start | Constraint:`>= 0` |
| end_sequence:number | Type:integer | Req:yes | Inclusive verification end | Constraint:`>= start_sequence` |
| break_at:number | Type:integer | Req:no | First sequence where verification failed | Constraint:required when `valid=false` |

```json
{
  "valid": false,
  "start_sequence": 0,
  "end_sequence": 5,
  "break_at": 3
}
```

Invariants:
- `break_at` is omitted when `valid=true`.
- `break_at` identifies the first failed event, not the last successful one.

### E-003 — Ledger Tip
- Scope: SHARED
- Used By: append callers through the ledger abstraction, replay tools, diagnostics
- Source: SC-002, SC-006
- Description: The latest committed append position in the linear event chain.

| Field | Type | Required | Description | Constraints |
| sequence_number:number | Type:integer | Req:yes | Latest committed sequence | Constraint:`>= 0` when non-empty ledger |
| hash:string | Type:hash | Req:yes | Hash stored on the tip event | Constraint:`sha256:<64 lowercase hex>` |

```json
{
  "sequence_number": 12,
  "hash": "sha256:8b6e4791d3035430dc7f00692cfd0d2a59d789ab3ed86855f81044cd22fdfd4d"
}
```

Invariants:
- `sequence_number` and `hash` must match the most recent stored event.
- The next successful append must use this `hash` as `previous_hash`.

### E-004 — Provenance
- Scope: SHARED
- Used By: all event producers and auditors
- Source: SC-003
- Description: The event origin block that ties an event to framework scope, pack provenance, and actor class.

| Field | Type | Required | Description | Constraints |
| framework_id:string | Type:string | Req:yes | Framework origin identifier | Constraint:canonical stored value uses full framework identifier `FMWK-NNN-name` |
| pack_id:string | Type:string | Req:yes | Pack that emitted or owns the event | Constraint:non-empty pack identifier |
| actor:string | Type:enum | Req:yes | Origin actor class | Constraint:`system`, `operator`, or `agent` |

```json
{
  "framework_id": "FMWK-001-ledger",
  "pack_id": "PC-001-ledger-core",
  "actor": "system"
}
```

Invariants:
- `framework_id` stores the full framework identifier form `FMWK-NNN-name`; shorthand `FMWK-NNN` references in source material are treated as schematic placeholders.
- `actor` is restricted to the approved enum.
- Provenance is always present; anonymous events are invalid.

### E-005 — Node Creation Payload
- Scope: SHARED
- Used By: FMWK-002 write-path, FMWK-005 graph
- Source: SC-003
- Description: Minimum payload schema for the event that introduces a new graph node into ledger history.

| Field | Type | Required | Description | Constraints |
| node_id:string | Type:string | Req:yes | New node identifier | Constraint:non-empty |
| node_type:string | Type:string | Req:yes | Node kind discriminator | Constraint:non-empty |
| initial_state:object | Type:object | Req:yes | Framework-defined starting state | Constraint:must be JSON object |
| associated_entities:array | Type:array | Req:no | Related IDs recorded at creation | Constraint:array of strings when present |
| session_id:string | Type:string | Req:no | Session that caused creation | Constraint:non-empty when present |

```json
{
  "node_id": "intent-0195b8d1",
  "node_type": "intent",
  "initial_state": {
    "status": "DECLARED",
    "title": "Rebuild ledger framework"
  },
  "associated_entities": [
    "session-0195b8d1"
  ],
  "session_id": "session-0195b8d1"
}
```

Invariants:
- `node_id` must be unique within the owning framework's namespace.
- `initial_state` is opaque to ledger verification but must remain serializable under canonical JSON rules.

### E-006 — Signal Delta Payload
- Scope: SHARED
- Used By: FMWK-002 write-path, FMWK-005 graph
- Source: SC-003
- Description: Minimum payload schema for a signal adjustment event recorded by the ledger for later fold by the Write Path.

| Field | Type | Required | Description | Constraints |
| node_id:string | Type:string | Req:yes | Target node identifier | Constraint:non-empty |
| signal_name:string | Type:string | Req:yes | Named signal counter | Constraint:non-empty |
| delta:number | Type:integer | Req:yes | Integer signal increment or decrement | Constraint:non-zero integer |
| reason:string | Type:string | Req:no | Human-readable cause | Constraint:UTF-8 string when present |
| session_id:string | Type:string | Req:no | Session context | Constraint:non-empty when present |

```json
{
  "node_id": "memory-0195b8d1",
  "signal_name": "operator_reinforcement",
  "delta": 1,
  "reason": "operator confirmed importance",
  "session_id": "session-0195b8d1"
}
```

Invariants:
- `delta` is an integer; floating-point values are not allowed in the minimum schema.
- Ledger stores the delta only; it does not compute methylation values.

### E-007 — Package Install Payload
- Scope: SHARED
- Used By: FMWK-006 package-lifecycle, cold-storage validation tools
- Source: SC-003
- Description: Minimum payload schema for the package lifecycle event that records framework installation provenance in the ledger.

| Field | Type | Required | Description | Constraints |
| package_id:string | Type:string | Req:yes | Installed package identifier | Constraint:non-empty |
| framework_id:string | Type:string | Req:yes | Installed framework identifier | Constraint:non-empty |
| version:string | Type:semver | Req:yes | Installed version | Constraint:semantic version string |
| install_scope:string | Type:string | Req:yes | Installation domain or phase | Constraint:non-empty |
| manifest_hash:string | Type:hash | Req:yes | Hash of the installed package manifest | Constraint:`sha256:<64 lowercase hex>` |

```json
{
  "package_id": "PKG-0001-kernel",
  "framework_id": "FMWK-001-ledger",
  "version": "1.0.0",
  "install_scope": "kernel",
  "manifest_hash": "sha256:06dfb23ab8cf9c6621fe58f465bf6f6a2e4698af1c8d8de7c093b2b26a3e5fb7"
}
```

Invariants:
- `manifest_hash` must use the canonical hash string format.
- Package lifecycle owns install semantics; ledger owns only storage and ordering.

### E-008 — Session Start Payload
- Scope: SHARED
- Used By: FMWK-002 write-path, operator/session management flows
- Source: SC-003
- Description: Minimum payload schema for the mechanical system event that marks the start of a session boundary.

| Field | Type | Required | Description | Constraints |
| session_id:string | Type:string | Req:yes | Session identifier | Constraint:non-empty |
| session_kind:string | Type:string | Req:yes | Session class | Constraint:`operator` or `user` in current usage |
| subject_id:string | Type:string | Req:yes | Authenticated principal or actor namespace | Constraint:non-empty |
| started_by:string | Type:enum | Req:yes | Actor category that initiated the session | Constraint:`system`, `operator`, or `agent` |

```json
{
  "session_id": "session-0195b8d1",
  "session_kind": "operator",
  "subject_id": "ray",
  "started_by": "operator"
}
```

Invariants:
- Session boundary events are mechanical system events and remain append-only like all other events.
- Session lifecycle semantics beyond recording are owned outside the ledger.

### E-009 — Snapshot Created Payload
- Scope: SHARED
- Used By: FMWK-002 write-path, FMWK-005 graph
- Source: SC-007
- Description: Ledger-owned reference payload for a snapshot marker event. It records the existence, hash, and replay boundary of a snapshot file without defining snapshot file contents.

| Field | Type | Required | Description | Constraints |
| snapshot_sequence:number | Type:integer | Req:yes | Sequence at which the snapshot was taken | Constraint:`>= 0` |
| snapshot_path:string | Type:string | Req:yes | Snapshot location | Constraint:must match `/snapshots/<sequence_number>.snapshot` |
| snapshot_hash:string | Type:hash | Req:yes | Hash of snapshot file contents | Constraint:`sha256:<64 lowercase hex>` |

```json
{
  "snapshot_sequence": 42,
  "snapshot_path": "/snapshots/42.snapshot",
  "snapshot_hash": "sha256:5c1f3ed4c95346f1dc3ddca6ca9ea6240cfa0b8455174a8c4363130f0f2387cc"
}
```

Invariants:
- Ledger owns the reference marker only; the snapshot file format is external to this framework.
- `snapshot_sequence` defines the lower bound for replay-after-snapshot.

## Entity Relationship Map
```text
E-003 Ledger Tip
   ^
   | identifies latest
   |
E-001 Ledger Event ---- contains ----> E-004 Provenance
   |
   +---- payload(event_type=node_creation) ----> E-005 Node Creation Payload
   |
   +---- payload(event_type=signal_delta) ----> E-006 Signal Delta Payload
   |
   +---- payload(event_type=package_install) -> E-007 Package Install Payload
   |
   +---- payload(event_type=session_start) ---> E-008 Session Start Payload
   |
   +---- payload(event_type=snapshot_created) -> E-009 Snapshot Created Payload
   |
   +---- participates in chain verification --> E-002 Verification Result
```

## Migration Notes
No prior model — greenfield.
