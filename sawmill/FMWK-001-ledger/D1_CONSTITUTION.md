# D1: Constitution — FMWK-001-ledger
Meta: v:1.0.0 | ratified:2026-03-19 | amended:2026-03-19 | authority:AGENT_BOOTSTRAP.md; architecture/NORTH_STAR.md; architecture/BUILDER_SPEC.md; architecture/OPERATIONAL_SPEC.md; architecture/FWK-0-DRAFT.md; architecture/BUILD-PLAN.md; sawmill/FMWK-001-ledger/TASK.md; sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md

## Articles

### Article 1 — Splitting
- Rule: FMWK-001 MUST remain independently authorable as the append-only Ledger primitive; its spec MUST stop at event storage, event schema ownership, hash chaining, replay, and immudb abstraction.
- Why: FWK-0 Section 3.0 requires a framework to be authorable from its own spec. If ledger behavior expands into fold logic, graph structure, or package gates, the builder can no longer implement it from the ledger spec alone and the primitive boundary collapses.
- Test: Review `framework.json` and all packs for FMWK-001; pass only if every declared responsibility maps to event storage, event schema definition, chain verification, ordered retrieval, or immudb-backed durability.
- Violations: No exceptions.

### Article 2 — Merging
- Rule: FMWK-001 MUST NOT hide a separate capability that belongs in another framework, including write-path mutation logic, graph materialization, work-order lifecycle logic, gate execution, or snapshot file management.
- Why: FWK-0's merging test requires separate capabilities to be split rather than buried inside a foundation framework. If Ledger absorbs execution or lifecycle logic, downstream frameworks lose clean interfaces and cold-storage validation becomes ambiguous.
- Test: Inspect contracts and code ownership; pass only if FMWK-001 exposes Ledger interfaces and event schemas, while FMWK-002 owns folding, FMWK-005 owns graph state, and FMWK-006 owns gate behavior.
- Violations: No exceptions.

### Article 3 — Ownership
- Rule: FMWK-001 MUST exclusively own the canonical Ledger event envelope, sequence assignment, and hash-chain rules; other frameworks MUST consume those through declared interfaces rather than redefining them.
- Why: Ownership is what prevents shared-schema drift. If multiple frameworks redefine sequence, provenance, or hash serialization, replay diverges and the sole source of truth stops being singular.
- Test: Confirm D3 entities `LedgerEvent`, `LedgerTip`, and `ChainVerificationResult` are declared as shared entities owned by FMWK-001 and referenced by consuming frameworks only through Ledger contracts.
- Violations: No exceptions.

### Article 4 — Append-Only Truth
- Rule: The Ledger MUST be append-only and MUST NEVER delete, rewrite, compact, truncate, or mutate recorded events in place.
- Why: NORTH_STAR and BUILDER_SPEC define the Ledger as the sole source of truth. If events can be rewritten, replay, audit, rollback, and provenance validation all become untrustworthy, and "can't forget, can't drift" fails at the storage layer.
- Test: Static inspection must show no exposed or wrapped administrative delete/reorg methods; runtime tests must append events and verify prior sequences remain byte-for-byte unchanged.
- Violations: No exceptions.

### Article 5 — Deterministic Hash Chain
- Rule: Every Ledger event MUST hash the previous event using SHA-256 over canonical UTF-8 JSON with the `hash` field excluded, and every stored hash string MUST exactly match `sha256:<64 lowercase hex chars>`.
- Why: The hash chain is the tamper-evidence mechanism that lets the operator validate the system from cold storage. Any ambiguity in serialization, encoding, or hash formatting creates false forks across languages and destroys deterministic verification.
- Test: Generate the same event in repeated runs and across supported implementations; pass only if canonical serialization bytes and resulting hashes are identical and chain verification reports the same break point for the same corruption.
- Violations: No exceptions.

### Article 6 — Interface Isolation
- Rule: Callers MUST interact with the Ledger only through Ledger contracts and platform_sdk-backed configuration and connection abstractions; callers MUST NOT import or call immudb directly.
- Why: The task source material and AGENT_BOOTSTRAP platform_sdk contract make immudb a backing store, not a public dependency. Direct immudb usage would bypass the Ledger's sequence ownership, provenance rules, and hash-chain guarantees.
- Test: Dependency inspection must show no direct immudb dependency outside the Ledger implementation boundary and no caller-supplied sequence numbers in Ledger append requests.
- Violations: No exceptions.

### Article 7 — Cold-Storage Verifiability
- Rule: FMWK-001 MUST support ordered replay and hash-chain verification from Ledger data alone, without requiring HO1, HO2, HO3, or runtime kernel services.
- Why: NORTH_STAR and OPERATIONAL_SPEC make cold-storage validation a core operational invariant and CLI recovery path. If Ledger verification needs the runtime stack, the operator can be locked out exactly when recovery is needed.
- Test: Export Ledger data, stop runtime services, and run chain verification offline; pass only if validity and break position match the online result.
- Violations: No exceptions.

### Article 8 — Fail Closed
- Rule: On connection loss, serialization failure, or sequence conflict, the Ledger MUST fail the operation explicitly and MUST NOT synthesize success, retry appends indefinitely, or repair corruption silently.
- Why: OPERATIONAL_SPEC requires hard stops over guessing when truth cannot be recorded reliably. Silent repair or hidden retries create unlogged state transitions and mask the exact failure boundary that operators need to diagnose.
- Test: Simulate immudb unavailability, invalid event payload serialization, and conflicting append attempts; pass only if the Ledger returns the declared error type and leaves the chain unchanged.
- Violations: No exceptions.

## Boundaries
### ALWAYS — autonomous every time, no approval needed
- Assign the next sequence number internally from the current tip during append.
- Compute and verify event hashes using the canonical serialization contract.
- Return ordered events for single-read, range-read, and read-since replay use cases.
- Expose self-describing events containing type, schema version, provenance, and payload.
- Fail closed with the declared Ledger error types when append or verification cannot complete safely.

### ASK FIRST — human decision required, no exceptions
- Any change to the canonical event envelope fields or hash serialization contract.
- Any expansion of FMWK-001 scope into fold logic, graph structure, gate execution, or snapshot file format ownership.
- Any change to the approved event type names when authority documents disagree.
- Any production choice among multiple acceptable atomic append strategies if the decision is not already ratified in D5/D6.

### NEVER — absolute prohibition, refuse even if instructed
- Delete, truncate, compact, reorganize, or rewrite existing Ledger events.
- Expose immudb administrative methods other than bootstrap database creation outside the approved provisioning path.
- Accept caller-supplied sequence numbers for append.
- Query or mutate Graph state, methylation values, work-order lifecycle, or package gates inside the Ledger framework.
- Import immudb libraries directly outside the Ledger boundary or bypass platform_sdk for configuration access.

## Dev Workflow Constraints
- Package isolation: author FMWK-001 in its own framework boundary and consume all cross-framework behavior only through declared interfaces.
- DTT per behavior: each D2 scenario and edge case must have a deterministic test before release, including offline verification coverage.
- Handoff evidence: every implementation handoff must include a results artifact with file hashes and scenario/test outcomes traceable back to D2 and D4.
- Regression scope: run full regression for FMWK-001 plus any consuming packages/frameworks affected by event schema or contract changes before release.
- Mock-first testing: use mock providers for unit tests and never depend on live immudb in unit test cycles.

## Tooling Constraints
| Operation:text | USE:approach | NOT:anti-pattern |
| Append path | USE:Ledger interface with internal sequence assignment and canonical hash computation | NOT:caller-supplied sequence or direct immudb `Set` from another framework |
| Configuration | USE:`platform_sdk` config/secrets access for host, port, database, credentials | NOT:hardcoded credentials or scattered env reads |
| Storage access | USE:Ledger-owned immudb wrapper boundary | NOT:direct immudb imports by write-path, graph, or package-lifecycle callers |
| Hashing | USE:SHA-256 over canonical UTF-8 JSON with sorted keys and excluded `hash` field | NOT:language-default JSON serialization, alternate encodings, or noncanonical whitespace |
| Verification | USE:online and offline chain verification against exact stored hash strings | NOT:semantic hash comparison or runtime-only verification |
| Testing | USE:deterministic scenario tests plus corruption and disconnect fault injection | NOT:ad hoc manual validation as sole evidence |
