# D2: Specification — FMWK-001-ledger
Meta: pkg:FMWK-001-ledger | v:1.0.0 | status:Final | author:spec-agent | sources:architecture/NORTH_STAR.md, architecture/BUILDER_SPEC.md, architecture/OPERATIONAL_SPEC.md, architecture/FWK-0-DRAFT.md, architecture/BUILD-PLAN.md, sawmill/FMWK-001-ledger/TASK.md, sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md | constitution:D1_CONSTITUTION.md

## Purpose
FMWK-001 provides the append-only, hash-chained event store that acts as the sole source of truth for DoPeJarMo state. It owns the canonical event envelope, deterministic sequence assignment, ordered replay, and mechanical chain verification so every acknowledged mutation can be replayed and validated from cold storage without relying on cognitive runtime services.

## NOT
- FMWK-001-ledger is NOT the Write Path. It does not fold events into Graph state or compute methylation.
- FMWK-001-ledger is NOT the Graph. It does not execute queries over resolved runtime state.
- FMWK-001-ledger is NOT Package Lifecycle. It does not run gates or decide install validity.
- FMWK-001-ledger is NOT infrastructure provisioning. It does not create the `ledger` database during runtime connect.
- FMWK-001-ledger is NOT a business logic engine. It does not interpret event meaning beyond envelope validation and chain integrity.

## Scenarios
### Primary
#### SC-001
- Priority: P0(blocker)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Observable hash chain behaviors"; BUILDER_SPEC.md Ledger primitive
- GIVEN an empty ledger WHEN the first event is appended THEN the ledger assigns `sequence = 0`, sets `previous_hash` to `sha256:` plus 64 zeros, computes the event hash from canonical JSON, and persists the event synchronously.
- Testing Approach: Integration test against a clean ledger plus fixture assertion on assigned sequence, previous hash, and hash format.

#### SC-002
- Priority: P0(blocker)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Sequence numbering" and "Observable hash chain behaviors"
- GIVEN a ledger with an existing tip WHEN a new event is appended THEN the ledger reads the current tip atomically, assigns the next global sequence, copies the prior event hash into `previous_hash`, computes the new hash, and persists exactly one new event.
- Testing Approach: Sequential append test with deterministic fixtures and immudb-backed persistence verification.

#### SC-003
- Priority: P1(must)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Event Schema" and "immudb Integration"
- GIVEN an append request for a supported event type WHEN the request omits ledger-owned fields THEN the ledger validates the envelope, fills ledger-owned fields, and stores a self-describing event containing event type, schema version, provenance, payload, previous hash, and computed hash.
- Testing Approach: Contract tests for request/response shape and stored event shape using minimum payload schemas for `node_creation`, `signal_delta`, `package_install`, and `session_start`.

#### SC-004
- Priority: P1(must)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "immudb Integration"
- GIVEN a stored ledger WHEN a caller requests `read`, `read_range`, or `read_since` THEN the ledger returns events in ascending sequence order without altering the stored payload bytes.
- Testing Approach: Integration test with fixture events covering single read, bounded range read, and replay-after-sequence behavior.

#### SC-005
- Priority: P1(must)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Observable hash chain behaviors" and OPERATIONAL_SPEC.md recovery sections
- GIVEN a valid ledger WHEN `verify_chain` runs online or against exported ledger data offline THEN the ledger recomputes canonical SHA-256 hashes for each event in order and returns `valid=true` when the chain is intact.
- Testing Approach: Dual-path verification test comparing online and offline results over the same exported event set.

#### SC-006
- Priority: P1(must)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "immudb Integration"
- GIVEN a non-empty ledger WHEN `get_tip` is requested THEN the ledger returns the latest sequence number and hash as the authoritative append point for the next write.
- Testing Approach: Integration test after multiple appends verifying exact latest sequence/hash pair.

#### SC-007
- Priority: P1(must)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Snapshots"
- GIVEN a snapshot reference event request WHEN a snapshot is recorded THEN the ledger stores a `snapshot_created` event whose payload contains the snapshot file hash and snapshot sequence reference, while leaving snapshot file contents to the graph-owned snapshot format.
- Testing Approach: Contract test on `snapshot_created` payload schema and replay boundary behavior using a simulated snapshot reference.

### Edge Cases
#### SC-008
- Priority: P0(blocker)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Observable hash chain behaviors" and OPERATIONAL_SPEC.md failure matrix
- GIVEN a ledger with a corrupted event WHEN `verify_chain` runs THEN the ledger returns `valid=false` and `break_at` equal to the first corrupted sequence and MUST NOT report success.
- Testing Approach: Tampered fixture test with exact break-point assertion.

#### SC-009
- Priority: P0(blocker)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Sequence numbering"
- GIVEN a concurrent append race or any tip mismatch WHEN the ledger cannot preserve a single linear next sequence THEN it rejects the append with `LedgerSequenceError` rather than creating a fork.
- Testing Approach: Concurrency or fault-injection test that forces a tip mismatch and asserts explicit rejection.

#### SC-010
- Priority: P1(must)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Database initialization" and "Connection handling"
- GIVEN the `ledger` database is absent or immudb is unreachable WHEN the ledger connects or appends THEN it fails fast with `LedgerConnectionError`, may perform one reconnect retry on disconnect, and MUST NOT provision the database during runtime.
- Testing Approach: Connection-failure integration test covering absent database, disconnect/retry-once, and final failure surface.

#### SC-011
- Priority: P1(must)
- Source: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md "Canonical JSON rules" and "Error types"
- GIVEN an event cannot be serialized under the canonical UTF-8 JSON rules WHEN append or verify requires hash input bytes THEN the ledger fails with `LedgerSerializationError` and MUST NOT persist a partial event.
- Testing Approach: Serialization failure fixture asserting no event is appended and the explicit error code is returned.

## Deferred Capabilities
### DEF-001
- What: Full payload schema catalog for event types beyond `node_creation`, `signal_delta`, `package_install`, `session_start`, and the ledger-owned snapshot reference payload.
- Why Deferred: Source material explicitly allows other payload schemas to be deferred to the frameworks that own those behaviors.
- Trigger to add: When the owning framework reaches spec/build and needs its payload contract formalized.
- Impact if never added: Cross-framework event validation remains incomplete for those event types until each owner specifies its payload.

### DEF-002
- What: Snapshot file content format.
- Why Deferred: Source material marks snapshot format OPEN and ties the decision to FMWK-005 graph needs; ledger owns only the reference event, path convention, and replay boundary.
- Trigger to add: FMWK-005 defines snapshot serialization for Graph state.
- Impact if never added: Replay can still function from full ledger replay, but snapshot loading optimization cannot be standardized.

## Success Criteria
- [ ] Ledger appends assign sequence numbers internally and never accept caller-supplied sequence values.
- [ ] First-event and next-event append behaviors produce exact `previous_hash` and sequence outcomes.
- [ ] Canonical event hashes are deterministic byte-for-byte across online and offline verification.
- [ ] `read`, `read_range`, `read_since`, `get_tip`, and `verify_chain` operate over a linear ordered event stream.
- [ ] Corruption, connection, sequence, and serialization failures surface as explicit ledger errors and do not create partial writes.
- [ ] The ledger remains verifiable from exported data without Graph, HO1, HO2, or kernel runtime services.

## Clarifications
All clarifications live in D6. Use pointers only: See D6 CLR-001, CLR-002, CLR-003.
