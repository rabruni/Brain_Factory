# D1: Constitution — FMWK-001-ledger
Meta: v:1.0.0 | ratified:2026-03-01 | amended:— | authority:NORTH_STAR.md v3.0, BUILDER_SPEC.md v3.0, OPERATIONAL_SPEC.md v3.0, FWK-0-DRAFT.md v0.2

---

## Articles

### Article 1: SPLITTING — Independent Authorship
**Rule:** The Ledger MUST be independently authorable from its spec pack and FWK-0 alone, with zero requirement to co-author FMWK-002, FMWK-003, FMWK-004, FMWK-005, or FMWK-006 simultaneously.

**Why:** The KERNEL build plan requires concurrent builders on independent frameworks. If the Ledger builder must coordinate with the Write-Path builder to resolve an ambiguity, the two frameworks are not truly independent and the decomposition is wrong. Independent authorship is the prerequisite for the dark factory model to function.

**Test:** Run FMWK-001 gate validation with only FMWK-000 installed. All gates pass without any other KERNEL framework present. The builder's context window contains only the FMWK-001 spec pack and FWK-0 — no other framework's spec material is required to produce a complete, gate-passing artifact.

**Violations:** No exceptions. Any authoring dependency on another KERNEL framework is a decomposition failure — resolve by adjusting the boundary, not by expanding scope.

---

### Article 2: MERGING — Single Capability
**Rule:** The Ledger MUST NOT contain capabilities that belong to another framework. Fold logic, signal accumulation, gate validation, Graph update logic, work order management, and snapshot format are all prohibited. The Ledger stores events. Period.

**Why:** If the Ledger absorbs fold logic, it couples to the Write Path. If it absorbs gate logic, it couples to Package Lifecycle. Each coupling creates a shared surface that makes isolated testing impossible and creates cascading failure modes. The decomposition standard requires capability boundaries to be clean.

**Test:** Static analysis of all FMWK-001 code confirms zero imports of FMWK-002, FMWK-003, FMWK-004, FMWK-005, or FMWK-006 interfaces. Only FMWK-000 schema references are permitted. Any other cross-framework import is a build failure.

**Violations:** No exceptions. If a needed capability appears to belong elsewhere, flag in D6 before implementing.

---

### Article 3: OWNERSHIP — Exclusive Data Authority
**Rule:** No framework other than FMWK-001 MUST define, modify, or extend the event base schema, hash chain structure, or sequence numbering convention. Other frameworks define their payload schemas within the envelope FMWK-001 owns.

**Why:** Shared schema ownership creates silent incompatibilities. If FMWK-002 defines a field on the base event, FMWK-001 cannot validate it and the hash chain becomes unverifiable by Ledger-only tools. The base schema must have exactly one owner for cold-storage verification to remain possible.

**Test:** Grep all non-FMWK-001 files for definitions of `event_id`, `previous_hash`, `sequence`, `schema_version`, or `hash` as base schema fields. Zero matches permitted. Payload schemas defined by other frameworks are referenced through declared interfaces, never inlined into the base schema.

**Violations:** No exceptions. Other frameworks declare payload schemas through D4 interface contracts that the Ledger consumes at event validation time.

---

### Article 4: APPEND-ONLY IMMUTABILITY
**Rule:** The Ledger MUST NOT expose or call any immudb administrative operation that modifies, deletes, reorganizes, or truncates existing event data. Every append is permanent.

**Why:** Immutability is the foundation of DoPeJarMo's truth contract. If the Ledger can delete events, the Graph cannot be reliably rebuilt from Ledger replay, provenance chains break, and cold-storage verification becomes impossible. Every framework in the system depends on this invariant — a single delete corrupts truth for all downstream consumers. The NORTH_STAR Principle 5 ("Projection must be reversible") depends on this being absolute.

**Test:** Static analysis confirms zero calls to `DatabaseDelete`, `DropDatabase`, `CompactIndex`, `TruncateDatabase`, `CleanIndex`, or any immudb method that modifies existing data. This check MUST be a build gate failure, not a warning.

**Violations:** No exceptions. Not for storage pressure (addressed by FMWK-012 Storage Management via governed Ledger events, never direct deletion), not for correcting mistakes, not for administrative convenience.

---

### Article 5: DETERMINISTIC HASH CHAIN
**Rule:** Every appended event MUST include `previous_hash` = `sha256:<64 lowercase hex chars>` computed as SHA-256 of the preceding event's canonical JSON with the `hash` field excluded. The genesis event's `previous_hash` MUST be exactly `sha256:0000000000000000000000000000000000000000000000000000000000000000`.

**Why:** The hash chain is what makes cold-storage verification possible without any runtime services. Any deviation from the canonical format breaks verification for any tool reading the Ledger — including CLI tools running without the kernel. Uppercase letters, `0x` prefix, base64, or raw bytes are silent bugs that break cross-tool interoperability. The format is a byte-level contract.

**Test:** Append 3 events to a fresh Ledger. Assert: (1) event 0's `previous_hash` is exactly the 64-zero genesis sentinel, (2) each subsequent event's `previous_hash` equals SHA-256 of the preceding event's canonical JSON (sorted keys, no whitespace, `hash` field excluded, UTF-8 no BOM, no escaped unicode), (3) all hashes match regex `^sha256:[0-9a-f]{64}$`. Tests MUST use exact string comparison — no semantic equivalence.

**Violations:** No exceptions. The hash format is a byte-level contract. Any variation is a bug.

---

### Article 6: SEQUENCE MONOTONICITY — Caller-Opaque Sequencing
**Rule:** The Ledger MUST assign sequence numbers internally. Callers MUST NOT pass sequence numbers to `append()`. The Ledger MUST reject any concurrent write that would produce a non-monotonic sequence with `LedgerSequenceError`.

**Why:** Caller-supplied sequences create race conditions even in a single-writer design. A forked sequence creates a forked truth — the system has no way to order events correctly for Graph replay. Sequence 0 must always precede sequence 1; if a caller can supply sequence numbers, that guarantee is only as reliable as the caller's correctness. The Ledger must own the guarantee.

**Test:** Verify `append()` interface accepts no `sequence` parameter. Write 5 events, verify sequences are exactly 0, 1, 2, 3, 4 with no gaps. Simulate a concurrent write conflict (force via mock); verify `LedgerSequenceError` is raised rather than silent acceptance.

**Violations:** No exceptions. This applies to system events (SESSION_START, SESSION_END, SNAPSHOT_CREATED) as well — all events go through `append()`.

---

### Article 7: IMMUDB ABSTRACTION — No Direct Dependencies
**Rule:** All access to immudb MUST go through `platform_sdk.tier0_core.data`. No framework, service, agent, or CLI tool may import immudb SDK libraries directly. FMWK-001 wraps platform_sdk; callers wrap FMWK-001.

**Why:** immudb is an infrastructure dependency. If callers depend on immudb directly, swapping the backing store becomes a system-wide refactor touching every framework that writes events. The abstraction preserves the ability to evolve infrastructure. This also enforces the Platform SDK contract, which is non-negotiable per AGENT_BOOTSTRAP.md.

**Test:** Grep all non-FMWK-001 files for `import immudb`, `from immudb`, or any immudb SDK namespace. Zero matches permitted. CLI tools use the same Ledger interface (or a thin offline re-implementation defined in D4) — they also do not import immudb directly.

**Violations:** No exceptions. The platform_sdk contract is architectural law, not a suggestion.

---

### Article 8: COLD-STORAGE VERIFIABILITY — No Runtime Dependency
**Rule:** The `verify_chain()` operation MUST function correctly using only the immudb data in the `ledger_data` volume. It MUST NOT require the kernel process, the Graph (FMWK-005), HO1 (FMWK-004), HO2 (FMWK-003), or any cognitive runtime component.

**Why:** OPERATIONAL_SPEC Q4 guarantees the operator is never locked out. If cold-storage verification requires a running kernel, and the kernel is broken, the operator cannot diagnose the state of the system. The hash chain must be checkable by a CLI tool connecting directly to immudb on :3322 with nothing else running.

**Test:** Stop the kernel container. Connect a CLI tool directly to immudb on :3322. Run `verify_chain()`. Assert the result is identical to online verification with the kernel running.

**Violations:** No exceptions. This is the operational invariant that makes DoPeJarMo recoverable.

---

### Article 9: INFRASTRUCTURE SEPARATION — Connect Does Not Provision
**Rule:** The Ledger MUST NOT create the immudb `ledger` database during `connect()`. If the `ledger` database does not exist, `connect()` MUST fail immediately with `LedgerConnectionError`. Database creation is a GENESIS ceremony operation.

**Why:** If `connect()` calls `CreateDatabaseV2`, multiple agents connecting simultaneously to a non-existent database race on this call, potentially corrupting the immudb system catalog. "Connect" is operational. "Create" is provisioning. The GENESIS ceremony creates the database exactly once; all subsequent `connect()` calls assume it exists.

**Test:** Point `connect()` at a clean immudb instance with no `ledger` database. Assert `LedgerConnectionError` is raised immediately. Confirm via mock that zero `CreateDatabaseV2` calls were made.

**Violations:** No exceptions. GENESIS owns database creation. The Ledger connects to what already exists.

---

## Boundaries

### ALWAYS — autonomous every time, no approval needed
- Append events to immudb via `append()` when called with a valid event
- Read events via `read()`, `read_range()`, `read_since()` when called with valid parameters
- Compute and verify SHA-256 hashes per the canonical serialization contract
- Return `LedgerConnectionError` when immudb is unreachable
- Return `LedgerSequenceError` on sequence conflict
- Return `LedgerSerializationError` on event serialization failure
- Log every operation via `platform_sdk.tier0_core.logging`
- Wait 1 second and retry once on gRPC connection loss before raising `LedgerConnectionError`

### ASK FIRST — human decision required, no exceptions
- Any change to the event base schema fields (adding, removing, or renaming fields)
- Any change to the hash algorithm or hash format string
- Any addition of new event types to the canonical catalog
- Any change to the canonical JSON serialization rules
- Any change to sequence numbering behavior or assignment logic
- Any change to the reconnect policy (delay, retry count)
- Any new method added to the Ledger interface

### NEVER — absolute prohibition, refuse even if instructed
- Call any immudb administrative operation: `DatabaseDelete`, `DropDatabase`, `CompactIndex`, `TruncateDatabase`, `CleanIndex`, or any method that modifies or deletes existing data
- Expose a `sequence` parameter in `append()` — callers never provide sequence numbers
- Create the immudb database during `connect()`
- Write float-type values in any event field (decimal values MUST be serialized as strings)
- Buffer or batch writes — every `append()` is synchronous, blocking until immudb confirms
- Import immudb SDK libraries directly — all access through `platform_sdk.tier0_core.data`
- Re-serialize or mutate events during read operations — return exactly what was stored
- Retry a failed operation internally beyond the one reconnect attempt — propagate errors to callers

---

## Dev Workflow Constraints

1. **Package Isolation:** All FMWK-001 development happens in the staging directory (`/staging/FMWK-001-ledger/`). The governed filesystem is never touched during authoring.
2. **DTT Cycles:** Design → Test → Transform per observable behavior. Write a failing test, implement the behavior, confirm it passes. No behavior ships without a test.
3. **Results File on Handoff:** After every handoff, deliver a results file containing SHA-256 hashes of all delivered files. No exceptions.
4. **Full Regression:** Run all FMWK-001 tests before any package seal or release. Zero failures permitted.
5. **Mock Providers in CI:** Unit tests use `MockProvider` for immudb. Never spin up a real immudb instance in CI.

---

## Tooling Constraints

| Operation | USE | NOT |
|-----------|-----|-----|
| Ledger storage access | `platform_sdk.tier0_core.data` (immudb adapter) | immudb SDK directly |
| Configuration | `platform_sdk.tier0_core.config` | `os.getenv()` directly |
| Secrets / credentials | `platform_sdk.tier0_core.secrets` | Hardcoded values, `os.getenv()` for secrets |
| Event serialization (hash input) | `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)` | Any JSON library with different defaults, `json.dumps()` without explicit args |
| Hash computation | `hashlib.sha256(utf8_bytes).hexdigest()` prefixed with `sha256:` | Any hash shortcut, base64, raw bytes, uppercase output |
| Error reporting | `platform_sdk.tier0_core.errors` | `raise Exception(...)` or bare Python exceptions |
| Logging | `platform_sdk.tier0_core.logging` | `print()`, raw `structlog`, `logging.basicConfig()` |
| Health reporting | `platform_sdk.tier2_reliability.health` | Custom `/health` endpoints |
| Metrics | `platform_sdk.tier2_reliability` metrics module | Raw Prometheus client imports |
