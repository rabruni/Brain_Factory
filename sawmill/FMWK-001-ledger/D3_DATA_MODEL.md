# D3: Data Model — FMWK-001-ledger
Meta: v:1.0.0 (matches D2) | status:Final | shared entities:7

## Entities

### E-001 — LedgerEvent
- Scope: SHARED
- Used By: FMWK-002 write-path; FMWK-005 graph; FMWK-006 package-lifecycle; cold-storage CLI validation
- Source: SC-001, SC-002, SC-003, SC-004, SC-005, SC-006, SC-010
- Description: Canonical append-only event envelope stored in the Ledger. It is the sole persisted truth record for governed state transitions and carries the sequence, type metadata, provenance, payload, and hash-chain fields required for replay and audit.

| Field | Type | Required | Description | Constraints |
| event_id | Type:uuid-v7 | Req:yes | Stable unique event identifier | Must be UUIDv7 text |
| sequence | Type:integer | Req:yes | Global monotonic Ledger position | `>= 0`; assigned by Ledger only |
| event_type | Type:string | Req:yes | Event classifier | Non-empty snake_case string from approved catalog |
| schema_version | Type:string | Req:yes | Event schema version | Semver string |
| timestamp | Type:string | Req:yes | Event creation timestamp | ISO-8601 UTC |
| provenance | Type:object | Req:yes | Origin metadata | Must satisfy E-002 |
| previous_hash | Type:string | Req:yes | Prior event hash in chain | Exact `sha256:<64 lowercase hex>`; all-zero payload for genesis |
| payload | Type:object | Req:yes | Type-specific body | Must match payload entity for `event_type` |
| hash | Type:string | Req:yes | Hash of canonical event JSON excluding `hash` | Exact `sha256:<64 lowercase hex>` |

```json
{
  "event_id": "0195b7fc-c29c-7c2f-a4da-8f6d2eb6d1a1",
  "sequence": 4,
  "event_type": "signal_delta",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-19T23:11:12Z",
  "provenance": {
    "framework_id": "FMWK-004",
    "pack_id": "PC-002-signal-logging",
    "actor": "agent"
  },
  "previous_hash": "sha256:6a4f8649e9449e51d4538f86d3c31ab8f6b2f9fa3012af5d0dd03d5f5f258d4a",
  "payload": {
    "node_id": "node-sarah-french",
    "delta": "1",
    "reason": "active_intent_hit",
    "intent_id": "intent-dining-recall"
  },
  "hash": "sha256:4f5b54bcf2ef4e7be116a6df080f59b0bb5f80927b0d6162825250efce5435b1"
}
```

Invariants:
- `sequence` is contiguous and unique within the Ledger.
- `previous_hash` equals the prior event's `hash`, except genesis which uses 64 zeros.
- `hash` is computed from canonical UTF-8 JSON with the `hash` field excluded.
- Event content is immutable once persisted.

### E-002 — EventProvenance
- Scope: SHARED
- Used By: All Ledger event producers and consumers
- Source: SC-005
- Description: Provenance metadata carried inside every Ledger event to identify which framework and pack originated the event and which actor category initiated it.

| Field | Type | Required | Description | Constraints |
| framework_id | Type:string | Req:yes | Originating framework identifier | Must match `FMWK-NNN` or `FMWK-NNN-name` style authority usage |
| pack_id | Type:string | Req:yes | Originating pack identifier | Non-empty `PC-NNN-name` string |
| actor | Type:enum | Req:yes | Origin class | One of `system`, `operator`, `agent` |

```json
{
  "framework_id": "FMWK-006",
  "pack_id": "PC-004-install-runner",
  "actor": "system"
}
```

Invariants:
- Provenance is always present.
- `actor` is categorical and never free-form.

### E-003 — NodeCreationPayload
- Scope: SHARED
- Used By: FMWK-002 write-path; FMWK-005 graph
- Source: SC-005
- Description: Minimum canonical payload for `node_creation` events so the Ledger can store a graph-node creation record without owning graph behavior.

| Field | Type | Required | Description | Constraints |
| node_id | Type:string | Req:yes | Identifier for the created node | Non-empty |
| node_type | Type:string | Req:yes | Node classifier | Non-empty |
| lifecycle_state | Type:string | Req:yes | Initial lifecycle state | Non-empty |
| metadata | Type:object | Req:yes | Framework-defined metadata | JSON object; may be empty |

```json
{
  "node_id": "node-intent-dining-recall",
  "node_type": "intent",
  "lifecycle_state": "LIVE",
  "metadata": {
    "title": "Find Sarah's restaurant recommendation"
  }
}
```

Invariants:
- `node_id` is present at creation time.
- Ledger stores the creation payload but does not validate graph topology.

### E-004 — SignalDeltaPayload
- Scope: SHARED
- Used By: FMWK-002 write-path; FMWK-013 meta-learning-agent; FMWK-020 memory
- Source: SC-005
- Description: Canonical payload for `signal_delta` events used to record a bounded signal change against an existing node or scope.

| Field | Type | Required | Description | Constraints |
| node_id | Type:string | Req:yes | Target node identifier | Non-empty |
| delta | Type:string | Req:yes | Signed signal change | Stored as string to avoid float drift |
| reason | Type:string | Req:yes | Cause of signal change | Non-empty |
| intent_id | Type:string | Req:no | Active intent scope | Omit only when framework contract allows |

```json
{
  "node_id": "node-sarah-french",
  "delta": "1",
  "reason": "active_intent_hit",
  "intent_id": "intent-dining-recall"
}
```

Invariants:
- Numeric-like payload values that could drift across languages are stored as strings.
- Ledger stores the event; accumulation semantics are owned by FMWK-002.

### E-005 — PackageInstallPayload
- Scope: SHARED
- Used By: FMWK-006 package-lifecycle; cold-storage CLI validation
- Source: SC-005 and FWK-0 install event catalog
- Description: Canonical minimum payload for package installation events that make framework provenance and cold-storage validation possible.

| Field | Type | Required | Description | Constraints |
| package_id | Type:string | Req:yes | Installed package identifier | Non-empty |
| framework_ids | Type:array[string] | Req:yes | Frameworks included in the package action | At least one value |
| version | Type:string | Req:yes | Package version | Semver string |
| timestamp | Type:string | Req:yes | Lifecycle event timestamp | ISO-8601 UTC |

```json
{
  "package_id": "PKG-kernel-1.0.0",
  "framework_ids": ["FMWK-001", "FMWK-002"],
  "version": "1.0.0",
  "timestamp": "2026-03-19T23:20:00Z"
}
```

Invariants:
- Lifecycle events must identify the package and affected frameworks.
- Install history is reconstructed from Ledger replay, not filesystem names alone.

### E-006 — SessionStartPayload
- Scope: SHARED
- Used By: FMWK-002 write-path; FMWK-003 orchestration
- Source: SC-005
- Description: Canonical minimum payload for a `session_start` infrastructure event.

| Field | Type | Required | Description | Constraints |
| session_id | Type:string | Req:yes | Session identifier | Non-empty |
| actor_id | Type:string | Req:yes | Authenticated actor or agent identifier | Non-empty |
| channel | Type:string | Req:yes | Entry channel | Non-empty |
| started_at | Type:string | Req:yes | Session start time | ISO-8601 UTC |

```json
{
  "session_id": "sess-operator-0001",
  "actor_id": "operator-ray",
  "channel": "operator",
  "started_at": "2026-03-19T23:30:00Z"
}
```

Invariants:
- Session boundary events are system events but still use the canonical Ledger envelope.

### E-007 — SnapshotCreatedPayload
- Scope: SHARED
- Used By: FMWK-002 write-path; FMWK-005 graph; cold-storage recovery tooling
- Source: SC-006
- Description: Ledger payload that records snapshot existence and replay boundary metadata without owning snapshot file contents.

| Field | Type | Required | Description | Constraints |
| snapshot_sequence | Type:integer | Req:yes | Sequence at which snapshot was taken | `>= 0` |
| snapshot_path | Type:string | Req:yes | Snapshot file location | Must match `/snapshots/<sequence>.snapshot` authority pattern |
| snapshot_hash | Type:string | Req:yes | Hash of the snapshot file | Exact `sha256:<64 lowercase hex>` |
| created_at | Type:string | Req:yes | Snapshot creation timestamp | ISO-8601 UTC |

```json
{
  "snapshot_sequence": 128,
  "snapshot_path": "/snapshots/128.snapshot",
  "snapshot_hash": "sha256:9b9fb5c95f203123ac2994631b2bbaf36c6385c8202c7848d8c1ebb03eecb3d9",
  "created_at": "2026-03-19T23:40:00Z"
}
```

Invariants:
- The Ledger records snapshot metadata only.
- Snapshot format remains out of scope for FMWK-001.

### E-008 — LedgerTip
- Scope: SHARED
- Used By: FMWK-002 write-path; recovery tooling
- Source: SC-002, SC-003
- Description: Lightweight representation of the latest Ledger position returned by `get_tip`.

| Field | Type | Required | Description | Constraints |
| sequence_number | Type:integer | Req:yes | Latest persisted sequence | `>= 0` for non-empty ledger |
| hash | Type:string | Req:yes | Latest persisted event hash | Exact `sha256:<64 lowercase hex>` |

```json
{
  "sequence_number": 128,
  "hash": "sha256:cc5af2f9c31b1db5d90d2f39c23027d580f509512cc3fc74b18298f8310ca71c"
}
```

Invariants:
- Tip reflects the last successfully persisted event only.

### E-009 — ChainVerificationResult
- Scope: SHARED
- Used By: CLI validation; FMWK-006 package-lifecycle; operator diagnostics
- Source: SC-004, SC-010
- Description: Verification outcome for a Ledger chain walk.

| Field | Type | Required | Description | Constraints |
| valid | Type:boolean | Req:yes | Whether the checked chain segment passed validation | Exact boolean |
| break_at | Type:integer | Req:no | First failing sequence | Required when `valid=false` |
| start | Type:integer | Req:no | First checked sequence | `>= 0` when present |
| end | Type:integer | Req:no | Last checked sequence | `>= start` when present |

```json
{
  "valid": false,
  "break_at": 3,
  "start": 0,
  "end": 5
}
```

Invariants:
- `break_at` is absent when `valid=true`.
- Verification reports the first failing sequence, not an arbitrary later mismatch.

## Entity Relationship Map
```text
EventProvenance (E-002)
          |
          v
LedgerEvent (E-001) ---------> LedgerTip (E-008)
     |   |   |   |   \
     |   |   |   |    \------> ChainVerificationResult (E-009)
     |   |   |   |
     |   |   |   +-----------> SnapshotCreatedPayload (E-007)
     |   |   +---------------> SessionStartPayload (E-006)
     |   +-------------------> PackageInstallPayload (E-005)
     +-----------------------> NodeCreationPayload (E-003) / SignalDeltaPayload (E-004)
```

## Migration Notes
No prior model — greenfield.
