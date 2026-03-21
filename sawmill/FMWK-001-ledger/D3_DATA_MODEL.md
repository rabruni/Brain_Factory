# D3: Data Model — Ledger (FMWK-001)
Meta: v:1.0.0 (matches D2) | status:Final | shared entities:4

---

## Entities

### E-001 — LedgerEvent
- Scope: SHARED
- Used By: FMWK-002 (Write Path — reads events for fold), FMWK-005 (Graph — reads events for replay), FMWK-006 (Package Lifecycle — reads framework_install events for gate validation), cold-storage CLI tools
- Source: SC-001, SC-002, SC-003, SC-004, SC-005, SC-007, SC-008, SC-009
- Description: The fundamental unit of storage in the Ledger. Every state mutation in DoPeJarMo is recorded as a LedgerEvent. Events are immutable once written. The hash field is computed from the canonical JSON of all other fields (including previous_hash, excluding hash itself). The sequence field is assigned by the Ledger — callers never supply it.

Fields:

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| event_id | string | yes | Globally unique identifier for this event | UUID v7 format (e.g., "01956b3c-4f2a-7000-8000-000000000001") |
| sequence | integer | yes | Global monotonic position in the Ledger | ≥ 0; assigned by Ledger, never by caller; genesis event = 0 |
| event_type | string | yes | Category of this event | Must be a value from the EventType enum (see below) |
| schema_version | string | yes | Version of the payload schema for this event_type | semver format, e.g., "1.0.0" |
| timestamp | string | yes | Time the event was created | ISO-8601 UTC with Z suffix, e.g., "2026-03-21T03:21:00Z" |
| provenance | Provenance | yes | Who/what created this event | See E-002 Provenance |
| previous_hash | string | yes | SHA-256 hash of the preceding event's canonical JSON | Format: "sha256:" + exactly 64 lowercase hex chars; genesis = "sha256:0000000000000000000000000000000000000000000000000000000000000000" |
| payload | object | yes | Event-type-specific data | JSON object; schema per event_type; see payload schemas below; the Ledger validates JSON serializability but not payload field structure |
| hash | string | yes | SHA-256 hash of this event's canonical JSON (hash field excluded from input) | Format: "sha256:" + exactly 64 lowercase hex chars |

JSON Example:
```json
{
  "event_id": "01956b3c-4f2a-7000-8000-000000000001",
  "event_type": "session_start",
  "hash": "sha256:a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
  "payload": {
    "actor_id": "op-01956b3c-0001",
    "session_id": "01956b3c-4f2a-7000-9000-000000000001",
    "session_type": "operator"
  },
  "previous_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "provenance": {
    "actor": "operator",
    "framework_id": "FMWK-002",
    "pack_id": "PC-001-write"
  },
  "schema_version": "1.0.0",
  "sequence": 0,
  "timestamp": "2026-03-21T03:21:00Z"
}
```

Invariants:
- `sequence` is unique across all LedgerEvents. No two events share a sequence number.
- `previous_hash` of event at sequence N equals `hash` of event at sequence N-1.
- `previous_hash` of the genesis event (sequence 0) is "sha256:" + 64 zeros.
- `hash` equals SHA-256 of canonical JSON (all fields including previous_hash, excluding hash itself; see Canonical JSON Serialization Constraint below).
- `event_id` is unique across all LedgerEvents (UUID v7 ensures this with high probability).
- `hash` format is exactly "sha256:" followed by 64 lowercase hex characters. No uppercase, no "0x" prefix, no base64.

---

### E-002 — Provenance
- Scope: SHARED (embedded in E-001 LedgerEvent)
- Used By: Wherever LedgerEvent is used; also inspected directly by FMWK-006 (Package Lifecycle) for ownership verification
- Source: SC-001, SC-002 (every appended event carries provenance)
- Description: Identifies the originating framework, pack (if applicable), and type of actor for a LedgerEvent. Enables attribution of any event back to its source framework for audit, governance rule verification, and ownership checks.

Fields:

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| framework_id | string | yes | Framework that produced this event | e.g., "FMWK-002"; must match an installed framework ID |
| pack_id | string | no | Pack within the framework that produced this event | e.g., "PC-001-write"; may be null if not applicable |
| actor | string | yes | Type of entity that triggered this event | Enum: "system", "operator", "agent" |

JSON Example:
```json
{
  "actor": "system",
  "framework_id": "FMWK-002",
  "pack_id": "PC-001-write"
}
```

Invariants:
- `actor` must be one of: "system", "operator", "agent". No other values.
- `framework_id` is always present and non-empty.

---

### E-003 — TipRecord
- Scope: SHARED
- Used By: FMWK-002 (Write Path — reads tip before each append to determine next sequence number), FMWK-006 (Package Lifecycle — reads tip for chain walk start)
- Source: SC-006
- Description: A point-in-time snapshot of the Ledger's latest position. Returned by get_tip(). Provides the sequence number and hash of the most recently appended event — the two pieces of information needed to continue the chain.

Fields:

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| sequence_number | integer | yes | Sequence number of the latest event | ≥ 0; equals -1 if Ledger is empty (see D6 CLR-002) |
| hash | string | yes | SHA-256 hash of the latest event | "sha256:" + 64 lowercase hex chars; equals "sha256:" + 64 zeros if Ledger is empty |

JSON Example:
```json
{
  "hash": "sha256:a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
  "sequence_number": 41
}
```

Invariants:
- `hash` of the TipRecord equals `hash` of the LedgerEvent at `sequence_number`.
- After a successful append(), TipRecord.sequence_number increases by exactly 1.

---

### E-004 — ChainVerificationResult
- Scope: SHARED
- Used By: FMWK-006 (Package Lifecycle — validates framework chain integrity), cold-storage CLI tools, FMWK-005 (Graph — on startup)
- Source: SC-007, SC-008, SC-009
- Description: The result of a hash chain integrity verification. Reports whether the chain is intact over the verified range, and if not, identifies the first corrupted sequence number.

Fields:

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| valid | boolean | yes | True if all events in the verified range have correct hashes and correct previous_hash links | |
| break_at | integer | no | Sequence number of the first event where corruption was detected | Present only when valid=false; absent (null) when valid=true |

JSON Example (intact):
```json
{
  "break_at": null,
  "valid": true
}
```

JSON Example (corrupted at sequence 3):
```json
{
  "break_at": 3,
  "valid": false
}
```

Invariants:
- `break_at` is null when valid=true.
- `break_at` is present (non-null) when valid=false.
- `break_at` identifies the lowest sequence number where either the stored hash does not match the recomputed SHA-256 of the event's canonical JSON, or the previous_hash does not match the hash of the preceding event.

---

## Payload Schemas (for Ledger-owned event types)

The Ledger owns payload schemas for event types produced by the Ledger itself or by KERNEL bootstrapping. The `payload` field in E-001 is typed per `event_type`. Floats in payloads MUST be serialized as strings to prevent cross-language representation drift (see Canonical JSON Serialization Constraint).

### node_creation payload
```json
{
  "base_weight": "0.5",
  "initial_methylation": "0.0",
  "node_id": "01956b3c-4f2a-7000-8000-000000000042",
  "node_type": "learning_artifact"
}
```
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| node_id | string | yes | UUID v7 of the new Graph node |
| node_type | string | yes | Type of Graph node being created (e.g., "learning_artifact", "intent", "work_order") |
| initial_methylation | string | yes | Float 0.0–1.0 serialized as string (e.g., "0.0") |
| base_weight | string | yes | Non-negative float serialized as string (e.g., "0.5") |

### signal_delta payload
```json
{
  "delta": "0.1",
  "node_id": "01956b3c-4f2a-7000-8000-000000000042",
  "signal_type": "entity"
}
```
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| node_id | string | yes | UUID v7 of the target Graph node |
| signal_type | string | yes | Enum: "entity", "mode", "stimulus", "regime" |
| delta | string | yes | Signed float serialized as string (e.g., "0.1", "-0.05") |

### package_install payload
```json
{
  "framework_id": "FMWK-002",
  "manifest_hash": "sha256:b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
  "package_id": "FMWK-002-write-path",
  "version": "1.0.0"
}
```
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| package_id | string | yes | Package identifier (e.g., "FMWK-002-write-path") |
| framework_id | string | yes | Framework being installed (e.g., "FMWK-002") |
| version | string | yes | semver string (e.g., "1.0.0") |
| manifest_hash | string | yes | SHA-256 hash of the package manifest; "sha256:" + 64 lowercase hex chars |

### session_start payload
```json
{
  "actor_id": "op-01956b3c-0001",
  "session_id": "01956b3c-4f2a-7000-9000-000000000001",
  "session_type": "operator"
}
```
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| session_id | string | yes | UUID v7 for this session |
| actor_id | string | yes | Identifier of the connecting actor |
| session_type | string | yes | Enum: "operator", "user" |

### session_end payload
```json
{
  "reason": "normal",
  "session_id": "01956b3c-4f2a-7000-9000-000000000001"
}
```
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| session_id | string | yes | UUID v7 matching the session_start event |
| reason | string | yes | Enum: "normal", "timeout", "error" |

### snapshot_created payload
```json
{
  "snapshot_file": "/snapshots/41.snapshot",
  "snapshot_hash": "sha256:c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
  "snapshot_sequence": 41
}
```
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| snapshot_sequence | integer | yes | The Ledger sequence number at which the snapshot was taken |
| snapshot_file | string | yes | Path to snapshot file: "/snapshots/<sequence_number>.snapshot" |
| snapshot_hash | string | yes | SHA-256 hash of the snapshot file; "sha256:" + 64 lowercase hex chars |

### Deferred payload schemas
The following event types' payload schemas are owned by other frameworks and are deferred to those frameworks' specs:
- `methylation_delta` → FMWK-002 (Write Path)
- `suppression` → FMWK-002 (Write Path)
- `unsuppression` → FMWK-002 (Write Path)
- `mode_change` → FMWK-002 (Write Path)
- `consolidation` → FMWK-002 (Write Path)
- `work_order_transition` → FMWK-003 (Orchestration)
- `intent_transition` → FMWK-021 (Intent)
- `package_uninstall` → FMWK-006 (Package Lifecycle)
- `framework_install` → FMWK-006 (Package Lifecycle)

The Ledger accepts these payloads as opaque JSON objects, validates JSON serializability, and stores them without inspecting field content.

---

## Canonical JSON Serialization Constraint

This is a data model invariant enforced by the Ledger on every append() and verify_chain() call:

1. Start with the event dict containing all fields EXCEPT `hash`
2. Serialize to JSON: sort all keys alphabetically at every nesting level; use separators=(',', ':') (no whitespace); ensure_ascii=False (literal UTF-8 characters, not \uNNNN escapes)
3. Encode to UTF-8 bytes with no BOM
4. Compute SHA-256 digest
5. Store as "sha256:" + 64 lowercase hex characters

Python reference implementation:
```python
import hashlib, json
def canonical_hash(event_dict: dict) -> str:
    d = {k: v for k, v in event_dict.items() if k != "hash"}
    canonical = json.dumps(d, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    return f"sha256:{digest}"
```

Additional rules:
- Integer fields (sequence, snapshot_sequence) are bare digits: 0, 1, 42 (no decimal point)
- Float values in payload do not exist in this schema — all numeric values that are floats (methylation, delta, base_weight) are stored as strings: "0.1", "0.0"
- Null fields are included in serialization as `"field":null`, not omitted
- The `hash` field is excluded from the serialization input and computed after all other fields are fixed

---

## EventType Enum

Valid values for the `event_type` field in E-001 LedgerEvent:

| Value | Owner Framework | Description |
|-------|----------------|-------------|
| node_creation | FMWK-001 (via FMWK-002) | New Graph node created |
| signal_delta | FMWK-001 (via FMWK-002) | Signal increment/decrement on a Graph node |
| methylation_delta | FMWK-002 | Direct methylation adjustment |
| suppression | FMWK-002 | Graph node suppressed |
| unsuppression | FMWK-002 | Graph node unsuppressed |
| mode_change | FMWK-002 | Graph node mode changed |
| consolidation | FMWK-002 | Graph nodes consolidated |
| work_order_transition | FMWK-003 | Work order state changed |
| intent_transition | FMWK-021 | Intent lifecycle state changed |
| session_start | FMWK-001 | Session boundary — session started |
| session_end | FMWK-001 | Session boundary — session ended |
| package_install | FMWK-006 | Package installed via gates |
| package_uninstall | FMWK-006 | Package uninstalled |
| framework_install | FMWK-006 | Framework installed (gate-verified) |
| snapshot_created | FMWK-001 | Snapshot of Graph state taken |

---

## Entity Relationship Map

```
LedgerEvent (E-001)
│
├── provenance: Provenance (E-002)
│   ├── framework_id: string
│   ├── pack_id: string (optional)
│   └── actor: enum {system, operator, agent}
│
├── payload: object (type-specific, see payload schemas)
│
├── previous_hash → hash of LedgerEvent[sequence-1]
│                   (sha256:0000...0000 for genesis)
│
└── hash = SHA-256(canonical_json(event_without_hash))

TipRecord (E-003)
│
├── sequence_number → LedgerEvent[sequence_number].sequence
└── hash → LedgerEvent[sequence_number].hash

ChainVerificationResult (E-004)
│
├── valid: boolean
└── break_at: integer | null (sequence of first corrupted event)
```

---

## Migration Notes

No prior model — greenfield. FMWK-001-ledger is a KERNEL framework built from scratch. No migration from a prior data model is required.
