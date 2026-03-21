# D6: Gap Analysis — Ledger (FMWK-001)
Meta: v:1.0.0 (matches D2/D3/D4) | status:Complete | shared gaps:3 | private gaps:2 | unresolved:0 — GATE PASS

---

## Boundary Analysis

### 1. Data In — How data enters the Ledger

| Boundary | Classification | Status |
|----------|---------------|--------|
| append(event_data) call from Write Path | CONTROLLED — single caller, typed interface | RESOLVED |
| Event payload content (opaque JSON object) | PERMISSIVE — Ledger validates JSON serializability only, not payload schema | RESOLVED |
| Caller-supplied event_type must be in EventType enum | VALIDATED — Ledger rejects unknown event_types | RESOLVED |
| Caller MUST NOT supply sequence number | ENFORCED — Ledger assigns all sequence numbers | RESOLVED |
| All access must go through platform_sdk | ENFORCED — D1 Article 10 | RESOLVED |

Gaps found: None. The single-caller model (Write Path only) and the opaque payload policy are both explicitly resolved. The Ledger rejects unknown event_types and callers that pass sequence numbers.

---

### 2. Data Out — What the Ledger produces

| Boundary | Classification | Status |
|----------|---------------|--------|
| append() returns integer sequence_number | TYPED — integer ≥ 0 | RESOLVED |
| read() returns complete LedgerEvent (E-001) | TYPED — all fields | RESOLVED |
| read_range() / read_since() return [LedgerEvent] | TYPED — ordered list, may be empty | RESOLVED |
| get_tip() returns TipRecord (E-003) | TYPED — sequence_number and hash | RESOLVED |
| verify_chain() returns ChainVerificationResult (E-004) | TYPED — valid + optional break_at | RESOLVED |
| Error types raised on failure | ENUMERATED — 4 error codes in D4 | RESOLVED |

Gaps found: None. All return types are fully defined in D3 and D4.

---

### 3. Persistence — What the Ledger persists and where

| What | Where | Owned By | Status |
|------|-------|----------|--------|
| LedgerEvents (all fields) | immudb, key=zero-padded-sequence, value=canonical JSON bytes | FMWK-001 exclusively | RESOLVED |
| Snapshot files | /snapshots/<sequence>.snapshot (Docker volume) | FMWK-005 (Graph) — Ledger records snapshot_created event only | RESOLVED |
| immudb database itself | ledger_data Docker volume | Infrastructure (Docker Compose) | RESOLVED |

Gaps found: None. The Ledger owns exactly the events in immudb. Snapshot file format and content are FMWK-005's concern; the Ledger only records that a snapshot was taken (snapshot_created event with file hash).

---

### 4. Auth/Authz — Authorization boundary

| Boundary | Status |
|----------|--------|
| Caller authorization check | RESOLVED (assumed): The Ledger performs no authorization checks. All callers are trusted at the KERNEL level. Authorization is enforced at the Write Path (FMWK-002) level, which is the sole permitted caller. KERNEL frameworks operate under the assumption that the calling component is already authorized. |
| immudb credentials | RESOLVED: Config-driven via platform_sdk.tier0_core.config and platform_sdk.tier0_core.secrets. Default immudb credentials (immudb/immudb) used for local development. Production credentials are config-driven. Never hardcoded. |
| Database name | RESOLVED: Always "ledger". Config-driven (host and port are config-driven; database name is a constant). |

Gaps found: None. Auth/authz is deferred to the Write Path and the platform_sdk config/secrets modules.

---

### 5. External Services — What the Ledger depends on

| Service | Interface | Status |
|---------|-----------|--------|
| immudb | gRPC on port 3322 (config-driven), database "ledger" | RESOLVED |
| immudb admin operations | FORBIDDEN — only Set, Get, Scan, and connection operations | RESOLVED (D1 Article 4, D1 NEVER boundary) |
| platform_sdk.tier0_core.data | Ledger-to-immudb gRPC layer | RESOLVED |
| platform_sdk.tier0_core.ids | UUID v7 generation for event_id | RESOLVED |
| platform_sdk.tier0_core.config | Connection parameters (host, port, database name) | RESOLVED |
| platform_sdk.tier0_core.secrets | immudb credentials | RESOLVED |

Gaps found: None. All external service dependencies are identified and their access pattern is specified.

---

### 6. Configuration — What is config-driven

| Config Item | Source | Status |
|-------------|--------|--------|
| immudb host | platform_sdk.tier0_core.config | RESOLVED |
| immudb port | platform_sdk.tier0_core.config | RESOLVED (default: 3322) |
| immudb database name | Constant "ledger" in code | RESOLVED |
| immudb username | platform_sdk.tier0_core.secrets (default: "immudb") | RESOLVED |
| immudb password | platform_sdk.tier0_core.secrets (default: "immudb") | RESOLVED |
| Connection retry wait (1 second) | Hardcoded constant in Ledger | RESOLVED (see D5 RQ-005) |

Gaps found: None. Configuration items are identified, sourced, and do not require hardcoding of sensitive values.

---

### 7. Error Propagation — How errors flow

| Error Source | Propagation Path | Status |
|-------------|------------------|--------|
| immudb connection failure | Ledger → LedgerConnectionError → Write Path (FMWK-002) → system hard stop | RESOLVED |
| Hash chain corruption detected by verify_chain() | Ledger → LedgerCorruptionError → Package Lifecycle (FMWK-006) or CLI → operator alert | RESOLVED |
| Concurrent append (design violation) | Ledger → LedgerSequenceError → Write Path (FMWK-002) → operator alert | RESOLVED |
| Out-of-range read | Ledger → LedgerSequenceError → caller adjusts bounds | RESOLVED |
| Payload serialization failure | Ledger → LedgerSerializationError → Write Path (FMWK-002) → event rejected | RESOLVED |
| immudb unreachable during verify_chain() | LedgerConnectionError (NOT a {valid:false} result) | RESOLVED — D4 IN-005 postcondition #6 |

Gaps found: None. All error paths are enumerated in D4 ERR-001 through ERR-004. The distinction between connection failure and corruption is explicitly specified.

---

### 8. Observability — What the Ledger emits

| What | How | Status |
|------|-----|--------|
| Append errors | platform_sdk.tier0_core.logging (ERROR level) | RESOLVED (assumed — standard platform_sdk logging contract) |
| Connection retry attempts | platform_sdk.tier0_core.logging (WARN level) | RESOLVED (assumed) |
| Sequence numbers at append (for debugging) | platform_sdk.tier0_core.logging (DEBUG level) | RESOLVED (assumed) |
| Metrics (append count, error count, latency) | platform_sdk.tier0_core.metrics | RESOLVED (assumed — builder follows platform_sdk conventions) |
| Chain verification results | Returned to caller; caller decides how to surface | RESOLVED |

Gaps found: None. Observability follows the platform_sdk contract. The builder is assumed to instrument using the standard SDK modules.

---

### 9. Resource Accounting — What resources the Ledger consumes

| Resource | Accounting Method | Status |
|----------|------------------|--------|
| Disk (immudb data) | Unlimited append-only growth; Storage Management (FMWK-012) governs trimming at system level | RESOLVED — Ledger does not trim; FMWK-012 does |
| RAM | Single persistent gRPC connection + in-process event buffer (one event at a time) | RESOLVED — minimal; no caching or buffering |
| CPU | SHA-256 computation per append; canonical JSON serialization | RESOLVED — acceptable for current scale |
| gRPC connection | Single persistent connection; no pooling | RESOLVED (D5 RQ-001 rationale) |

Gaps found: None. Resource accounting is appropriate for KERNEL scale. Disk pressure management is FMWK-012's responsibility.

---

## Isolation Completeness Check

### Turn C (Holdout Agent reads D2+D4 only)

Verification that Turn C can write holdout scenarios using only D2 and D4:

| What Turn C needs | Where it is defined | Status |
|-------------------|---------------------|--------|
| GIVEN/WHEN/THEN for SC-001 through SC-011 | D2 Scenarios section | COMPLETE |
| Field schemas for append() requests | D4 IN-001 (including inline payload schemas) | COMPLETE |
| Field schemas for read() requests | D4 IN-002 | COMPLETE |
| Field schemas for read_range() requests | D4 IN-003 | COMPLETE |
| Field schemas for read_since() requests | D4 IN-004 | COMPLETE |
| Field schemas for verify_chain() requests | D4 IN-005 | COMPLETE |
| Observable postconditions for all scenarios | D4 IN-001 through IN-006 postconditions | COMPLETE |
| "No fork" operationalized | D4 IN-001 postcondition #6 | COMPLETE |
| "No partial write" operationalized | D4 IN-001 postcondition #8 | COMPLETE |
| "Unchanged tip" after failure operationalized | D4 IN-001 postcondition #8 | COMPLETE |
| "Chain intact" operationalized | D4 IN-001 postcondition #3 | COMPLETE |
| Error codes | D4 Error Code Enum | COMPLETE |
| EventType enum (for SC-001, SC-002 payload construction) | D4 EventType Enum table | COMPLETE |
| node_creation payload schema | D4 IN-001 inline payload schemas | COMPLETE |
| signal_delta payload schema | D4 IN-001 inline payload schemas | COMPLETE |
| session_start payload schema | D4 IN-001 inline payload schemas | COMPLETE |

**Isolation check verdict: PASS.** Turn C does not need to read D3, D5, D1, or any other document to write holdout scenarios for all D2 scenarios. All behavior is fully operationalized in D4.

---

### Turn D (Builder reads D10+handoff+D3+D4)

Verification that Turn D can implement the Ledger using D3 and D4:

| What Turn D needs | Where it is defined | Status |
|-------------------|---------------------|--------|
| Full entity schemas (all fields, types, constraints) | D3 E-001 through E-004 | COMPLETE |
| Canonical JSON serialization rules | D3 (Canonical JSON Serialization Constraint section) + D4 SIDE-002 | COMPLETE |
| EventType enum | D3 EventType Enum table | COMPLETE |
| Payload schemas for Ledger-owned event types | D3 (Payload Schemas section) | COMPLETE |
| Interface method contracts (request + postconditions) | D4 IN-001 through IN-006 | COMPLETE |
| immudb mapping detail | D3 note + D4 SIDE-001 | COMPLETE |
| Error types and codes | D4 ERR-001 through ERR-004 + Error Code Enum | COMPLETE |
| Architectural assumption (in-process mutex) | D5 RQ-001 Decision (D10 will include) | COMPLETE |

**Isolation check verdict: PASS.** Turn D has all schemas, contracts, and postconditions needed for implementation.

---

### D4-D3 Restatement Check

| D4 contract | D3 source | Match status |
|------------|-----------|--------------|
| IN-001 request fields (event_type, schema_version, timestamp, provenance, payload) | D3 E-001 (caller-supplied subset; Ledger-assigned fields excluded from request) | MATCHES |
| IN-001 inline node_creation payload | D3 Payload Schemas → node_creation | MATCHES |
| IN-001 inline signal_delta payload | D3 Payload Schemas → signal_delta | MATCHES |
| IN-001 inline package_install payload | D3 Payload Schemas → package_install | MATCHES |
| IN-001 inline session_start payload | D3 Payload Schemas → session_start | MATCHES |
| IN-001 inline session_end payload | D3 Payload Schemas → session_end | MATCHES |
| IN-001 inline snapshot_created payload | D3 Payload Schemas → snapshot_created | MATCHES |
| OUT-002 LedgerEvent | D3 E-001 | MATCHES |
| OUT-004 TipRecord | D3 E-003 | MATCHES |
| OUT-005 ChainVerificationResult | D3 E-004 | MATCHES |
| D4 SIDE-002 canonical JSON rules | D3 Canonical JSON Serialization Constraint | MATCHES |
| D4 EventType enum | D3 EventType enum | MATCHES |

**D4-D3 restatement check verdict: PASS.** No divergence found. D4 restates D3 definitions verbatim. No new fields added, no fields renamed, no required/optional status changed.

---

### Holdout Behavior Check

Verification that D2+D4 define pass/fail behavior tightly enough for Turn C:

| Scenario | Temporal assertions needed | Covered in D4 |
|----------|---------------------------|---------------|
| SC-001 genesis event | previous_hash must be 64zeros | D4 IN-001 postcondition #3: "or sha256+64zeros if sequence=0" |
| SC-002 chain continuation | previous_hash = hash of event N-1 | D4 IN-001 postcondition #3 |
| SC-010 failure atomicity | tip unchanged, no partial write | D4 IN-001 postcondition #8 explicit |
| SC-011 concurrent append | exactly one success, one error | D4 IN-001 constraints + ERR-003 |
| SC-007 intact chain | returns {valid:true, break_at:null} | D4 IN-005 postcondition #3 |
| SC-008 corruption | returns {valid:false, break_at:N} | D4 IN-005 postcondition #4 |
| SC-009 offline same result | CLI produces same ChainVerificationResult | D4 IN-005 postcondition #7 |

**Holdout behavior check verdict: PASS.** Turn C does not need to infer temporal assertions. All observable behaviors are operationalized.

---

## Clarification Log

### CLR-001 — Database initialization separation
- Found During: D1 (source material APPROVED decisions)
- Question: Should connect() create the immudb database if it doesn't exist?
- Options: (A) connect() creates database if missing, (B) connect() fails fast if database doesn't exist
- Status: RESOLVED
- Resolution: Option B. connect() MUST fail fast with LedgerConnectionError if the "ledger" database does not exist. Database creation is a separate bootstrap operation using CreateDatabaseV2 (the ONLY permitted admin operation). Reason: if connect() handled creation, multiple agents connecting simultaneously to a non-existent database would race on CreateDatabaseV2, potentially corrupting the immudb system catalog.
- Blocks: D4 ERR-001 (LedgerConnectionError includes "database does not exist" as a trigger condition)

### CLR-002 — get_tip() on empty Ledger
- Found During: D5 (RQ-004), D2 SC-006
- Question: What does get_tip() return when no events have been appended?
- Options: (A) raise LedgerSequenceError, (B) return sentinel TipRecord with sequence_number=-1 and hash=sha256+64zeros
- Status: RESOLVED
- Resolution: Option B. Returns TipRecord{sequence_number: -1, hash: "sha256:0000000000000000000000000000000000000000000000000000000000000000"}. This allows the Write Path to use a uniform append() implementation: next_sequence = tip.sequence_number + 1 = 0 (genesis), previous_hash = tip.hash = sha256+64zeros. Eliminates a special case in the Write Path.
- Blocks: D4 IN-006 (postcondition #2 for empty case)

### CLR-003 — Float serialization in payload
- Found During: D3 (payload schema design)
- Question: How should floating-point values (methylation, delta, base_weight) be stored in event payloads?
- Options: (A) raw JSON numbers (0.1), (B) strings ("0.1")
- Status: RESOLVED
- Resolution: Option B. All float values in payloads MUST be serialized as strings. Reason: raw JSON float numbers produce different SHA-256 hashes across language implementations due to IEEE 754 float64 representation differences. Storing as strings eliminates cross-language hash divergence. Applied to: node_creation.initial_methylation, node_creation.base_weight, signal_delta.delta, and any future payload fields containing floats.
- Blocks: D3 payload schemas, D4 IN-001 inline payload schemas, D4 SIDE-002

### CLR-004 — read_range inclusive vs exclusive bounds
- Found During: D2 SC-004 (design decision needed)
- Question: Are the start and end arguments to read_range() inclusive or exclusive?
- Options: (A) inclusive on both ends [start, end], (B) exclusive end [start, end), (C) inclusive start, exclusive end
- Status: RESOLVED
- Resolution: Option A — inclusive on both ends [start, end]. read_range(3, 7) returns events at sequences 3, 4, 5, 6, 7 (5 events). Reason: matches the most natural description for event-sourcing replay ("give me events from sequence 3 to sequence 7") and is consistent with read_since(N) which returns everything > N (so a caller can do read_since(last_known_sequence) to get new events without off-by-one errors).
- Blocks: D4 IN-003 (postcondition #1), D2 SC-004

---

## Gap Register

### GAP-001 — Deferred payload schemas for non-Ledger-owned event types
- Category: Data In (payload validation)
- What Is Needed: Type-specific payload schemas for methylation_delta, suppression, unsuppression, mode_change, consolidation, work_order_transition, intent_transition, package_uninstall, framework_install
- Existing Contract: None for these types in FMWK-001 scope
- Gap Description: These event types are written to the Ledger by frameworks other than FMWK-001. The Ledger does not validate their payload structure. The schemas must be defined in the owning frameworks' specs.
- Shared? YES — impacts FMWK-002, FMWK-003, FMWK-006, FMWK-021
- Recommendation: Each owning framework defines its payload schemas in its own D3 and D4.
- Resolution: RESOLVED — The Ledger's design explicitly accepts payload as an opaque JSON object and does not validate payload field content for these types. This is by design (D1 Article 5 — No Business Logic). The gap is not a Ledger gap; it is a forward dependency on other frameworks' specs. FMWK-001 is complete. The owning frameworks must include payload schemas in their own D3/D4.
- Impact If Unresolved: FMWK-002, FMWK-003, FMWK-006, and FMWK-021 cannot be fully built without their payload schemas. FMWK-001 is unaffected.

### GAP-002 — Snapshot file format
- Category: Persistence
- What Is Needed: The binary/serialization format of the snapshot files stored at /snapshots/<sequence>.snapshot
- Existing Contract: SOURCE_MATERIAL.md marked this OPEN
- Gap Description: The snapshot_created event's payload references the snapshot file and its hash, but the Ledger does not define the file format. The Ledger's responsibility is only to record that a snapshot was taken.
- Shared? YES — impacts FMWK-005 (Graph)
- Recommendation: FMWK-005 (Graph) defines the snapshot format in its D3 data model. The Ledger's interface does not change regardless of snapshot format.
- Resolution: RESOLVED — The snapshot file format is FMWK-005's responsibility. FMWK-001 is complete without it. The Ledger records snapshot_created events with the snapshot file's hash (which FMWK-005 computes). The Ledger's interface is unchanged.
- Impact If Unresolved: FMWK-005 cannot be implemented until its snapshot format is decided. FMWK-001 is unaffected.

### GAP-003 — Operational log format and transport
- Category: Observability
- What Is Needed: Specific log format and transport details (structured JSON fields, log level mappings, metrics schema)
- Existing Contract: OPERATIONAL_SPEC.md §Schemas Deferred explicitly defers "Operational log format and transport"
- Gap Description: The platform_sdk provides the logging contract, but specific field names and log levels for Ledger-specific events are not defined here.
- Shared? YES — affects all KERNEL frameworks
- Recommendation: Follow platform_sdk.tier0_core.logging conventions. Builder uses standard SDK log calls. Specific log schema is defined by the platform_sdk module.
- Resolution: RESOLVED (ASSUMED) — The builder follows the platform_sdk logging contract. The specific field names are determined by the SDK. This is not a blocking gap for FMWK-001 spec work.
- Impact If Unresolved: No impact on Ledger behavior. At worst, log fields are non-standard during initial build.

### GAP-004 — immudb ExecAll API availability
- Category: External Services
- What Is Needed: Confirmation that immudb's gRPC API supports ExecAll (or equivalent batch transaction) for the builder to choose Option A atomicity if desired
- Existing Contract: D5 RQ-001 resolved atomicity as Option B (in-process mutex), making this a contingency
- Gap Description: If Option B (in-process mutex) is deemed insufficient for a future multi-process deployment, the builder needs to know whether ExecAll exists in the deployed immudb version.
- Shared? NO — internal to FMWK-001 build
- Recommendation: Builder verifies immudb gRPC API version at build time. D5 RQ-001 decision (Option B) is the primary choice; immudb version check is a precaution.
- Resolution: RESOLVED (ASSUMED) — D5 RQ-001 selects Option B. The ExecAll question is informational only and does not block the spec or build. Option B is sufficient for the single-process KERNEL deployment model.
- Impact If Unresolved: No impact on the spec. At most, builder may want to note immudb version in the results file.

### GAP-005 — Turn E / Evaluator isolation completeness
- Category: Isolation boundary
- What Is Needed: Confirmation that Turn E (Evaluator reads D9+staging only) can evaluate holdout scenarios without needing D1-D6
- Existing Contract: The holdout scenarios (D9) are generated by Turn C from D2+D4
- Gap Description: The Evaluator assesses whether the builder's staged code passes the D9 holdout scenarios. The Evaluator does not need spec documents — only D9 scenarios and the staged output.
- Shared? NO
- Recommendation: Confirm that D9 scenarios are self-contained executable test cases (not references to D2/D4).
- Resolution: RESOLVED (ASSUMED) — D9 holdout scenarios are produced by the Holdout Agent from D2+D4. The spec agent's obligation is to ensure D2 and D4 are complete (which they are). The Holdout Agent produces self-contained D9 scenarios. Turn E isolation is maintained.
- Impact If Unresolved: No impact on spec. Turn C (Holdout Agent) is responsible for D9 self-containedness.

---

## Summary

| Category | Gaps Found | Shared | Resolved | Remaining |
|----------|-----------|--------|----------|-----------|
| 1. Data In | 0 | 0 | 0 | 0 |
| 2. Data Out | 0 | 0 | 0 | 0 |
| 3. Persistence | 0 | 0 | 0 | 0 |
| 4. Auth/Authz | 0 | 0 | 0 | 0 |
| 5. External Services | 0 | 0 | 0 | 0 |
| 6. Configuration | 0 | 0 | 0 | 0 |
| 7. Error Propagation | 0 | 0 | 0 | 0 |
| 8. Observability | 0 | 0 | 0 | 0 |
| 9. Resource Accounting | 0 | 0 | 0 | 0 |
| Gap Register | 5 | 3 | 5 | 0 |
| Clarifications | 4 | — | 4 | 0 |

**Gate verdict: PASS — zero open items. All 5 gaps resolved or assumed with justification. All 4 clarifications resolved. Isolation completeness checks pass for Turn C, Turn D, and Turn E. D4-D3 restatement check passes. Holdout behavior check passes. D7 may proceed.**
