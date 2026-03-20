# D2: Specification — FMWK-001-ledger
Meta: pkg:FMWK-001-ledger | v:1.0.0 | status:Final | author:Codex spec-agent | sources:AGENT_BOOTSTRAP.md; architecture/NORTH_STAR.md; architecture/BUILDER_SPEC.md; architecture/OPERATIONAL_SPEC.md; architecture/FWK-0-DRAFT.md; architecture/BUILD-PLAN.md; sawmill/FMWK-001-ledger/TASK.md; sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md | constitution:D1_CONSTITUTION.md

## Purpose
FMWK-001-ledger provides the append-only, hash-chained event store that records every governed mutation as a self-describing event and replays those events in order for audit, recovery, and Graph reconstruction. It owns event envelope shape, sequence assignment, chain integrity, ordered retrieval, and immudb-backed durability, while explicitly not owning interpretation, fold logic, graph state, or package gate behavior.

## NOT
- FMWK-001-ledger is NOT the Write Path. It does not decide what events should be written or fold them into Graph state.
- FMWK-001-ledger is NOT HO3. It does not store resolved node state, run graph queries, or compute methylation.
- FMWK-001-ledger is NOT the Package Lifecycle. It does not run gates or decide install validity.
- FMWK-001-ledger is NOT a snapshot manager. It records `snapshot_created` events but does not define snapshot file format or load snapshots into Graph state.
- FMWK-001-ledger is NOT an immudb admin surface. It does not create/delete databases during normal operation or expose reorganization APIs.

## Scenarios

### Primary

#### SC-001
- Priority: P0(blocker)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Hash Chain" and "Sequence numbering"
- GIVEN an empty Ledger WHEN the first valid event is appended THEN the Ledger assigns `sequence = 0`, sets `previous_hash` to `sha256:` plus 64 zeros, computes the canonical event hash, persists the event synchronously, and returns sequence `0`
- Testing Approach: deterministic append test against empty storage plus exact-string assertions on `sequence`, `previous_hash`, and `hash`

#### SC-002
- Priority: P0(blocker)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Sequence numbering" and "immudb Integration"
- GIVEN a Ledger with an existing tip WHEN a valid event is appended THEN the Ledger reads the current tip atomically, assigns the next global monotonic sequence, sets `previous_hash` to the prior event hash, persists exactly one new event, and returns the assigned sequence
- Testing Approach: append N ordered events, inspect returned sequences and stored `previous_hash` links, and confirm no gaps or forks appear

#### SC-003
- Priority: P1(must)
- Source: sawmill/FMWK-001-ledger/TASK.md "Owns" and sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Interface"
- GIVEN recorded Ledger events WHEN a caller requests `read`, `read_range`, or `read_since` THEN the Ledger returns events in canonical stored form and sequence order suitable for replay and Graph reconstruction
- Testing Approach: seed events, call each read contract, and compare returned event order and content against stored values

#### SC-004
- Priority: P0(blocker)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Verification" and architecture/OPERATIONAL_SPEC.md recovery sections
- GIVEN a contiguous Ledger chain WHEN `verify_chain` is invoked online or against exported Ledger data offline THEN the Ledger recomputes each hash from canonical serialization, compares against stored hashes, and returns the same validity verdict and break position in both modes
- Testing Approach: run identical verification against live-backed data and offline-exported data, then compare verdict structures

#### SC-005
- Priority: P1(must)
- Source: sawmill/FMWK-001-ledger/TASK.md "Constraints" and sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Event Schema"
- GIVEN a caller submits an event payload WHEN the Ledger accepts it THEN the stored event is self-describing and includes `event_type`, `schema_version`, provenance, payload, assigned sequence, `previous_hash`, timestamp, and computed `hash`
- Testing Approach: append representative events and validate stored envelope fields against D3 constraints and per-type payload schemas

#### SC-006
- Priority: P1(must)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Snapshots" and architecture/BUILDER_SPEC.md "Snapshotting"
- GIVEN the system creates a snapshot boundary WHEN the corresponding Ledger event is appended THEN the Ledger records a `snapshot_created` event whose payload contains snapshot metadata required for post-snapshot replay, while leaving snapshot file creation and loading to other frameworks
- Testing Approach: append a `snapshot_created` event and verify the payload schema, stored sequence continuity, and replay boundary semantics

### Edge Cases

#### SC-007
- Priority: P1(must)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Sequence numbering"
- GIVEN a concurrent append arrives during sequence assignment WHEN the next sequence cannot be reserved cleanly THEN the Ledger rejects the append with `LedgerSequenceError` and MUST NOT create a forked chain
- Testing Approach: fault-injection or concurrency test that simulates conflicting append attempts and verifies one explicit rejection with no extra event written

#### SC-008
- Priority: P1(must)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Canonical JSON rules" and "Error types"
- GIVEN an event cannot be serialized under the canonical JSON contract WHEN append is attempted THEN the Ledger returns `LedgerSerializationError` and writes nothing
- Testing Approach: submit intentionally invalid or noncanonical input and confirm error type plus unchanged tip

#### SC-009
- Priority: P1(must)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Connection handling" and architecture/OPERATIONAL_SPEC.md failure table
- GIVEN immudb is unreachable or the `ledger` database does not exist WHEN a Ledger operation is attempted THEN the Ledger performs the approved reconnect-once behavior for connection loss, otherwise fails with `LedgerConnectionError` and does not report success
- Testing Approach: disconnect/restart fault injection and missing-database startup test with explicit error assertions

#### SC-010
- Priority: P0(blocker)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Observable hash chain behaviors"
- GIVEN a stored event is corrupted WHEN `verify_chain` is run THEN the Ledger returns `valid=false` and the first failing sequence in `break_at`
- Testing Approach: corrupt one stored event in a test fixture and assert exact break position

## Deferred Capabilities

### DEF-001
- What: Full payload schemas for all event types beyond `node_creation`, `signal_delta`, `package_install`, `session_start`, and `snapshot_created`
- Why Deferred: Source material explicitly says other payload schemas can be deferred to the frameworks that own them
- Trigger to add: Owning framework reaches its spec turn and needs Ledger-canonical payload definition
- Impact if never added: Event envelope remains stable, but some event types would rely on framework-local contracts instead of complete Ledger-owned catalog coverage

### DEF-002
- What: Snapshot file format and snapshot file contents
- Why Deferred: Source material marks format OPEN and ties the choice to FMWK-005 graph needs
- Trigger to add: FMWK-005 defines snapshot load/store contract
- Impact if never added: Snapshot replay optimization remains underspecified, though base Ledger append/replay still works

### DEF-003
- What: Alternate atomic append implementation strategies beyond the approved v1 assumption
- Why Deferred: Source material lists multiple acceptable implementation options and leaves the final builder mechanism open
- Trigger to add: Performance, deployment, or concurrency requirements exceed the single-writer v1 assumption
- Impact if never added: v1 remains correct under the single-writer architecture but may need revision for future concurrency expansion

## Success Criteria
- [ ] First append stores sequence `0` with the all-zero genesis `previous_hash`
- [ ] Subsequent appends always return contiguous monotonic sequences with exact prior-hash linkage
- [ ] All stored events conform to the D3 Ledger event envelope and declared payload schemas
- [ ] `read`, `read_range`, and `read_since` return ordered stored events without interpretation or mutation
- [ ] `verify_chain` returns identical results online and offline for the same data set
- [ ] Corruption detection identifies the first failing sequence deterministically
- [ ] Connection failure, missing database, serialization failure, and sequence conflict surface the declared error types and do not alter the chain
- [ ] No Ledger contract requires callers to import immudb or pass sequence numbers

## Clarifications
All clarifications live in D6. Use pointers only: See D6 CLR-001, CLR-002, CLR-003, CLR-004.
