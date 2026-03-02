# Source Material: FMWK-001-ledger

> Source material for spec agent extraction. Extract and structure into D1-D6.
> Items marked OPEN should be flagged in D6 for human resolution.

---

## Event Schema

Every Ledger event has this base shape:

```json
{
  "event_id": "uuid-v7",
  "sequence": 0,
  "event_type": "string",
  "schema_version": "1.0.0",
  "timestamp": "ISO-8601 UTC",
  "provenance": {
    "framework_id": "FMWK-NNN",
    "pack_id": "PC-NNN-name",
    "actor": "system | operator | agent"
  },
  "previous_hash": "sha256:<64hex>",
  "payload": {},
  "hash": "sha256:<64hex>"
}
```

**Sequence numbering**: Global monotonic. Single writer (Write Path) ensures no conflicts. Sequence 0 is the genesis event. The Ledger enforces monotonicity internally — callers do NOT pass sequence numbers. The Ledger reads the current tip, increments by 1, and assigns. If a concurrent call somehow arrives (design violation — should be impossible with single writer), the Ledger MUST reject with `LedgerSequenceError` rather than silently creating a fork.

**Event types** (from BUILDER_SPEC.md):
- `node_creation` — new node in Graph
- `signal_delta` — increment/decrement signal on a node
- `methylation_delta` — direct methylation adjustment (rare, admin)
- `suppression` — suppress a node (M → 1.0)
- `unsuppression` — unsuppress a node
- `mode_change` — change node mode
- `consolidation` — merge nodes
- `work_order_transition` — work order state change
- `intent_transition` — intent lifecycle state change
- `session_start` / `session_end` — session boundaries
- `package_install` / `package_uninstall` — package lifecycle
- `framework_install` — framework installed via gates
- `snapshot_created` — snapshot taken

Each event type has a type-specific `payload` schema. The spec agent should define at minimum the payload schemas for: `node_creation`, `signal_delta`, `package_install`, `session_start`. Other payload schemas can be deferred to the frameworks that own them (flag in D6).

## Hash Chain

- **Algorithm**: SHA-256 over the canonical JSON-serialized event (sorted keys, no whitespace, `hash` field excluded from input)
- **Chain structure**: Linear. Each event's `previous_hash` = the `hash` of the preceding event.
- **Genesis event**: `previous_hash` = `sha256:0000000000000000000000000000000000000000000000000000000000000000` (exactly 64 lowercase hex chars, no `0x` prefix, no uppercase)
- **Hash format**: ALL hashes in the system use the format `sha256:<64 lowercase hex chars>`. No variations: no uppercase, no `0x` prefix, no raw bytes, no base64. This is a byte-level contract — tests MUST compare exact string equality, not semantic equivalence.
- **Verification**: Walk from genesis to tip. Recompute each hash from canonical JSON. Compare against stored hash. Any mismatch = corruption at that sequence number.
- **Cold verification**: Requires only the Ledger data file. No runtime services needed.

**Observable hash chain behaviors** (the spec agent should extract these as D2 scenarios so the holdout agent can test them):
- GIVEN empty ledger WHEN first event appended THEN event.previous_hash = `sha256:` + 64 zeros AND event.sequence = 0
- GIVEN ledger with N events WHEN event N+1 appended THEN event.previous_hash = hash of event N AND event.sequence = N
- GIVEN ledger with events 0-5 WHEN verify_chain(0, 5) THEN recompute SHA-256 of each event's canonical JSON (excluding hash field), compare to stored hash, return valid=true if all match
- GIVEN ledger with corrupted event at sequence 3 WHEN verify_chain() THEN return {valid: false, break_at: 3}
- GIVEN ledger data exported to file WHEN verify_chain run offline (no immudb) THEN produces same result as online verification

**Canonical JSON rules** (the spec agent should include in D3 as a data model constraint AND D4 as a serialization contract):
- Keys sorted alphabetically at every nesting level
- No whitespace between tokens: separators are `,` and `:` with no spaces (Python: `json.dumps(obj, sort_keys=True, separators=(',', ':'))`)
- The `hash` field is excluded from the serialization before hashing
- All other fields including `previous_hash` are included
- This ensures the same event always produces the same hash regardless of field insertion order
- **Encoding**: UTF-8, no BOM. All strings are UTF-8 encoded before hashing.
- **Number representation**: integers as bare digits (no decimal point, no trailing zeros). No floating point fields exist in the base schema — if a payload includes floats, they MUST be serialized as strings to avoid cross-language representation drift.
- **Unicode**: no escaped unicode sequences. Characters are stored as literal UTF-8 bytes, not `\uNNNN` escapes. (Python: `ensure_ascii=False`)
- **Null handling**: null fields are included in serialization as `"field":null`, not omitted.
- The spec agent MUST extract this as a D4 Serialization Contract (e.g., SIDE-002 or a dedicated contract) that defines the exact byte-ordering of hash input. Without this contract, the hash chain will diverge across language boundaries.

## immudb Integration

The Ledger module wraps immudb. Callers see a Ledger interface, never immudb directly.

**Interface** (what the spec agent should define as D4 contracts):
- `append(event) → sequence_number` — append one event, returns its sequence
- `read(sequence_number) → event` — read one event by sequence
- `read_range(start, end) → [events]` — read a range of events
- `read_since(sequence_number) → [events]` — read all events after a sequence
- `verify_chain(start?, end?) → {valid: bool, break_at?: sequence}` — verify hash chain integrity
- `get_tip() → {sequence_number, hash}` — get the latest event's sequence and hash

**Sequence enforcement**: Every `append()` call MUST enforce `new_sequence = get_tip().sequence + 1`. The Ledger is the sole owner of sequence numbering — callers do NOT pass a sequence number. This is the syntactic guarantee behind "append-only": if the tip is at sequence 41, the next event is ALWAYS 42, no exceptions.

**Atomicity**: The read-tip-then-write-event operation MUST be atomic. The builder MUST NOT implement this as a separate `get_tip()` followed by a `Set()` — that creates a read-then-write race window. Implementation options (builder chooses, spec agent flags in D5 as a research question):
- Option A: Use immudb's `ExecAll` to batch the read+write in a single transaction
- Option B: Use an in-process mutex/lock (acceptable because single-writer architecture guarantees one caller)
- Option C: Use immudb's `VerifiedSet` which provides server-side atomicity
The spec agent should document this choice in D5 (Research) and the builder implements whichever option D5 resolves to.

**immudb mapping** (implementation detail for builder, not for D4):
- immudb `Set(key, value)` for append (key = sequence number as zero-padded string, value = serialized event)
- immudb `Get(key)` for read
- immudb `Scan(prefix, start, end)` for range reads
- immudb gRPC on `localhost:3322`, database name `ledger`

## immudb Operational Detail (APPROVED for builder extraction)

**Authentication**: immudb ships with default credentials (`immudb` / `immudb`). The Ledger module uses these for local development. Production credentials are config-driven via `platform_sdk.config` — NEVER hardcoded. The spec agent should include this in D4 as a configuration dependency; the builder should read credentials from config.

**Connection handling**: Single persistent gRPC connection. No connection pooling (single writer model — one connection is sufficient). On disconnect: close, wait 1 second, reconnect, retry the operation once. If retry fails: return `LedgerConnectionError`. Connection parameters (host, port, database name) are config-driven.

**Forbidden administrative operations**: The Ledger module MUST NOT expose or call any immudb administrative gRPC methods. Specifically forbidden:
- `DatabaseDelete` / `DropDatabase`
- `CompactIndex`
- `TruncateDatabase`
- `CleanIndex`
- Any method that modifies, deletes, or reorganizes existing data

These are D1 constitutional violations (append-only immutability). The builder MUST NOT import or wrap these methods. The spec agent should include this in D1 as an explicit NEVER boundary.

**Database initialization**: APPROVED: database creation is a separate bootstrap operation, NOT part of the Ledger module's `connect()` method. Reason: "Connect" is operational, "Create" is provisioning. If `connect()` handles creation, multiple agents connecting simultaneously to a non-existent database would race on `CreateDatabaseV2`, potentially corrupting the immudb system catalog. The bootstrap step uses `CreateDatabaseV2` (the ONLY permitted admin operation) then `UseDatabase`. The Ledger module's `connect()` MUST fail fast with `LedgerConnectionError` if the `ledger` database does not exist. This enforces "Ledger does NOT own infrastructure."

**Error types**:
- `LedgerConnectionError` — cannot reach immudb
- `LedgerCorruptionError` — hash chain verification failed
- `LedgerSequenceError` — sequence number conflict (should be impossible with single writer)
- `LedgerSerializationError` — event cannot be serialized

## Snapshots

- **OPEN**: Snapshot format (JSON dump of Graph state? protobuf? custom binary?)
  - Flag in D6. The spec agent should not decide this — it depends on FMWK-005 (graph) snapshot needs.
- **APPROVED**: Snapshot is taken by writing a `snapshot_created` event to the Ledger, with the snapshot file hash in the payload.
- **APPROVED**: Snapshots are stored alongside the Ledger. Location: `/snapshots/<sequence_number>.snapshot`
- **APPROVED**: Replay after snapshot = load snapshot into Graph, then replay events with sequence > snapshot's sequence.

## Durability

- **Synchronous writes**: Every `append()` call is synchronous. The caller blocks until immudb confirms the write.
- **No batching**: Events are written one at a time. No write buffering.
- **immudb handles fsync**: immudb's built-in durability guarantees apply. The Ledger trusts immudb for disk persistence.
- **On immudb failure**: `append()` returns `LedgerConnectionError`. The Write Path (FMWK-002) decides what to do — the Ledger does not retry.

## What the Ledger Does NOT Own

- **Fold logic** — owned by FMWK-002 (write-path). The Ledger stores events; the Write Path interprets them.
- **Graph structure** — owned by FMWK-005 (graph). The Ledger provides replay; the Graph builds its structure.
- **Signal accumulation** — owned by FMWK-002. The Ledger stores `signal_delta` events; the Write Path computes methylation.
- **Gate logic** — owned by FMWK-006 (package-lifecycle). The Ledger stores `package_install` events; gates are run by FMWK-006.
- **Work order management** — owned by FMWK-003. The Ledger stores transitions; orchestration manages state.
