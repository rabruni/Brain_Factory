# D1: Constitution — Write Path (FMWK-002)
Meta: v:1.0.0 | ratified:2026-03-21 | amended:— | authority:NORTH_STAR.md v3.0, BUILDER_SPEC.md v3.0, OPERATIONAL_SPEC.md v3.0, FWK-0-DRAFT.md v1.0.0, BUILD-PLAN.md v1.0

---

## Articles

### Article 1 — Splitting Test (FWK-0 Section 3.0 mandatory)

**Rule:** The Write Path MUST be independently authorable from its spec pack and FWK-0 alone, without co-authoring Ledger, Graph, Orchestration, or Execution.

**Why:** FWK-0 requires each framework to be independently authorable. The Write Path is tightly coupled to Ledger and Graph at runtime, but its job is still bounded: accept a mutation request, append via Ledger, fold into Graph, and manage snapshot/replay sequencing. If the builder needed to co-author Graph internals or Ledger storage internals to implement the Write Path, the framework boundary would be wrong and KERNEL decomposition would be invalid.

**Test:** Hand a builder only the Write Path D1-D6 packet, FWK-0, and the declared dependency contracts from FMWK-001. Confirm the builder can implement append-plus-fold, snapshot orchestration, and replay/refold coordination without writing FMWK-001 or FMWK-005 code.

**Violations:** No exceptions. If implementation requires simultaneous authorship of another framework, the boundary must be corrected before build proceeds.

### Article 2 — Merging Test (FWK-0 Section 3.0 mandatory)

**Rule:** The Write Path MUST NOT absorb separate capabilities such as durable event storage, graph query serving, orchestration policy, or LLM execution.

**Why:** The Write Path exists to uphold one invariant: acknowledged mutations are durable in the Ledger and immediately reflected in the Graph. If it starts owning storage administration, query planning, retrieval ranking, or prompt execution, it stops being a consistency layer and becomes a hidden monolith. That breaks the KERNEL decomposition and makes replay behavior unverifiable.

**Test:** Verify the framework exposes zero: direct query APIs for HO2, prompt contract execution, immudb administrative operations, or framework gate logic. Confirm its public surface is limited to mutation submission, snapshot orchestration, recovery replay, and retroactive refold control.

**Violations:** No exceptions. Any absorbed capability must be extracted back to its owning framework.

### Article 3 — Ownership Test (FWK-0 Section 3.0 mandatory)

**Rule:** The Write Path MUST have exclusive ownership of synchronous mutation sequencing, fold application, signal accumulator folding, and snapshot/replay coordination.

**Why:** No other component may decide when Graph state changes relative to Ledger durability. If HO1, HO2, Graph, or Package Lifecycle could independently append or fold, read-your-writes consistency would fracture and replay would no longer reconstruct the same runtime state. Exclusive ownership of the append-plus-fold path is what keeps the OS mechanically deterministic.

**Test:** Confirm that only FMWK-002 calls FMWK-001 `append()` for live mutations, only FMWK-002 writes live state into FMWK-005, and only FMWK-002 initiates snapshot/replay/refold flows.

**Violations:** No exceptions. Any second writer to Ledger or Graph is a constitutional failure.

### Article 4 — Synchronous Acknowledgment

**Rule:** The Write Path MUST acknowledge success only after the Ledger append is durable and the corresponding Graph fold is complete.

**Why:** The design authority ties read-your-writes consistency directly to the synchronous Write Path contract. Returning before the Ledger acknowledges breaks durability; returning before fold completion breaks immediate query visibility. Either failure violates the core architectural and operational invariants because the caller cannot know whether the system state it just wrote is actually retrievable.

**Test:** Submit a valid mutation and immediately query the Graph through the declared read interface. Confirm the folded state is already visible when the Write Path returns success. Simulate Ledger latency and confirm the Write Path does not return early.

**Violations:** No exceptions. "Append queued," "fold pending," or any eventual-consistency acknowledgment is forbidden.

### Article 5 — No Dual Writes

**Rule:** Callers MUST submit exactly one mutation request to the Write Path; they MUST NOT write separately to both Ledger and Graph.

**Why:** The architecture explicitly rejects dual-write systems because they drift under failure. The Write Path is the single consistency boundary. If a caller could write one side directly or retry only one side, the Ledger would cease to be the sole source of truth and the Graph would stop being a faithful materialized view.

**Test:** Confirm all mutation-capable callers depend on Write Path contracts, not on both FMWK-001 and FMWK-005. Grep for any direct Graph-write or direct Ledger-append calls outside FMWK-002 and fail the build if found.

**Violations:** No exceptions. Direct caller-managed dual writes are prohibited even during recovery or maintenance.

### Article 6 — Fold, Don’t Interpret

**Rule:** The Write Path MUST mechanically fold events into Graph state; it MUST NOT execute business policy, retrieval policy, or semantic interpretation.

**Why:** Fold logic updates runtime state according to event type. Business decisions about what to write belong to HO1, HO2, or higher-layer frameworks. If the Write Path starts deciding whether a mutation is "good," "important," or "relevant," replay no longer becomes a deterministic function of the Ledger and fold code. The Write Path must remain a pure consistency layer.

**Test:** Inspect fold handlers. Confirm they transform Graph state only from event fields and do not read prompts, infer intent from text, apply framework policy thresholds, or dispatch work orders.

**Violations:** No exceptions. Semantic or policy logic discovered in FMWK-002 must be removed.

### Article 7 — Range-Bounded Signal Accumulation

**Rule:** Signal accumulator folds MUST keep methylation values in the closed range `0.0` through `1.0`.

**Why:** The primitive definition promises continuous methylation values on Graph nodes in the range `0.0–1.0`. If a fold can produce values outside that range, downstream retrieval math `(1 - M)` becomes invalid and cross-session replay can diverge because higher-layer frameworks assume bounded state.

**Test:** Start with methylation at `0.95`, apply `+0.10`, and confirm the folded value is `1.0`. Start at `0.05`, apply `-0.10`, and confirm the folded value is `0.0`.

**Violations:** No exceptions. Out-of-range methylation is a data-integrity bug.

### Article 8 — Replayability Over Time

**Rule:** Startup recovery and retroactive healing MUST rebuild Graph state solely from snapshot marker plus Ledger replay, or from full Ledger replay when no usable snapshot exists.

**Why:** The system depends on replay for crash recovery, operator trust, and maintenance upgrades. If any state needed for reconstruction lives only in process memory or untracked side state, a crash or refold produces a different Graph than the original run. Replayability is the operational proof that the Ledger is actually truth and Graph is actually derived state.

**Test:** Build Graph state from live writes, snapshot it, then destroy the process state. Recover from the snapshot marker and post-snapshot events. Confirm the rebuilt Graph matches the pre-crash state. Repeat with full replay from genesis.

**Violations:** No exceptions. Hidden side state or wall-clock-only effects invalidate replay and must be removed.

### Article 9 — Deterministic Failure Posture

**Rule:** The Write Path MUST block and surface explicit errors on append, fold, snapshot, or replay failure; it MUST NOT silently continue, buffer indefinitely, or guess recovery.

**Why:** OPERATIONAL_SPEC sets the failure posture: block rather than guess. A consistency layer that partially succeeds in secret is worse than one that stops, because it creates ambiguous state the operator cannot reason about. Explicit blocking failures preserve trust and keep recovery paths deterministic.

**Test:** Simulate Ledger unavailability, fold failure, and snapshot write failure. Confirm the Write Path returns typed errors immediately, does not report success, and requires recovery before proceeding.

**Violations:** No exceptions. Hidden retries, unbounded buffering, or silent degradation are forbidden.

### Article 10 — Platform SDK Contract

**Rule:** All Ledger, storage, logging, config, secrets, and error interactions inside the Write Path MUST go through `platform_sdk`.

**Why:** The platform SDK contract applies to KERNEL frameworks too. Bypassing it breaks MockProvider-based testing and creates direct dependency sprawl into immudb and infrastructure libraries. The Write Path is foundational; if it bypasses the SDK, every downstream framework inherits brittle test and runtime behavior.

**Test:** Verify there are no direct immudb imports, no raw env-var reads for secrets/config, and no raw error/logging frameworks in FMWK-002. Confirm unit tests can run against declared doubles without live services.

**Violations:** No exceptions. SDK bypasses block the framework.

## Boundaries

### ALWAYS — autonomous every time, no approval needed
- Accept valid mutation requests from declared callers
- Append through FMWK-001, then fold into Graph before returning success
- Author `session_start`, `session_end`, and `snapshot_created` system events when invoked through declared system paths
- Update signal accumulator values while preserving the `0.0–1.0` range
- Trigger snapshot creation at session boundaries when asked by HO2/system runtime
- Recover Graph from snapshot marker plus post-snapshot replay, or from full replay if no usable snapshot exists
- Stop and return typed errors when Ledger, fold, snapshot, or replay steps fail

### ASK FIRST — human decision required, no exceptions
- Any change to the three-step synchronous contract
- Any new event type or payload field owned by FMWK-002
- Any change to the methylation fold rule or bounds
- Any change to snapshot marker format or replay boundary semantics
- Any change to failure posture after a durable append but unsuccessful fold
- Any expansion of public surface beyond mutation, snapshot, replay, and refold control

### NEVER — absolute prohibition, refuse even if instructed
- Write directly to Graph from any component other than FMWK-002
- Append directly to Ledger from any component other than FMWK-002
- Return success before both append and fold complete
- Add background daemons, queues, or eventual-consistency buffering to the Write Path
- Execute HO2 policy, HO1 prompt work, or package gate logic inside fold handlers
- Introduce wall-clock-only state changes that cannot be reproduced from Ledger replay
- Import immudb libraries directly instead of using `platform_sdk`
- Ask callers to perform compensating writes to Graph or Ledger manually

## Dev Workflow Constraints

1. Package isolation: all Write Path work happens in staging and enters governed state only through Package Lifecycle.
2. DTT per behavior: define each mutation/snapshot/replay contract in D4, write tests from D2 scenarios, then implement.
3. Results file with hashes: every handoff includes artifact hashes for the packet and later code outputs.
4. Full regression before release: mutation path, fold path, snapshot/recovery, and retroactive-healing tests all pass before KERNEL assembly.
5. Failure-first verification: every success-path behavior ships with an explicit failure-path test for append, fold, snapshot, or replay.

## Tooling Constraints

| Operation | USE | NOT |
|-----------|-----|-----|
| Ledger access | FMWK-001 contracts through `platform_sdk` | Direct immudb client usage |
| Graph writes | Declared FMWK-005 interface/double | Ad hoc shared-memory mutation outside contract |
| Snapshot file I/O | `platform_sdk` storage/filesystem modules | Raw uncontrolled filesystem helpers |
| Logging | `platform_sdk.tier0_core.logging` | `print()`, raw logging libraries |
| Errors | `platform_sdk.tier0_core.errors` | Raw `Exception` trees only |
| Configuration | `platform_sdk.tier0_core.config` | scattered `os.getenv()` |
| Secrets | `platform_sdk.tier0_core.secrets` | hardcoded credentials |
| Tests | Declared package-code doubles and MockProvider | live immudb or live kernel required for unit tests |
