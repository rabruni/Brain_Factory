# D4: Contracts — FMWK-001-ledger
Meta: v:1.0.0 (matches D2) | data model: D3 1.0.0 | status:Final

IDs: IN-NNN (inbound), OUT-NNN (outbound), SIDE-NNN (side-effect), ERR-NNN (error).

## Inbound
### IN-001 — Append Event
- Caller: FMWK-002 write-path and approved mechanical system-event producers behind the ledger abstraction
- Trigger: Caller needs to persist one new event in the linear ledger chain
- Scenarios (D2 SC-001, SC-002, SC-003, SC-007, SC-009, SC-011)
- Request Shape:

| Field | Type | Required | Description | Constraints |
| event_type | string | yes | Event type to append | Must be in approved catalog |
| schema_version | string | yes | Event schema version | `1.0.0` for this spec |
| timestamp | string | yes | Event timestamp | ISO-8601 UTC |
| provenance | E-004 | yes | Event provenance block | Must satisfy E-004 |
| payload | object | yes | Event payload | Must satisfy event-type payload schema |

- Constraints: Caller MUST NOT send `sequence`, `previous_hash`, or `hash`; ledger assigns them. Append is synchronous and one-event-at-a-time. Event must serialize under canonical JSON rules before persistence.
- Example:

```json
{
  "event_type": "session_start",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:20:00Z",
  "provenance": {
    "framework_id": "FMWK-001-ledger",
    "pack_id": "PC-001-ledger-core",
    "actor": "system"
  },
  "payload": {
    "session_id": "session-0195b8d1",
    "session_kind": "operator",
    "subject_id": "ray",
    "started_by": "operator"
  }
}
```

### IN-002 — Read Event
- Caller: Replay consumers, diagnostics, cold-storage tools
- Trigger: Caller needs one event by sequence number
- Scenarios (D2 SC-004)
- Request Shape:

| Field | Type | Required | Description | Constraints |
| sequence_number | integer | yes | Sequence to read | `>= 0` |

- Constraints: Sequence must address exactly one committed event.
- Example:

```json
{
  "sequence_number": 4
}
```

### IN-003 — Read Range
- Caller: Replay consumers, diagnostics, cold-storage tools
- Trigger: Caller needs an inclusive contiguous event interval
- Scenarios (D2 SC-004, SC-005)
- Request Shape:

| Field | Type | Required | Description | Constraints |
| start | integer | yes | Inclusive start sequence | `>= 0` |
| end | integer | yes | Inclusive end sequence | `>= start` |

- Constraints: Returned events MUST be ordered ascending by sequence.
- Example:

```json
{
  "start": 0,
  "end": 5
}
```

### IN-004 — Read Since
- Caller: Graph rebuild, replay consumers
- Trigger: Caller needs all events strictly after a known sequence boundary
- Scenarios (D2 SC-004, SC-007)
- Request Shape:

| Field | Type | Required | Description | Constraints |
| sequence_number | integer | yes | Lower replay boundary | `>= -1`; `-1` means from genesis |

- Constraints: Results exclude the provided boundary sequence and preserve ascending order.
- Example:

```json
{
  "sequence_number": 42
}
```

### IN-005 — Verify Chain
- Caller: Cold-storage validation tools, package lifecycle validation, diagnostics
- Trigger: Caller needs integrity verification over the full ledger or a bounded interval
- Scenarios (D2 SC-005, SC-008, SC-011)
- Request Shape:

| Field | Type | Required | Description | Constraints |
| start | integer | no | Inclusive start sequence | Defaults to genesis when omitted |
| end | integer | no | Inclusive end sequence | Defaults to current tip when omitted |
| source_mode | string | yes | Verification source | `online` or `offline` |

- Constraints: Verification MUST recompute canonical hash input bytes for every event checked and compare exact stored string values.
- Example:

```json
{
  "start": 0,
  "end": 5,
  "source_mode": "offline"
}
```

### IN-006 — Get Tip
- Caller: Append path, diagnostics
- Trigger: Caller needs the latest committed append point
- Scenarios (D2 SC-002, SC-006)
- Request Shape:

| Field | Type | Required | Description | Constraints |
| include_hash | boolean | yes | Whether to include tip hash in response | Current contract requires `true` |

- Constraints: Response must reflect the most recently committed event only.
- Example:

```json
{
  "include_hash": true
}
```

## Outbound
### OUT-001 — Append Success
- Consumer: Caller of IN-001
- Scenarios: D2 SC-001, SC-002, SC-003, SC-007
- Response Shape: E-001 Ledger Event
- Example success:

```json
{
  "event_id": "0195b8d1-6d8d-7ef9-9c6a-4bd29ca2dce4",
  "sequence": 0,
  "event_type": "session_start",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:20:00Z",
  "provenance": {
    "framework_id": "FMWK-001-ledger",
    "pack_id": "PC-001-ledger-core",
    "actor": "system"
  },
  "previous_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "payload": {
    "session_id": "session-0195b8d1",
    "session_kind": "operator",
    "subject_id": "ray",
    "started_by": "operator"
  },
  "hash": "sha256:b2bbde319c7c9677b6d6816d9b422c8ec9787c6d0ca7f64444f0715a8ca54ac8"
}
```

- Example failure:

```json
{
  "code": "LEDGER_SEQUENCE_ERROR",
  "message": "tip changed during append"
}
```

### OUT-002 — Read Success
- Consumer: Caller of IN-002
- Scenarios: D2 SC-004
- Response Shape: E-001 Ledger Event
- Example success:

```json
{
  "event_id": "0195b8d1-6d8d-7ef9-9c6a-4bd29ca2dce4",
  "sequence": 4,
  "event_type": "signal_delta",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:23:00Z",
  "provenance": {
    "framework_id": "FMWK-002",
    "pack_id": "PC-002-write-path",
    "actor": "system"
  },
  "previous_hash": "sha256:4f2d393b4e0d8c5c1ef4c2f4d90ebfcfbf8faed53ddbf220e8f61b4891b653bb",
  "payload": {
    "node_id": "memory-0195b8d1",
    "signal_name": "operator_reinforcement",
    "delta": 1,
    "reason": "operator confirmed importance"
  },
  "hash": "sha256:26e3571f3f5f7084c8aa10c7d82df90b257f847a6ee8e6484ae69770642f4964"
}
```

- Example failure:

```json
{
  "code": "LEDGER_CONNECTION_ERROR",
  "message": "read failed"
}
```

### OUT-003 — Range/Replay Success
- Consumer: Caller of IN-003 or IN-004
- Scenarios: D2 SC-004, SC-007
- Response Shape: array of E-001 Ledger Event
- Example success:

```json
[
  {
    "event_id": "0195b8d1-6d8d-7ef9-9c6a-4bd29ca2dce4",
    "sequence": 42,
    "event_type": "snapshot_created",
    "schema_version": "1.0.0",
    "timestamp": "2026-03-20T20:30:00Z",
    "provenance": {
      "framework_id": "FMWK-002",
      "pack_id": "PC-002-write-path",
      "actor": "system"
    },
    "previous_hash": "sha256:fb0df437c30bd8f2878080efcc6f4ebc8bbafef5e9a56715ebfa7774d7ab54d8",
    "payload": {
      "snapshot_sequence": 42,
      "snapshot_path": "/snapshots/42.snapshot",
      "snapshot_hash": "sha256:5c1f3ed4c95346f1dc3ddca6ca9ea6240cfa0b8455174a8c4363130f0f2387cc"
    },
    "hash": "sha256:8ff89cb84bc2447a94b45dbf5fc08117790e927c8db56d6a30f2147fdbcb5289"
  }
]
```

- Example failure:

```json
{
  "code": "LEDGER_CONNECTION_ERROR",
  "message": "range read failed"
}
```

### OUT-004 — Verification Success
- Consumer: Caller of IN-005
- Scenarios: D2 SC-005, SC-008
- Response Shape: E-002 Verification Result
- Example success:

```json
{
  "valid": true,
  "start_sequence": 0,
  "end_sequence": 5
}
```

- Example failure:

```json
{
  "valid": false,
  "start_sequence": 0,
  "end_sequence": 5,
  "break_at": 3
}
```

### OUT-005 — Tip Success
- Consumer: Caller of IN-006
- Scenarios: D2 SC-002, SC-006
- Response Shape: E-003 Ledger Tip
- Example success:

```json
{
  "sequence_number": 42,
  "hash": "sha256:8ff89cb84bc2447a94b45dbf5fc08117790e927c8db56d6a30f2147fdbcb5289"
}
```

- Example failure:

```json
{
  "code": "LEDGER_CONNECTION_ERROR",
  "message": "tip unavailable"
}
```

## Side-Effects
### SIDE-001 — Persist Event To immudb
- Target System: immudb via the ledger abstraction
- Trigger: Successful IN-001 append request
- Scenarios: D2 SC-001, SC-002, SC-003, SC-007, SC-009, SC-011
- Write Shape: key = zero-padded sequence string; value = canonical serialized E-001 bytes
- Ordering Guarantee: Atomic single linear append. The ledger obtains the current tip, assigns the next sequence, computes `previous_hash` and `hash`, and commits exactly one event before acknowledging success.
- Failure Behavior: If sequencing cannot remain linear, return `LEDGER_SEQUENCE_ERROR`. If persistence fails, return `LEDGER_CONNECTION_ERROR`. No partial success.

### SIDE-002 — Canonical Hash Serialization
- Target System: internal hash computation path and offline verification tooling
- Trigger: Any append or verify operation requiring event hashing
- Scenarios: D2 SC-001, SC-002, SC-005, SC-008, SC-011
- Write Shape: UTF-8 bytes of the event JSON with keys sorted alphabetically at every level, separators `,` and `:`, `ensure_ascii=false`, nulls preserved, `hash` field omitted from input, and floats forbidden in the base envelope
- Ordering Guarantee: The exact same logical event yields the exact same hash input bytes in every supported path.
- Failure Behavior: If serialization cannot satisfy the byte-level contract, return `LEDGER_SERIALIZATION_ERROR` and abort the operation.

### SIDE-003 — Connection Retry
- Target System: immudb gRPC connection managed through ledger runtime configuration
- Trigger: Connection drops during a ledger operation
- Scenarios: D2 SC-010
- Write Shape: close connection, wait 1 second, reconnect once using configured host, port, database, and credentials
- Ordering Guarantee: Retry occurs at most once per failed operation and only before returning failure.
- Failure Behavior: If reconnect or retried operation fails, return `LEDGER_CONNECTION_ERROR`.

### SIDE-004 — Offline Verification
- Target System: exported ledger data file used by CLI/cold-storage validation
- Trigger: IN-005 with `source_mode=offline`
- Scenarios: D2 SC-005, SC-008
- Write Shape: sequentially read stored event bytes from exported ledger data and apply SIDE-002 hash rules
- Ordering Guarantee: Verification order matches on-disk sequence order from start through end.
- Failure Behavior: Return verification failure for corruption or `LEDGER_SERIALIZATION_ERROR` if exported bytes cannot be parsed into the canonical event model.

## Errors
### ERR-001
- Condition: immudb is unreachable, the `ledger` database does not exist, or reconnect/retry fails
- Scenarios: D2 SC-010
- Caller Action: Stop the operation, surface `LEDGER_CONNECTION_ERROR`, and let the caller or operator restore infrastructure. Do not provision the database in runtime code.

### ERR-002
- Condition: Hash recomputation or prior-hash linkage fails during verification
- Scenarios: D2 SC-008
- Caller Action: Surface `LEDGER_CORRUPTION_ERROR` and stop dependent operations. Treat as catastrophic for runtime writes.

### ERR-003
- Condition: Tip changes or append sequencing cannot remain linear
- Scenarios: D2 SC-009
- Caller Action: Surface `LEDGER_SEQUENCE_ERROR`, do not retry blindly, and investigate the single-writer violation.

### ERR-004
- Condition: Event cannot be serialized under the canonical JSON contract
- Scenarios: D2 SC-011
- Caller Action: Surface `LEDGER_SERIALIZATION_ERROR` and correct the event data or serializer before retrying.

## Error Code Enum
| Code | Meaning | Retryable |
| LEDGER_CONNECTION_ERROR | Ledger cannot reach or use immudb for the requested operation | yes, once internally on disconnect; otherwise caller-managed |
| LEDGER_CORRUPTION_ERROR | Stored chain data failed hash or previous-hash verification | no |
| LEDGER_SEQUENCE_ERROR | Append would create a non-linear sequence or fork | no |
| LEDGER_SERIALIZATION_ERROR | Canonical event bytes could not be produced or parsed | no |
