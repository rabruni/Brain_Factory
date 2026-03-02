# D6: Gap Analysis — FMWK-001-ledger
Meta: v:1.0.0 (matches D2/D3/D4) | status:Complete | shared gaps:3 | private gaps:1 | unresolved:0 — GATE READY

---

## Boundary Analysis

### 1. Data In — How Data Enters the Ledger

| Boundary | Classification | Status |
|----------|---------------|--------|
| `append()` event base fields | D4 IN-001 | RESOLVED — full schema in D3 E-001, constraints in D4 IN-001 |
| Caller-supplied `sequence`, `previous_hash`, `hash` | D4 IN-001 constraints | RESOLVED — caller MUST NOT supply these; Ledger assigns |
| Payload schemas for `node_creation`, `session_start/end`, `package_install`, `snapshot_created` | D3 E-005, E-006, E-007, E-008 | RESOLVED — defined in this spec |
| Payload schemas for 10 deferred event types | Not defined in FMWK-001 | GAP-1 — deferred to owning frameworks |
| Float-type values in payload | D4 SIDE-002, D1 NEVER | RESOLVED — prohibited; `LedgerSerializationError` on detection |
| `connect()` credentials | D4 IN-007 | RESOLVED — platform_sdk.tier0_core.secrets, never hardcoded |

Gaps found: GAP-1

---

### 2. Data Out — What the Ledger Produces

| Boundary | Classification | Status |
|----------|---------------|--------|
| `append()` return — sequence_number | D4 OUT-001 | RESOLVED |
| `read()` return — full LedgerEvent | D4 IN-002 | RESOLVED — returned as stored, no transformation |
| `read_since()` return — ordered event list | D4 IN-004, OUT-002 | RESOLVED — strict ascending sequence, no gaps |
| `verify_chain()` return — VerifyChainResult | D4 IN-005, OUT-003, D3 E-004 | RESOLVED |
| `get_tip()` return — LedgerTip | D4 IN-006, OUT-004, D3 E-003 | RESOLVED |
| Empty ledger tip representation | D4 IN-006 | RESOLVED — `{sequence_number: -1, hash: ""}` |

Gaps found: None

---

### 3. Persistence

| What | Where | Owned By | Status |
|------|-------|----------|--------|
| Event data | immudb / ledger_data Docker volume | FMWK-001 (via platform_sdk) | RESOLVED |
| Snapshot files (content) | /snapshots/<seq>.snapshot | FMWK-005 (format), FMWK-001 (event that records it) | GAP-2 — format deferred to FMWK-005; Ledger's payload schema (E-005) is format-agnostic |
| Event ordering key in immudb | 12-digit zero-padded decimal string | FMWK-001 | RESOLVED — see D5 RQ-006 |

Gaps found: GAP-2

---

### 4. Auth/Authz

| Boundary | Status |
|----------|--------|
| immudb credentials for local dev | RESOLVED — default immudb/immudb, config-driven via platform_sdk.config |
| immudb credentials for production | RESOLVED — platform_sdk.tier0_core.secrets; never hardcoded |
| Authorization boundary for `append()` callers | GAP-3 — resolved by architectural assumption (Docker network boundary) |
| Authorization for `verify_chain()` (CLI tools) | RESOLVED — any caller with immudb :3322 access; no JWT required for read-only verification |

Gaps found: GAP-3

---

### 5. External Services

| Service | Interface | Status |
|---------|-----------|--------|
| immudb | gRPC :3322, via platform_sdk.tier0_core.data | RESOLVED — abstracted through platform_sdk; never imported directly |
| platform_sdk.tier0_core.data | Module import | ASSUMED — see D6 CLR-002 for resolution |
| immudb admin gRPC (CreateDatabaseV2) | Forbidden (GENESIS only) | RESOLVED — prohibited in D1 Article 9 and D1 NEVER; zero calls from FMWK-001 |

Gaps found: None (CLR-002 assumed)

---

### 6. Configuration

| Config Item | Source | Status |
|-------------|--------|--------|
| immudb host | platform_sdk.tier0_core.config | RESOLVED |
| immudb port (default 3322) | platform_sdk.tier0_core.config | RESOLVED |
| immudb database name (default "ledger") | platform_sdk.tier0_core.config | RESOLVED |
| immudb username | platform_sdk.tier0_core.secrets | RESOLVED |
| immudb password | platform_sdk.tier0_core.secrets | RESOLVED |
| Reconnect delay (1 second) | Hardcoded in Ledger module | RESOLVED — specified in SOURCE_MATERIAL.md; not config-driven (intentional) |

Gaps found: None

---

### 7. Error Propagation

| Error Source | Propagation Path | Status |
|-------------|-----------------|--------|
| immudb gRPC failure (connect or mid-operation) | → LedgerConnectionError → caller → system hard-stop (OPERATIONAL_SPEC Q4) | RESOLVED — D4 ERR-001 |
| Hash chain mismatch (verify_chain) | → LedgerCorruptionError → caller → operator investigation | RESOLVED — D4 ERR-002 |
| Sequence conflict (concurrent write) | → LedgerSequenceError → fatal, not retried | RESOLVED — D4 ERR-003 |
| Float or unserializable type in event | → LedgerSerializationError → caller fixes event | RESOLVED — D4 ERR-004 |
| immudb unreachable at connect() with missing database | → LedgerConnectionError (immediate) | RESOLVED — D4 IN-007, D2 SC-EC-004 |
| D2 SC-EC-001 (corrupt event in chain) | → LedgerCorruptionError with break_at | RESOLVED — D4 ERR-002 covers this |
| D2 SC-EC-002 (concurrent write) | → LedgerSequenceError | RESOLVED — D4 ERR-003 covers this |
| D2 SC-EC-003 (connection lost mid-append) | → SIDE-003 reconnect → LedgerConnectionError if retry fails | RESOLVED — D4 SIDE-003, ERR-001 |
| D2 SC-EC-004 (missing database on connect) | → LedgerConnectionError immediately | RESOLVED — D4 IN-007, ERR-001 |

Gaps found: None

**D4 Self-Check (required after D4):** All D2 edge case scenarios have corresponding D4 error contracts:
- SC-EC-001 → ERR-002 ✓
- SC-EC-002 → ERR-003 ✓
- SC-EC-003 → ERR-001 + SIDE-003 ✓
- SC-EC-004 → ERR-001 + IN-007 ✓

---

### 8. Observability

| What | How | Status |
|------|-----|--------|
| Every `append()` call | Log via platform_sdk.tier0_core.logging | ASSUMED — builder follows SDK conventions |
| Every `verify_chain()` call | Log start, end, result via platform_sdk.tier0_core.logging | ASSUMED |
| LedgerConnectionError events | Log + platform_sdk.tier0_core.errors capture | ASSUMED |
| LedgerCorruptionError events | Log + platform_sdk.tier0_core.errors capture (critical) | ASSUMED |
| Ledger event count (cumulative) | platform_sdk.tier2_reliability metrics | GAP-4 — specific metric names not defined |
| immudb connection health | platform_sdk.tier2_reliability.health | GAP-4 — health probe not defined |
| Append latency | platform_sdk.tier2_reliability metrics | GAP-4 — metric name not defined |

Gaps found: GAP-4

---

### 9. Resource Accounting

| Resource | Accounting Method | Status |
|----------|------------------|--------|
| Disk (immudb / ledger_data volume) | Grows append-only; trimmed by FMWK-012 (Storage Management) using methylation values | RESOLVED — FMWK-012 owns trimming; Ledger is never deleted from directly |
| gRPC connection count | Single persistent connection; no pool | RESOLVED |
| Memory (read operations) | Bounded by event count × event size in `read_since()` and `read_range()` | PARTIAL — DEF-002 (pagination) covers the large-range risk; acceptable for KERNEL phase |
| CPU (hash computation) | O(1) per append; O(N) for verify_chain over N events | RESOLVED — no concern at KERNEL scale |

Gaps found: None (DEF-002 covers the memory partial)

---

## Gap Register

**GAP-1: Payload schemas for 10 deferred event types**
- Category: Data In
- What Is Needed: Payload schemas for `signal_delta`, `methylation_delta`, `suppression`, `unsuppression`, `mode_change`, `consolidation`, `work_order_transition`, `intent_transition`, `package_uninstall`, `framework_install`
- Existing Contract: NONE — these payload schemas are not defined in FMWK-001
- Gap Description: SOURCE_MATERIAL.md directs the spec agent to define 4 payload schemas (node_creation, session, package_install, snapshot_created). The remaining 10 are owned by the frameworks that produce them. FMWK-001 validates only the base schema at `append()` time; payload validation is pluggable (DEF-001).
- Shared? YES — affects FMWK-002, FMWK-003, FMWK-004, FMWK-006, FMWK-021
- Recommendation: Each framework that owns an event type defines its payload schema in its own D3 and registers it with FMWK-001 for validation when DEF-001 is implemented.
- Resolution: RESOLVED — deferred via DEF-001. FMWK-001 validates base schema only. Owning frameworks validate payload shape. No action needed in FMWK-001 beyond defining the payload validation extension point.
- Impact If Unresolved: Malformed payloads accepted silently; they surface as fold errors in FMWK-002. Not blocking for KERNEL phase build and test.

**GAP-2: Snapshot file format**
- Category: Persistence
- What Is Needed: Format definition for `/snapshots/<seq>.snapshot` file contents
- Existing Contract: SOURCE_MATERIAL.md §Snapshots explicitly marks this OPEN, deferred to FMWK-005
- Gap Description: The Ledger records that a snapshot occurred (snapshot_created event with E-005 payload). The format of the file content is outside FMWK-001's ownership. FMWK-005 must define it before snapshot round-trip tests can pass.
- Shared? YES — FMWK-001 (event recording) + FMWK-005 (file format) must agree on what the snapshot_hash covers
- Recommendation: FMWK-005 defines snapshot format in its D3. FMWK-001's E-005 payload schema is format-agnostic — it stores path + hash regardless of format.
- Resolution: ASSUMED — FMWK-001's E-005 payload schema is format-agnostic. The Ledger records what FMWK-005 provides. No blocking dependency on format definition for FMWK-001 implementation. FMWK-005 must define format before end-to-end snapshot tests pass.
- Impact If Unresolved: FMWK-001 can be built and tested without knowing snapshot format. End-to-end snapshot validation requires FMWK-005's format decision.

**GAP-3: Authorization boundary for append() callers**
- Category: Auth/Authz
- What Is Needed: Specification of which callers are authorized to call `append()` and how the Ledger enforces this
- Existing Contract: D4 IN-001 lists callers as "FMWK-002, FMWK-006, kernel infrastructure" — the term "authorized" is undefined at the Ledger layer
- Gap Description: BUILDER_SPEC.md states HO1 is "the sole agent-level entry point for the Write Path" — but the Ledger has no visibility into HO1 identity. The question: does the Ledger enforce caller identity, or rely on architectural controls?
- Shared? YES — architectural boundary between FMWK-001 and FMWK-002
- Recommendation: The Ledger does not enforce caller identity. Authorization is enforced architecturally: immudb is accessible only from within the Docker network (kernel container connects via gRPC; external callers cannot reach :3322 per OPERATIONAL_SPEC Q8). Application-level caller identity would require JWT validation inside the Ledger, coupling it to Zitadel — that coupling is wrong for a storage primitive.
- Resolution: ASSUMED — Ledger trusts all callers reaching it via platform_sdk. Network boundary (Docker bridge) enforces who can connect. This matches OPERATIONAL_SPEC Q8 network posture. Zero caller identity check in FMWK-001 code.
- Impact If Unresolved: No impact on FMWK-001 implementation. The boundary is architectural, not code-level. A future multi-tenant scenario would require revisiting, but that is explicitly out of scope for KERNEL phase.

**GAP-4: Observability specifics (metric names, health probe definition)**
- Category: Observability
- What Is Needed: Specific metric names for append count / verify duration / connection health, and health probe field definitions
- Existing Contract: platform_sdk provides the health and metrics modules; specific names not defined in SOURCE_MATERIAL.md
- Gap Description: The Ledger should expose at minimum: (a) `ledger_append_total` counter, (b) `ledger_verify_chain_duration_seconds` histogram, (c) immudb connection health in `/health` response. These are not defined in the source material.
- Shared? NO — internal to FMWK-001
- Recommendation: Builder defines metric names and health probe following platform_sdk conventions. Suggest standard naming: `dopejarmo_ledger_append_total`, `dopejarmo_ledger_verify_seconds`. No spec-level decision needed.
- Resolution: ASSUMED — builder uses platform_sdk.tier0_core.logging and platform_sdk.tier2_reliability per SDK conventions. Metric names follow SDK naming patterns. No blocking dependency.
- Impact If Unresolved: Observability works but metrics may not align with any monitoring configuration. Acceptable for KERNEL phase.

---

## Clarification Log

**CLR-001: Atomicity mechanism for read-tip-then-write-event**
- Found During: D4 (IN-001 constraints), D5 (RQ-001)
- Question: Which atomicity option should the builder implement for `append()`? Option A (immudb ExecAll), Option B (in-process mutex), or Option C (VerifiedSet)?
- Options:
  - A: immudb ExecAll — server-side transaction; future-proof; immudb-version-dependent
  - B: In-process mutex — simplest; sufficient for single-writer design; no immudb version dependency
  - C: VerifiedSet — cryptographic guarantee; highest latency
- Status: RESOLVED — ASSUMED: Option B (in-process mutex). Rationale: BUILDER_SPEC.md declares single-writer architecture — exactly one caller (FMWK-002 Write Path) invokes `append()` concurrently. An in-process mutex is sufficient and eliminates immudb API version risk. If multi-writer scenarios arise, migration to Option A is the path. D1 Article 6 mandates `LedgerSequenceError` as the catch — mutex failure is detectable.
- Blocks: D7, D8 (builder must implement chosen mechanism in `append()`)

**CLR-002: platform_sdk.tier0_core.data support for immudb**
- Found During: D5 (RQ-004)
- Question: Does platform_sdk.tier0_core.data currently expose an immudb adapter, or must one be added?
- Options:
  - A: platform_sdk already wraps immudb gRPC — builder imports from platform_sdk as-is
  - B: platform_sdk wraps a generic KV store interface — immudb is one implementation; builder adds immudb adapter
  - C: platform_sdk does not yet support immudb — builder adds immudb adapter following SDK patterns (Protocol + MockProvider + RealProvider)
- Status: RESOLVED — ASSUMED: The builder adds an immudb adapter to platform_sdk.tier0_core.data as part of the FMWK-001 implementation work, following platform_sdk patterns (Protocol interface + MockProvider + RealProvider selected via environment variable). FMWK-001 then imports from platform_sdk. FMWK-001 never imports immudb directly regardless of which option is true.
- Blocks: D7 (builder needs to know the import path and whether adapter work is in scope)

**CLR-003: Decimal representation for signal delta values**
- Found During: D3 (E-001 invariants), D5 (RQ-005)
- Question: Signal deltas are small decimal increments (e.g., +0.05). Must they be strings in payload fields?
- Options:
  - A: All decimal values in all event fields are strings — consistent cross-language behavior
  - B: Integers only for deltas — simpler serialization, no decimal precision needed
  - C: Floats allowed in payload fields (but not base fields) — risk of cross-language drift
- Status: RESOLVED — Option A (strings for all decimal values universally, including signal delta payloads). Cross-language hash chain verification is a hard requirement (D1 Article 8). Float-to-string algorithms differ across Python, Go, JS. String representation is the only safe, deterministic choice. This ruling applies to FMWK-002's payload schemas for signal_delta events — they MUST serialize delta values as strings.
- Blocks: FMWK-002 D3/D4 (must comply with this ruling when defining signal_delta payload schema)

---

## D1 ↔ D2 Self-Check

**After D2, verify "What it is NOT" matches D1 NEVER boundaries:**

| D2 NOT | D1 NEVER / Boundary |
|--------|-------------------|
| NOT a query engine (no filter/sort/search) | D1 NEVER: call admin ops; D1 Article 2: no capabilities beyond store |
| NOT a message queue (no pub/sub) | D1 Article 2 (MERGING): no queue capability |
| NOT for arbitrary data | D1 Article 3 (OWNERSHIP): events only, with mandatory base fields |
| NOT responsible for interpreting events | D1 NEVER: interpret events; D1 Article 2: fold logic is FMWK-002 |
| NOT the Graph | D1 Article 2: Graph is FMWK-005 |
| NOT responsible for snapshot format | D1 Article 2/3: snapshot format is FMWK-005 |

All D2 NOT items are covered by D1 NEVER or D1 Article 2/3. ✓

**After D4, verify error contracts cover all D2 edge case scenarios:**

| D2 Scenario | D4 Error Contract |
|-------------|------------------|
| SC-EC-001 (corrupt hash) | ERR-002 LedgerCorruptionError ✓ |
| SC-EC-002 (concurrent write) | ERR-003 LedgerSequenceError ✓ |
| SC-EC-003 (connection lost mid-append) | ERR-001 + SIDE-003 reconnect ✓ |
| SC-EC-004 (connect to missing database) | ERR-001 + IN-007 immediate fail ✓ |

All D2 edge cases have D4 coverage. ✓

**After D6, verify all boundary walks have corresponding D4 contracts:**

| D6 Boundary Category | D4 Coverage |
|---------------------|-------------|
| Data In (append inputs) | IN-001, IN-007 ✓ |
| Data Out (all return shapes) | OUT-001, OUT-002, OUT-003, OUT-004 ✓ |
| Persistence (immudb write) | SIDE-001 ✓ |
| Auth/Authz (assumed architectural) | IN-007 (credentials) ✓ |
| External Services (immudb) | SIDE-001, SIDE-003, IN-007 ✓ |
| Configuration | IN-007 ✓ |
| Error Propagation | ERR-001, ERR-002, ERR-003, ERR-004 ✓ |
| Observability | ASSUMED (no D4 contract needed — SDK convention) ✓ |
| Resource Accounting | SIDE-001 (synchronous), DEF-002 (large reads) ✓ |

All boundary walks have D4 coverage. ✓

---

## Summary

| Category | Gaps Found | Shared | Resolved | Remaining |
|----------|-----------|--------|----------|-----------|
| Data In | 1 (GAP-1) | 1 | 1 | 0 |
| Data Out | 0 | 0 | 0 | 0 |
| Persistence | 1 (GAP-2) | 1 | 1 | 0 |
| Auth/Authz | 1 (GAP-3) | 1 | 1 | 0 |
| External Services | 0 | 0 | 0 | 0 |
| Configuration | 0 | 0 | 0 | 0 |
| Error Propagation | 0 | 0 | 0 | 0 |
| Observability | 1 (GAP-4) | 0 | 1 | 0 |
| Resource Accounting | 0 | 0 | 0 | 0 |
| **Total** | **4** | **3** | **4** | **0** |

**Gate Verdict: PASS — zero open items. All 4 gaps are RESOLVED or ASSUMED with justification. All 3 CLRs are RESOLVED with documented rationale. D6 is gate-ready.**
