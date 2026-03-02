# D3: Data Model — FMWK-001-ledger
Meta: v:1.0.0 (matches D2) | status:Draft | shared entities:5

---

## Entities

### E-001: LedgerEvent (base schema)
- Scope: SHARED — all frameworks that produce or consume events
- Used By: FMWK-002 (write-path — appends and folds), FMWK-003 (orchestration — reads work_order_transition), FMWK-004 (execution — appends call logs), FMWK-005 (graph — replays for reconstruction), FMWK-006 (package-lifecycle — appends package_install)
- Source: SC-001, SC-002, SC-003, SC-006, SC-007
- Description: The canonical shape of every event recorded in the Ledger. FMWK-001 owns the base schema. Other frameworks own payload schemas for their event types, which slot into the `payload` field.

Fields:
| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| event_id | string | yes | Globally unique event identifier | UUID v7 format |
| sequence | integer | yes | Global monotonic sequence number | 0-indexed; assigned by Ledger, NOT caller |
| event_type | string | yes | Event type from canonical catalog | See E-009 catalog |
| schema_version | string | yes | Schema version for this event | Semantic version, e.g. "1.0.0" |
| timestamp | string | yes | Creation time (ISO-8601 UTC) | Must include "Z" suffix |
| provenance.framework_id | string | yes | Framework that produced this event | FMWK-NNN format |
| provenance.pack_id | string | yes | Pack within that framework | PC-NNN-name format |
| provenance.actor | string | yes | Who triggered the event | enum: "system" \| "operator" \| "agent" |
| previous_hash | string | yes | Hash of the preceding event's canonical JSON | Format: `sha256:<64 lowercase hex>` |
| payload | object | yes | Event type-specific data | Schema defined by payload owner (see E-009) |
| hash | string | yes | Hash of this event's canonical JSON (hash field excluded from input) | Format: `sha256:<64 lowercase hex>` |

JSON example:
```json
{
  "event_id": "018e3b2a-4f6c-7e8d-9012-3456789abcde",
  "sequence": 42,
  "event_type": "signal_delta",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-01T14:22:00Z",
  "provenance": {
    "framework_id": "FMWK-004",
    "pack_id": "PC-001-execution",
    "actor": "agent"
  },
  "previous_hash": "sha256:3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c",
  "payload": {
    "node_id": "node-abc-123",
    "signal_type": "entity",
    "delta": "+0.05"
  },
  "hash": "sha256:a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2"
}
```

Invariants:
- `hash` = `sha256:` + lowercase hex of `SHA-256(canonical_json(event, hash_field_excluded))`
- `previous_hash` of event N = `hash` of event N-1
- `previous_hash` of event 0 = `sha256:0000000000000000000000000000000000000000000000000000000000000000`
- `sequence` is strictly monotonic with no gaps (0, 1, 2, …)
- All hash strings match `^sha256:[0-9a-f]{64}$` — no uppercase, no `0x` prefix, no base64
- `payload` contains no float-type values; decimal values MUST be strings
- `sequence`, `previous_hash`, and `hash` are assigned by the Ledger — callers do not supply these

---

### E-002: Canonical JSON Serialization (constraint)
- Scope: PRIVATE — Ledger's internal contract for hash computation
- Source: SC-001, SC-004, SC-005, SC-006, SC-007
- Description: The exact byte-level algorithm used to produce the hash input for every event. This is a constraint, not a stored entity. It must be reproduced identically by any tool that verifies the chain, including offline CLI tools and implementations in other languages.

Serialization algorithm (reference implementation in Python):
1. Copy the event object. Remove the `hash` field entirely.
2. `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`
   - Keys sorted alphabetically at every nesting level (recursive)
   - No whitespace between tokens: separators are `,` and `:` only
   - `ensure_ascii=False`: characters stored as literal UTF-8 bytes, NOT `\uNNNN` escapes
3. Encode the resulting string to bytes using UTF-8 (no BOM).
4. `hashlib.sha256(utf8_bytes).hexdigest()` — produces 64 lowercase hex chars.
5. Prefix with `sha256:` — store as the `hash` field.

Critical rules:
- The `hash` field is excluded from hash input. All other fields including `previous_hash` are included.
- `null` fields are included: `"field":null` — not omitted.
- No floating point values may appear. Any decimal value is serialized as a string before this step.
- Integer fields are bare digits: no decimal point, no trailing zeros, no `e` notation.

---

### E-003: LedgerTip
- Scope: SHARED — callers use this to learn the current write position
- Used By: FMWK-002 (write-path — reads tip to determine next sequence in atomicity mechanism)
- Source: SC-009
- Description: The current tip of the Ledger — the sequence number and hash of the most recently appended event. Callers read this to understand current state.

Fields:
| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| sequence_number | integer | yes | Sequence of the most recent event | ≥ 0 |
| hash | string | yes | Hash of the most recent event | `sha256:<64 lowercase hex>` |

JSON example: `{"sequence_number": 42, "hash": "sha256:a1b2c3d4..."}`

Invariants:
- `sequence_number` increases monotonically with every successful `append()` call
- `hash` matches the `hash` field of the event at `sequence_number`
- If no events have been written, `get_tip()` returns an empty tip marker: `{"sequence_number": -1, "hash": ""}`

---

### E-004: VerifyChainResult
- Scope: SHARED — callers receive this from `verify_chain()`
- Used By: CLI tools, FMWK-006 (package-lifecycle system gate), operator diagnostics
- Source: SC-004, SC-005, SC-EC-001
- Description: Result of a hash chain integrity walk. Indicates whether the chain is intact and, if not, where the first break occurred.

Fields:
| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| valid | boolean | yes | true if chain is intact for the verified range | |
| break_at | integer | conditional | Sequence number of the first mismatch | Present only if `valid=false`; MUST be absent if `valid=true` |

JSON examples:
- Success: `{"valid": true}`
- Failure at sequence 3: `{"valid": false, "break_at": 3}`

Invariants:
- If `valid=true`, `break_at` MUST be absent
- If `valid=false`, `break_at` MUST be present and ≥ 0

---

### E-005: SnapshotCreatedPayload (payload for `snapshot_created` event type)
- Scope: SHARED — FMWK-005 (graph) reads this when validating or loading snapshots
- Used By: FMWK-005 (graph replay path)
- Source: SC-008, SOURCE_MATERIAL.md §Snapshots
- Description: The payload for a `snapshot_created` event. Recorded by the Ledger when a Graph snapshot is taken. The snapshot file format is owned by FMWK-005 — this payload is format-agnostic.

Fields:
| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| snapshot_path | string | yes | Filesystem path to the snapshot file | Follows convention `/snapshots/<snapshot_sequence>.snapshot` |
| snapshot_hash | string | yes | SHA-256 of the snapshot file contents | `sha256:<64 lowercase hex>` |
| snapshot_sequence | integer | yes | Ledger sequence at time of snapshot | ≥ 0; events after this sequence must be replayed |

JSON example:
```json
{
  "snapshot_path": "/snapshots/1042.snapshot",
  "snapshot_hash": "sha256:9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e",
  "snapshot_sequence": 1042
}
```

Invariants:
- `snapshot_path` MUST follow naming convention `/snapshots/<snapshot_sequence>.snapshot`
- `snapshot_hash` verifies against the actual file contents at `snapshot_path`
- `snapshot_sequence` in payload matches the Ledger event's surrounding sequence context

---

### E-006: NodeCreationPayload (payload for `node_creation` event type)
- Scope: SHARED — FMWK-002 (write-path) folds this to create a Graph node; FMWK-005 (graph) stores the node
- Used By: FMWK-002, FMWK-005
- Source: SC-001 (append path), BUILDER_SPEC.md §Ledger
- Description: Payload for a `node_creation` event. Defines the initial state of a new Graph node. FMWK-001 owns this payload schema because `node_creation` is a foundational event type and its schema is needed before FMWK-002 can be fully specified.

Fields:
| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| node_id | string | yes | Unique identifier for the new Graph node | Non-empty, unique within Graph |
| node_type | string | yes | Classification of this Graph node | Application-defined enum (e.g., "learning_artifact", "intent", "session") |
| base_weight | string | yes | Initial system-assigned retrieval weight | Decimal string, range "0.0"–"1.0" (string, not float) |
| initial_methylation | string | yes | Initial methylation value for Signal Accumulator | Decimal string, range "0.0"–"1.0" (string, not float) |

JSON example:
```json
{
  "node_id": "node-7f8a9b0c-1d2e",
  "node_type": "learning_artifact",
  "base_weight": "0.5",
  "initial_methylation": "0.0"
}
```

Invariants:
- `base_weight` and `initial_methylation` are strings, not floats (cross-language hash safety)
- `node_id` is unique at Graph scope — duplicate node_id in `node_creation` is a caller error

---

### E-007: SessionPayload (payload for `session_start` and `session_end` event types)
- Scope: SHARED — FMWK-002 (write-path folds session boundaries), FMWK-003 (orchestration reads session context), FMWK-013 (meta-learning-agent triggered at session end)
- Used By: FMWK-002, FMWK-003, FMWK-013
- Source: BUILDER_SPEC.md §Ledger, OPERATIONAL_SPEC.md §Q1
- Description: Payloads for session lifecycle events. Session boundaries drive aperture calibration, MLA triggering, and Graph snapshotting.

Fields for `session_start`:
| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| session_id | string | yes | Unique session identifier | Non-empty string |
| operator_id | string | conditional | Operator identity for operator sessions | Present for operator sessions; absent for user sessions |
| user_id | string | conditional | User identity for user sessions | Present for user sessions; absent for operator sessions |

Fields for `session_end`:
| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| session_id | string | yes | Session being closed | Must match a prior `session_start.session_id` |
| end_reason | string | yes | Why the session ended | enum: "operator_disconnect" \| "user_disconnect" \| "timeout" \| "system_shutdown" |

JSON examples:
```json
{"session_id": "sess-abc-001", "operator_id": "ray@dopejarmo.local"}
{"session_id": "sess-abc-001", "end_reason": "operator_disconnect"}
```

Invariants:
- `session_end.session_id` MUST match a previously recorded `session_start.session_id`
- Exactly one of `operator_id` or `user_id` is present in `session_start` (not both, not neither)

---

### E-008: PackageInstallPayload (payload for `package_install` event type)
- Scope: SHARED — FMWK-006 (package-lifecycle) reads this for governance chain validation
- Used By: FMWK-006
- Source: BUILDER_SPEC.md §Package Lifecycle
- Description: Payload for a `package_install` event. Records every file installed and the gate results that authorized the install. This is what makes cold-storage framework chain validation possible.

Fields:
| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| package_id | string | yes | Package (framework) being installed | FMWK-NNN format |
| package_version | string | yes | Version of the installed package | Semantic version "M.m.p" |
| gate_results | array | yes | Results of all validation gates | Array of `{gate_id: string, result: "pass" \| "fail"}` |
| file_hashes | object | yes | Hash of every installed file keyed by path | `{"/governed/path/file.txt": "sha256:<64hex>"}` |

JSON example:
```json
{
  "package_id": "FMWK-002",
  "package_version": "1.0.0",
  "gate_results": [
    {"gate_id": "framework-gate", "result": "pass"},
    {"gate_id": "specpack-gate", "result": "pass"}
  ],
  "file_hashes": {
    "/governed/FMWK-002-write-path/framework.json": "sha256:abc123..."
  }
}
```

Invariants:
- All `gate_results` MUST have `result: "pass"` — a `package_install` event is never written for a failed install
- `file_hashes` keys are absolute paths in the governed filesystem
- `file_hashes` values match regex `^sha256:[0-9a-f]{64}$`

---

### E-009: Event Type Catalog (constraint)
- Scope: SHARED — all frameworks reference this catalog when constructing or reading events
- Source: SOURCE_MATERIAL.md §Event Schema, BUILDER_SPEC.md §Ledger
- Description: The complete catalog of canonical event types in the system (v1.0.0). FMWK-001 owns this catalog. Event types not listed here are invalid.

| event_type | Payload Owner | Payload Entity | Description |
|------------|--------------|----------------|-------------|
| node_creation | FMWK-001 | E-006 | New Graph node created |
| signal_delta | FMWK-002 | defined in FMWK-002 D3 | Signal increment/decrement on a node |
| methylation_delta | FMWK-002 | defined in FMWK-002 D3 | Direct methylation adjustment (rare, admin) |
| suppression | FMWK-002 | defined in FMWK-002 D3 | Suppress a node (methylation → 1.0) |
| unsuppression | FMWK-002 | defined in FMWK-002 D3 | Reverse suppression of a node |
| mode_change | FMWK-002 | defined in FMWK-002 D3 | Change node mode |
| consolidation | FMWK-002 | defined in FMWK-002 D3 | Pattern synthesis / node merge |
| work_order_transition | FMWK-003 | defined in FMWK-003 D3 | Work order state change |
| intent_transition | FMWK-021 | defined in FMWK-021 D3 | Intent lifecycle state change |
| session_start | FMWK-001 | E-007 | Session opened |
| session_end | FMWK-001 | E-007 | Session closed |
| package_install | FMWK-006 | E-008 | Package installed through gates |
| package_uninstall | FMWK-006 | defined in FMWK-006 D3 | Package removed |
| framework_install | FMWK-006 | defined in FMWK-006 D3 | Framework installed via governance gates |
| snapshot_created | FMWK-001 | E-005 | Graph snapshot taken |

Note: Payload schemas for 10 event types (signal_delta, methylation_delta, suppression, unsuppression, mode_change, consolidation, work_order_transition, intent_transition, package_uninstall, framework_install) are deferred to the frameworks that own them. See D6 GAP-1. The Ledger validates base schema only at `append()` time; payload validation is pluggable per DEF-001.

---

## Entity Relationship Map

```
LedgerEvent (E-001)
  │
  ├── hash ──────────────────────────→ computed by Canonical JSON Serialization (E-002)
  │                                    (hash field excluded from input)
  │
  ├── previous_hash ─────────────────→ hash of preceding LedgerEvent (chain link)
  │                                    (genesis sentinel for sequence 0)
  │
  └── payload (by event_type)
        ├── node_creation  ──────────→ NodeCreationPayload (E-006)
        ├── session_start  ──────────→ SessionPayload (E-007, start shape)
        ├── session_end    ──────────→ SessionPayload (E-007, end shape)
        ├── package_install ─────────→ PackageInstallPayload (E-008)
        ├── snapshot_created ────────→ SnapshotCreatedPayload (E-005)
        └── [10 deferred types] ─────→ [defined in owning framework D3s]

get_tip() ──────────────────────────→ LedgerTip (E-003)
verify_chain() ──────────────────────→ VerifyChainResult (E-004)
Event Type Catalog (E-009) ──────────→ validates event_type field of every E-001
```

---

## Migration Notes

No prior model — greenfield.
