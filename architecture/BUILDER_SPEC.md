---
title: "BUILDER SPEC — Assembly Instructions"
status: BUILD AUTHORITY
authority_level: "build authority — NORTH_STAR.md resolves ambiguity"
version: "3.0"
last_updated: "2026-02-25"
author: Ray Bruni
audience: "Builder agents. No metaphors. No analogies. Mechanical specifications only."
resolves_ambiguity_for: []
depends_on:
  - NORTH_STAR.md
---

# BUILDER SPEC — Assembly Instructions

**Status**: BUILD AUTHORITY — this document tells you what to build and how pieces connect. If ambiguity exists here, NORTH_STAR.md resolves it.

**Audience**: Builder agents. No metaphors. No analogies. Mechanical specifications only.

**Relationship to other documents:**
- NORTH_STAR.md — design authority (why). Resolves all ambiguity.
- This document — build authority (what to build)
- OPERATIONAL_SPEC.md — operational authority (how it runs)
- FRAMEWORK_REGISTRY.md — framework segregation, build order, coding boundaries

---

## What You Are Building

**DoPeJarMo** is a governed operating system AND an interactive agent session shell. The operator logs in and works through DoPeJarMo conversationally — not a dashboard, not a monitoring layer. You build the OS primitives. The DoPeJarMo Agent Interface is the first framework installed (via command-line Package Lifecycle tools from KERNEL). Once it's installed, DoPeJarMo can accept operator sessions and all subsequent framework installs go through him. Capabilities are added as frameworks installed through the governed lifecycle.

**DoPeJar** is the first application on DoPeJarMo. She is a set of installed frameworks. You do not build DoPeJar directly — you build the OS, then build and install her day-one frameworks through DoPeJarMo. DoPeJarMo must be running before DoPeJar can be installed or used.

**You assemble from primitives. You do not create primitives.**

---

## The Data Pattern: Event Sourcing with CQRS

**"The Ledger is Truth; the Graph is State."**

Before understanding the primitives, understand how data works in this system. There are two layers:

**Layer 1: The Ledger (Truth, Disk).** Append-only, immutable sequence of events. Every signal, creation, methylation delta, suppression command, mode change, and system event. History is never rewritten. The Ledger's design principle is append-only — no in-place mutation, no rewriting. Under disk pressure, the Storage Management framework (Layer 1, required) governs trimming of the oldest and least-used entries using methylation values. Trimming is itself a Ledger event — logged, governed, auditable.

**Layer 2: The Graph (State, RAM).** In-memory directed graph derived from the Ledger. Nodes are artifacts with current resolved state (methylation values, suppression masks, lifecycle status). Edges are causal connections (work order chains, intent hierarchy, explicit references). **The Graph is transient.** It can be destroyed and perfectly rebuilt from the Ledger at any moment.

**The Write Path** is the synchronous infrastructure service that maintains consistency between the two layers:
1. HO1 submits an event
2. Write Path appends event to Ledger (disk)
3. Write Path immediately folds the event into the Graph (RAM) — updates nodes, edges, methylation values
4. Write Path returns acknowledgment

This ensures **read-your-writes consistency**: when HO1 writes a memory, it is immediately available for HO2 to query from the Graph. No background daemons. No eventual consistency lag.

**Snapshotting:** At session boundaries (triggered by HO2, not on a timer), the Write Path serializes the current Graph state to disk. On startup: load snapshot, then replay only post-snapshot Ledger events. This optimizes startup without requiring daemons.

**Retroactive Healing:** If fold logic is improved (e.g., better decay algorithm via framework upgrade), the system can re-fold the entire Ledger with new logic during a governed maintenance operation. Delete Graph, replay from Genesis. The Ledger is untouched; behavior changes because the interpretation changes.

**No Dual Writes:** We never "write to HO3 and the Ledger." We write to the Ledger; the Write Path updates the Graph. If you see "written to Ledger and HO3" in NORTH_STAR, this is what it means.

**Exception — System Events:** The Write Path can append mechanical system events (SESSION_START, SESSION_END, SNAPSHOT_CREATED) directly to the Ledger without routing through HO1. These are infrastructure events, not cognitive events.

---

## The Nine Primitives

These must exist before any framework can be installed. Everything else is configuration of these nine.

### 1. Ledger

Append-only, hash-chained truth store. The sole source of truth for all state.

- Every state change is a Ledger event
- Events are immutable once written
- Hash chain provides tamper detection
- Event types include: creation, signal_delta, methylation_delta, suppression, unsuppression, mode_change, consolidation, work_order_transition, intent_transition, session_start, session_end, package_install, system events
- Mechanical fields on every event: scope, key, timestamp, provenance, associated_entities, session_id, sequence_number
- Human-relatable payload field (on learning artifacts): natural-language description, travels through untouched, never queried
- Every LLM call records: prompt, response, contract_id, token_cost
- The Ledger is on disk. HO2 does NOT query the Ledger at runtime for retrieval — it queries the Graph (HO3). The Ledger is for truth, audit, and replay.

### 2. Signal Accumulator (Gate)

A named counter that tracks signal deltas as Ledger events, folded into a continuous methylation value (0.0–1.0) on Graph nodes. The primitive is the accumulator only — it has no opinion on what the value means.

**What the primitive does:**
- Accepts signal_delta events (submitted by HO1 through the Write Path)
- The Write Path folds deltas into a continuous methylation value on the corresponding Graph node
- Signal types: entity (who/what), mode (how user engages), stimulus (emotional intensity), regime (system-level patterns)
- Same accumulator mechanism for all types — different signal sources, different accumulation rates
- The primitive accepts deltas and folds them into methylation values. Mechanical controls (decay, density normalization, session caps, Traveler Rule) are framework logic applied by the Meta-Learning Agent — not enforced by the primitive itself. See Primitive / Framework Boundary.

**What the primitive does NOT do:**
- Does not define thresholds — frameworks define thresholds
- Does not trigger mode changes — frameworks read methylation values and decide
- Does not trigger consolidation — the MLA (a framework) reads values and dispatches work orders
- Does not interpret what accumulated signal means — that is framework logic

**Governance gates (install-time):**
- Degenerate case of the same concept: threshold = 1, single evaluation, no accumulation
- Binary pass/fail validation at each layer of the framework hierarchy
- G0A: package self-consistency (manifest matches files, hashes match contents)
- G0B: no ownership conflicts (no file claimed by two packages)
- G1: framework chain valid (package → spec pack → framework references resolve)
- G1-COMPLETE: framework fully wired (all declared spec packs and packs exist)

### 3. HO1 — Execution

All LLM calls go through HO1. HO1 is also the sole agent-level entry point for the Write Path. No exceptions.

- Stateless single-shot workers under prompt contracts
- At write time: structures conversations into learning artifacts (mechanical fields + human-relatable payload) and submits them as events to the Write Path
- At read time: executes work orders that HO2 planned using context retrieved from the Graph
- Runs Prompt Pack Inspection calls: these ARE work orders (type=classify) dispatched by HO2 under a Prompt Contract. Constrained Ollama, no context window, strict JSON output, predetermined field choices. Not a separate mechanism — the normal dispatch path with a specific work order type
- Submits signal_delta events to the Write Path per turn — ONLY for entities/scopes within active intent
- Threaded for concurrent work order execution
- Logs every call: prompt + response + contract_id + token_cost → submitted as events to Write Path → Ledger
- **HO1 never writes directly to the Graph (HO3) or the Ledger.** It submits events. The Write Path handles persistence and folding.

### 4. HO2 — Orchestration

Mechanical only. Never calls LLM. Never interprets text. Reads from the Graph (HO3), never from the Ledger at runtime.

- Dispatches user message to HO1 for Prompt Pack Inspection (a Work Order with type=classify under a Prompt Contract) → receives structured fields (entities, scopes, temporal markers, mode, sentiment, urgency)
- Reads current state from the Graph (HO3): methylation values, suppression masks, policy rulesets, reachability edges
- Computes effective weight per artifact: `score = field_match × base_weight × recency_factor × outcome_reinforcement × (1 - M)`
  - field_match: deterministic structured field matching (tags, IDs, scope overlap, explicit references). NOT embedding similarity. NOT semantic search.
  - base_weight: system-assigned default on the learning artifact (set at creation, not by the LLM)
  - recency_factor: computed from session-boundary timestamps on the Graph node
  - outcome_reinforcement: derived from work order success/failure outcomes (aggregated on Graph nodes by the Write Path)
  - (1 - M): accessibility modifier, where M is the current methylation value on the Graph node. M=0 (fresh) = full accessibility. M=1 (fully methylated) = functionally invisible but still exists.
- Computes LIVE ∩ REACHABLE ∩ NOT_SUPPRESSED from active intent, ranked by effective weight
  - LIVE: no lifecycle event has superseded, closed, or abandoned the artifact (node state on Graph)
  - REACHABLE: causal path exists from active intent node through Graph edges (work order chains, intent hierarchy, explicit references)
  - NOT_SUPPRESSED: artifact's suppression mask does not include the current projection scope
- Determines aperture (computational depth for this turn):
  - Learned prior from regime/mode methylation values + current evidence from inspection result
  - Determines work order count and query scope
- Plans work orders, dispatches to HO1, merges results, applies quality gate
- Resolves intent lifecycle transitions deterministically (accepts/overrides/blocks HO1 proposals based on policy from Graph)
- Routes work orders to appropriate LLM (Ollama local vs external API) based on routing policy rulesets in the Graph. Routing is mechanical: HO2 reads policy, matches work order type to provider. Routing policy is installed by frameworks, not hardcoded.
- Detects session boundaries (turn arrival stops) and signals the Meta-Learning Agent
- At session end: triggers Write Path to append SESSION_END event and snapshot the Graph

### 5. HO3 — The Graph (Materialized View)

**HO3 is the Graph.** It is the in-memory directed graph derived from the Ledger by the Write Path's fold operation. It is the runtime state that HO2 reads from. It is transient — destroy it and rebuild it from the Ledger at any time.

- Nodes: artifacts with current resolved state (methylation value, suppression mask, lifecycle status, base_weight, session timestamps, outcome history)
- Edges: causal connections (work order parent chains, intent hierarchy, explicit references) built during folding
- Stores current methylation values for all signal accumulators (folded from signal_delta events)
- Stores invariant policy rulesets (installed by frameworks through Package Lifecycle)
- Stores consolidation artifacts (folded from consolidation events)
- HO2 reads. The Write Path updates. No other component writes to the Graph.
- Never scans, never computes, never executes on its own

**If you are adding active execution, LLM calls, prompt packs, timeout logic, daemon processes, or per-turn evaluation to HO3 — STOP. You are drifting. HO3 is a derived view. The Write Path maintains it. HO2 reads it. That is all.**

### 6. Work Order

The atom of dispatched work.

- Fields: wo_id, type (classify | execute | synthesize | tool_call), tier_target (HO1), input_context, constraints, parent_wo (for chaining), tool_permissions
- Lifecycle: planned → dispatched → executing → completed | failed
- Every state transition → Ledger entry
- Must reference a session, must have bounded token budget, must specify tier
- Scoped: defines what the executing agent can read and write

### 7. Prompt Contract

Governed LLM interaction template.

- Fields: contract_id, boundary, input_schema, output_schema, prompt_template, validation_rules
- HO1 loads contracts by ID, renders templates, validates I/O
- Every LLM call is auditable: contract ID + rendered prompt + validated output → Ledger entry
- Prompt packs (collections of related contracts) are themselves Ledger entries under gate scrutiny
- The system tracks which prompt packs produce good results (work orders succeed) and which don't (work orders rejected)

### 8. Package Lifecycle

Staging → gates → filesystem. The only way anything enters or leaves DoPeJarMo.

**Stage 1 — Author in staging.** Builder works in staging directory (NOT the governed filesystem). Writes framework definition, spec packs, packs, tests. Staging has no governance — it's a workbench.

**Stage 2 — Package in staging.** Builder assembles: manifest.json with SHA256 hashes for every file, framework ID, spec pack IDs, dependency declarations. Package is self-contained and internally verifiable.

**Stage 3 — Install through gates.** Package enters governed filesystem through gate validation at each hierarchy layer. All gates pass → files copied to correct locations, ownership recorded, Ledger entry appended. Any gate fails → entire package rejected. Atomic.

**Stage 4 — Verify.** System-wide gate check validates entire filesystem including new framework. Inconsistent → rollback.

**Genesis constraint:** Two bootstrap artifacts (GENESIS and KERNEL) are hand-verified by a human and create the install lifecycle itself. After those two, EVERYTHING has a framework. No exceptions.

### 9. Framework Hierarchy

Framework → Spec Pack → Pack → File. The logical structure that gives packages meaning.

```
Framework (FMWK-NNN)
│  Governance rules, boundaries, contracts
│  Scoped: single responsibility, explicit interfaces
│
├── Spec Pack (SPEC-NNN)
│   │  Describes contained packs
│   │  The architecture a builder reads to know what to assemble
│   │
│   ├── Prompt Packs — governed LLM templates
│   ├── Module Packs — code
│   ├── Quality Measures — validation schemas (JSON)
│   ├── Protocol Definitions — interface contracts
│   └── ... other pack types as needed
│
└── Files — actual artifacts within each pack
```

**Framework + Spec Pack = sufficient specification for a builder to assemble.** You receive a framework and its spec pack. You write the modules, write the prompts, wire the governance, deliver a package. You do not need to understand the full OS.

**Validation at every layer:**
- Framework: declares valid governance rules, boundaries, contracts?
- Spec Pack: references valid framework? Declares all contained packs?
- Pack: references valid spec pack? Files match manifest? Hashes correct?
- File: owned by exactly one pack? Hash matches ownership record? Correct location on disk?

Logical hierarchy and filesystem mirror each other. Governance gates validate compliance at every layer. Chain is cryptographically verifiable.

**Frameworks are microservice-scoped:** single responsibility, explicit interfaces, own your data, declare dependencies, independently testable, contract-first. A framework is a capability (HOW the system does something). Domain knowledge (dining, careers, health) is data within frameworks, not separate frameworks.

**One framework = one package.** Package is the framework made installable.

---

## The Dispatch Sequence (Per Turn)

```
Step 1: Aperture       HO2 reads methylation values from Graph + Prompt Pack Inspection result
                       → determines computational depth (work order count, query scope)

Step 2: Planning       HO2 translates intent → work orders, scoped by aperture
                       HO2 routes each work order to LLM provider per routing policy in Graph

Step 3: Execution      HO1 executes work orders under prompt contracts
                       HO1 submits signal_delta events to Write Path for entities/scopes within active intent
                       HO1 submits all call logs to Write Path → Ledger

Step 4: Verification   HO2 checks results against acceptance criteria (quality gate)

Step 5: Feedback       HO2 evaluates: did depth match outcome?
                       Outcome signal submitted as event → Write Path → folds into Graph for future aperture calibration
```

All steps are mechanical except Step 3 (HO1 calls LLM). The Graph (HO3) is read at Step 1 and updated by the Write Path after Steps 3 and 5.

---

## The Meta-Learning Agent

Not a tier. A **framework** — a cross-cutting governed agent created through the Package Lifecycle with identity, namespace, and scoped capabilities.

- Triggered by HO2 when session boundary is detected (turn arrival stops). HO2 owns session detection — the MLA does not poll or self-trigger
- Reads current methylation values and signal history from the Graph (HO3)
- Applies mechanical controls (these are framework logic, not primitive behavior):
  - **Time-based decay:** methylation values relax toward neutral over session boundaries (NOT wall-clock). Time step = session count.
  - **Density-relative normalization:** framework-defined thresholds scale proportionally to signal volume. Prevents flooding.
  - **Session cap:** no accumulator gains more than X delta per session. Prevents spikes.
  - **Traveler Rule:** methylation only becomes durable if reinforced across sessions. Single-session spikes decay. Cross-session reinforcement persists.
- **Bistable mode switching (framework logic):** MLA reads methylation values and applies hysteresis thresholds to prevent behavioral oscillation. Example: "Don't enter deep-work mode until M > 0.8. Don't exit until M < 0.3." When a threshold is crossed, MLA dispatches a work order to HO1 to submit a MODE_CHANGE event. This prevents the system from jittering between modes.
- **Consolidation (framework logic):** When methylation values cross framework-defined consolidation thresholds, MLA dispatches work orders to HO1 for pattern synthesis. HO1 structures consolidation artifacts (mechanical fields + human-relatable payload) and submits them as events to the Write Path → Ledger → Graph.
- All work goes through HO1 (one mouth). All results logged. All consolidation artifacts are governed Ledger entries.
- The MLA is itself a Ledger entry under gate scrutiny — the system tracks whether its consolidation produces good results.

---

## Intent Lifecycle

Intent is a first-class entity with explicit lifecycle transitions:

```
INTENT_DECLARED → INTENT_SUPERSEDED
                → INTENT_CLOSED
                → INTENT_FORKED
                → INTENT_ABANDONED
```

- HO1 proposes transitions (semantic). HO2 resolves transitions (mechanical, deterministic).
- All transitions logged. No inference. No "the user moved on."
- One active intent at a time (strict sequentiality). Block rather than guess.
- Policy rulesets in HO3 constrain which transitions are legal. HO2 reads and enforces.

**Two levels of intent extraction:**

1. **Prompt Pack Inspection** (pre-Attention): HO2 dispatches raw message to HO1 with governed prompt pack. HO1 runs constrained Ollama call (no context, strict JSON). Returns: entities, scopes, temporal markers, mode, sentiment, urgency. These fields drive Attention query.

2. **Semantic intent classification** (post-Attention): After Attention retrieves candidates, HO1 classifies full intent. May trigger proposed lifecycle transition. HO2 resolves.

**Bridge Mode** (rollout scaffolding only — must have kill date): Auto-create INTENT_DECLARED(scope=SESSION) at session start. One session-scoped intent. Compatibility layer while agents are not yet intent-aware. Not the architecture.

---

## The Primitive / Framework Boundary

**This is the line between "what we build as the OS" and "what frameworks configure."** If you are a builder working on DoPeJarMo primitives, stay above this line. If you are a builder authoring a framework, you use what's above and configure what's below.

**Primitive-level (the OS provides):**
- Ledger: append-only event store
- Signal Accumulator: accepts deltas, folds into methylation values on Graph nodes
- Write Path: synchronous append + fold + snapshot
- HO1: LLM execution + event submission
- HO2: mechanical orchestration + Graph reads + session detection
- HO3 (Graph): materialized view derived from Ledger
- Work Order: scoped, budgeted, lifecycle-tracked atom of work
- Prompt Contract: governed LLM interaction template
- Package Lifecycle: staging → gates → filesystem
- Framework Hierarchy: logical structure with cryptographic verification
- Suppression filtering: HO2 applies NOT_SUPPRESSED mask during LIVE ∩ REACHABLE. Suppression entries are Ledger events. Unsuppression reverses them. The primitive supports the filter; frameworks decide when to suppress.
- Context computation: HO2 computes LIVE ∩ REACHABLE ∩ NOT_SUPPRESSED by traversing Graph edges from active intent. This is the primitive algorithm. What the edges mean and how they're weighted is framework policy.
- Scoring formula: `score = field_match × base_weight × recency_factor × outcome_reinforcement × (1 - M)`. The formula is primitive. The field definitions and match rules are framework-configured.

**Framework-level (installed through Package Lifecycle):**
- Threshold definitions (what methylation value triggers consolidation or mode change)
- Bistable mode switching (hysteresis logic that prevents behavioral oscillation)
- Consolidation policy (when and how patterns are synthesized into new artifacts)
- Mechanical controls (decay rates, normalization ratios, session caps, Traveler Rule parameters)
- Gate taxonomy configuration (which signal types exist, their accumulation rates)
- Routing policy (which LLM provider handles which work order types)
- Intent lifecycle semantics (what FORKED means operationally, when multi-intent is allowed)
- Session boundary definition (what constitutes "turn arrival stops")
- Homeostasis parameters (healthy gate population ranges, distribution targets)
- Aperture calibration (how methylation values map to work order depth)
- base_weight defaults for new learning artifacts (system-assigned, not LLM-assigned)

**The test:** If changing it requires rebuilding the OS → primitive. If changing it requires installing/upgrading a framework → framework. Frameworks use primitives. Primitives don't know about frameworks.

---

## Homeostasis

The Meta-Learning Agent monitors gate population health at system level:

- Too many gates active → system over-opinionated
- Too few gates active → system not learning
- Signal distribution across gate types (entity / mode / stimulus / regime)
- Any gate type dominating → fixation on one dimension

Same gate + threshold mechanism applied to the distribution of gate activity. System-wide regulation.

---

## Failure Mode Protections

| Failure | What Happens | Protection |
|---|---|---|
| Flooding (ADHD) | Too many signals, everything important | Density-relative normalization |
| Fixation (OCD) | One pattern dominates | Reinforcement caps per session |
| Rigidity | Nothing changes | Time-based decay at session boundaries |
| Mania spikes | Single event overwhelms | Session cap + Traveler Rule |
| Manipulation | External actor forces weight change | No single stimulus flips a gate |
| Sensory overload | Gate population overwhelmed | Homeostasis monitoring |

---

## DoPeJarMo OS-Level Frameworks (Layer 1 — Required)

These frameworks must be installed for DoPeJarMo to operate. They are the first frameworks through the Package Lifecycle after GENESIS and KERNEL. See FRAMEWORK_REGISTRY.md for full segregation and dependency details.

- **DoPeJarMo Agent Interface** — the interactive session shell the operator logs into. First governed install (via CLI package tools from KERNEL). Once installed, all subsequent installs go through DoPeJarMo. Governed, versioned, upgradeable.
- **Storage Management** — Ledger trimming using methylation values to identify oldest + least used artifacts, pressure-driven at write rate. Required because without it, Ledger fills disk and the system hard stops.
- **Meta-Learning Agent** — decay, density normalization, session caps, Traveler Rule, bistable mode switching, consolidation, homeostasis monitoring. Required because without it, the cognitive failure mode protections don't exist.
- **Routing** — which LLM provider handles which work order types. Mechanical policy read by HO2. Required because without it, HO2 cannot dispatch work orders to the correct LLM provider.

---

## DoPeJar Day-One Frameworks (Layer 2 — Product)

These frameworks are built in staging and installed through DoPeJarMo after Layer 1 is operational. DoPeJarMo runs without them — but DoPeJar doesn't exist without them.

- **Memory framework** — learning artifacts, consolidation patterns, methylation-weighted Attention configuration
- **Intent framework** — lifecycle management, proposal/authority boundary, bridge mode scaffolding
- **Conversation framework** — DoPeJar's personality (Donna Paulsen + Pepper Potts + JARVIS), response generation, user-facing behavior

Additional capabilities arrive as additional frameworks over time.

---

## The Three Build Questions

1. **What Docker services does DoPeJarMo need?** (The OS — supports the nine primitives + Write Path)
2. **Which frameworks must DoPeJarMo have to operate?** (Layer 1 — Agent Interface, Storage Management, Meta-Learning Agent, Routing)
3. **Which frameworks does DoPeJar need installed day one?** (Layer 2 — Memory, Intent, Conversation)

---

## Boot Order

This is the install sequence. Each step must complete before the next can proceed.

```
1. GENESIS                    (hand-verified, creates governed filesystem + Ledger + hierarchy)
2. KERNEL                     (hand-verified, creates nine primitives + Write Path + Package Lifecycle tools incl. CLI)
   ── core operational invariant now holds ──
3. DoPeJarMo Agent Interface  (first governed install, via CLI package tools — DoPeJarMo can now accept operator sessions)
4. Storage Management         (keeps Ledger writable — installed through DoPeJarMo)
5. Meta-Learning Agent        (signal regulation, cognitive failure mode protection)
6. Routing                    (LLM provider dispatch policy)
   ── DoPeJarMo fully operational, operator can work ──
7. Memory                     (learning artifacts, Attention configuration)
8. Intent                     (lifecycle management, proposal/authority)
9. Conversation               (DoPeJar's personality, user-facing behavior)
   ── DoPeJar alive, users can interact ──
```

---

## Constraints

- All LLM calls go through HO1. One mouth, one log, one contract enforcement point.
- HO2 never calls LLM. Never interprets text. Never interprets human-relatable payloads.
- HO3 never executes. Stores data. Other components read and write.
- **THE CORE OPERATIONAL INVARIANT:** Nothing enters DoPeJarMo without a framework. After GENESIS and KERNEL (hand-verified), every artifact in the governed filesystem exists because a framework declared it, a package carried it through gates, and a Ledger event recorded it. Every file traces back — through its pack, its spec pack, its framework — to a hash-verified, Ledger-recorded provenance chain. The entire governed filesystem can be validated against the Ledger from cold storage with no runtime services. This is what makes DoPeJarMo a real operating system and guarantees the operator is never locked out.
- Frameworks are built in staging, never in the governed filesystem.
- The builder never touches the governed filesystem directly.
- Every LLM call logs: prompt, response, contract ID, token cost. Non-negotiable.
- Time effects use session boundaries, not wall-clock. Preserves replay.
- Block rather than guess. Determinism over cleverness.
- **Projection must be reversible** (NORTH_STAR Principle 5) — normative for Ledger/Graph behavior. Suppression is a view, never a deletion. Any derived state can be unwound to reveal full truth. This justifies ledger-first, no in-place mutation, and refold capability.
- **Intent is namespace, not label** (NORTH_STAR Principle 6) — normative for reachability Graph construction and fork semantics. Intent defines the root that gives edges their meaning and scopes conflict resolution. Not a tag. A structural boundary.

---

## Schemas Deferred to Genesis Framework Spec

The following concrete data schemas are required for implementation but are NOT architecture decisions — they are engineering specifications defined when the GENESIS and KERNEL bootstrap artifacts are authored:

- Ledger event schema (full event type catalog, field set per event type, sequence numbering)
- Graph node schema (methylation value storage, suppression mask format, lifecycle status, outcome history)
- Graph edge schema (edge types: work_order_chain, intent_hierarchy, explicit_reference)
- Work Order schema (full field definitions, state machine transitions, success/failure tracking)
- Prompt Contract schema (template format, template rendering syntax, validation rule DSL, example contract)
- Learning artifact schema (mechanical fields + payload structure, system-assigned defaults for base_weight)
- Governed filesystem layout (root paths, directory conventions mirroring framework hierarchy)
- Write Path fold logic (how each event type updates Graph state)
- Snapshot format (serialization of Graph state, sequence marker for replay-from)
- ID conventions (naming scheme for frameworks, spec packs, packs, contracts)
- One complete reference framework as canonical example (Memory framework recommended)
- `INTENT_FORKED` semantics are defined by the Intent Framework. The primitive layer treats it as a Ledger event establishing a new intent namespace with parent linkage; no execution or concurrency semantics are implied.

These schemas implement the nine primitives. They do not add to or change the primitives.

Genesis must also document: HO2 has access to machine time as a system service (for injecting timestamps into work order context). This is infrastructure, not a primitive.
