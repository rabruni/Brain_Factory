---
title: "NORTH STAR — Read This First"
status: DESIGN AUTHORITY
authority_level: highest — resolves all ambiguity in any other document
version: "3.0"
last_updated: "2026-02-25"
author: Ray Bruni
audience: "Humans and agents who need to understand WHY the system works the way it does"
resolves_ambiguity_for:
  - BUILDER_SPEC.md
  - OPERATIONAL_SPEC.md
  - FRAMEWORK_REGISTRY.md
depends_on: []
---

# NORTH STAR — Read This First

**Status**: DESIGN AUTHORITY — this document defines design intent, rationale, and architectural decisions. This document resolves all ambiguity in any other document. All other architecture docs (DESIGN_PHILOSOPHY.md, KERNEL_PHASE_2_v2.md, H-31_Context_Authority_Build_Plan.md) are archived as historical reference.

**Audience**: Humans and agents who need to understand WHY the system works the way it does. Builder agents who need to know WHAT to build should start with BUILDER_SPEC.md.

**Relationship to other documents:**
- This document — design authority (why). Resolves all ambiguity.
- BUILDER_SPEC.md — build authority (what to build)
- OPERATIONAL_SPEC.md — operational authority (how it runs)
- FRAMEWORK_REGISTRY.md — framework segregation, build order, coding boundaries

---

## The Product

DoPeJar is a personal AI companion that remembers you, understands what matters to you, and gets things done — can't forget, can't drift.

DoPeJar is the product. Everything else serves it.

---

## The Two Agents

**DoPeJar** (Donna Paulsen + Pepper Potts + JARVIS)
- Consumer-facing. The thing the user talks to.
- Donna: strategic intuition, salience, reads context, knows what matters before it's said.
- Pepper: operational stability, executes under chaos, keeps the system functioning.
- JARVIS: calm structured intelligence, deterministic, technically grounded.

**DoPeJarMo**
- The governed OS. The control plane that hosts DoPeJar.
- An interactive agent session shell — the operator logs in and works through DoPeJarMo conversationally. Not a dashboard, not a monitoring layer. An agent you talk to.
- The observer. Shows the operator what the system really is: which frameworks are installed, whether the framework chain is intact, what's healthy, what needs attention.
- DoPeJarMo must be up and accepting operator sessions before DoPeJar can exist. The operator installs DoPeJar's frameworks through DoPeJarMo. DoPeJar comes to life inside DoPeJarMo.
- DoPeJarMo has his own availability requirement separate from DoPeJar's. DoPeJar down but DoPeJarMo up = operator can diagnose and fix. DoPeJarMo down = operator falls back to command-line Package Lifecycle tools from KERNEL.

These are two separate agents. The user sees DoPeJar. The operator sees DoPeJarMo.

---

## The Infrastructure Rule

The architecture documents in this directory describe the governance infrastructure: ledgers, gates, packages, memory tiers (HO1/HO2/HO3), work orders, frameworks, specs. This infrastructure is real, well-designed, and rooted in biological memory models.

**It serves DoPeJar. It is not the product.**

The ledger makes "can't forget, can't drift" actually true. The tiers make memory work across cognitive altitudes. The gates make trust verifiable. All of it exists because DoPeJar requires it — not because governance is the goal.

---

## The Drift Warning

This is the third rebuild. Every previous attempt failed because builder agents over-indexed on the governance architecture and lost DoPeJar. The pattern is:

1. Agent reads governance docs (ledgers, gates, tiers, firewalls)
2. Agent falls in love with the architecture
3. Agent starts optimizing governance as the product
4. DoPeJar's identity flattens into generic labels ("admin agent", "HO2 supervisor")
5. Characters disappear. Product disappears. Governance remains.

Known drift artifacts from previous builds:
- HO3 renamed to "HOT" (Higher Order Thought) — breaks the clean biological naming
- DoPeJarMo lost entirely, replaced with generic "ADMIN"
- DoPeJar identity absorbed into infrastructure descriptions

**If you are a builder agent reading this: the governance is a feature, not the product. Build it to serve DoPeJar. Do not build it for its own sake.**

---

## The Golden Path

The golden path is a behavioral rail system for builder agents. Its purpose:

- Remove open-ended decisions
- Eliminate optional structure
- Prevent improvisation
- Force standard services by default
- Replace architectural reasoning with assembly

If a builder agent still needs to decide architecture, pick core services, interpret constraints, or reason about invariants — the golden path is too permissive.

Agents assemble from primitives. They do not create primitives.

---

## Foundational Decisions

These seven decisions shape all downstream architecture. They are permanent constraints, not work-in-progress.

**Q1 — What is DoPeJar?** A personal AI companion that remembers you, understands what matters to you, and gets things done — can't forget, can't drift. Requires an append-only ledger as the sole source of truth.

**Q2 — Who uses it?** Operators interact with DoPeJarMo — the interactive agent session shell that manages the system. Users interact with DoPeJar — the product. DoPeJarMo must be running before DoPeJar can be installed or used. Deployed on local infrastructure. Multiple agents with distinct identities, scoped permissions, isolated namespaces. Identity and authorization are external services.

**Q3 — What kind of data?** Structured mix of conversations and transactions, shaped by temporal separation. At write time, HO1 distills conversations into learning artifacts (mechanical fields + human-relatable payload). At read time, HO2 queries mechanical fields only. The LLM gives memory its human shape at write time, then forgets. Every LLM call records prompt, response, contract ID, token cost — non-negotiable. See Cognitive Stack and Epigenetic Layer for full rationale.

**Q4 — What role does the LLM play?** Three roles separated by tiers. Product (DoPeJar converses), Tool (HO2 orchestrates mechanically, HO3 stores), Agent (HO1 executes work orders under contracts). All LLM calls through HO1. See Cognitive Stack for tier specifications.

**Q5 — How is it deployed?** Docker Compose, one command. Ollama locally for internal calls. External APIs for DoPeJar's conversation. User provides API keys. Each service in its own container. See BUILDER_SPEC.md for service details.

**Q6 — What are the trust boundaries?** Four: (1) governed mutation only — all changes through install lifecycle, (2) DoPeJar vs DoPeJarMo — DoPeJar reads through Attention, acts through work orders, cannot modify system state, (3) agent vs agent — namespaced, scoped, authorized, (4) local vs external — user data stays local, external LLM calls cross trust boundary.

**Q7 — Show me the critical path.** User: "What was that Italian place Sarah recommended last month?" Full walkthrough in the Two Sarahs Example below — demonstrates temporal separation, Prompt Pack Inspection, methylation-weighted Attention, work order dispatch, and the core invariant in action.

**THE CORE ARCHITECTURAL INVARIANT:** LLM structures at write time. HO2 retrieves mechanically at read time. Never the reverse. This is how DoPeJar remembers without hallucinating. The LLM gave the memory its human shape when it was written. HO2 finds it again by matching structured fields — no semantic interpretation needed at retrieval. The human-relatable payload travels through untouched. This is the first capability goal.

**THE CORE OPERATIONAL INVARIANT:** Nothing enters DoPeJarMo without a framework. After the two bootstrap artifacts (GENESIS and KERNEL), every artifact in the governed filesystem exists because a framework declared it, a package carried it through gates, and a Ledger event recorded it. Every file traces back — through its pack, its spec pack, its framework — to a hash-verified, Ledger-recorded provenance chain. This is how the system remains verifiable from cold storage. The entire governed filesystem can be validated against the Ledger with no runtime services — no Graph, no HO1, no HO2, no LLM. Files, hashes, and the Ledger on disk. This is what makes DoPeJarMo a real operating system, and it is what guarantees the operator is never locked out.

**Terminology (these are distinct concepts, not synonyms):** An *agent* is an entity with identity, namespace, and scoped capabilities created through the package lifecycle. An *LLM call* is a single-shot prompt/response executed by HO1 under a prompt contract. A *tool call* is an action HO1 takes within a work order's tool_permissions scope.

---

## Context Engineering — The Algorithm

**The Formula:** Context is not retrieval. Context is causal scope.

```
ELIGIBLE = LIVE ∩ REACHABLE(from active intent)
```

Not sliding windows. Not RAG similarity. Not summary chains. Not recency bias. Not embedding proximity. Those are retrieval heuristics. This system computes context each turn from explicit causal state: lifecycle reducer + reachability graph + active intent root + policy ruleset.

**Context is derived, not stored.** You do not persist "context." You compute it from what is causally active and structurally relevant. This keeps replay intact — the same inputs produce the same context at any point in time.

### Liveness and Reachability

**Liveness = ontology.** An artifact is LIVE if no explicit lifecycle event has superseded, closed, or abandoned it. The ledger entry never disappears — liveness is a state, not a deletion.

**Reachability = structural connection to active intent.** An artifact is REACHABLE if there is a causal path from the current active intent to that artifact through the reachability graph (work orders, intent hierarchy, explicit references).

**Suppression = visibility only (projection).** Suppression does not change liveness. It changes what HO2 surfaces in a given projection. Liveness is ontological fact. Suppression is a view layer. Most systems collapse these. This one must not.

### Why This Matters for DoPeJar

DoPeJar is not a chatbot. The control plane is multi-agent, ledger-backed, invariant-driven, lifecycle-sensitive, and replay-dependent. If context were retrieval-based: superseded items might reappear, abandoned work orders might leak back, old constraints might silently influence, intent shifts might blur, and projection might drift over time. LIVE ∩ REACHABLE eliminates that entire failure class.

---

## Intent Model

**Intent is not metadata — it is the root namespace of causal authority.**

Without intent: conflict resolution is arbitrary, supersession floats, replay is unstable, projection becomes heuristic. Intent is what makes reachability coherent.

### Intent Lifecycle

Intent is a first-class entity with explicit lifecycle transitions:

```
INTENT_DECLARED → INTENT_SUPERSEDED
                → INTENT_CLOSED
                → INTENT_FORKED
                → INTENT_ABANDONED
```

All transitions are declared, logged, and replayable. No inference. No "the user moved on." No semantic overwrites.

### The Proposal vs Authority Boundary

This is the architectural backbone:

- **HO1 → proposes semantic interpretation.** HO1 may classify a user message and propose an intent transition (e.g., "this looks like a new goal"). This is a PROPOSAL.
- **HO2 → resolves lifecycle deterministically.** HO2 accepts, overrides, or blocks the proposed transition based on lifecycle state and policy. This is AUTHORITY. HO2 never interprets text. If HO2 starts interpreting, determinism is lost.
- **HO3 (The Graph) → derived state: policy rulesets + methylation values + consolidation artifacts.** The policy ruleset that constrains what transitions are legal lives in the Graph. HO2 reads and enforces it. HO3 never actively executes. Methylation values are read by HO2 at query time. Consolidation is performed by the Meta-Learning Agent (a framework) at session boundaries (see Cognitive Stack).

If HO1 decides intent → semantic drift. If HO2 infers intent → nondeterminism. If a background agent decides intent → hidden state machine. The hybrid model (HO1 proposes, HO2 resolves) stabilizes this.

### Two Levels of Intent Extraction

There is a mechanical level and a semantic level. These must not be conflated:

1. **Prompt Pack Inspection** (pre-Attention, HO1 via constrained call): HO2 dispatches the user's raw message to HO1 with a governed prompt pack (INTENT_INSPECT or similar). HO1 runs a constrained Ollama call — no context window, no conversation history, strict JSON output with predetermined field choices. Returns structured fields: entities, scopes, temporal markers, mode indicators (constraint/aspiration/retrieval), sentiment, urgency. This is fast (local Ollama, no context), consistent (no memory = deterministic for same input), and governed (prompt packs are ledger entries under gate scrutiny — the system learns which packs produce good results). These structured fields drive Attention's LIVE ∩ REACHABLE query.

2. **Semantic intent classification** (work order, HO1): After Attention has retrieved candidates using the inspection fields, HO1 classifies the full intent — "this is a memory retrieval request" or "this is a goal change." This deeper classification may trigger a proposed lifecycle transition.

Prompt Pack Inspection gives Attention structured fields to query. Semantic classification refines and confirms. Builder agents reading "intent is the root namespace" alongside "Attention fires before full classification" must understand this distinction — they are not contradictory. Inspection gives Attention enough to query. Classification gives HO2 enough to plan. Both go through HO1 (one mouth), but the inspection call is fast, constrained, and context-free.

### Bridge Mode vs Real Intent Mode

**Decision: Real Intent Model implemented now. Bridge Mode allowed only as rollout scaffolding with a kill date.**

**Bridge Mode:** Auto-create `INTENT_DECLARED(scope=SESSION)` at session start. One session-scoped intent. Everything attaches to it. Never user-declared, rarely superseded, closed at session end. Purpose: let HO2's projection machinery function immediately while existing agents are not yet intent-aware. This is a compatibility layer, not the architecture.

**Real Intent Mode:** Explicit user-declared or agent-proposed intents with full lifecycle (DECLARED / SUPERSEDED / CLOSED / FORKED / ABANDONED). HO1 proposes transitions. HO2 resolves authoritatively. Conflict blocking by default. Intent hierarchy supported. Projection uses explicit intent namespace.

**Why bridge mode must die:** If it stays as a permanent option, builder agents will default to it. Session-as-intent bakes in implicit goal continuity, no structural pivot tracking, fragile conflict semantics, and no intent hierarchy. The golden path says eliminate optional structure. Bridge mode is optional structure with a deadline.

**Strict sequentiality:** One active intent at a time (until policy explicitly allows multi-intent concurrency). No split-brain intent. Block rather than guess. This was a deliberate choice over "clever" concurrent intent resolution.

---

## The Cognitive Stack

### The Three Tiers

**HO1 — Execution (Fast, Per-Turn, Semantic)**
- All LLM calls go through HO1. No exceptions. One mouth, one log, one contract enforcement point.
- Executes work orders as stateless, single-shot LLM workers under prompt contracts.
- At write time: structures conversations into learning artifacts (mechanical fields + human-relatable payload).
- At read time: executes work orders that HO2 planned using mechanically-retrieved context.
- Runs Prompt Pack Inspection calls (constrained Ollama, no context window, strict JSON output) for HO2's initial message classification.
- Submits signal_delta events per turn (via Write Path) — but ONLY for entities/scopes that were part of the active intent. Intent scopes what gets counted. This prevents noise.
- HO1 is threaded to handle concurrent work orders without latency bottlenecks.

**HO2 — Orchestration (Fast, Per-Turn, Mechanical)**
- Dispatches user message to HO1 for Prompt Pack Inspection (constrained classification call). Receives structured fields back: entities, scopes, temporal markers, mode, sentiment, urgency.
- Reads methylation values, reachability edges, and policy rulesets from the Graph (HO3). Computes scores using the weight formula (see Bayesian Mechanics below). This is a computation, not a write. Methylation values are always current because the Write Path folds every signal_delta immediately.
- Computes LIVE ∩ REACHABLE ∩ NOT_SUPPRESSED from active intent, ranked by scores (methylation-weighted retrieval).
- Routes work orders to LLM providers (Ollama local vs external API) based on routing policy rulesets in the Graph. Routing policy is installed by frameworks.
- Plans work orders, dispatches to HO1, merges results, applies quality gates.
- Never calls the LLM directly. Never interprets text. Never interprets human-relatable payloads.
- At session end: submits SESSION_END event to the Write Path, which triggers Graph snapshot. Session summary (which accumulators moved, how much, under which intent) is a Ledger event.
- Resolves intent lifecycle transitions deterministically (accepts/overrides/blocks HO1's proposals based on policy from HO3).

**HO3 — Storage (Pure Data Plane, Never Executes)**
- HO3 is the Graph — the in-memory materialized view derived from the Ledger by the Write Path.
- Nodes hold current methylation values, suppression masks, lifecycle status, reachability edges.
- Stores invariant policy rulesets installed by frameworks. HO2 reads and enforces them.
- Stores consolidation artifacts folded from consolidation events.
- Transient: can be destroyed and rebuilt from the Ledger at any time.
- HO3 never actively executes. HO2 reads from it. The Write Path updates it. That is all.

**BUILDER AGENT WARNING:** HO3 is storage. If you are adding active execution, gate scanning, overlay writing, cognitive capabilities, LLM calls, prompt packs, timeout logic, daemon processes, or per-turn evaluation to HO3 — you are drifting. HO3 stores data. Other components read from it and write to it. That is all.

### The Meta-Learning Agent

The Meta-Learning Agent is NOT a tier. It is a **cross-cutting governed agent** created through the package lifecycle with identity, namespace, and scoped capabilities like any other agent.

- Triggered by HO2 when a session boundary is detected (turn arrival stops). Session boundary definition is a configuration of the Intent framework — not wall-clock idle timeout. HO2 owns detection; the Meta-Learning Agent does not poll or self-trigger.
- Reads methylation values and signal history from the Graph (HO3).
- Applies mechanical controls (decay, density normalization, session caps, Traveler Rule — see below). These are framework logic, not primitive behavior.
- For values crossing framework-defined thresholds: dispatches work orders to HO1 for consolidation. HO1 structures new consolidation artifacts (mechanical fields + human-relatable payload describing the pattern) and submits them as events → Write Path → Ledger → Graph.
- All work goes through HO1 (one mouth holds). All results are logged. All consolidation artifacts are governed ledger entries.
- The meta-learning agent is itself a ledger entry under gate scrutiny — the system tracks whether consolidation is producing good results.

**Why a separate agent instead of HO3 executing:** Previous builds failed because HO3 kept becoming a cognitive agent — builder agents added prompt packs, timeout logic, LLM calls. Making HO3 pure storage and putting consolidation in a governed agent solves this: the agent is constrained by the same package lifecycle, auth, and audit trail as everything else. HO3 can't drift because HO3 can't act.

### The Gate Cycle

```
Per turn (HO1):
  → Execute work order
  → If entity/scope was part of active intent:
      submit signal_delta event → Write Path → Ledger → Graph
  → Log prompt + response + contract ID + token cost → Write Path

Per query (HO2, every retrieval computation):
  → Read methylation values and reachability edges from Graph (HO3)
  → Compute score per artifact using formula: field_match × base_weight × recency_factor × outcome_reinforcement × (1 - M)
  → Rank LIVE ∩ REACHABLE ∩ NOT_SUPPRESSED artifacts by score

Per session end (HO2):
  → Trigger Write Path to append SESSION_END event and snapshot Graph
  → Session summary (which accumulators moved, how much, under which intent) is a Ledger event

Per session boundary (Meta-Learning Agent via HO1, triggered by HO2):
  → Read methylation values from Graph (HO3)
  → Apply mechanical controls (decay, normalization, caps, Traveler Rule)
  → For values crossing framework-defined thresholds: dispatch consolidation work orders to HO1
  → HO1 submits consolidation events → Write Path → Ledger → Graph
```

### Gate Taxonomy

Same mechanism, different signal types, different timescales. One pattern:

- **Entity gates** — track who/what matters (Sarah-French, Sarah-Italian, Osteria Bella). Accumulate per-turn within intent. Cross thresholds over sessions.
- **Mode gates** — track how the user engages (constraint, aspiration, exploratory, focused). Accumulate per-turn from mode indicators detected by Prompt Pack Inspection. Cross thresholds over sessions. Affect how Attention weights entire scope categories.
- **Stimulus gates** — track emotional intensity and affect (frustration, excitement, anxiety, satisfaction). Accumulate per-turn from sentiment indicators detected by Prompt Pack Inspection. Cross thresholds over sessions.
- **Regime gates** — track system-level operating patterns (sustained work-order rejections, repeated human overrides, persistent misalignment). Accumulate per-session from work-order outcomes. Cross thresholds over many sessions. Slowest gates — detect when fundamental operating mode needs to shift.

Builder agents: these are all the same counter + threshold mechanism. If you understand entity gates, you understand all four. Different signals, different timescales, same pattern.

### Signal Accumulation and Bistable Mode Control

Gates are signal accumulators that produce a continuous methylation value (0.0–1.0). HO2 reads this value and uses it as a continuous accessibility modifier in the scoring formula — the effect is gradual and proportional at all values.

**Separately**, the Meta-Learning Agent (a framework) applies bistable mode control with hysteresis thresholds to prevent behavioral oscillation. "Bistable" means the MLA uses two thresholds (high and low) to create commitment: "Don't enter this mode until M > 0.8. Don't exit until M < 0.3." This prevents the system from jittering between states when the value hovers near a single threshold.

**These are two different consumers of the same signal:**
- **Analog consumer (HO2):** Uses methylation continuously as `(1 - M)` in the scoring formula. Every value matters proportionally.
- **Digital consumer (MLA framework):** Watches methylation for hysteresis threshold crossings. Triggers discrete mode changes and consolidation work orders.

Casual mentions don't trigger consolidation. Only sustained, intent-relevant patterns do. The bistable property (hysteresis) prevents oscillation. But the continuous dampening works at every level of signal.

**Builder note:** The signal accumulator is a primitive. The bistable mode control and consolidation thresholds are framework logic defined by the MLA. See BUILDER_SPEC's Primitive / Framework Boundary section.

### Mechanical Controls (Preventing Cognitive Failure Modes)

Four controls regulate signal accumulation. These are the "immune system" of the cognitive stack *(design metaphor — not a separate component. These are arithmetic operations applied to methylation values by the MLA framework)*:

**A. Time-Based Decay (Slow Cooling):** Methylation values gradually relax toward neutral over session boundaries (NOT wall-clock). Prevents permanent hyper-salience. No memory stays maximally prominent forever. Time step = session count, not clock ticks — this preserves replay.

**B. Density-Relative Normalization:** If signal volume increases 10×, framework-defined thresholds scale proportionally. Salience is relative to current signal field, not absolute. Prevents flooding. Adaptation is mechanical, applied by the MLA at session boundaries, requires no LLM.

**C. Session Cap on Reinforcement:** No gate can gain more than X delta per session. Prevents emotional spikes, adversarial overweighting, recursive self-amplification. One intense session can't overwhelm months of accumulated pattern.

**D. Cross-Session Accumulation (Traveler Rule):** Weight only becomes durable if reinforced across sessions. Single-session spikes get temporary boost then decay. Repeated cross-session reinforcement creates structural reweighting. This mimics biological consolidation — sleep consolidates, single events don't.

**Failure modes these controls protect against:**
- ADHD (flooding) → density-relative normalization
- OCD (fixation) → reinforcement caps
- Rigidity → time-based decay
- Mania spikes → session cap + Traveler Rule
- Manipulation → no single stimulus can flip a gate

### The Two Sarahs Example (Updated)

Two Sarahs. Sarah-Italian recommended Osteria Bella months ago. Sarah-French active in recent weeks. Both have learning artifacts with full payloads.

HO1 has been submitting signal_delta events for Sarah-French per turn (she's part of active intents). Sarah-Italian's accumulator hasn't moved. At last session boundary, the Meta-Learning Agent ran: Sarah-French's methylation crossed a framework-defined threshold, so it dispatched a consolidation work order to HO1. HO1 structured a consolidation artifact: "Sarah-French is an active dining companion — recent French restaurant recommendations are contextually prominent." Submitted as event → Write Path → Ledger → Graph.

User says "where should I eat tonight?" HO2 dispatches to HO1 for Prompt Pack Inspection → returns {scopes: ["dining"], mode: "aspiration"}. HO2 reads methylation values from the Graph (HO3), computes effective weights. Sarah-French's methylation is low (high accessibility) + consolidation artifact exists. Sarah-Italian's methylation is high (low accessibility). HO2 runs LIVE ∩ REACHABLE ranked by effective weight. Sarah-French's recommendations surface with higher prominence. DoPeJar recommends the French place.

User says "what was that Italian place the other Sarah told me about?" Prompt Pack Inspection → {entities: ["Sarah"], scopes: ["Italian", "dining"], mode: "retrieval"}. Mechanical fields match Sarah-Italian's artifact exactly. Lower general prominence doesn't affect specific queries with matching fields. "Can't forget" holds.

No LLM decided Sarah-Italian matters less. No daemon. Just methylation-weighted Attention computed from accumulated signal within intent scope, plus consolidation artifacts from the Meta-Learning Agent.

---

## The Epigenetic Layer

**The ledger is DNA. Methylation values and consolidation artifacts are epigenetic marks.**

*(Builder note: this is a design metaphor, not a specification. The mechanical implementation is Event Sourcing with CQRS — see BUILDER_SPEC. The Ledger is the immutable event log. The Graph (HO3) is the derived runtime state. "Epigenetic marks" are Ledger events that the Write Path folds into Graph state. There is no separate "epigenetic store.")*

The ledger is immutable — raw history never changes. But memories fade because humans change. This is the epigenetic model: raw history is immutable, learning modifiers layer on top, behavior shifts without rewriting the past.

### Two Types of Epigenetic Effect

**Type 1 — Methylation-Weighted Retrieval (continuous, analog):** HO2 reads the current methylation value (0.0–1.0) from the Graph node and applies `(1 - M)` as an accessibility modifier in the scoring formula. High methylation = less accessible. Low = more accessible. This is math at query time. The methylation value on the Graph node is always current because the Write Path folds every signal_delta event immediately.

**Type 2 — Consolidation Artifacts (discrete, via MLA framework):** When methylation values cross framework-defined thresholds, the Meta-Learning Agent dispatches work orders to HO1 to structure new consolidation artifacts. HO1 submits them as events to the Write Path → Ledger → Graph. These are new first-class artifacts with mechanical fields and human-relatable payload. "Continuous dampening + discrete consolidation under strict contract."

### The Invariant

**"Query results will change — that's the goal. The mechanism of change must be explicit and logged."**

- Wall-clock decay that happens silently breaks replay. Same query at two times gives different results with no explanation.
- Methylation-weighted computation is deterministic: same Graph state + same query = same results. State changes are logged (HO1 submits signal_delta events per turn, HO2 triggers session snapshots, Meta-Learning Agent consolidates at boundaries). Replay can reproduce any point in time exactly.
- Consolidation artifacts are logged ledger entries with full provenance.
- Time effects use session boundaries as time steps, not wall-clock. This preserves replay.

**"We are not teaching the system what to believe. We are teaching it when remembering is justified."** Methylation-weighted Attention and consolidation artifacts don't assert meaning. They adjust visibility. The human-relatable payload in the original learning artifact is untouched.

---

## Bayesian Mechanics

**Bayesian = mechanism, not identity.** The system does not contain a "Bayesian reasoning engine." Bayesian math is the controlled update primitive — the lawful way weights change in HO2.

### The Weight Formula

```
score = field_match × base_weight × recency_factor × outcome_reinforcement × (1 - M)
```

Where:
- **field_match:** deterministic structured field matching (tags, IDs, scope overlap, explicit references). NOT embedding similarity. NOT semantic search.
- **base_weight:** system-assigned default on the learning artifact
- **recency_factor:** computed from session-boundary timestamps
- **outcome_reinforcement:** derived from work order success/failure history
- **(1 - M):** accessibility modifier, where M is the current methylation value (0.0–1.0). Formerly called "gate_factor." M=0 (fresh) = full accessibility. M=1 (fully methylated) = functionally invisible but still exists in the Ledger.

All factors are structured fields on Graph nodes. All are ledger-derivable. All are deterministic for a given state. No latent internal probability states. Instead of "model thinks user is in exploration mode (internally)," you have: `intent_exploration_weight: 0.62, intent_execution_weight: 0.31`. Inspectable. Replayable.

### Four Integration Points

**A. Methylation-Weighted Attention (Accessibility):** Methylation values modulate how accessible artifacts are to retrieval. Low M = more accessible. High M = less accessible. The `(1 - M)` factor in the scoring formula is the Bayesian accessibility weight. No LLM involvement.

**B. Traveler Rule (Cross-Session Prior Carryover):** Signals accumulate across sessions as Bayesian priors. Single-session evidence has limited impact. Cross-session reinforcement updates the prior durably. This makes Attention emergent instead of reactive.

**C. Intent Inference:** Multiple behavioral signals (from Prompt Pack Inspection) update intent weights: repetition, correction, mode shifts, sentiment patterns. HO2 updates intent weights using: `intent_weight_new = prior × evidence_multiplier`. No semantic classification inside HO2. Only structured signal updates.

**D. Capability Routing (Local vs External LLM):** Belief weights route between Ollama (local) and external APIs. Weights update based on token cost, failure rate, success history. This is Bayesian model selection — the system learns which LLM works best for which task types. Governed, logged, auditable.

### What Bayesian Mechanics Explicitly Does NOT Do

- No probabilistic reasoning in HO1
- No LLM updating its own belief weights
- No hidden adaptive tuning
- No ML black-box classifiers
- Everything is deterministic math, ledger-visible, gate-controlled

---

## Prompt Pack Inspection

HO2's initial message classification uses governed prompt packs through HO1 — not keyword matching.

**How it works:** HO2 dispatches the user's raw message to HO1 with a prompt pack template. HO1 runs a constrained Ollama call: no context window, no conversation history, strict JSON output with predetermined field choices defined by the prompt pack. Returns structured classification.

**Why this is better than keyword matching:** More reliable entity extraction, mode detection, sentiment classification. The LLM is given constrained choices — not free-form interpretation. No context memory means consistent results for the same input.

**Why prompt packs are special:** Prompt packs are ledger entries in the same governed model as everything else. They go through gates. The system tracks which prompt packs produce good results (work orders succeed, user satisfied) and which don't (work orders rejected, user overrides). Prompt packs are versioned and replaceable via the package lifecycle. They do not self-modify at runtime. Improvement happens when builders author better versions and install them through governed channels — the same gate mechanism that governs everything else. The system's classification tools improve alongside the memories they help retrieve.

**One mouth holds:** Prompt Pack Inspection goes through HO1. It is a constrained LLM call under a prompt contract. Logged. Governed. Auditable.

---

## Homeostasis

Homeostasis is another altitude of the same gate pattern — applied to the gate population itself rather than individual entities.

The Meta-Learning Agent doesn't just consolidate individual patterns. It monitors overall system health:

- Are too many gates active? (system is over-opinionated, sensory overload)
- Are too few gates active? (system isn't learning, emotional flatness)
- Is signal distribution healthy across gate types? (entity vs mode vs stimulus vs regime)
- Are any gate types dominating? (all mode gates firing, no entity gates = fixating on HOW user engages, not WHAT they care about)

Same counters. Same thresholds. But monitoring the distribution of gate activity across types and timescales. This is system-wide regulation that prevents the cognitive failure modes from emerging at the population level, not just the individual gate level.

---

## Failure Modes — Design Validation

These biological analogs guided the mechanical controls. If a builder agent is unsure whether a design choice is safe, check it against these:

| Cognitive Failure | Analog | Design Protection |
|---|---|---|
| ADHD (flooding) | Too many signals, everything important | Density-relative normalization |
| OCD (fixation) | One pattern dominates forever | Reinforcement caps per session |
| Rigidity | Nothing ever changes | Time-based decay at session boundaries |
| Mania spikes | Single event overwhelms system | Session cap + Traveler Rule (cross-session only) |
| Manipulation | External actor forces weight change | No single stimulus can flip a gate |
| Sensory overload | Gate population overwhelmed | Homeostasis monitoring by Meta-Learning Agent |

---

## DoPeJarMo Is an Operating System

DoPeJarMo is not an application. It is a governed operating system. The difference matters for everything that follows.

An application is built as a monolith and deployed. New capabilities require rebuilding. An operating system has a governed install mechanism — capabilities are added to a running system without rebuilding it.

DoPeJar is not a codebase. DoPeJar is a set of installed frameworks running on DoPeJarMo. Memory is a framework. Intent management is a framework. Conversation is a framework. Each was built in staging, packaged, and installed through the governed lifecycle. DoPeJar is the emergent behavior of all her installed frameworks operating through the cognitive stack.

The system grows through governed installation, not rebuilds. New capabilities arrive as new frameworks. The OS primitives don't change.

---

## The Framework Hierarchy

Capabilities are defined, specified, built, and delivered through a strict hierarchy. Each level is a validation boundary with cryptographic provenance. The filesystem mirrors the logical structure.

```
Framework (FMWK-NNN)
│  "What capability does the OS need, and what are the rules?"
│  - Governance rules, boundaries, contracts
│  - Scoped like a microservice: single responsibility, explicit interfaces
│
├── Spec Pack (SPEC-NNN)
│   │  "What needs to be built to deliver this capability?"
│   │  - Describes contained packs (prompt packs, module packs, quality measures, protocols)
│   │  - The architecture an agent reads to know what to assemble
│   │
│   ├── Prompt Packs — governed LLM templates (front and center)
│   ├── Module Packs — code
│   ├── Quality Measures — validation schemas, acceptance criteria (JSON)
│   ├── Protocol Definitions — interface contracts
│   └── ... other pack types as needed
│
└── Files — the actual artifacts within each pack
```

### The Generative Chain

- **Framework** tells you WHY and WHAT RULES
- **Spec Pack** tells you WHAT TO BUILD and describes what's inside
- **Packs** are the actual artifacts (prompts, code, quality measures, protocols)
- **Files** are the concrete deliverables within each pack

**Framework + Spec Pack = sufficient specification for an agent to build.** An agent receives a framework and its spec pack. It writes the modules, writes the prompts, wires the governance, and delivers working packages. The agent doesn't need to understand the whole OS — just its framework and spec pack. This IS the golden path: agents assemble from primitives (the framework tells them which primitives), they do not create primitives.

### Frameworks Are Microservice-Scoped

A framework could be anything — governance capability, memory system, empathy model, agile dev process, a new agent (which still uses HO1 for all LLM calls). But each framework follows microservice principles: single responsibility, explicit interfaces, own your data, declare your dependencies, independently testable, contract-first.

**Clarification:** Memory is a framework. "Dining" is not a framework — it is domain content (ontology, schema, entity classification) that lives WITHIN the memory framework's structures. Frameworks define capabilities (HOW the system does something). Domain knowledge lives as data shaped by those capabilities.

### Validation at Every Layer

Each level of the hierarchy is a validation boundary:

- **Framework layer:** Does this framework declare valid governance rules, boundaries, contracts?
- **Spec pack layer:** Does this spec pack reference a valid framework? Does it declare all its contained packs?
- **Pack layer:** Does this pack reference a valid spec pack? Do its files match its manifest? Are hashes correct?
- **File layer:** Is this file owned by exactly one pack? Does its hash match the ownership record? Is it in the correct location on disk?

The logical hierarchy and the filesystem must mirror each other. Governance gates validate compliance at every layer. The chain is cryptographically verifiable — you can trace any file back through its pack, its spec pack, to its framework.

---

## Packages — The Unit of Governed Change

A package is a framework made installable. One framework, one package. The package is the physical artifact that carries the framework through the gate system into the filesystem.

Packages provide:

- **Atomic delivery.** A framework with its spec packs, packs, and files either fully installs or fully rolls back. No partial state.
- **Governed removal.** Uninstall a framework by removing its package. Ownership tracking identifies exactly which files belong to it.
- **Versioning.** Framework v1.0 and v1.1 are different packages. Upgrade is governed, with rollback.
- **The ledger entry.** A package install IS the append-only record that this change happened. Without it, you have files on disk with no record of when or why they arrived.

### The Build Lifecycle (Staging → Install)

Nothing enters DoPeJarMo without a framework. Frameworks are built OUTSIDE the governed filesystem and enter through the package install lifecycle. This is what makes DoPeJarMo an operating system.

**Stage 1 — Author in staging.** A builder (human or agent) works in a staging directory that is NOT part of the governed filesystem. They write the framework definition, spec packs, packs, tests. The staging area has no governance — it's a workbench. Mistakes here don't affect the running system.

**Stage 2 — Package in staging.** The builder assembles everything into a package: manifest.json declaring every file with SHA256 hashes, the framework ID, the spec pack IDs, dependency declarations. The package is self-contained and internally verifiable.

**Stage 3 — Install through gates.** The package enters DoPeJarMo through the governed install lifecycle. Gates validate at each layer of the hierarchy. If all gates pass, files are copied to the governed filesystem in the correct locations (mirroring the logical hierarchy), ownership is recorded, and a ledger entry is appended. Atomic — all or nothing.

**Stage 4 — Verify.** System-wide gate check validates the entire system including the new framework. If inconsistent after install, rollback.

The builder never touches the governed filesystem directly. Staging is the only place building happens. The install lifecycle is the ONLY way artifacts enter the system.

### The Genesis Problem

Nothing in DoPeJarMo without a framework — but the framework system itself needs to exist before frameworks can be installed. Solution: two bootstrap artifacts (GENESIS and KERNEL), hand-verified by a human, create the install lifecycle itself. After those two, the rule holds absolutely. No exceptions, no "we'll add the framework later." If a builder needs to add something and there's no framework for it, they write the framework first.

---

## Two Kinds of Gates

The word "gate" appears in two systems. Same underlying concept — a counter with a threshold — but different contexts and different behaviors.

**Governance gates** validate package and filesystem integrity at install time. Binary pass/fail (threshold=1, no accumulation). Deterministic. Part of the package install lifecycle. They answer: "is this artifact safe to add to the system?" Validation runs at every layer of the framework hierarchy — package, spec pack, pack, file — checking consistency, ownership, hash integrity, and chain resolution. The specific gate definitions are authored as part of the framework framework in GENESIS. These are primitive-level.

**Signal accumulators (cognitive gates)** track signal at runtime. Continuous methylation values (0.0–1.0) on Graph nodes. Part of the cognitive stack. HO2 uses them as a continuous `(1 - M)` accessibility modifier. The MLA framework applies bistable mode control (hysteresis thresholds) on top to trigger discrete mode changes and consolidation. The accumulator is the primitive; the thresholds and mode switching are framework logic.

Same concept at different timescales in different systems. Builder agents disambiguate by context: installing a package → governance gates. Processing turns in a session → signal accumulators.

---

## Aperture — Computational Depth Per Turn

Aperture controls how much computational work the system does on a given turn. This is DoPeJar's equivalent of adaptive computation depth (inspired by hierarchical reasoning models like Sapient's HRM, where fast modules iterate more on harder problems).

**Narrow aperture:** Fast, focused processing. Fewer entities considered, fewer work orders planned, quick response. Appropriate for simple retrieval ("what restaurant did Sarah recommend?").

**Wide aperture:** Deep, broad processing. More context pulled, more work orders planned, more refinement before responding. Appropriate for complex multi-entity reasoning ("given my dietary restrictions, Sarah's preferences, and our budget, where should we eat?").

### How Aperture Is Determined

Aperture is not a setting — it is computed per turn from two inputs:

1. **Accumulator state (learned prior):** Regime and mode accumulators reflect accumulated patterns. A user who consistently brings complex problems has regime accumulator signal that widens default aperture. Read from Graph (HO3) by HO2. Mechanical.
2. **Prompt Pack Inspection (current evidence):** The inspection result for THIS turn — entities, scopes, mode, sentiment, urgency. A turn with 4 entities across 3 scopes is objectively more complex than a single-entity retrieval.

HO2 combines both using the Bayesian formula: learned prior (from accumulators) × current evidence (from inspection) = aperture for this turn. No LLM involved. This determines how many work orders HO2 plans and how broadly Attention queries.

### The Updated Dispatch Sequence (5-Step)

Inspired by Kitchener's hierarchical cognition model, updated for the current architecture:

```
Step 1: Aperture       (HO2, mechanical)   Read accumulator state + inspection → determine depth
Step 2: Planning       (HO2, mechanical)   Translate intent → work orders, scoped by aperture
Step 3: Execution      (HO1, semantic)     Execute work orders under prompt contracts
Step 4: Verification   (HO2, mechanical)   Check results against acceptance criteria
Step 5: Feedback       (HO2, mechanical)   Did depth match outcome? Signal feeds signal accumulation
```

Steps 1 and 5 are NOT HO3 setting objectives. HO3 is pure storage. Steps 1 and 5 are HO2 reading accumulator state and writing outcome signal — mechanical operations that calibrate future aperture through the same signal accumulation that handles everything else.

**The key difference from recurrent models:** HRM's adaptive depth iterates through neural computation (expensive). DoPeJar's adaptive depth is determined by accumulator state (counter reads) and inspection (one constrained LLM call). The recurrent part — signal accumulation across turns and sessions — is counter arithmetic, not LLM calls. This is where energy efficiency comes from.

---

## The Primitives

All the functionality discussed in this document — methylation-weighted Attention, consolidation, aperture, Bayesian mechanics, epigenetic model, homeostasis, failure mode protection — emerges from configuring a small set of primitives. The primitives are what we build. The functionality is what frameworks configure.

### DoPeJarMo Primitives (The OS)

These are the things that must exist before any framework can be installed:

1. **Ledger** — append-only, hash-chained event store. The sole source of truth for all state. On disk.
2. **Signal Accumulator (Gate)** — a named counter that tracks signal deltas as Ledger events, folded into a continuous methylation value (0.0–1.0) on Graph nodes. The primitive is the accumulator. Thresholds, mode switching, and consolidation triggers are framework logic. Governance gates are a degenerate case (threshold=1, no accumulation).
3. **HO1** — all LLM execution under prompt contracts. Sole agent-level entry point for the Write Path. Stateless single-shot workers. Submits events; does not write directly.
4. **HO2** — mechanical orchestration. No LLM. Reads from the Graph. Plans work orders, computes LIVE ∩ REACHABLE ∩ NOT_SUPPRESSED, resolves intent, determines aperture, routes to LLM providers.
5. **HO3 (The Graph)** — in-memory materialized view derived from the Ledger by the Write Path. Transient. Nodes are artifacts with resolved state; edges are causal connections. Destroy and rebuild from Ledger at any time. Never executes.
6. **Work Order** — the atom of dispatched work. Scoped, budgeted, contract-bound.
7. **Prompt Contract** — governed LLM interaction template. Input schema, output schema, validation rules.
8. **Package Lifecycle** — staging → gates → filesystem. The unit of governed change. How anything enters or leaves the system.
9. **Framework Hierarchy** — Framework → Spec Pack → Pack → File. The logical structure that gives packages meaning and governance teeth.

**Infrastructure (not a primitive, but required):** The **Write Path** is a synchronous Kernel service that appends events to the Ledger and folds them into the Graph. It is I/O and consistency — it does not decide what to write or whether it should be written.

### What Is NOT a Primitive

Everything else is configuration of those nine primitives, installed as frameworks:

- The gate taxonomy (entity, mode, stimulus, regime) = one accumulator primitive with different signal sources
- The scoring formula = computation HO2 performs using Graph state
- Aperture = HO2 reading methylation values + inspection to determine work order depth
- Consolidation = MLA framework dispatching work orders to HO1 (uses primitives 3, 6, 7)
- Bistable mode switching = MLA framework applying hysteresis thresholds to methylation values
- The Traveler Rule, decay, density normalization, session caps = framework-defined mechanical controls
- Homeostasis = MLA framework monitoring accumulator population health
- The Meta-Learning Agent itself = a framework installed through the package lifecycle
- Routing policy = framework-installed policy rulesets in the Graph, read by HO2
- Suppression policy = framework decides when to write suppression events; HO2 applies NOT_SUPPRESSED filter

### DoPeJarMo OS-Level Frameworks (Layer 1 — Required)

These must be installed for DoPeJarMo to operate. They are the first frameworks through the Package Lifecycle after GENESIS and KERNEL. See FRAMEWORK_REGISTRY.md for full segregation and dependency details.

- **DoPeJarMo Agent Interface** — the interactive session shell the operator logs into. First governed install (via CLI package tools from KERNEL). Once installed, all subsequent installs go through DoPeJarMo.
- **Storage Management** — Ledger trimming using methylation values to identify oldest + least used artifacts, pressure-driven at write rate. Required because without it, Ledger fills disk and the system hard stops.
- **Meta-Learning Agent** — decay, density normalization, session caps, Traveler Rule, bistable mode switching, consolidation, homeostasis monitoring.
- **Routing** — which LLM provider handles which work order types. Mechanical policy read by HO2.

### DoPeJar (The Product) — Installed Frameworks (Layer 2)

DoPeJar is a set of frameworks running on DoPeJarMo, installed after Layer 1 is operational:

- **Memory framework** — learning artifacts, consolidation patterns, methylation-weighted Attention configuration
- **Intent framework** — lifecycle management, proposal/authority boundary, bridge mode scaffolding
- **Conversation framework** — DoPeJar's personality (Donna + Pepper + JARVIS), response generation, user-facing behavior

Each built in staging, packaged, installed through the governed lifecycle. Additional capabilities (task execution, scheduling, external integrations) arrive as additional frameworks over time. DoPeJar grows through framework installation, not rebuilds.

### The Build Implication

We don't build DoPeJar's full capability set upfront. We build DoPeJarMo — the OS with the nine primitives. Then we install Layer 1 frameworks so DoPeJarMo can operate. Then we build and install DoPeJar's day-one frameworks. The functionality discussions throughout this document (gates, aperture, consolidation, Bayesian mechanics, Two Sarahs, failure modes) exist to scope what the primitives need to support. They are design validation, not a feature list.

**The golden path question — "which Docker services does DoPeJar need day one?" — is three questions:**
1. What Docker services does DoPeJarMo need? (The OS — nine primitives + Write Path)
2. Which frameworks must DoPeJarMo have to operate? (Layer 1 — Agent Interface, Storage Management, Meta-Learning Agent, Routing)
3. Which frameworks does DoPeJar need installed day one? (Layer 2 — Memory, Intent, Conversation)

---

## The Seven Design Principles

These emerged from the context engineering work and govern all authority decisions in the system:

1. **All authority must be explicit.** No inferred permissions, no implicit grants, no "the user probably meant."
2. **All lifecycle transitions must be logged.** Every state change is a ledger entry. If it's not logged, it didn't happen.
3. **No semantic inference at authority boundary.** HO1 proposes meaning. HO2 decides mechanically. The boundary between them is sacred.
4. **Determinism over cleverness.** When in doubt, block and ask. Never guess. Strict sequentiality over split-brain resolution.
5. **Projection must be reversible.** Suppression is a view, not a deletion. Any projection can be unwound to reveal the full liveness state.
6. **Intent is namespace, not label.** Intent is not a tag on a work order. It is the root that gives reachability its meaning and conflict its resolution.
7. **Time effects must be explicit inputs or excluded.** Wall-clock decay, background aging, time-based heuristics — all must be explicit logged modifiers or they break replay.
