# D4: Contracts — FMWK-001-ledger
Meta: v:1.0.0 (matches D2) | data model:D3 v1.0.0 | status:Draft

IDs: IN-NNN (inbound), OUT-NNN (outbound), SIDE-NNN (side-effect), ERR-NNN (error).

---

## Inbound Contracts

### IN-001: append(event)
- Caller: FMWK-002 (write-path — all cognitive events), FMWK-006 (package-lifecycle — install events), kernel infrastructure (session events, snapshot events)
- Trigger: Any state mutation requiring a Ledger record
- Scenarios: SC-001, SC-006, SC-007, SC-008

Request Shape (fields caller supplies):
| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| event_id | string | yes | UUID v7 | UUID v7 format; caller assigns |
| event_type | string | yes | From canonical catalog | Must be in E-009 catalog |
| schema_version | string | yes | Schema version | "1.0.0" (current) |
| timestamp | string | yes | ISO-8601 UTC with "Z" suffix | e.g., "2026-03-01T14:22:00Z" |
| provenance | object | yes | {framework_id, pack_id, actor} | actor: "system"\|"operator"\|"agent" |
| payload | object | yes | Event type-specific data | No float-type values anywhere in payload |

Constraints:
- Caller MUST NOT supply `sequence`, `previous_hash`, or `hash` — these are Ledger-assigned
- `payload` MUST NOT contain float-type values; all decimal values MUST be strings
- `event_type` MUST be in the E-009 canonical catalog

Returns: `sequence_number: int` — the sequence number assigned to this event

---

### IN-002: read(sequence_number)
- Caller: FMWK-002 (write-path), FMWK-005 (graph replay), CLI verification tools
- Trigger: Fetching a specific event by position
- Scenarios: SC-002

Request Shape: `sequence_number: int`

Constraints:
- `sequence_number` must be in range [0, current_tip.sequence_number]
- Raises `LedgerConnectionError` if immudb unreachable
- Raises `LedgerConnectionError` if `sequence_number` is out of range (missing key / no stored event at that sequence)

Returns: Full LedgerEvent (E-001) exactly as stored — no transformation or re-serialization

---

### IN-003: read_range(start, end)
- Caller: FMWK-005 (graph replay), CLI verification tools
- Trigger: Fetching a contiguous window of events
- Scenarios: SC-003 (variant — fixed-range form)

Request Shape:
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| start | int | yes | ≥ 0 |
| end | int | yes | ≥ start; ≤ current_tip.sequence_number |

Constraints:
- Raises `LedgerConnectionError` if immudb unreachable

Returns: `[LedgerEvent]` in strictly ascending sequence order. Empty list if start > tip.

---

### IN-004: read_since(sequence_number)
- Caller: FMWK-005 (graph replay after snapshot load)
- Trigger: Graph reconstruction — load snapshot then replay events after snapshot_sequence
- Scenarios: SC-003

Request Shape: `sequence_number: int` — returns all events with sequence > this value

Constraints:
- If `sequence_number` equals current tip, returns empty list (not an error)
- Raises `LedgerConnectionError` if immudb unreachable

Returns: `[LedgerEvent]` in strictly ascending sequence order

---

### IN-005: verify_chain(start?, end?)
- Caller: CLI tools (cold-storage validation), FMWK-006 (system-gate), operator diagnostics via DoPeJarMo
- Trigger: Integrity verification, post-recovery validation, framework chain validation
- Scenarios: SC-004, SC-005, SC-EC-001

Request Shape:
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| start | int | no | Default 0 |
| end | int | no | Default current tip sequence |

Constraints:
- MUST function without a running kernel process (cold-storage capable — direct immudb connection only)
- Recomputes each event's hash from canonical JSON and compares to stored `hash`
- Verifies `previous_hash` chain linkage at every step
- Raises `LedgerConnectionError` if immudb is unreachable during the chain walk

Returns: VerifyChainResult (E-004) — `{valid: true}` or `{valid: false, break_at: N}`

---

### IN-006: get_tip()
- Caller: FMWK-002 (via atomicity mechanism before append), any caller checking current position
- Trigger: Before computing next sequence (internal), on-demand position check
- Scenarios: SC-009

Request Shape: No parameters

Constraints:
- Raises `LedgerConnectionError` if immudb unreachable

Returns: LedgerTip (E-003) — `{sequence_number: N, hash: "sha256:..."}`. If no events exist: `{sequence_number: -1, hash: ""}`.

---

### IN-007: connect(config)
- Caller: Kernel boot process, CLI tools at startup
- Trigger: System initialization, CLI tool startup
- Scenarios: SC-EC-004

Request Shape:
| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| host | string | yes | immudb hostname | From `LedgerConfig`; reads env var `IMMUDB_HOST` |
| port | int | yes | immudb gRPC port | From `LedgerConfig`; reads env var `IMMUDB_PORT` (default 3322) |
| database | string | yes | Database name | From `LedgerConfig`; reads env var `IMMUDB_DATABASE` (default "ledger") |
| username | string | yes | immudb credentials | From `platform_sdk.tier0_core.secrets`; NEVER hardcoded |
| password | string | yes | immudb credentials | From `platform_sdk.tier0_core.secrets`; NEVER hardcoded |

Constraints:
- MUST fail immediately with `LedgerConnectionError` if the `ledger` database does not exist — zero admin operations
- Single persistent gRPC connection (no connection pool)
- On connection loss: wait exactly 1 second, attempt one reconnect; if fails, raise `LedgerConnectionError`
- MUST NOT call `CreateDatabaseV2` or any immudb administrative gRPC method

Returns: void (connection established or exception raised)

---

## Outbound Contracts

### OUT-001: append() acknowledgment → Write Path
- Consumer: FMWK-002 (write-path) — uses returned sequence to confirm write position
- Scenarios: SC-001
- Response Shape: `sequence_number: int` — the sequence assigned to the appended event
- Example success: `42`
- Example failure: raises `LedgerConnectionError` (caller handles)

---

### OUT-002: Event stream → Graph replay
- Consumer: FMWK-005 (graph) — receives ordered events from `read_since()` to rebuild materialized view
- Scenarios: SC-003
- Response Shape: `[LedgerEvent]` (list of E-001)
- Ordering guarantee: Strictly ascending by `sequence` field. No gaps. No duplicates.
- Example success: `[{sequence:11,...}, {sequence:12,...}, ..., {sequence:20,...}]`
- Example failure: raises `LedgerConnectionError` if immudb unreachable during read

---

### OUT-003: Chain verification result → CLI / gate
- Consumer: CLI tools, FMWK-006 package-lifecycle system gate
- Scenarios: SC-004, SC-005
- Response Shape: VerifyChainResult (E-004)
- Example success: `{"valid": true}`
- Example failure (chain broken): `{"valid": false, "break_at": 3}`

---

### OUT-004: Current tip → caller
- Consumer: FMWK-002 (atomicity mechanism), any caller checking position
- Scenarios: SC-009
- Response Shape: LedgerTip (E-003)
- Example: `{"sequence_number": 42, "hash": "sha256:a1b2c3..."}`
- Empty ledger: `{"sequence_number": -1, "hash": ""}`

---

## Side-Effect Contracts

### SIDE-001: immudb write
- Target System: immudb (ledger_data volume)
- Trigger: Every successful call to `append()`
- Scenarios: SC-001, SC-006, SC-007, SC-008
- Write Shape:
  - Key: zero-padded sequence number string (12 digits, e.g., `"000000000042"`)
  - Value: canonical JSON of the complete event (including `hash` and `previous_hash`), UTF-8 encoded
- Ordering Guarantee: immudb write completes (synchronous gRPC acknowledgment) before `append()` returns. No write buffering.
- Failure Behavior: If immudb write fails (gRPC error), `LedgerConnectionError` is raised. The event is NOT recorded. The caller (FMWK-002) handles all retry and recovery decisions.

---

### SIDE-002: Canonical JSON Serialization (hash computation contract)
- Target System: `hashlib.sha256` (internal, pure function)
- Trigger: Every hash computation — during `append()` (computing `hash`) and during `verify_chain()` (recomputing expected hash)
- Scenarios: SC-001, SC-004, SC-005, SC-006, SC-007

Exact serialization steps (byte-level contract — MUST be reproduced identically by any verifier):
1. Copy the event object as a Python dict (or equivalent in other languages).
2. Remove the `hash` key entirely from the copy.
3. Serialize: `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`
   - Keys: sorted alphabetically at every nesting level (recursive)
   - Separators: `,` between items, `:` between key-value — no whitespace
   - `ensure_ascii=False`: literal UTF-8 characters, NOT `\uNNNN` escapes
   - `null` fields: included as `"key":null`, not omitted
   - Integer fields: bare digits only (no `.0`, no `e` notation)
   - No float-type values exist in valid events — if encountered, this is a `LedgerSerializationError`
4. Encode the resulting string to bytes: UTF-8, no BOM.
5. `hashlib.sha256(utf8_bytes).hexdigest()` → 64 lowercase hex chars.
6. Prefix with `sha256:` → assign as the `hash` field.

Ordering Guarantee: Pure function — no ordering dependency.
Failure Behavior: If the event contains any value that cannot be serialized (e.g., float, bytes, set), raise `LedgerSerializationError` before any immudb write is attempted.

---

### SIDE-003: Reconnection behavior
- Target System: immudb gRPC connection
- Trigger: gRPC connection failure detected during any operation
- Scenarios: SC-EC-003

Behavior sequence:
1. Connection failure detected (gRPC error on any operation).
2. Wait exactly 1 second.
3. Attempt one reconnect to immudb using the same config from `connect()`.
4. If reconnect succeeds, complete the original operation.
5. If reconnect fails, raise `LedgerConnectionError`. DO NOT retry the original operation again.

Ordering Guarantee: At most one reconnect attempt per failure. The caller handles all higher-level recovery.

---

## Error Contracts

### ERR-001: LedgerConnectionError
- Condition: Cannot reach immudb — initial `connect()` with missing database, gRPC failure during any operation, or reconnect failure after one retry
- Scenarios: SC-EC-003, SC-EC-004
- Code: `LEDGER_CONNECTION_ERROR`
- Caller Action: Do NOT retry inside the Ledger. Propagate to caller. FMWK-002 decides recovery (per OPERATIONAL_SPEC Q4: system hard-stops when Ledger is unreachable — cannot write means nothing can happen).

---

### ERR-002: LedgerCorruptionError
- Condition: `verify_chain()` finds a stored hash that does not match the recomputed SHA-256 of that event's canonical JSON
- Scenarios: SC-EC-001, SC-004
- Code: `LEDGER_CORRUPTION_ERROR`
- Caller Action: Stop all operations. Report to operator via DoPeJarMo. Manual investigation required — this is a catastrophic condition. The `break_at` sequence in VerifyChainResult identifies where corruption begins.

---

### ERR-003: LedgerSequenceError
- Condition: Concurrent write detected — the read-tip-then-write atomicity mechanism detects a non-monotonic or duplicate sequence number
- Scenarios: SC-EC-002
- Code: `LEDGER_SEQUENCE_ERROR`
- Caller Action: This is a design violation (single writer should prevent this). Treat as fatal. Log with full context. Do NOT retry. Investigate how the single-writer invariant was breached.

---

### ERR-004: LedgerSerializationError
- Condition: Event object cannot be serialized to canonical JSON (float-type value present, unserializable Python type, etc.)
- Scenarios: SC-001 (failure path)
- Code: `LEDGER_SERIALIZATION_ERROR`
- Caller Action: Fix the event construction before retrying. This is a programming error in the caller, not a transient condition.

---

## Error Code Enum

| Code | Meaning | Retryable |
|------|---------|-----------|
| LEDGER_CONNECTION_ERROR | Cannot reach immudb (network, auth, or missing database) | No — caller decides recovery |
| LEDGER_CORRUPTION_ERROR | Hash chain mismatch detected during verify_chain | No — fatal, requires manual investigation |
| LEDGER_SEQUENCE_ERROR | Sequence conflict — non-monotonic write attempted | No — fatal design violation |
| LEDGER_SERIALIZATION_ERROR | Cannot serialize event to canonical JSON | No — programming error in caller |
