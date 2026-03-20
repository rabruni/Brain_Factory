# D4: Contracts — FMWK-001-ledger
Meta: v:1.0.0 (matches D2) | data model: D3 1.0.0 | status:Final

IDs: IN-NNN (inbound), OUT-NNN (outbound), SIDE-NNN (side-effect), ERR-NNN (error).

## Inbound

### IN-001 — Append Event
- Caller: FMWK-002 write-path and approved infrastructure producers of system events
- Trigger: A governed mutation or system event must be recorded
- Scenarios: SC-001, SC-002, SC-005, SC-006, SC-007, SC-008, SC-009

| Field | Type | Required | Description | Constraints |
| event_id | Type:uuid-v7 | Req:yes | Event identifier | Must be unique |
| event_type | Type:string | Req:yes | Event classifier | Approved catalog value |
| schema_version | Type:string | Req:yes | Event schema version | Semver string |
| timestamp | Type:string | Req:yes | Event timestamp | ISO-8601 UTC |
| provenance | Type:object | Req:yes | Event origin | Must satisfy E-002 |
| payload | Type:object | Req:yes | Event payload | Must match event-specific schema |

Constraints:
- Caller MUST NOT provide `sequence`, `previous_hash`, or `hash`.
- Ledger assigns `sequence` and `previous_hash` from the current tip.
- Serialization MUST satisfy SIDE-002 before persistence.

Example:
```json
{
  "event_id": "0195b7fc-c29c-7c2f-a4da-8f6d2eb6d1a1",
  "event_type": "node_creation",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-19T23:50:00Z",
  "provenance": {
    "framework_id": "FMWK-002",
    "pack_id": "PC-001-fold-engine",
    "actor": "system"
  },
  "payload": {
    "node_id": "node-intent-dining-recall",
    "node_type": "intent",
    "lifecycle_state": "LIVE",
    "metadata": {
      "title": "Find Sarah's restaurant recommendation"
    }
  }
}
```

### IN-002 — Read One Event
- Caller: Any framework or tool that needs an exact stored event
- Trigger: Point lookup by sequence
- Scenarios: SC-003

| Field | Type | Required | Description | Constraints |
| sequence_number | Type:integer | Req:yes | Requested Ledger sequence | `>= 0` |

Constraints:
- Sequence must reference an existing event.

Example:
```json
{
  "sequence_number": 4
}
```

### IN-003 — Read Event Range
- Caller: FMWK-005 graph rebuild, diagnostics, recovery tooling
- Trigger: Ordered replay over a bounded sequence interval
- Scenarios: SC-003, SC-004

| Field | Type | Required | Description | Constraints |
| start | Type:integer | Req:yes | First sequence to read | `>= 0` |
| end | Type:integer | Req:yes | Last sequence to read | `>= start` |

Constraints:
- Returned events must be ordered by ascending sequence.

Example:
```json
{
  "start": 0,
  "end": 127
}
```

### IN-004 — Read Since Sequence
- Caller: FMWK-005 graph recovery after snapshot load
- Trigger: Replay all events after a known sequence boundary
- Scenarios: SC-003, SC-006

| Field | Type | Required | Description | Constraints |
| sequence_number | Type:integer | Req:yes | Exclusive lower bound | `>= -1`; `-1` means from genesis |

Constraints:
- Events with `sequence > sequence_number` are returned in ascending order.

Example:
```json
{
  "sequence_number": 128
}
```

### IN-005 — Verify Chain
- Caller: Cold-storage CLI tools, operator diagnostics, startup validation
- Trigger: Integrity validation request
- Scenarios: SC-004, SC-010

| Field | Type | Required | Description | Constraints |
| start | Type:integer | Req:no | Optional first sequence | Defaults to genesis |
| end | Type:integer | Req:no | Optional last sequence | Defaults to current tip |
| source_mode | Type:enum | Req:yes | Verification source | `online` or `offline_export` |

Constraints:
- Verification recomputes hashes from canonical serialized bytes, not stored hash-to-hash comparisons only.

Example:
```json
{
  "start": 0,
  "end": 5,
  "source_mode": "offline_export"
}
```

### IN-006 — Get Tip
- Caller: FMWK-002 write-path and diagnostics
- Trigger: Need the latest Ledger position
- Scenarios: SC-002, SC-003

| Field | Type | Required | Description | Constraints |
| none | Type:none | Req:yes | No request body | Caller invokes contract with no payload |

Constraints:
- Empty-ledger behavior is only valid before genesis append.

Example:
```json
{}
```

## Outbound

### OUT-001 — Append Result
- Consumer: Append caller
- Scenarios: SC-001, SC-002, SC-005, SC-006
- Response Shape: sequence number plus persisted `LedgerEvent` (E-001)

Example success:
```json
{
  "sequence_number": 4,
  "event": {
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
}
```

Example failure:
```json
{
  "error_code": "LEDGER_SEQUENCE_ERROR",
  "message": "Sequence assignment conflict; append rejected."
}
```

### OUT-002 — Read Result
- Consumer: Read caller
- Scenarios: SC-003
- Response Shape: `LedgerEvent` (E-001)

Example success:
```json
{
  "event": {
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
}
```

Example failure:
```json
{
  "error_code": "LEDGER_CONNECTION_ERROR",
  "message": "Unable to read from immudb."
}
```

### OUT-003 — Range Replay Result
- Consumer: Replay caller
- Scenarios: SC-003, SC-006
- Response Shape: ordered list of `LedgerEvent` (E-001)

Example success:
```json
{
  "events": [
    {
      "event_id": "0195b7f0-1111-7c2f-a4da-8f6d2eb6d100",
      "sequence": 0,
      "event_type": "session_start",
      "schema_version": "1.0.0",
      "timestamp": "2026-03-19T23:00:00Z",
      "provenance": {
        "framework_id": "FMWK-002",
        "pack_id": "PC-003-session-events",
        "actor": "system"
      },
      "previous_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
      "payload": {
        "session_id": "sess-operator-0001",
        "actor_id": "operator-ray",
        "channel": "operator",
        "started_at": "2026-03-19T23:00:00Z"
      },
      "hash": "sha256:1111111111111111111111111111111111111111111111111111111111111111"
    }
  ]
}
```

Example failure:
```json
{
  "error_code": "LEDGER_CONNECTION_ERROR",
  "message": "Replay read failed."
}
```

### OUT-004 — Verification Result
- Consumer: Integrity caller
- Scenarios: SC-004, SC-010
- Response Shape: `ChainVerificationResult` (E-009)

Example success:
```json
{
  "valid": true,
  "start": 0,
  "end": 5
}
```

Example failure:
```json
{
  "valid": false,
  "break_at": 3,
  "start": 0,
  "end": 5
}
```

### OUT-005 — Tip Result
- Consumer: Tip caller
- Scenarios: SC-002, SC-003
- Response Shape: `LedgerTip` (E-008)

Example success:
```json
{
  "sequence_number": 128,
  "hash": "sha256:cc5af2f9c31b1db5d90d2f39c23027d580f509512cc3fc74b18298f8310ca71c"
}
```

Example failure:
```json
{
  "error_code": "LEDGER_CONNECTION_ERROR",
  "message": "Unable to read tip from immudb."
}
```

## Side-Effects

### SIDE-001 — Persistent Append
- Target System: immudb `ledger` database
- Trigger: Successful `append`
- Scenarios: SC-001, SC-002, SC-005, SC-006

| Field | Type | Required | Description | Constraints |
| key | Type:string | Req:yes | Storage key | Zero-padded sequence string per implementation mapping |
| value | Type:bytes | Req:yes | Canonical serialized event bytes | UTF-8, no BOM |

Ordering Guarantee:
- Append is synchronous and becomes visible only after immudb acknowledges the write.
- Sequence assignment and persistence are atomic at the Ledger contract boundary.

Failure Behavior:
- Return `LedgerConnectionError`, `LedgerSerializationError`, or `LedgerSequenceError`.
- Do not report success and do not create a partial event.

### SIDE-002 — Canonical Serialization and Hashing
- Target System: Local hash computation before persistence
- Trigger: Any append and any verify operation
- Scenarios: SC-001, SC-002, SC-004, SC-008, SC-010

| Field | Type | Required | Description | Constraints |
| source_event | Type:object | Req:yes | Event object prior to hashing | `hash` field excluded from hash input |
| serialized_bytes | Type:bytes | Req:yes | Canonical JSON output | Sorted keys, separators `,` and `:`, UTF-8, `ensure_ascii=false`, nulls included |
| hash_output | Type:string | Req:yes | SHA-256 digest string | Exact `sha256:<64 lowercase hex>` |

Ordering Guarantee:
- Serialization occurs before persistence and before verification comparison.
- The same source event always produces the same bytes and hash.

Failure Behavior:
- Return `LedgerSerializationError`.
- Abort append or verification result generation.

### SIDE-003 — Reconnect Once on Connection Loss
- Target System: immudb gRPC connection
- Trigger: Connection drops during read or append
- Scenarios: SC-009

| Field | Type | Required | Description | Constraints |
| disconnect_event | Type:string | Req:yes | Connection failure indicator | Non-empty |
| retry_delay_ms | Type:integer | Req:yes | Wait before reconnect | Must be `1000` |

Ordering Guarantee:
- Close connection, wait one second, reconnect, and retry the interrupted operation once.

Failure Behavior:
- If retry fails, return `LedgerConnectionError`.
- No additional retry loop is allowed.

## Errors

### ERR-001
- Condition: immudb is unreachable, the `ledger` database does not exist, or reconnect-once retry fails
- Scenarios: SC-003, SC-009
- Caller Action: Treat as no-write/no-read success; surface operator-visible failure and let higher layers decide retry timing

### ERR-002
- Condition: event cannot be serialized under the canonical JSON contract
- Scenarios: SC-001, SC-002, SC-008
- Caller Action: Fix event construction; do not retry unchanged input

### ERR-003
- Condition: sequence reservation conflicts with the current tip during append
- Scenarios: SC-002, SC-007
- Caller Action: Treat as architectural violation under the single-writer model; do not create fallback sequence logic

### ERR-004
- Condition: hash-chain verification detects a mismatch
- Scenarios: SC-004, SC-010
- Caller Action: Treat as corruption, stop dependent operations, and surface `break_at`

## Error Code Enum
| Code | Meaning | Retryable |
| LEDGER_CONNECTION_ERROR | immudb connection or database access failed | yes |
| LEDGER_SERIALIZATION_ERROR | Event could not be canonically serialized | no |
| LEDGER_SEQUENCE_ERROR | Next sequence could not be assigned without conflict | no |
| LEDGER_CORRUPTION_ERROR | Stored chain failed verification | no |
