# Task: FMWK-002-write-path

## Framework
- ID: FMWK-002-write-path
- Layer: KERNEL

## What to Spec
The Write Path is the synchronous infrastructure service that maintains consistency between the Ledger (disk) and the Graph (RAM). It is the sole entry point for all mutations in DoPeJarMo. Nothing writes to the Ledger or the Graph directly — everything goes through the Write Path.

The Write Path implements a three-step synchronous operation:
1. Accept an event (from HO1 or from internal system events)
2. Append the event to the Ledger via FMWK-001 (disk)
3. Immediately fold the event into the Graph (RAM) — update nodes, edges, methylation values

This ensures read-your-writes consistency: when HO1 writes a memory, it is immediately available for HO2 to query from the Graph. No background daemons. No eventual consistency lag.

## Owns
- Synchronous mutation path (append to Ledger + fold into Graph, atomic)
- Fold logic (how each event type updates Graph state — nodes, edges, methylation values)
- Signal Accumulator primitive (accepts signal_delta events, folds into continuous methylation values 0.0–1.0 on Graph nodes)
- Snapshot creation (serialize Graph state to disk at session boundaries)
- Snapshot-based startup optimization (load snapshot, replay only post-snapshot Ledger events)
- Retroactive healing (re-fold entire Ledger with updated fold logic during governed maintenance)
- System event authoring (SESSION_START, SESSION_END, SNAPSHOT_CREATED — infrastructure events appended directly without routing through HO1)

## Dependencies
- FMWK-001-ledger: The Write Path appends events to the Ledger. It uses the Ledger's append and retrieval interfaces.
- FMWK-000 (FWK-0): Framework hierarchy and filesystem conventions.

## Constraints
- The Write Path is SYNCHRONOUS. No background daemons, no queues, no eventual consistency.
- The Write Path is the ONLY component that writes to the Graph (HO3). HO2 reads. Write Path writes. That is all.
- The Write Path is the ONLY component that appends events to the Ledger (via FMWK-001 interfaces).
- HO1 submits events TO the Write Path. HO1 never writes to the Ledger or Graph directly.
- System events (SESSION_START, SESSION_END, SNAPSHOT_CREATED) may be appended directly by the Write Path without routing through HO1. These are infrastructure events, not cognitive events.
- Fold logic must handle ALL event types defined in FMWK-001 event schemas (creation, signal_delta, methylation_delta, suppression, unsuppression, mode_change, consolidation, work_order_transition, intent_transition, session_start, session_end, package_install, and other system events).
- Signal Accumulator: accepts signal_delta events and folds them into a continuous methylation value (0.0–1.0). The primitive accepts deltas and folds them. Mechanical controls (decay, normalization, caps, Traveler Rule) are framework logic applied by the Meta-Learning Agent — NOT enforced by Write Path.
- Snapshot format must include a sequence marker so replay can start from the correct post-snapshot position.
- No dual writes: callers submit events to the Write Path. The Write Path handles both Ledger append and Graph update. Never "write to Ledger AND Graph."
- All access goes through platform_sdk. Never import immudb libraries directly.
- The Write Path does NOT execute business logic. It appends, folds, and snapshots. Period.

---

## Source Material

The authority chain for Write Path behavior:
- `architecture/BUILDER_SPEC.md` — "The Data Pattern" section defines the Write Path contract, fold logic, snapshotting, and retroactive healing
- `architecture/NORTH_STAR.md` — Core architectural invariant (LLM structures at write time, HO2 retrieves mechanically at read time)
- `architecture/OPERATIONAL_SPEC.md` — Runtime behavior: startup from snapshot, shutdown sequence, failure modes
- `architecture/BUILD-PLAN.md` — FMWK-002 position in KERNEL build order, dependency on FMWK-001
- FMWK-001-ledger outputs (D1-D10) — event schemas, Ledger interfaces, hash chain contract that Write Path must use

The spec agent should extract Write Path specifications from these documents rather than inventing behavior.
