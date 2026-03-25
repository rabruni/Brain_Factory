# D5: Research — Write Path (FMWK-002)
Meta: v:1.0.0 (matches D2) | status:Complete | open questions:0

---

## Research Log

### RQ-001 — What exactly defines success for the synchronous mutation path?

- Prompted By: D2 SC-001, D1 Article 4
- Priority: Blocking
- Sources Consulted: BUILDER_SPEC.md "The Data Pattern", TASK.md constraints, OPERATIONAL_SPEC.md "The Two Invariants", Archive FWK-0 pragmatic note `Write Path → Ledger append (acknowledged) → Graph fold → return`
- Findings: All authority sources align on a three-step contract: accept event, append durably, fold immediately, then return. The only stable interpretation of "read-your-writes" is that success means both durable append and visible fold have completed.
- Options Considered:

| Option | Pros | Cons |
|--------|------|------|
| Return after Ledger append only | Simple durability story | Breaks immediate Graph visibility |
| Return after Graph fold only | Immediate visibility | Could acknowledge undurable state |
| Return after append and fold | Matches both durability and visibility invariants | Requires explicit handling for fold failure after durable append |

- Decision: Return success only after append and fold both succeed.
- Rationale: This is the only option that satisfies the synchronous consistency contract extracted from authority.

### RQ-002 — How should fold failure be handled after a durable append?

- Prompted By: D2 SC-008, D4 ERR-002
- Priority: Blocking
- Sources Consulted: TASK.md ("append to Ledger + fold into Graph, atomic"), OPERATIONAL_SPEC.md Q4 ("block rather than guess"), BUILDER_SPEC.md "No Dual Writes"
- Findings: Authority requires atomic caller semantics but does not specify a rollback mechanism after durable append. The Ledger is append-only, so the write cannot be undone. The remaining deterministic option is to return failure, preserve the durable sequence boundary, and require recovery before more writes proceed.
- Options Considered:

| Option | Pros | Cons |
|--------|------|------|
| Return success anyway | Hides partial state from caller | Violates synchronous visibility guarantee |
| Delete the Ledger event | Preserves symmetry | Forbidden by append-only invariant |
| Return failure and recover from durable sequence boundary | Deterministic and replay-safe | Requires explicit recovery step |

- Decision: Return typed fold failure and recover from the durable sequence boundary before resuming writes.
- Rationale: This is the only option consistent with append-only Ledger truth and block-rather-than-guess failure posture.

### RQ-003 — What is the signal accumulator fold rule at the primitive boundary?

- Prompted By: D2 SC-003, D1 Article 7
- Priority: Blocking
- Sources Consulted: BUILDER_SPEC.md §Signal Accumulator, TASK.md constraint on `0.0–1.0` continuous methylation
- Findings: Authority clearly defines range and ownership boundary but does not spell out arithmetic. The minimal primitive interpretation is additive fold with clamping to the legal range; all other controls are explicitly delegated to higher-layer frameworks.
- Options Considered:

| Option | Pros | Cons |
|--------|------|------|
| Raw addition without bounds | Simplest implementation | Violates required `0.0–1.0` range |
| Add then clamp to bounds | Satisfies range guarantee and remains primitive-level | Assumption not spelled out verbatim in authority |
| Framework-specific decay/normalization in primitive | Rich behavior | Violates primitive/framework boundary |

- Decision: Add delta, then clamp to `0.0–1.0`.
- Rationale: This is the narrowest assumption that preserves the primitive contract without importing framework policy.

### RQ-004 — Where is the snapshot boundary between Write Path and Graph?

- Prompted By: D2 SC-004/SC-005, cross-read against FMWK-001 deferred snapshot notes
- Priority: Blocking
- Sources Consulted: BUILDER_SPEC.md "Snapshotting", OPERATIONAL_SPEC.md startup/shutdown, TASK.md owns list, FMWK-001 D2 DEF-001
- Findings: Authority gives FMWK-002 ownership of snapshot creation and replay coordination, while Graph remains the state being serialized. The stable boundary is: Write Path owns when snapshots happen, the sequence marker, and the `snapshot_created` event; Graph owns the runtime state being serialized and reloaded through a declared interface.
- Options Considered:

| Option | Pros | Cons |
|--------|------|------|
| Write Path owns full Graph serialization internals | Simple single-owner story | Bleeds into Graph data-model ownership |
| Graph owns all snapshot timing and events | Keeps serialization close to state | Violates Write Path ownership stated in task |
| Write Path owns orchestration and replay boundaries; Graph exposes serialization/load interface | Matches both documents | Requires a declared dependency interface |

- Decision: Write Path owns snapshot orchestration and replay boundary; Graph supplies load/save operations behind a declared interface.
- Rationale: This closes the ownership boundary without moving query/state ownership out of FMWK-005.

## Prior Art Review

### What Worked

Append-then-project event-sourcing systems work when the projector is deterministic and recovery can always replay from durable truth. Snapshot markers paired with post-snapshot replay are a standard startup optimization that preserves correctness while shortening boot time.

### What Failed

Dual-write systems that acknowledge before both durable storage and projection complete drift under failure. Background queues and wall-clock-only state mutations also break replay because the same Ledger history no longer recreates the same runtime state.

### Lessons for This Build

1. The success condition must be narrower than "event accepted"; it is "event durable and folded."
2. A durable append followed by fold failure is a first-class failure mode, not an implementation detail.
3. Keep signal accumulation primitive-level: bounded arithmetic only, no policy controls.
4. Snapshot timing and replay boundaries belong in the Write Path packet so Turn C/D/E can reason about recovery without inventing behavior.
