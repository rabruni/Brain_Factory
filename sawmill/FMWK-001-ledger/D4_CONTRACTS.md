# D4: Contracts — Ledger (FMWK-001)
Meta: v:1.0.0 (matches D2) | data model:D3 v1.0.0 | status:Final

IDs: IN-NNN (inbound), OUT-NNN (outbound), SIDE-NNN (side-effect), ERR-NNN (error).
Every contract references at least one D2 scenario.

---

## Inbound (IN-###)

### IN-001 — append(event_data) → sequence_number

- Caller: Write Path (FMWK-002). The Write Path is the sole permitted caller of append(). All other components route mutations through the Write Path, not directly to the Ledger.
- Trigger: Any state mutation in DoPeJarMo (node creation, signal delta, session boundary, package install, snapshot, etc.)
- Scenarios: SC-001, SC-002, SC-010, SC-011

**Request Shape** (caller-supplied fields; Ledger assigns event_id, sequence, previous_hash, hash):

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| event_type | string | yes | Must be a valid EventType enum value (see enum table below) |
| schema_version | string | yes | semver string; e.g., "1.0.0" |
| timestamp | string | yes | ISO-8601 UTC with Z suffix; e.g., "2026-03-21T03:21:00Z" |
| provenance.framework_id | string | yes | Framework ID of the caller; e.g., "FMWK-002" |
| provenance.pack_id | string | no | Pack ID within framework; may be omitted or null |
| provenance.actor | string | yes | Enum: "system", "operator", "agent" |
| payload | object | yes | Event-type-specific JSON object; must be JSON-serializable |

**Inline Payload Schemas** (Turn C reads D2+D4 only; full schemas restated here verbatim from D3):

*node_creation payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| node_id | string | yes | UUID v7 of the new Graph node |
| node_type | string | yes | Type of node (e.g., "learning_artifact", "intent", "work_order") |
| initial_methylation | string | yes | Float 0.0–1.0 serialized as string; e.g., "0.0" |
| base_weight | string | yes | Non-negative float serialized as string; e.g., "0.5" |

*signal_delta payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| node_id | string | yes | UUID v7 of the target Graph node |
| signal_type | string | yes | Enum: "entity", "mode", "stimulus", "regime" |
| delta | string | yes | Signed float serialized as string; e.g., "0.1", "-0.05" |

*package_install payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| package_id | string | yes | Package identifier; e.g., "FMWK-002-write-path" |
| framework_id | string | yes | Framework being installed; e.g., "FMWK-002" |
| version | string | yes | semver string; e.g., "1.0.0" |
| manifest_hash | string | yes | "sha256:" + 64 lowercase hex chars |

*session_start payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| session_id | string | yes | UUID v7 for this session |
| actor_id | string | yes | Identifier of the connecting actor |
| session_type | string | yes | Enum: "operator", "user" |

*session_end payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| session_id | string | yes | UUID v7 matching the session_start event |
| reason | string | yes | Enum: "normal", "timeout", "error" |

*snapshot_created payload:*
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| snapshot_sequence | integer | yes | Ledger sequence number at snapshot time |
| snapshot_file | string | yes | Path: "/snapshots/<sequence_number>.snapshot" |
| snapshot_hash | string | yes | "sha256:" + 64 lowercase hex chars |

*Deferred payload types* (owned by other frameworks; Ledger accepts as opaque JSON objects):
- methylation_delta, suppression, unsuppression, mode_change, consolidation → FMWK-002
- work_order_transition → FMWK-003
- intent_transition → FMWK-021
- package_uninstall, framework_install → FMWK-006

**Observable Postconditions** (caller-visible invariants after a successful append()):
1. Returns an integer sequence_number ≥ 0.
2. **Durability**: subsequent read(returned_sequence_number) returns the identical event with all fields intact.
3. **Chain continuity**: the returned event's previous_hash equals the hash of the event at sequence returned_sequence_number-1 (or "sha256:"+64zeros if returned_sequence_number=0).
4. **Hash correctness**: the returned event's hash equals the SHA-256 of its canonical JSON (hash field excluded; see SIDE-002).
5. **Monotonicity**: returned sequence_number = (previous tip.sequence_number + 1). No gaps, no skips.
6. **No fork**: exactly one event exists at the returned sequence_number. Calling read(returned_sequence_number) always returns this same event.
7. **Tip advance**: immediately after append() returns, get_tip() returns {sequence_number: returned_sequence_number, hash: <hash_of_new_event>}.
8. **Atomicity on failure**: if LedgerConnectionError or LedgerSerializationError is raised, the Ledger state is unchanged — tip is unchanged, no new event exists, chain is intact.

**Constraints:**
- Callers MUST NOT pass a sequence number. The Ledger assigns all sequence numbers.
- Callers MUST NOT call append() concurrently. Single-writer architecture. Concurrent calls result in LedgerSequenceError (see ERR-003).
- The Ledger does not validate payload field content beyond JSON serializability.

Example (success):
```
Request: {event_type: "session_start", schema_version: "1.0.0", timestamp: "2026-03-21T03:21:00Z",
          provenance: {framework_id: "FMWK-002", actor: "system"},
          payload: {session_id: "01956b3c-...", actor_id: "op-001", session_type: "operator"}}
Response: 0  (sequence_number, integer)
```

Example (failure — immudb down):
```
Request: {valid event_data}
Response: raises LedgerConnectionError
Postcondition: get_tip() unchanged, no event written
```

---

### IN-002 — read(sequence_number) → LedgerEvent

- Caller: Write Path (FMWK-002), Package Lifecycle (FMWK-006), cold-storage CLI tools, Graph (FMWK-005) during replay
- Trigger: Event retrieval by exact position
- Scenarios: SC-003

**Request Shape:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| sequence_number | integer | yes | ≥ 0 |

**Observable Postconditions:**
1. If sequence_number ≤ tip.sequence_number: returns the complete LedgerEvent (E-001) stored at that sequence number, with all fields: event_id, sequence, event_type, schema_version, timestamp, provenance, previous_hash, payload, hash.
2. If sequence_number > tip.sequence_number: raises LedgerSequenceError (ERR-003).
3. If sequence_number < 0: raises LedgerSequenceError (ERR-003).
4. The returned event's hash is identical to what was stored at append time — the Ledger does not recompute hashes on read.
5. If immudb unreachable: raises LedgerConnectionError (ERR-001).

Example (success):
```
Request: read(5)
Response: LedgerEvent{sequence: 5, event_type: "signal_delta", hash: "sha256:...", ...}
```

Example (out of range):
```
Request: read(999)   # tip is at 41
Response: raises LedgerSequenceError
```

---

### IN-003 — read_range(start, end) → [LedgerEvent]

- Caller: Write Path (FMWK-002), Graph (FMWK-005) for bulk replay, cold-storage CLI tools
- Trigger: Batch retrieval for Graph reconstruction, audit, or replay
- Scenarios: SC-004

**Request Shape:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| start | integer | yes | ≥ 0 |
| end | integer | yes | ≥ start |

**Observable Postconditions:**
1. If end ≤ tip.sequence_number: returns a list of (end - start + 1) LedgerEvents at sequences start, start+1, ..., end inclusive, in ascending order.
2. If end > tip.sequence_number: raises LedgerSequenceError (ERR-003).
3. If start > tip.sequence_number: raises LedgerSequenceError (ERR-003).
4. If start = end = N and N ≤ tip: returns a list containing exactly one event (equivalent to [read(N)]).
5. The list preserves ascending sequence order. Events are never reordered.
6. If immudb unreachable: raises LedgerConnectionError (ERR-001).

Example (success):
```
Request: read_range(3, 7)
Response: [LedgerEvent{seq:3}, LedgerEvent{seq:4}, LedgerEvent{seq:5}, LedgerEvent{seq:6}, LedgerEvent{seq:7}]
```

---

### IN-004 — read_since(sequence_number) → [LedgerEvent]

- Caller: Graph (FMWK-005) for post-snapshot replay, Write Path (FMWK-002) for recovery
- Trigger: Startup replay after snapshot load; recovery after crash
- Scenarios: SC-005

**Request Shape:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| sequence_number | integer | yes | ≥ 0 |

**Observable Postconditions:**
1. Returns all events with sequence > sequence_number, in ascending order.
2. If sequence_number = tip.sequence_number: returns an empty list [].
3. If sequence_number > tip.sequence_number: raises LedgerSequenceError (ERR-003).
4. The returned list begins at sequence_number + 1 and ends at tip.sequence_number inclusive.
5. If immudb unreachable: raises LedgerConnectionError (ERR-001).

Example (success — 5 events to return):
```
Request: read_since(5)   # tip is at 10
Response: [LedgerEvent{seq:6}, LedgerEvent{seq:7}, LedgerEvent{seq:8}, LedgerEvent{seq:9}, LedgerEvent{seq:10}]
```

Example (nothing new):
```
Request: read_since(10)  # tip is at 10
Response: []
```

---

### IN-005 — verify_chain(start?, end?) → ChainVerificationResult

- Caller: Package Lifecycle (FMWK-006), cold-storage CLI tools, Graph (FMWK-005) on startup, operator-initiated audits
- Trigger: Integrity verification (startup, post-install, explicit audit)
- Scenarios: SC-007, SC-008, SC-009

**Request Shape:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| start | integer | no | ≥ 0; defaults to 0 if omitted |
| end | integer | no | ≥ start; defaults to tip.sequence_number if omitted |

**Observable Postconditions:**
1. Walks all events from start to end inclusive, recomputing SHA-256 of each event's canonical JSON (hash field excluded per SIDE-002) and comparing to the stored hash field.
2. Also verifies chain linkage: each event's previous_hash must equal the hash field of the event at sequence-1 (or "sha256:"+64zeros for sequence 0).
3. If all checks pass: returns ChainVerificationResult{valid: true, break_at: null}.
4. If any check fails: returns ChainVerificationResult{valid: false, break_at: N} where N is the **lowest** sequence number with a hash mismatch or chain linkage failure.
5. Verification stops at the first detected failure (break_at is returned immediately; subsequent events are not verified).
6. If immudb unreachable: raises LedgerConnectionError (ERR-001). Does NOT return {valid:false} — an unreachable immudb is an infrastructure failure, not a corruption.
7. Produces identical results whether called from the kernel process or from the cold-storage CLI tool connecting directly to immudb. No kernel runtime required.

Example (intact):
```
Request: verify_chain()   # tip is at 5
Response: ChainVerificationResult{valid: true, break_at: null}
```

Example (corruption at sequence 3):
```
Request: verify_chain()   # tip is at 9
Response: ChainVerificationResult{valid: false, break_at: 3}
```

---

### IN-006 — get_tip() → TipRecord

- Caller: Write Path (FMWK-002) — reads before each append to determine next sequence number; Package Lifecycle (FMWK-006) — reads for chain walk; Graph (FMWK-005) — reads on startup to know current state
- Trigger: Pre-append sequence determination; chain walk start; startup state check
- Scenarios: SC-006

**Request Shape:** None. get_tip() takes no arguments.

**Observable Postconditions:**
1. If Ledger is non-empty: returns TipRecord{sequence_number: N, hash: <hash_of_event_at_N>} where N is the sequence number of the most recently appended event.
2. If Ledger is empty: returns TipRecord{sequence_number: -1, hash: "sha256:0000000000000000000000000000000000000000000000000000000000000000"} (see D6 CLR-002).
3. The returned hash equals the hash field of the event returned by read(N).
4. After a successful append() returning sequence_number=K, an immediate get_tip() returns TipRecord{sequence_number: K, hash: <hash_of_event_K>}.
5. If immudb unreachable: raises LedgerConnectionError (ERR-001).

Example (non-empty):
```
Request: get_tip()   # latest event is at sequence 41
Response: TipRecord{sequence_number: 41, hash: "sha256:a1b2c3..."}
```

Example (empty):
```
Request: get_tip()   # no events yet
Response: TipRecord{sequence_number: -1, hash: "sha256:0000000000000000000000000000000000000000000000000000000000000000"}
```

---

## Outbound (OUT-###)

### OUT-001 — sequence_number (return value from append)
- Consumer: Write Path (FMWK-002)
- Scenarios: SC-001, SC-002
- Response Shape: integer ≥ 0; the globally unique sequence number assigned to the appended event
- Example success: 0 (genesis), 1, 2, ..., N

### OUT-002 — LedgerEvent (return value from read)
- Consumer: Write Path (FMWK-002), Graph (FMWK-005), Package Lifecycle (FMWK-006), cold-storage CLI
- Scenarios: SC-003
- Response Shape: Complete E-001 LedgerEvent with all fields as stored at append time
- Example success: see E-001 JSON Example in D3

### OUT-003 — [LedgerEvent] (return value from read_range and read_since)
- Consumer: Graph (FMWK-005), Write Path (FMWK-002), cold-storage CLI
- Scenarios: SC-004, SC-005
- Response Shape: Ordered list of E-001 LedgerEvents in ascending sequence order; may be empty []

### OUT-004 — TipRecord (return value from get_tip)
- Consumer: Write Path (FMWK-002), Package Lifecycle (FMWK-006), Graph (FMWK-005)
- Scenarios: SC-006
- Response Shape: E-003 TipRecord with sequence_number and hash

### OUT-005 — ChainVerificationResult (return value from verify_chain)
- Consumer: Package Lifecycle (FMWK-006), cold-storage CLI, Graph (FMWK-005)
- Scenarios: SC-007, SC-008, SC-009
- Response Shape: E-004 ChainVerificationResult with valid and optional break_at

---

## Side-Effects (SIDE-###)

### SIDE-001 — Ledger Write to immudb
- Target System: immudb (gRPC on port 3322, database "ledger")
- Trigger: append() call with a valid event
- Scenarios: SC-001, SC-002
- Write Shape: immudb Set(key=<zero-padded sequence number as string>, value=<canonical JSON bytes of full LedgerEvent including hash>)
- Ordering Guarantee: Strictly monotonic. The in-process mutex (see D5 RQ-001) ensures that the read-tip, compute-next-sequence, and write operations are atomic from the caller's perspective. Sequence N+1 is never written before sequence N is confirmed.
- Failure Behavior: If the immudb gRPC call fails, the Ledger closes the connection, waits 1 second, reconnects once, and retries the operation once. If the retry fails, LedgerConnectionError is raised. The Ledger state is unchanged (no partial write). The in-process mutex is released so subsequent appends can be attempted.

### SIDE-002 — Canonical JSON Serialization (hash input computation)
- Target System: N/A (local computation)
- Trigger: Every append() call (hash computation) and every verify_chain() call (hash recomputation for verification)
- Scenarios: SC-001, SC-002, SC-007, SC-008, SC-009
- This is the byte-level contract that governs hash computation. Any deviation produces a different hash and breaks chain verification:
  1. Take the event dict with all fields populated EXCEPT `hash`
  2. Serialize to JSON: keys sorted alphabetically at every nesting level (including nested objects); separators=(',', ':') — comma between items, colon between key-value, NO spaces anywhere; ensure_ascii=False (store literal UTF-8 chars, not \uNNNN escapes)
  3. Encode the resulting string to UTF-8 bytes (no BOM)
  4. Compute SHA-256 digest of the bytes
  5. Format result as "sha256:" + hexdigest in lowercase
- Python reference: `hashlib.sha256(json.dumps(event_without_hash, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()`
- Additional rules: integers as bare digits (41, not 41.0); floats in payload stored as strings (never raw JSON numbers); null fields included as `"field":null` (not omitted)
- Failure Behavior: If json.dumps raises (e.g., non-serializable object in payload), raises LedgerSerializationError before any write to immudb. The Ledger state is unchanged.

---

## Errors (ERR-###)

### ERR-001 — LedgerConnectionError
- Condition: immudb unreachable; gRPC connection refused; gRPC timeout; retry (one reconnect + one retry) exhausted
- Scenarios: SC-010
- Caller Action: Surface the error to the Write Path (FMWK-002). The Ledger does not retry further — the Write Path owns the retry policy. The system should block (not silently buffer or continue) when the Ledger is unreachable.
- Retryable: Caller decides. The Ledger itself does not retry beyond the one built-in reconnect attempt.

### ERR-002 — LedgerCorruptionError
- Condition: Hash chain verification failure detected during verify_chain() — a stored hash does not match the recomputed SHA-256, or a previous_hash link is broken
- Scenarios: SC-008
- Caller Action: Surface the error to the operator through DoPeJarMo. Manual investigation is required. The system must not continue operating as if the Ledger is reliable. The ChainVerificationResult {valid:false, break_at:N} indicates where corruption begins.
- Retryable: No. Corruption is not transient; it requires manual intervention.

### ERR-003 — LedgerSequenceError
- Condition: (a) Concurrent append() call detected (design violation — single-writer architecture guarantees this should be impossible), OR (b) read()/read_range()/read_since() called with a sequence number beyond tip.sequence_number
- Scenarios: SC-011 (concurrent append), SC-003/SC-004/SC-005 (out-of-range read)
- Caller Action: For out-of-range reads: caller adjusts the requested sequence bounds and retries. For concurrent append: this is a system design violation; alert the operator; do not proceed.
- Retryable: Out-of-range reads: yes, with corrected bounds. Concurrent append: no.

### ERR-004 — LedgerSerializationError
- Condition: The event payload (or any other event field) cannot be serialized to canonical JSON using SIDE-002 rules (e.g., contains a non-serializable Python object, or json.dumps raises)
- Scenarios: SC-001, SC-002 (implicit — all appends may trigger this)
- Caller Action: Surface to Write Path (FMWK-002). The event is not appended. The Ledger state is unchanged. The Write Path should reject the event and notify the originating component.
- Retryable: No. The payload must be fixed to be JSON-serializable before retrying.

---

## Error Code Enum

| Code | Meaning | Retryable |
|------|---------|-----------|
| LEDGER_CONNECTION_ERROR | immudb unreachable after one reconnect+retry | Caller decides |
| LEDGER_CORRUPTION_ERROR | Hash chain verification failure | No — manual intervention |
| LEDGER_SEQUENCE_ERROR | Concurrent write attempt or out-of-range read | Conditional (yes for reads, no for concurrent write) |
| LEDGER_SERIALIZATION_ERROR | Event payload not JSON-serializable | No — fix the payload |

---

## EventType Enum (Turn C reference — restated from D3)

Valid values for the `event_type` field in IN-001 requests:

| Value | Valid For append() |
|-------|--------------------|
| node_creation | yes |
| signal_delta | yes |
| methylation_delta | yes |
| suppression | yes |
| unsuppression | yes |
| mode_change | yes |
| consolidation | yes |
| work_order_transition | yes |
| intent_transition | yes |
| session_start | yes |
| session_end | yes |
| package_install | yes |
| package_uninstall | yes |
| framework_install | yes |
| snapshot_created | yes |
