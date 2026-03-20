# D1: Constitution — FMWK-001-ledger
Meta: v:1.0.0 | ratified:2026-03-20 | amended:2026-03-20 | authority:architecture/NORTH_STAR.md, architecture/BUILDER_SPEC.md, architecture/OPERATIONAL_SPEC.md, architecture/FWK-0-DRAFT.md, architecture/BUILD-PLAN.md, sawmill/FMWK-001-ledger/TASK.md, sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md

## Articles
### Article 1 — Splitting
- Rule: FMWK-001 MUST remain independently authorable from the ledger/event schema specification plus FWK-0 and MUST NOT require co-authoring any other framework.
- Why: FWK-0 defines Ledger as its own primitive and requires frameworks to be independently authorable. If ledger specification depends on write-path, graph, or package-lifecycle implementation details, the foundation framework stops being buildable in isolation and the KERNEL dependency order collapses.
- Test: Hand the builder only FWK-0, the authority chain, `TASK.md`, and `SOURCE_MATERIAL.md`; verify the builder can produce ledger contracts, data model, and tests without reading another framework's staged implementation.
- Violations: No exceptions.

### Article 2 — Merging
- Rule: FMWK-001 MUST NOT absorb fold logic, graph structure, gate logic, work order management, or any other capability owned by another framework.
- Why: FWK-0's merging test forbids hiding separate capabilities inside one framework. If ledger starts interpreting events, managing graph state, or running gates, the nine-primitives boundary blurs and downstream frameworks lose clear ownership.
- Test: Verify every exported contract is limited to append, read, replay, tip lookup, and chain verification; reject any contract that mutates graph state, evaluates gates, or executes business logic.
- Violations: No exceptions.

### Article 3 — Ownership
- Rule: FMWK-001 MUST exclusively own the canonical ledger event envelope, global sequence assignment, previous-hash linkage, and replay ordering, while all consumed data from other frameworks enters only through declared payload schemas and interfaces.
- Why: FWK-0 requires exclusive data ownership. If another framework owns the event envelope or sequence rules, replay and cold validation stop being deterministic. If ledger starts owning other frameworks' behavioral state, responsibilities overlap and audit provenance becomes ambiguous.
- Test: Verify D3 marks the ledger event envelope and verification/tip entities as shared ledger-owned entities, and verify D2/D4 defer non-ledger-owned payload semantics to their owning frameworks.
- Violations: No exceptions.

### Article 4 — Source Of Truth
- Rule: The Ledger MUST be the sole source of truth for DoPeJarMo state and MUST persist every acknowledged mutation as an append-only event.
- Why: NORTH_STAR and BUILDER_SPEC define "The Ledger is Truth; the Graph is State." If any authoritative state exists outside the ledger or acknowledged work can occur without a ledger event, replay breaks, audit breaks, and "can't forget, can't drift" becomes false.
- Test: Destroy the in-memory Graph, rebuild from snapshot plus ledger replay, and verify the rebuilt state matches the pre-destruction state for covered scenarios.
- Violations: No exceptions.

### Article 5 — Append-Only Immutability
- Rule: The Ledger MUST NEVER delete, rewrite, compact, truncate, or reorganize existing events.
- Why: Append-only immutability is constitutional in the task and source material. Rewriting or deleting historical events breaks the hash chain, destroys provenance, invalidates cold-storage verification, and makes rollback and audit untrustworthy.
- Test: Static inspection must show no ledger contract or wrapped immudb admin method for delete/truncate/compact operations, and runtime tests must prove sequence numbers only increase.
- Violations: No exceptions.

### Article 6 — Separation Of Concerns
- Rule: The Ledger MUST store and retrieve events only and MUST NOT execute business logic, fold graph state, evaluate gates, or manage work orders.
- Why: BUILDER_SPEC separates Ledger, Write Path, Graph, Orchestration, and Package Lifecycle. If ledger performs behavioral interpretation, HO3/Write Path boundaries collapse and the core invariant drifts toward execution at the storage layer.
- Test: Review contracts and implementation boundaries for absence of fold functions, graph mutation logic, gate runners, and orchestration state machines within the ledger module.
- Violations: No exceptions.

### Article 7 — Deterministic Hashing And Replay
- Rule: The Ledger MUST compute hashes from canonical UTF-8 JSON with exact serialization rules and MUST provide deterministic ordered replay and verifiable hash-chain integrity from genesis to tip.
- Why: The hash chain is only meaningful if every implementation hashes the same bytes and every replay traverses the same sequence. Any serialization drift or non-deterministic ordering creates false corruption or, worse, silent divergence across runtimes.
- Test: Use the same event fixture across independent serializers and verify byte-for-byte hash input equality, exact `sha256:<64 lowercase hex>` output equality, and identical verification results online and offline.
- Violations: No exceptions.

### Article 8 — Cold-Storage Verifiability And Failure Boundaries
- Rule: The Ledger MUST remain verifiable from cold storage without cognitive runtime services and MUST fail closed on connection, serialization, sequence, or corruption errors.
- Why: OPERATIONAL_SPEC requires command-line recovery and framework-chain validation when the kernel is down. If ledger verification depends on Graph, HO1, or HO2, the operator can be locked out. If ledger fails open, corruption or sequence forks can propagate into the rest of the system.
- Test: Run offline chain verification against exported ledger data with no kernel services, and verify connection loss, corruption, and sequence conflicts return explicit ledger errors instead of partial success.
- Violations: No exceptions.

## Boundaries
### ALWAYS — autonomous every time, no approval needed
- Define and validate the canonical ledger event envelope and minimum approved payload schemas.
- Assign global monotonic sequence numbers inside the ledger and reject attempted forks.
- Serialize events using the canonical hash-input rules and compute exact SHA-256 hashes.
- Append one event at a time synchronously after atomic tip-to-write sequencing.
- Read single events, ranges, and replay streams in sequence order.
- Verify the hash chain online or offline and report the first break point deterministically.
- Expose ledger access only through declared ledger contracts and platform SDK-backed configuration.

### ASK FIRST — human decision required, no exceptions
- Expanding the canonical event type catalog beyond types already named in authority documents.
- Changing the event envelope fields, hash algorithm, hash string format, or genesis previous-hash constant.
- Reassigning ownership of payload schemas between ledger and another framework.
- Changing snapshot file contents or snapshot serialization format beyond the ledger-owned reference event.
- Introducing new operational behaviors that alter cold-storage validation assumptions.

### NEVER — absolute prohibition, refuse even if instructed
- Delete, rewrite, compact, truncate, or mutate existing ledger events.
- Expose direct immudb access to callers or import/wrap forbidden immudb administrative methods.
- Place business logic, graph fold logic, gate evaluation, work-order management, or LLM execution in the ledger.
- Let callers supply sequence numbers or bypass ledger-owned sequencing.
- Acknowledge writes before immudb confirms persistence.
- Produce hash strings in any format other than `sha256:<64 lowercase hex chars>`.
- Depend on HO1, HO2, HO3, or any runtime cognitive service to verify ledger integrity.

## Dev Workflow Constraints
- Package isolation is mandatory: ledger work must remain inside the ledger framework boundary and use declared interfaces for all external concerns.
- Develop behavior-by-behavior with DTT cycles: write or update one contract scenario, implement or specify it, then verify before moving to the next behavior.
- After every handoff, produce a results artifact with file hashes so provenance remains inspectable.
- Run full regression for all ledger package behaviors before release, including append, replay, corruption detection, and offline verification.
- Treat sequence assignment and canonical serialization as byte-level contracts; fixture-based regression tests must lock them down.

## Tooling Constraints
| Operation:text | USE:approach | NOT:anti-pattern |
| Append/read/verify implementation | USE:`platform_sdk` configuration, secrets, logging, and error surfaces with a ledger abstraction over immudb | NOT:direct caller access to immudb clients or ad hoc environment handling |
| Event serialization | USE:canonical UTF-8 JSON with sorted keys, no whitespace, `ensure_ascii=False`, and explicit exclusion of `hash` from hash input | NOT:language-default JSON formatting, escaped unicode, omitted nulls, or floating-point hash inputs |
| Sequence control | USE:ledger-owned atomic tip-plus-write sequencing | NOT:caller-supplied sequence numbers or non-atomic read-then-write windows |
| Durability | USE:synchronous single-event appends confirmed by immudb | NOT:buffered writes, batch buffering, or early acknowledgement |
| Verification | USE:mechanical hash recomputation and ordered replay from stored data | NOT:semantic inspection, graph-dependent checks, or LLM-assisted validation |
| Administrative scope | USE:bootstrap-time database creation outside ledger runtime and runtime fail-fast if database is absent | NOT:runtime database provisioning, delete/truncate operations, or hidden admin wrappers |
