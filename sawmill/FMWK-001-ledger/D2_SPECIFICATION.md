# D2: Specification — Ledger (FMWK-001)
Meta: pkg:FMWK-001-ledger | v:1.0.0 | status:Final | author:spec-agent | sources:BUILDER_SPEC.md v3.0, NORTH_STAR.md v3.0, FWK-0-DRAFT.md v1.0.0, SOURCE_MATERIAL.md | constitution:D1 v1.0.0

---

## Purpose

The Ledger is the append-only, hash-chained event store for DoPeJarMo. It is the sole source of truth for all system state. Every mutation in the system is recorded as a Ledger event — node creations, signal deltas, mode changes, work order transitions, session boundaries, and package installs all enter the system as Ledger events. The in-memory Graph (FMWK-005) is derived entirely from Ledger replay: destroy the Graph, rebuild it by reading the Ledger from genesis (or from the last snapshot plus subsequent events). The Ledger provides durable, ordered, tamper-evident storage backed by immudb, with cryptographic integrity verification runnable from cold storage using only the immudb data volume and no other running services.

---

## NOT

- The Ledger is NOT a query database. It does not support filtering by payload fields, text search, aggregation, or any query beyond retrieval by sequence number or sequence range.
- The Ledger is NOT a message queue. It does not push events to consumers. Consumers pull events by sequence number via read(), read_range(), or read_since().
- The Ledger is NOT responsible for fold logic, signal accumulation, or Graph construction. It stores events; FMWK-002 (Write Path) reads them and folds them into the Graph.
- The Ledger is NOT responsible for gate validation or package lifecycle management. It stores package_install and framework_install events; FMWK-006 (Package Lifecycle) runs the gates before those events are written.
- The Ledger is NOT responsible for work order state management or orchestration. It stores work_order_transition events; FMWK-003 (Orchestration) manages the work order lifecycle.
- The Ledger is NOT responsible for creating or initializing the immudb database. Database provisioning is a bootstrap operation; the Ledger's connect() fails fast if the database does not exist.
- The Ledger is NOT a snapshot store. It records that a snapshot was taken (snapshot_created event); the snapshot files themselves are stored separately and owned by FMWK-005 (Graph).

---

## Scenarios

### Primary

#### SC-001 — Append first event (genesis)
- Priority: P0 (blocker)
- Source: SOURCE_MATERIAL.md (hash chain section), BUILDER_SPEC.md §Ledger
- GIVEN an empty Ledger (no events yet appended) WHEN append() is called with a valid node_creation event THEN the Ledger assigns sequence=0 AND sets previous_hash=sha256:0000000000000000000000000000000000000000000000000000000000000000 AND computes hash=SHA-256 of the canonical JSON (hash field excluded) AND persists the event to immudb AND returns sequence_number=0
- Testing Approach: Unit test with MockProvider. Verify sequence_number=0, previous_hash=sha256+64zeros, hash computed correctly, get_tip() returns {sequence_number:0, hash:<correct_hash>}.

#### SC-002 — Append subsequent event (chain continuation)
- Priority: P0 (blocker)
- Source: SOURCE_MATERIAL.md (hash chain section), BUILDER_SPEC.md §Ledger
- GIVEN a Ledger with N events (sequence 0 through N-1, tip.sequence_number=N-1) WHEN append() is called with a valid event THEN the Ledger assigns sequence=N AND sets previous_hash=hash_of_event_at_sequence_N-1 AND computes hash=SHA-256 of canonical JSON (hash excluded) AND persists the event AND returns sequence_number=N AND get_tip() returns {sequence_number:N, hash:<hash_of_new_event>}
- Testing Approach: Append 5 events sequentially. Verify each gets sequence 0,1,2,3,4. Verify each event's previous_hash equals the hash of the preceding event.

#### SC-003 — Read event by sequence number
- Priority: P0 (blocker)
- Source: SOURCE_MATERIAL.md (interface section)
- GIVEN a Ledger with events at sequences 0 through 10 WHEN read(5) is called THEN returns the complete LedgerEvent stored at sequence 5 with all fields: event_id, sequence=5, event_type, schema_version, timestamp, provenance, previous_hash, payload, hash
- Testing Approach: Append events, read back specific sequences, compare all fields.

#### SC-004 — Read range of events
- Priority: P1 (must)
- Source: SOURCE_MATERIAL.md (interface section)
- GIVEN a Ledger with events at sequences 0 through 10 WHEN read_range(3, 7) is called THEN returns exactly 5 events, at sequences 3,4,5,6,7 in ascending order, with all fields intact
- Testing Approach: Append 11 events, read_range(3,7), verify count=5, sequences=[3,4,5,6,7], events are in order.

#### SC-005 — Read all events since a sequence number
- Priority: P1 (must)
- Source: SOURCE_MATERIAL.md (interface section)
- GIVEN a Ledger with events at sequences 0 through 10 WHEN read_since(5) is called THEN returns exactly 5 events at sequences 6,7,8,9,10 in ascending order
- Testing Approach: Append 11 events, read_since(5), verify count=5, sequences=[6,7,8,9,10].

#### SC-006 — Get tip (latest sequence and hash)
- Priority: P0 (blocker)
- Source: SOURCE_MATERIAL.md (interface section)
- GIVEN a Ledger with events at sequences 0 through N WHEN get_tip() is called THEN returns TipRecord with sequence_number=N and hash=hash_of_event_at_sequence_N AND a subsequent append followed by get_tip() returns sequence_number=N+1
- Testing Approach: Append events, call get_tip() after each, verify sequence_number and hash match the last appended event.

---

### Edge Cases

#### SC-007 — Verify intact hash chain
- Priority: P0 (blocker)
- Source: SOURCE_MATERIAL.md (observable hash chain behaviors)
- GIVEN a Ledger with 6 events at sequences 0 through 5, no corruption WHEN verify_chain(0, 5) is called THEN returns {valid: true, break_at: null}
- Testing Approach: Append 6 clean events, verify_chain(0,5), assert result.valid=True, result.break_at=None.

#### SC-008 — Detect corruption at specific sequence
- Priority: P0 (blocker)
- Source: SOURCE_MATERIAL.md (observable hash chain behaviors)
- GIVEN a Ledger with events at sequences 0 through 9 where the event at sequence 3 has been corrupted (its stored hash no longer matches a recomputed SHA-256 of its canonical JSON) WHEN verify_chain() is called with no arguments THEN returns {valid: false, break_at: 3}
- Testing Approach: In test harness, inject a corrupted event. Call verify_chain(). Assert result.valid=False, result.break_at=3.

#### SC-009 — Offline cold-storage verification
- Priority: P0 (blocker)
- Source: SOURCE_MATERIAL.md (observable hash chain behaviors), OPERATIONAL_SPEC.md Q3, D1 Article 8
- GIVEN a Ledger with events 0 through N verified online WHEN verify_chain() is called from a CLI tool connecting directly to immudb (kernel process stopped) THEN returns the same {valid, break_at} result as the online verification
- Testing Approach: Run verify_chain() online, stop kernel, run via CLI tool, compare results.

#### SC-010 — immudb unreachable on append
- Priority: P1 (must)
- Source: SOURCE_MATERIAL.md (durability section), OPERATIONAL_SPEC.md Q4
- GIVEN immudb is unreachable (connection refused or timeout) WHEN append() is called THEN raises LedgerConnectionError AND the Ledger state is unchanged (no partial write, tip unchanged, chain intact) AND the caller receives the error immediately after one reconnect attempt
- Testing Approach: MockProvider simulates connection failure. Assert LedgerConnectionError raised. Assert get_tip() unchanged after failure.

#### SC-011 — Concurrent append attempt (design violation)
- Priority: P1 (must)
- Source: SOURCE_MATERIAL.md (sequence numbering section)
- GIVEN a single-writer architecture where concurrent append is a design violation WHEN two append() calls arrive concurrently (e.g., during a test of the in-process mutex) THEN exactly one append succeeds AND the other receives LedgerSequenceError AND the Ledger state contains exactly one new event (no fork, no duplicate sequence number, chain intact)
- Testing Approach: Concurrent append via threading in unit test. Assert exactly one success, one LedgerSequenceError, get_tip().sequence_number incremented by exactly 1.

---

## Deferred Capabilities

**DEF-001 — Snapshot file format**
- What: The binary/serialization format of snapshot files (JSON, protobuf, custom binary, etc.)
- Why Deferred: Snapshot format depends on how FMWK-005 (Graph) structures its state. The Ledger's responsibility is only to record the snapshot_created event (with file hash); the format is FMWK-005's concern.
- Trigger to add: FMWK-005 (Graph) spec is written and snapshot format is decided.
- Impact if never added: Cold replay from genesis is always required; no snapshot-based startup optimization.

**DEF-002 — Payload schemas for events owned by other frameworks**
- What: Type-specific payload schemas for: methylation_delta, suppression, unsuppression, mode_change, consolidation, work_order_transition, intent_transition, package_uninstall, framework_install
- Why Deferred: These events are owned by their respective frameworks (FMWK-002, FMWK-003, FMWK-006, FMWK-021). The Ledger accepts payload as an opaque JSON object and does not validate payload structure beyond JSON serializability.
- Trigger to add: Each owning framework writes its spec.
- Impact if never added: Those frameworks cannot be built until their payload schemas are defined.

**DEF-003 — Read performance optimization**
- What: Caching, secondary indexes, or range-read optimization for high-volume replay
- Why Deferred: Initial scale does not require it. immudb's native scan is sufficient for KERNEL build.
- Trigger to add: Replay time from genesis exceeds acceptable startup threshold (TBD operational threshold).
- Impact if never added: Startup time grows linearly with Ledger size; acceptable for early builds.

---

## Success Criteria

- [ ] append() returns monotonically increasing sequence numbers starting at 0
- [ ] Every appended event's previous_hash equals the hash of the preceding event (or 64-zero hash for genesis)
- [ ] Every appended event's hash equals SHA-256 of its canonical JSON (hash field excluded)
- [ ] read(N) returns the complete event stored at sequence N
- [ ] read_range(start, end) returns events in ascending order, inclusive bounds
- [ ] read_since(N) returns events with sequence > N in ascending order
- [ ] get_tip() returns correct sequence_number and hash of the latest event
- [ ] verify_chain() returns {valid:true} for an intact chain
- [ ] verify_chain() returns {valid:false, break_at:N} for a corrupted chain
- [ ] verify_chain() produces identical results online and offline (CLI → immudb direct)
- [ ] LedgerConnectionError raised when immudb unreachable; Ledger state unchanged
- [ ] LedgerSequenceError raised on concurrent append; no fork created
- [ ] LedgerSerializationError raised when event cannot be serialized to canonical JSON
- [ ] No immudb administrative methods callable through Ledger interface
- [ ] All unit tests pass with MockProvider (no live immudb required)

---

## Clarifications

All clarifications live in D6. Use pointers only:
- See D6 CLR-001 (database initialization separation)
- See D6 CLR-002 (get_tip on empty ledger)
- See D6 CLR-003 (float serialization in payload)
- See D6 CLR-004 (read_range inclusive vs exclusive bounds)
