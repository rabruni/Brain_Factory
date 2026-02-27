---
title: "FWK-0 — Open Questions, Guesses, and Concerns"
status: SCRATCH PAPER — working document
last_updated: "2026-02-26"
author: "Ray Bruni + Claude"
purpose: >
  Track every unresolved question, assumption, and concern about FWK-0.
  Each item needs a decision before FWK-0 can be promoted to authority status.
  Items are grouped by category and tagged with severity.
---

# FWK-0 — Open Questions, Guesses, and Concerns

---

## Category 1: ID Conventions and Naming

### Q1.1 — Sequential vs Content-Addressed IDs
**Severity:** High — affects every ID in the system
**Current assumption:** Sequential (FMWK-001, FMWK-002, ...).
**Alternative:** Content-addressed (hash-derived from framework contents).
**Trade-off:** Sequential is simple, human-readable, and predictable. Content-addressed prevents collisions when independent builders author frameworks in parallel (no central registry needed). Sequential requires a central counter or coordination mechanism.
**Concern:** If two builder agents independently create frameworks in staging, who assigns the next ID? Does staging have an ID allocator? Does the install lifecycle assign the ID at install time rather than authoring time?
**Decision needed:** Who assigns IDs and when?

### Q1.2 — ID Encoding in Filesystem Paths
**Severity:** High — affects every path in the governed filesystem
**Current assumption:** `FMWK-NNN-<name>` as directory name (e.g., `FMWK-003-memory`).
**Concern:** What characters are valid in `<name>`? Lowercase only? Hyphens allowed? Underscores? Max length? This needs to be a concrete regex, not a convention.
**Decision needed:** Exact naming regex for each layer's directory.

### Q1.3 — ID Numbering Scheme Across Boot Phases
**Severity:** Medium — affects readability and organization
**Question:** Should KERNEL frameworks occupy a reserved ID range (e.g., FMWK-001 through FMWK-009)? Should Layer 1 frameworks occupy a different range? Or is it purely sequential regardless of phase?
**Concern:** If KERNEL decomposes into 7 frameworks, and we later discover we need an 8th, a reserved range avoids ID gaps. But reserved ranges are fragile if the count changes.
**Decision needed:** Reserved ranges or pure sequential?

---

## Category 2: Schema Design

### Q2.1 — What Are "Governance Rules" as Data?
**Severity:** High — affects framework.json schema and gate implementation
**Current assumption:** Array of objects with rule_id, description, enforcement fields.
**Concern:** This is the fuzziest field in the entire schema. "Governance rules, boundaries, contracts" is how the docs describe what a framework declares, but never defines what a rule looks like as structured data. Options:
  - **Declarative assertions:** "all files in this framework must have X property" — checked by gates.
  - **References to gate checks:** "run gate check Y at install time for this framework."
  - **Free-text descriptions:** human-readable only, not machine-validated.
  - **Executable code:** a validation function the gate runner calls.
The draft uses declarative with a rule_id and enforcement type. But this hasn't been validated against a real framework to see if it's sufficient.
**Decision needed:** Concrete governance rule format.

### Q2.2 — Per-Layer Metadata Files vs Single manifest.json
**Severity:** High — affects filesystem layout and gate architecture
**Current assumption:** Per-layer metadata files (framework.json, specpack.json, pack.json) PLUS manifest.json as the package wrapper.
**Rationale:** Each gate validates its own layer's metadata independently. Per-layer files make this clean — a spec pack gate reads specpack.json without parsing the full package.
**Concern:** This means four metadata file types (five counting manifest.json). More schemas to define, more files to hash, more surface area for inconsistency between the metadata files and manifest.json.
**Decision needed:** Confirm per-layer approach or collapse to manifest.json only.

### Q2.3 — Pack Type: Structural Differences or Just a Flag?
**Severity:** Medium — affects pack.json schema and gate complexity
**Current assumption:** Base pack.json schema with type-specific gate validation. The schema is the same; the type field controls which additional checks gates run.
**Alternative:** Type-specific pack schemas (prompt_pack.json, module_pack.json, etc.) with different required fields per type.
**Trade-off:** Single schema + type flag is simpler and more extensible (new pack types don't require new schemas). Type-specific schemas are more precise but harder to extend.
**Decision needed:** Which approach?

### Q2.4 — Interface Contract Detail Level
**Severity:** Medium — affects how frameworks discover and validate each other
**Question:** How detailed is an interface contract in a protocol definition pack? Is it a full API schema (input types, output types, error cases)? Or a lighter declaration ("I provide attention-query capability")?
**Concern:** Full API schemas make gate validation very precise but add authoring burden. Light declarations are easy to write but gates can only check "does a provider exist?" not "does the provider match what the consumer expects?"
**Decision needed:** Interface contract detail level.

### Q2.5 — Required vs Optional Fields at Each Layer
**Severity:** Medium — affects the minimum viable framework
**Question:** The draft shows many fields. Which are required for a valid framework vs optional enrichment? A minimal framework with one module pack and no interfaces needs less than a full framework with governance rules, quality measures, and protocol definitions.
**Concern:** If everything is required, the bar to author a framework is high. If too much is optional, gates can't validate meaningfully and frameworks drift.
**Decision needed:** Required field set per layer.

---

## Category 3: Filesystem

### Q3.1 — Subdirectories Within Packs
**Severity:** Medium — affects module packs directly
**Current assumption:** All files are flat within the pack directory (no subdirectories).
**Concern:** Module packs containing Python packages need `__init__.py` files and subdirectory structure. JavaScript/TypeScript modules may need `src/` directories. If packs are flat, complex code has to be restructured into a flat layout that doesn't match standard project conventions.
**Alternative:** Allow subdirectories within packs. File paths in pack.json become relative paths (`src/handler.py` instead of just `handler.py`). Hashes still cover every file. Ownership still applies to every file.
**Risk:** Subdirectories add complexity to gate validation (recursive file discovery) and ownership checking.
**Decision needed:** Flat or allow subdirectories?

### Q3.2 — Metadata Files in Ownership Model
**Severity:** Low but important for consistency
**Question:** Are framework.json, specpack.json, pack.json, and manifest.json themselves owned files? They exist on the governed filesystem. They should be tracked. But they're metadata ABOUT the hierarchy, not artifacts WITHIN it.
**Current assumption:** Yes, they are owned — framework.json is owned by the framework (conceptually by a meta-pack or by FWK-0's schema pack). But this creates a bootstrapping question: who owns FWK-0's own metadata files?
**Decision needed:** Ownership model for metadata files.

### Q3.3 — Versioning and Filesystem Coexistence
**Severity:** High — affects upgrade and rollback strategy
**Question:** When a framework upgrades from v1.0.0 to v1.1.0, do both versions coexist on the governed filesystem? Or does v1.1.0 replace v1.0.0?
**Option A — Replace:** `FMWK-003-memory/` is updated in place. Rollback requires reinstalling v1.0.0 from the Ledger (replay its install events).
**Option B — Coexist:** `FMWK-003-memory-1.0.0/` and `FMWK-003-memory-1.1.0/` both exist. Rollback is just switching which one is "active." But this means version is encoded in the directory name, doubling filesystem entries.
**Concern:** The docs say "Framework v1.0 and v1.1 are different packages" which suggests they're distinct artifacts. But the docs also say "one framework = one package" which suggests replacement, not coexistence.
**Decision needed:** Replace or coexist? Rollback mechanism?

### Q3.4 — The /governed/ Root Path
**Severity:** Low — but must be defined once
**Question:** What is the actual mount point? The Docker topology has `governed_fs` as a volume. Is the root `/governed/`? `/var/lib/dopejarmo/governed/`? Something else?
**Decision needed:** Canonical root path.

---

## Category 4: Gates and Validation

### Q4.1 — Gate Implementation: Data or Code?
**Severity:** High — affects how gates are authored and executed
**Question:** Are gate definitions data (JSON schemas, declarative check specifications) that a gate runner interprets? Or are they code (Python functions, validation scripts) that the gate runner executes?
**Trade-off:** Data is safer (no arbitrary code execution during install) and easier to validate from cold storage. Code is more flexible (can express complex validation logic).
**Current assumption:** FWK-0 defines gates as data (JSON specifications). KERNEL implements a gate runner that interprets them.
**Decision needed:** Data, code, or hybrid?

### Q4.2 — Scope Overlap Detection
**Severity:** Medium — affects the framework gate
**Question:** The framework gate checks "does this framework's scope overlap with an existing framework?" How is overlap detected? Scope is currently a free-text responsibility string. Free text can't be mechanically compared for overlap.
**Options:**
  - **Keyword-based:** each framework declares scope keywords, gate checks for intersection.
  - **Capability registry:** a controlled vocabulary of capabilities, each framework claims capabilities, gate prevents duplicates.
  - **Human review:** scope overlap is flagged for operator approval, not mechanically rejected.
**Decision needed:** Scope overlap detection mechanism.

### Q4.3 — System Gate Detail
**Severity:** High — this is the last line of defense
**Question:** What exactly does the system gate (post-install verification) check? "Entire governed filesystem consistent" is the requirement. Concretely:
  - Every file's hash matches its pack manifest?
  - Every pack is declared by a spec pack?
  - Every spec pack is declared by a framework?
  - All interface contracts satisfied (every consumed interface has a provider)?
  - No ownership conflicts (no file claimed by two packs)?
  - Framework dependency graph has no dangling edges?
  - Something else?
**Concern:** The system gate is the most expensive check — it validates the ENTIRE filesystem, not just the new package. On a system with many frameworks, this could be slow.
**Decision needed:** Exact system gate checklist. Performance strategy for large systems.

### Q4.4 — Cold-Storage Validation Without Runtime
**Severity:** High — core operational invariant depends on this
**Question:** The docs require that "the entire governed filesystem can be validated against the Ledger from cold storage with no runtime services." This means CLI tools connect directly to immudb and walk the governed filesystem. But the gate definitions live inside FWK-0 on the governed filesystem. So cold-storage validation requires:
  1. Reading FWK-0's gate definitions from disk
  2. Reading every framework's metadata from disk
  3. Replaying Ledger events from immudb
  4. Comparing filesystem state to Ledger state
This is feasible but the CLI tools need to be independent of the kernel. They need to understand FWK-0's schemas and gate definitions without the kernel process.
**Decision needed:** Confirm cold-storage validation architecture.

---

## Category 5: Composition and Runtime

### Q5.1 — KERNEL Decomposition
**Severity:** High — determines how many frameworks exist at the primitive level
**Question:** How many frameworks does KERNEL decompose into? Candidates:
  - Ledger framework (owns append-only store, event schemas)
  - Write Path framework (owns synchronous mutation, fold logic)
  - HO1 framework (owns LLM execution, prompt contract enforcement)
  - HO2 framework (owns orchestration, work order planning)
  - HO3/Graph framework (owns in-memory derived view)
  - Signal Accumulator framework (owns fold logic for methylation values)
  - Package Lifecycle framework (owns gates, install/uninstall CLI tools)
  - Work Order framework (owns work order data structure and state machine)
  - Prompt Contract framework (owns contract schema and validation)
**Concern:** Nine primitives doesn't necessarily mean nine frameworks. Some primitives are tightly coupled (Write Path + Ledger, Signal Accumulator as fold logic within Write Path). Over-decomposition creates dependency complexity. Under-decomposition violates single responsibility.
**Decision needed:** KERNEL framework count and boundaries.

### Q5.2 — Framework-to-Framework Communication at Runtime
**Severity:** Medium — important for builder understanding
**Current assumption:** Frameworks never call each other directly. All communication flows through primitives (Ledger/Graph for data, Work Orders for execution).
**Question:** Is this always true? What about Package Lifecycle calling gate definitions from FWK-0? That's one framework's code reading another framework's data. Is that "direct communication" or "reading the governed filesystem"?
**Concern:** If we say "no direct communication" but the gate runner (Package Lifecycle framework) reads FWK-0's gate definitions from disk, we need to clarify what "direct" means. Reading another framework's files from the governed filesystem is different from calling another framework's functions.
**Decision needed:** Precise definition of "no direct communication."

### Q5.3 — Composition Registry Refresh
**Severity:** Low — operational detail
**Question:** The composition registry (in-memory map of installed frameworks and their interfaces) is built at kernel startup. What happens when a new framework is installed during a running session? Does the registry refresh? Does it require a restart?
**Decision needed:** Hot reload or restart-required?

---

## Category 6: Uninstall and Lifecycle

### Q6.1 — Uninstall Process
**Severity:** Medium — not needed for initial build but needed for completeness
**Question:** What does framework removal look like? Steps:
  1. Check no other framework depends on this one (reverse dependency check).
  2. Remove files from governed filesystem.
  3. Clear ownership records.
  4. Append uninstall events to Ledger.
  5. Run system gate to verify filesystem consistency after removal.
**Concern:** The docs mention "governed removal" and "ownership tracking identifies exactly which files belong to it" but don't define the process. FWK-0 should define it even if it's not built in KERNEL v1.
**Decision needed:** Uninstall sequence and Ledger events.

### Q6.2 — Upgrade Path
**Severity:** Medium — connected to Q3.3 (versioning)
**Question:** When upgrading a framework (v1.0 → v1.1), is it uninstall-then-install? Or is there an upgrade path that migrates state? If the framework owns data in the Graph, does upgrading affect that data?
**Concern:** Frameworks don't own Graph data directly (the Ledger does), so upgrade shouldn't require data migration. But the Graph is a derived view from Ledger events — if the new version changes how events fold into the Graph, a refold might be needed.
**Decision needed:** Upgrade strategy.

---

## Category 7: Authoring Experience

### Q7.1 — Builder Tooling in Staging
**Severity:** Low — engineering detail, not architecture
**Question:** What tools does a builder have in the staging directory? Does FWK-0 define a staging workflow, or is staging purely ungoverned?
**Current assumption:** Staging is ungoverned — "a workbench." But builders still need to validate their work before submitting for install. Do they run gates locally in staging as a dry run?
**Decision needed:** Staging tooling expectations.

### Q7.2 — The Reference Framework
**Severity:** Medium — important for builder agent onboarding
**Question:** BUILDER_SPEC line 440 says "One complete reference framework as canonical example (Memory framework recommended)." Should FWK-0 include the Memory framework as an appendix/example? Or is Memory authored separately and FWK-0 references it?
**Decision needed:** Where does the reference framework live?

---

## Category 8: Concerns and Risks

### C8.1 — FWK-0 Size and Agent Context Window
**Risk:** FWK-0 becomes too large for a builder agent to hold in context alongside a framework's spec pack.
**Mitigation:** Keep FWK-0 dense and structured. A builder only needs to read the layer sections relevant to their current work, not the entire document. Consider whether FWK-0 should be designed as a set of independently readable sections rather than a monolithic document.

### C8.2 — Self-Referential Bootstrap Circularity
**Risk:** FWK-0 defines the gate system, but FWK-0 is installed during GENESIS before the gate system exists. The gates can't validate FWK-0 because FWK-0 is what defines the gates.
**Mitigation:** FWK-0 is hand-verified during GENESIS, not gate-validated. After GENESIS, FWK-0's own gates can be run against it as a retroactive validation (confirming the hand-verification was correct). The self-referential property is a post-hoc test, not a bootstrap requirement.

### C8.3 — Filesystem Mirror as Single Point of Truth Drift
**Risk:** The logical hierarchy (in metadata) and the physical hierarchy (on disk) drift apart. A file is moved but its pack.json isn't updated. Or pack.json is updated but the file isn't moved.
**Mitigation:** The install lifecycle is the ONLY way files enter the governed filesystem. If the lifecycle correctly mirrors metadata to disk at install time, drift can only happen through direct filesystem manipulation — which is prohibited. The system gate (cold-storage validation) catches drift if it occurs.
**Ray's note:** This was a major miss in previous builds. The filesystem mirror is non-negotiable. Every gate check that validates metadata must also validate the corresponding filesystem state. They are not separate checks — they are one check with two sides.

### C8.4 — Gate Complexity Growth
**Risk:** As more frameworks are installed, the system gate (which validates the entire filesystem) becomes increasingly expensive. A system with 50 frameworks means checking 50 framework.json files, all their spec packs, all their packs, all their files, all ownership records, all interface contracts.
**Mitigation:** Incremental validation — the system gate only needs to fully validate the newly installed framework and its interface connections, not the entire filesystem. Previously validated frameworks are assumed correct unless their files have changed (detectable via hash comparison). But this optimization must not violate the cold-storage validation requirement — cold-storage validation must still be able to check everything.

### C8.5 — Naming Convention Rigidity
**Risk:** The `FMWK-NNN-<name>` naming convention bakes human-readable names into filesystem paths. If a framework is renamed (e.g., "memory" → "episodic-memory"), every path changes, every hash changes, every reference changes.
**Mitigation:** Don't rename frameworks. Create a new framework and migrate. Or: separate the ID from the name — use `FMWK-003/` as the directory name (ID only) and keep the human-readable name in framework.json only. This sacrifices path-readable provenance for rename safety.
**Decision needed:** ID-only paths or ID+name paths?

---

## Resolved (approved by Ray, best practice or design decision)

| ID | Decision | Rationale |
|----|----------|-----------|
| Q1.2 | Naming regex: `^[a-z][a-z0-9-]{1,63}$` | Standard filesystem-safe, URL-safe pattern |
| Q2.2 | Per-layer metadata files confirmed | Each bounded context owns its own descriptor |
| Q2.3 | Single pack.json schema + type flag, type-specific gate checks | Polymorphic pattern, easier to extend |
| Q2.5 | Small required core, everything else optional | Matches every mature package manager |
| Q3.1 | Subdirectories allowed within packs | Real code needs real project structure |
| Q3.4 | Root path: `/governed/`, `/staging/`, `/snapshots/` | Clean, short, unmistakable |
| Q4.1 | Gates as declarative JSON specs, interpreted by gate runner | Safer, auditable, supports cold-storage validation |
| Q4.2 | Scope overlap is operator decision, not gate check | Semantic judgment can't be mechanically automated |
| Q5.2 | No direct function calls. Reading published artifacts from governed filesystem permitted. Runtime data through primitives only. | Clean separation of published specs vs runtime communication |
| Q5.3 | Hot reload after install | Install lifecycle triggers registry refresh |
| Q7.1 | Staging provides scaffold/seal/validate/package CLI tools + inspect (read-only view of governed filesystem) + mock providers for testing | Full dark factory build environment |

## Structural Decisions (from design session 2026-02-26)

| Decision | Description |
|----------|-------------|
| Package ≠ Framework | Package is atomic delivery unit containing one or more frameworks. Framework is logical governance unit. |
| Hierarchy is extensible | FWK-0 defines initial hierarchy + extension mechanism (constitutional amendment model) |
| Pristine memory is the core value | Governance serves memory. Not governance-first. |
| Context reconstruction is the feature | Complete prompt rebuilt from pristine memory every turn. Not "no context" — perfectly accurate context. |
| Standards as frameworks | Governance-only frameworks containing quality measures. No module packs. |
| Multi-tenant OS | DoPeJarMo hosts any agent, not just DoPeJar |
| Dark factory is first-class | Build process defined in FWK-0, not an afterthought |

## New Open Questions (added 2026-02-26)

### Q9.1 — Hierarchy Extension Mechanism
**Severity:** High — affects long-term evolvability
**Question:** How does a hierarchy extension work concretely? Does it modify FWK-0's schemas directly (dangerous — changes the foundation), or add supplementary schemas that extend FWK-0 (safer — additive only)?
**Decision needed:** Extension mechanism: modify-in-place or additive-only?

### Q9.2 — Multi-Framework Package Internal Dependency Order
**Severity:** Medium — affects KERNEL package design
**Question:** Within a multi-framework package, frameworks may depend on each other. How does the install lifecycle determine the order to validate and place frameworks? Topological sort of internal dependency graph?
**Decision needed:** Internal dependency resolution strategy.

### Q9.3 — External Agent Integration Protocol
**Severity:** Low for now — important long-term
**Question:** What is the minimal protocol for external agents (Claude, Codex) to submit memories to DoPeJar? Event submission API? Structured format? Authentication model?
**Decision needed:** External integration protocol design.

### Q9.4 — Hybrid Context Model
**Severity:** Medium — affects Conversation framework design
**Question:** Should the LLM receive both pristine reconstructed context (from Ledger/Graph scoring) AND raw conversation history (last N turns)? Pristine context provides accurate memory. Raw history provides conversational continuity. Both may be needed.
**Decision needed:** This is a Conversation framework question, not FWK-0. But FWK-0 should not constrain it.

### Q9.5 — Package Grouping for Operator Review
**Severity:** Medium — affects operator experience
**Question:** With package ≠ framework, how should frameworks be grouped into packages for operator review? One mega-package (operator reviews once) vs many small packages (operator reviews each)? Should there be guidelines in FWK-0 for packaging decisions?
**Decision needed:** Packaging guidelines or leave to builder judgment.

## Summary: Decision Priority (Updated)

**Must resolve before drafting final FWK-0:**
1. Q1.1 — ID assignment (who, when)
2. Q2.1 — Governance rules as data
3. Q3.3 — Version coexistence or replacement
4. Q5.1 — KERNEL decomposition count
5. C8.5 — ID-only vs ID+name paths
6. Q9.1 — Hierarchy extension mechanism
7. Q9.2 — Multi-framework package dependency order

**Should resolve but can defer:**
8. Q4.3 — System gate checklist
9. Q6.1 — Uninstall process
10. Q9.5 — Packaging guidelines

**Can defer to implementation or other frameworks:**
11. Q1.3 — ID numbering ranges
12. Q2.4 — Interface contract detail
13. Q3.2 — Metadata file ownership
14. Q6.2 — Upgrade path
15. Q7.2 — Reference framework location
16. Q9.3 — External agent integration protocol
17. Q9.4 — Hybrid context model

---

## Proposed Resolutions (2026-02-26, pending Ray approval)

Concrete v1 answers proposed for all 7 must-resolve questions. Full analysis with rationale, implementation checklists, and forward-compatibility paths in `FWK-0-PRAGMATIC-RESOLUTIONS.md`.

| Question | Proposed Resolution | Status |
|----------|-------------------|--------|
| Q1.1 — ID assignment | Hybrid: builder proposes, gates validate uniqueness at install. Reserved ranges (001-009 KERNEL, 010-019 Layer 1, 020-029 Layer 2, 030+ extensions). | PENDING APPROVAL |
| Q2.1 — Governance rules | Declarative JSON. Three enforcement types: gate-check, architectural-boundary, ownership-check. Rules are data, not code. | PENDING APPROVAL |
| Q3.3 — Versioning | Replace in place. Rollback from Ledger replay. No version directories on filesystem. | PENDING APPROVAL |
| Q5.1 — KERNEL decomposition | 7 frameworks: ledger, write-path, orchestration, execution, graph, package-lifecycle, kernel-cli. | PENDING APPROVAL |
| C8.5 — Paths | ID+name (FMWK-NNN-name). Rename = new framework. Human-readable provenance > rename flexibility. | PENDING APPROVAL |
| Q9.1 — Hierarchy extension | Additive only. FWK-0 immutable after GENESIS. Extensions are separate frameworks layered on top. | PENDING APPROVAL |
| Q9.2 — Dependency order | Topological sort (Kahn's algorithm). Cycle detection. Sequential install in sorted order. | PENDING APPROVAL |

## New Gaps Surfaced (2026-02-26)

Seven critical gaps not captured in original open questions. Full analysis in `FWK-0-PRAGMATIC-RESOLUTIONS.md`.

### GAP-1 — GENESIS Bootstrap Sequence
**Severity:** Critical — blocks everything
**Issue:** GENESIS is described as "hand-verified" but no concrete step-by-step sequence exists. GENESIS is a ceremony, not an automated script. 10 steps: create volumes → init immudb → populate FWK-0 files → compute/verify hashes → assemble self-referential package → record bootstrap events → validate → operator confirmation.

### GAP-2 — Builder Agent Context Window Budget
**Severity:** Medium — affects builder effectiveness
**Issue:** FWK-0 + spec pack + generated framework must fit in context. FWK-0 should be stratified with reading paths per pack type to reduce token load. Complex module packs may need phased authoring.

### GAP-3 — Mock Provider Architecture
**Severity:** High — blocks dark factory testing
**Issue:** Mock Ollama, Ledger, Graph need concrete design. Same APIs as real services, deterministic responses. Three test tiers: smoke (gates pass), integration (prompts execute), E2E (full turn works).

### GAP-4 — KERNEL Activation Sequence
**Severity:** High — gap between "installed" and "running"
**Issue:** 12-step sequence from "KERNEL files on disk" to "accepting operator sessions" is undocumented. Includes: integrity validation → snapshot load → event replay → Write Path init → HO1/Zitadel init → composition registry → WebSocket start.

### GAP-5 — WebSocket Server Ownership
**Severity:** Medium — architectural clarity
**Decision:** WebSocket is KERNEL infrastructure, not a framework. Agent Interface uses it but doesn't own it. Prevents deadlock: removing Agent Interface doesn't kill the interaction path.

### GAP-6 — Prompt Contract Testing Before Cognitive Stack
**Severity:** Medium — affects builder validation
**Issue:** 5-stage validation: structural (schema), template (sanity), consistency (rules match output), mock execution (canned responses), integration (HO1 dispatcher works).

### GAP-7 — Capability Discovery and Registration
**Severity:** Medium — affects runtime composition
**Issue:** framework.json needs `capabilities[]` array mapping capability_id → contract → pack. Composition registry built at startup. HO1 looks up capability, loads contract, executes. Conflict detection (two frameworks claiming same capability).
