# D1: Constitution — Ledger (FMWK-001)
Meta: v:1.0.0 | ratified:2026-03-21 | amended:— | authority:NORTH_STAR.md v3.0, BUILDER_SPEC.md v3.0, OPERATIONAL_SPEC.md v3.0, FWK-0-DRAFT.md v1.0.0

---

## Articles

### Article 1 — Splitting Test (FWK-0 Section 3.0 mandatory)

**Rule:** The Ledger MUST be independently authorable from a spec pack and FWK-0 alone, without co-authoring any other framework.

**Why:** The decomposition standard requires that a builder agent can produce a complete framework without needing to simultaneously write another framework. If the Ledger's spec required co-authoring Write Path logic to know what to write, the boundary is wrong and the two frameworks would be secretly coupled. Independent authorability ensures the Ledger can be reviewed, upgraded, and replaced without touching FMWK-002, FMWK-005, or any other framework.

**Test:** Give a builder only the Ledger spec pack (specpack.json + D1-D6) and FWK-0. Confirm they can produce all Ledger code and tests without asking for Write Path, Graph, or Package Lifecycle spec packs. The Ledger's six interface methods (append, read, read_range, read_since, verify_chain, get_tip) are fully specifiable without any other framework's internals.

**Violations:** No exceptions. If a builder asks for another framework's spec to implement the Ledger, this is a decomposition failure and must be resolved by refining the Ledger interface before proceeding.

---

### Article 2 — Merging Test (FWK-0 Section 3.0 mandatory)

**Rule:** The Ledger MUST NOT contain capabilities that belong to a separate framework.

**Why:** Fold logic, signal accumulation, graph construction, gate validation, work order management, and snapshot format are all separate capabilities from durable ordered event storage. If the Ledger absorbed fold logic, it would need to understand event semantics — which breaks the append-only storage primitive. Each hidden capability makes the framework harder to test, upgrade, and reason about independently.

**Test:** Verify that the Ledger's implementation contains zero: (a) fold operations on event payloads, (b) Graph node construction, (c) methylation value computation, (d) gate-running logic, (e) work order state transitions. All of these belong to their respective owning frameworks (FMWK-002, FMWK-005, FMWK-006, FMWK-003).

**Violations:** No exceptions. Any detected bleed of these capabilities into the Ledger codebase is a constitutional violation requiring immediate extraction.

---

### Article 3 — Ownership Test (FWK-0 Section 3.0 mandatory)

**Rule:** The Ledger MUST have exclusive ownership of: the event store, the base event schema, the hash chain, and the canonical serialization contract.

**Why:** Shared ownership of event records or schemas between frameworks creates hidden coupling. If Write Path or Graph could write to immudb directly, or redefine what a LedgerEvent looks like, the Ledger's integrity guarantees break down. Ownership exclusivity ensures that all system state traces through one accountable point.

**Test:** Confirm that (a) no other framework imports immudb directly, (b) no other framework defines or modifies the base LedgerEvent schema fields, (c) all event writes go through the Ledger's append() interface, (d) the canonical JSON serialization rule is defined in D4 SIDE-002 and enforced only by the Ledger.

**Violations:** No exceptions. Direct immudb access by any component other than the Ledger is an architectural violation. Discovered violations require immediate refactoring.

---

### Article 4 — Append-Only Immutability

**Rule:** The Ledger MUST NEVER delete, modify, overwrite, or truncate any event once appended.

**Why:** DoPeJarMo's core operational invariant states that the entire governed filesystem can be validated against the Ledger from cold storage with no runtime services. This is only possible if the Ledger is an immutable record. Any mutation of existing events destroys the ability to replay, audit, and validate. "Can't forget" and "can't drift" are only true if history cannot be rewritten.

**Test:** Attempt to overwrite event at sequence 5. Confirm that no immudb method allows this (immudb's append-only design enforces this at the storage level). Confirm the Ledger module does not expose any method that calls DatabaseDelete, DropDatabase, CompactIndex, TruncateDatabase, CleanIndex, or any immudb method that reorganizes existing data.

**Violations:** No exceptions. Any exposed deletion or modification capability is an immediate architectural violation regardless of who requests it.

---

### Article 5 — No Business Logic

**Rule:** The Ledger MUST NOT execute business logic. It stores events. It does not interpret, transform, filter, route, or accumulate them.

**Why:** The Ledger's job is storage, not interpretation. If the Ledger starts interpreting signal_delta events to compute methylation values, it has absorbed Write Path logic. If it starts filtering events by payload content, it has absorbed query logic that belongs in the Graph. Every piece of logic added to the Ledger makes it harder to rebuild the Graph from a clean replay — because now the replay output depends on Ledger-internal state that may differ from what a pure event log would produce.

**Test:** Confirm that the Ledger's six methods (append, read, read_range, read_since, verify_chain, get_tip) contain zero: payload field inspection beyond JSON validity, methylation computation, graph node creation, event routing, or business-rule evaluation.

**Violations:** No exceptions. Business logic that has crept into the Ledger must be extracted to the appropriate owning framework.

---

### Article 6 — Self-Describing Events

**Rule:** Every event MUST carry its event_type, schema_version, and provenance (framework_id, actor). No event may omit these fields.

**Why:** Self-describing events make the Ledger readable from cold storage without any runtime context. An audit tool, recovery tool, or future framework can inspect any event and know what it is, who wrote it, and what schema version it uses — without querying any running service. This is the property that makes Ledger-based validation tractable across system upgrades.

**Test:** Read 10 random events from a running Ledger. Confirm every event has non-null event_type (valid enum value), schema_version (semver string), and provenance with framework_id and actor. Attempt to append an event missing any of these fields. Confirm LedgerSerializationError is raised.

**Violations:** No exceptions. Events with missing required fields must be rejected at append time, not silently stored.

---

### Article 7 — Hash Chain Integrity

**Rule:** Every event MUST contain the SHA-256 hash of the preceding event in previous_hash, and MUST store the SHA-256 hash of its own canonical JSON (hash field excluded) in hash.

**Why:** The hash chain provides tamper detection without requiring a trusted third party. If any event is modified after writing, the hash chain breaks at that sequence number and verify_chain() will detect it. This is the cryptographic backbone of "can't drift" — the operator can always validate that the system's recorded history is exactly what was written.

**Test:** Append 10 events. Call verify_chain(). Confirm {valid: true}. Manually modify one event's payload in immudb (if possible in test harness). Call verify_chain(). Confirm {valid: false, break_at: modified_sequence}. Confirm genesis event has previous_hash = sha256: + 64 lowercase hex zeros.

**Violations:** No exceptions. Events that fail hash chain validation indicate corruption. The system must stop and alert the operator.

---

### Article 8 — Cold-Storage Verifiability

**Rule:** The hash chain MUST be verifiable from the Ledger data file alone, with no running services other than immudb.

**Why:** The core operational invariant requires that the entire governed filesystem can be validated with no cognitive runtime — no Graph, no HO1, no HO2, no LLM. The Ledger's verify_chain() must be callable from the command-line package tools that connect directly to immudb. If verification required a running kernel, the operator could be locked out in the exact scenario where they most need verification (kernel down after a crash).

**Test:** Stop the kernel process. Run the CLI tools' verify_chain against immudb directly. Confirm the same verification result as when the kernel is running. Confirm no kernel process is required for the CLI tools to connect to immudb on port 3322.

**Violations:** No exceptions. Any implementation that requires the kernel to be running for hash chain verification violates this article.

---

### Article 9 — immudb Abstraction

**Rule:** The Ledger MUST abstract over immudb completely. Callers MUST NOT interact with immudb directly. The Ledger MUST NOT expose immudb internals through its interface.

**Why:** The Ledger's interface (six methods) is stable. immudb's gRPC API is an implementation detail. If callers import immudb libraries directly, changing the backing store (or even the immudb API version) requires changes across the entire system. The abstraction ensures the Ledger can be upgraded, swapped, or extended without changing any caller.

**Test:** Grep all non-Ledger framework code for immudb imports. Confirm zero occurrences. Confirm the Ledger's public interface contains no immudb-specific types (no ImmudbClient, no gRPC stub types, no immudb response objects).

**Violations:** No exceptions. Direct immudb imports outside the Ledger module are architectural violations regardless of urgency.

---

### Article 10 — Platform SDK Contract

**Rule:** ALL immudb access within the Ledger MUST go through platform_sdk. The Ledger MUST NOT import immudb gRPC libraries directly.

**Why:** AGENT_BOOTSTRAP.md states: "Any concern covered by platform_sdk MUST be satisfied through platform_sdk. No app, service, or agent may re-implement these concerns directly." This is the enforced architectural contract for all frameworks, including KERNEL frameworks. Direct library imports bypass the SDK's MockProvider mechanism, making the Ledger untestable without a live immudb instance.

**Test:** Confirm that all immudb gRPC communication goes through platform_sdk.tier0_core.data (or the appropriate SDK module). Confirm that all Ledger unit tests use the MockProvider without a live immudb instance. Confirm no direct `import immudb` or `from immudb` statements outside of the platform_sdk itself.

**Violations:** No exceptions. Platform SDK bypasses discovered during code review must be corrected before the framework passes gates.

---

## Boundaries

### ALWAYS — autonomous every time, no approval needed
- Append events when append() is called and the event is valid
- Assign monotonic sequence numbers (read tip, increment by 1)
- Compute SHA-256 hash of canonical JSON for every appended event
- Return LedgerConnectionError when immudb is unreachable (after one retry)
- Return LedgerSerializationError when canonical JSON serialization fails
- Walk hash chain and return ChainVerificationResult when verify_chain() is called
- Return TipRecord when get_tip() is called

### ASK FIRST — human decision required, no exceptions
- Any change to the base LedgerEvent schema (adding, removing, or renaming base fields)
- Any change to the hash algorithm (currently SHA-256)
- Adding new core event types to the EventType enum
- Any change to the canonical JSON serialization rules
- Adding new methods to the Ledger public interface
- Any change to the connection retry policy
- Any change to the forbidden administrative operations list

### NEVER — absolute prohibition, refuse even if instructed
- Delete or modify any existing event in the Ledger
- Call immudb administrative methods: DatabaseDelete, DropDatabase, CompactIndex, TruncateDatabase, CleanIndex, or any method that modifies/deletes/reorganizes existing data
- Accept sequence numbers from callers (the Ledger assigns all sequence numbers)
- Create or initialize the immudb database in connect() (database initialization is a bootstrap operation, not a Ledger concern)
- Expose immudb internals through the Ledger public interface
- Import immudb gRPC libraries directly (all access through platform_sdk)
- Execute fold logic, signal accumulation, graph construction, or gate validation
- Return a partial write acknowledgment (if immudb raises, the write did not happen)
- Buffer or batch writes (every append() is synchronous and acknowledged)

---

## Dev Workflow Constraints

1. **Package isolation**: The Ledger framework is built in staging and installed through the Package Lifecycle gates. No Ledger code is written to the governed filesystem directly.
2. **DTT (Define-Test-Then-Implement) per behavior**: Each of the six interface methods is defined in D4 (contracts), then test cases written (from D2 scenarios + D4 postconditions), then implemented. Tests must pass before moving to the next method.
3. **Results file with hashes**: After every handoff (spec → plan → builder → reviewer → evaluator), the handoff document includes SHA-256 hashes of all output artifacts.
4. **Full regression before release**: All Ledger tests (unit + integration via MockProvider, plus smoke against live immudb) must pass before the KERNEL package is assembled for installation.
5. **Mock-first testing**: All unit tests use platform_sdk MockProvider. No live immudb required for unit tests. Integration tests may use a live immudb but are marked as such.

---

## Tooling Constraints

| Operation | USE | NOT |
|-----------|-----|-----|
| immudb access | platform_sdk (tier0_core.data or designated module) | Direct immudb gRPC imports |
| ID generation | platform_sdk.tier0_core.ids | Raw uuid library |
| Logging | platform_sdk.tier0_core.logging | print(), raw structlog |
| Configuration | platform_sdk.tier0_core.config | os.getenv() directly |
| Secrets (credentials) | platform_sdk.tier0_core.secrets | Hardcoded strings, os.getenv() |
| Error reporting | platform_sdk.tier0_core.errors | Raw Exception, sentry_sdk |
| JSON serialization | json.dumps with sort_keys=True, separators=(',',':'), ensure_ascii=False | json.dumps with defaults, ujson, orjson (unless byte-identical to reference) |
| Hash computation | hashlib.sha256 (stdlib) | External crypto libraries |
| Sequence assignment | Internal Ledger tip-read + increment | Caller-provided sequence numbers |
