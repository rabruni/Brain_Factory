# D2: Specification — FMWK-001-ledger
Meta: pkg:FMWK-001 | v:1.0.0 | status:Draft | author:Spec Agent | sources:BUILDER_SPEC.md v3.0, OPERATIONAL_SPEC.md v3.0, SOURCE_MATERIAL.md | constitution:D1_CONSTITUTION.md

---

## Purpose

The Ledger is the append-only, hash-chained event store for DoPeJarMo. It provides the sole mechanism for recording state mutations and the authoritative event sequence from which all runtime state (the Graph) is derived. It wraps immudb, exposes a stable interface to all callers, owns all base event schemas, enforces the hash chain invariant on every write, and guarantees that any sequence of events can be replayed from cold storage with no runtime services other than immudb itself.

---

## NOT

The Ledger is NOT a query engine. It does not support filtering, sorting, full-text search, or semantic retrieval.

The Ledger is NOT a message queue. It has no pub/sub, no consumer groups, no push notifications, and no delivery guarantees beyond synchronous write acknowledgment.

The Ledger is NOT a general-purpose database. It stores structured events only — every stored item must have the mandatory base schema fields.

The Ledger is NOT responsible for interpreting events. It stores them. Fold logic (how events update the Graph) lives entirely in FMWK-002 (write-path).

The Ledger is NOT the Graph. The Graph (FMWK-005) is the runtime materialized view derived from Ledger replay. These are separate frameworks with separate responsibilities.

The Ledger is NOT responsible for snapshot file format or Graph reconstruction logic. It provides the ordered event stream and records that a snapshot was taken; FMWK-005 owns snapshot content.

---

## Scenarios

### Primary Scenarios

**SC-001 — Append a Well-Formed Event**
- Priority: P0 (blocker)
- Source: BUILDER_SPEC.md §Ledger, SOURCE_MATERIAL.md §Event Schema
- GIVEN the Ledger is connected to immudb AND the `ledger` database exists
  WHEN `append(event)` is called with a valid event (all base fields present except sequence/previous_hash/hash which are assigned internally)
  THEN the event is written to immudb atomically with `sequence = current_tip.sequence + 1`
  AND `previous_hash` is set to the hash of the preceding event (or the genesis sentinel for sequence 0)
  AND `hash` is computed as SHA-256 of the canonical JSON of the event (sorted keys, no whitespace, `hash` field excluded from input, UTF-8 no BOM, no escaped unicode)
  AND `append()` blocks until immudb confirms the write (synchronous, no buffering)
  AND `append()` returns the assigned `sequence_number` as an integer
- Testing Approach: Unit test with mock immudb. Assert returned sequence, assert `hash` matches regex `^sha256:[0-9a-f]{64}$`, assert `previous_hash` links correctly.

**SC-002 — Read Event by Sequence**
- Priority: P0 (blocker)
- Source: BUILDER_SPEC.md §Ledger, SOURCE_MATERIAL.md §immudb Integration
- GIVEN the Ledger contains events 0 through N
  WHEN `read(sequence_number)` is called with a valid sequence number (0 ≤ seq ≤ N)
  THEN the exact event written at that sequence is returned, unchanged
  AND no re-serialization or mutation of the event occurs during read
- Testing Approach: Write 5 events. Read back each by sequence. Assert byte-level equality of returned event vs original.

**SC-003 — Read Events Since Sequence (Graph Reconstruction)**
- Priority: P0 (blocker)
- Source: BUILDER_SPEC.md §Ledger, OPERATIONAL_SPEC.md §Q3
- GIVEN the Ledger contains events 0 through N
  WHEN `read_since(snapshot_sequence)` is called
  THEN all events with sequence > snapshot_sequence are returned in strictly ascending sequence order
  AND no events are skipped, duplicated, or reordered
  AND an empty list is returned if snapshot_sequence equals the current tip
- Testing Approach: Write 20 events. Snapshot at sequence 10. Call `read_since(10)`. Assert events 11–20 returned in order, none missing, none duplicated.

**SC-004 — Verify Hash Chain Integrity**
- Priority: P0 (blocker)
- Source: SOURCE_MATERIAL.md §Hash Chain, OPERATIONAL_SPEC.md §Q3
- GIVEN the Ledger contains events 0 through N with an intact chain
  WHEN `verify_chain(start=0, end=N)` is called
  THEN for each event, SHA-256 of its canonical JSON (hash field excluded) matches its stored `hash`
  AND each event's `previous_hash` equals the `hash` of the preceding event (or genesis sentinel for event 0)
  AND `{valid: true}` is returned
- Testing Approach: Write 10 events, call `verify_chain()`, assert `valid=true`. Then corrupt one event's stored hash directly in mock immudb. Re-run `verify_chain()`. Assert `{valid: false, break_at: <N>}`.

**SC-005 — Cold-Storage Chain Verification (Offline)**
- Priority: P0 (blocker)
- Source: OPERATIONAL_SPEC.md §Q4, SOURCE_MATERIAL.md §Hash Chain, D1 Article 8
- GIVEN the kernel process is stopped AND immudb is running AND the `ledger_data` volume is accessible
  WHEN `verify_chain()` is invoked via CLI tool connecting directly to immudb on :3322
  THEN the result is identical to running `verify_chain()` with the kernel running
  AND no kernel, Graph, HO1, HO2, or any other cognitive runtime is required
- Testing Approach: Integration test. Start immudb. Write 10 events via Ledger module. Stop kernel. Run CLI `verify_chain`. Assert result matches.

**SC-006 — Genesis Event Has Correct Sentinel**
- Priority: P0 (blocker)
- Source: SOURCE_MATERIAL.md §Hash Chain
- GIVEN an empty Ledger (no events yet)
  WHEN the first event is appended via `append()`
  THEN the event is assigned `sequence = 0`
  AND `event.previous_hash` = `sha256:0000000000000000000000000000000000000000000000000000000000000000` (exactly: `sha256:` prefix + 64 lowercase hex zero digits)
- Testing Approach: Fresh immudb. Append one event. Assert `previous_hash` using exact string comparison (not regex, not semantic check).

**SC-007 — Sequential Hash Chain Linkage**
- Priority: P0 (blocker)
- Source: SOURCE_MATERIAL.md §Hash Chain
- GIVEN the Ledger contains N events (sequences 0 through N-1)
  WHEN event N is appended
  THEN `event_N.previous_hash` equals the `hash` field of event N-1 exactly
  AND `event_N.sequence` equals N
- Testing Approach: Write 5 events. For each consecutive pair, assert `event[i].previous_hash == event[i-1].hash`. Assert all sequences are 0, 1, 2, 3, 4.

**SC-008 — Snapshot Event Recording**
- Priority: P1 (must)
- Source: SOURCE_MATERIAL.md §Snapshots
- GIVEN a Graph snapshot has been taken at Ledger sequence S, producing a snapshot file at `/snapshots/<S>.snapshot`
  WHEN the snapshot operation calls `append()` with a `snapshot_created` event
  THEN a `snapshot_created` event is written to the Ledger containing: `snapshot_path`, `snapshot_hash` (SHA-256 of the snapshot file), and `snapshot_sequence = S`
  AND the event is chained correctly into the hash chain
- Testing Approach: Mock snapshot operation. Call `append()` with a `snapshot_created` payload. Assert event written, assert payload fields present and correctly typed.

**SC-009 — Get Current Tip**
- Priority: P1 (must)
- Source: SOURCE_MATERIAL.md §immudb Integration
- GIVEN the Ledger contains events 0 through N
  WHEN `get_tip()` is called
  THEN `{sequence_number: N, hash: "<stored hash of event N>"}` is returned
  AND the hash matches the `hash` field of the last appended event exactly
- Testing Approach: Write 5 events (sequences 0–4). Call `get_tip()`. Assert `{sequence_number: 4, hash: <hash of event 4>}`.

---

### Edge Cases

**SC-EC-001 — Corrupted Event Detected During Chain Walk**
- Priority: P0 (blocker)
- Source: SOURCE_MATERIAL.md §Hash Chain, OPERATIONAL_SPEC.md §Failure Recovery Matrix
- GIVEN the Ledger contains events 0 through 5 AND the stored hash for event 3 has been corrupted (does not match SHA-256 of event 3's canonical JSON)
  WHEN `verify_chain(start=0, end=5)` is called
  THEN `{valid: false, break_at: 3}` is returned
  AND the walk stops at the first mismatch — events 4 and 5 are not verified
- Testing Approach: Write 6 events in mock immudb. Corrupt the `hash` field of event 3 directly. Call `verify_chain()`. Assert `{valid: false, break_at: 3}`.

**SC-EC-002 — Concurrent Write Attempt (Design Violation)**
- Priority: P1 (must)
- Source: SOURCE_MATERIAL.md §Sequence Numbering
- GIVEN the Ledger is correctly configured with a single writer AND the atomicity mechanism is bypassed to simulate a concurrent write (design violation — should be impossible with single writer + mutex)
  WHEN a second `append()` call would produce a non-monotonic or duplicate sequence
  THEN `LedgerSequenceError` is raised
  AND no partial write is recorded in immudb
- Testing Approach: Use mock to simulate atomicity failure. Assert `LedgerSequenceError` raised. Assert mock immudb shows no partial write.

**SC-EC-003 — immudb Connection Lost During Append**
- Priority: P1 (must)
- Source: SOURCE_MATERIAL.md §immudb Operational Detail, OPERATIONAL_SPEC.md §Failure Recovery Matrix
- GIVEN the Ledger is mid-append AND immudb becomes unreachable (gRPC connection fails)
  WHEN the gRPC call fails (timeout, connection refused, or reset)
  THEN the Ledger waits 1 second and attempts one reconnect
  AND if the reconnect also fails, `LedgerConnectionError` is raised
  AND the Write Path (caller) handles all retry and recovery decisions — the Ledger does NOT retry the append
  AND no partial write exists in immudb (gRPC call atomicity guarantees this)
- Testing Approach: Mock immudb to fail after connection established. Assert `LedgerConnectionError` propagated to caller. Assert mock shows no partial state.

**SC-EC-004 — Connect to Non-Existent Database**
- Priority: P0 (blocker)
- Source: SOURCE_MATERIAL.md §immudb Operational Detail, D1 Article 9
- GIVEN immudb is running AND the `ledger` database does not exist (clean immudb instance, GENESIS not yet run)
  WHEN `connect(config)` is called
  THEN `LedgerConnectionError` is raised immediately
  AND zero `CreateDatabaseV2` or any other admin operation calls are made
- Testing Approach: Point Ledger at mock immudb that reports no `ledger` database. Assert `LedgerConnectionError` raised immediately. Assert mock recorded zero admin calls.

---

## Deferred Capabilities

**DEF-001 — Payload Schema Validation for Deferred Event Types**
- What: Validate that each event type's payload conforms to its defined schema at `append()` time
- Why Deferred: Payload schemas for 11 of 15 event types are owned by other frameworks (FMWK-002 owns `signal_delta`, FMWK-003 owns `work_order_transition`, etc.) which cannot be defined until those frameworks are authored
- Trigger to add: When a framework defines and registers its payload schema with FMWK-001
- Impact if never added: Malformed payloads accepted silently; they surface as fold errors in FMWK-002. Debugging is harder but not blocking for KERNEL phase.

**DEF-002 — Paginated Range Read**
- What: `read_range(start, end, page_size, page_token)` for large replay windows that exceed available memory
- Why Deferred: Not needed for initial Graph reconstruction (snapshot + replay of a bounded post-snapshot window)
- Trigger to add: Graph reconstruction memory usage exceeds acceptable limit in sustained operation
- Impact if never added: Large replay windows may exhaust memory. Not a KERNEL phase blocker.

---

## Success Criteria

- [ ] All P0 scenarios pass in isolation against mock immudb
- [ ] `verify_chain()` produces identical results in online and cold-storage (offline kernel) modes
- [ ] Hash chain links correctly across 1000+ sequential events
- [ ] Genesis sentinel `sha256:` + 64 zeros matches exactly (string comparison, not regex)
- [ ] `LedgerConnectionError` raised correctly on immudb unreachable (initial connect and mid-operation)
- [ ] `LedgerSequenceError` raised on sequence conflict
- [ ] `LedgerSerializationError` raised on malformed event
- [ ] Zero immudb admin operation calls in static analysis of Ledger module code
- [ ] All base event schema fields present and internally assigned (`sequence`, `previous_hash`, `hash`) — never caller-supplied
- [ ] Float prohibition confirmed: no float-type values in any stored event (decimal values are strings)

---

## Clarifications

See D6 CLR-001 (atomicity mechanism choice), CLR-002 (platform_sdk immudb adapter), CLR-003 (float representation for signal deltas).
