---
title: "FWK-0 Pragmatic Resolutions — 48-Hour Sprint Decisions"
status: "DECISIONS FOR IMPLEMENTATION"
date: "2026-02-26"
audience: "Ray, builder agents, operators — needed to unblock GENESIS and KERNEL builds"
scope: "Resolving the 7 must-resolve questions + surfacing new critical gaps + identifying 48-hour risks"
---

# FWK-0 Pragmatic Resolutions — 48-Hour Sprint

## PART 1: CONCRETE ANSWERS TO THE 7 MUST-RESOLVE QUESTIONS

These are pragmatic v1 decisions designed to get agents running WITHOUT painting the system into a corner. Each includes evolution path for future refinement.

---

### Q1.1 — ID Assignment: Who Assigns, When?

**DECISION: Hybrid model — Sequential + Install-time validation**

```
AUTHORING TIME:
- Builder agent proposes an ID in the staging directory (e.g., FMWK-050-my-framework)
- The proposal is declarative — written in framework.json
- No lock, no central registry, no coordination needed at authoring time
- Multiple builders can author in parallel with overlapping ID proposals

INSTALL TIME (gates):
- Package Lifecycle validates: "Is this ID (FMWK-050) already installed?"
- If YES → reject as duplicate. Builder must resubmit with different ID.
- If NO → install and reserve the ID. Ledger records framework_installed event with the assigned ID.

WHY THIS WORKS FOR v1:
- Unblocks parallel development (no central ID allocator bottleneck)
- Gets you to running agents in 48 hours (synchronous validation is fast)
- Predictable and simple (sequential, human-readable)
- Deterministic gates (binary pass/fail)
- Forward-compatible: can migrate to content-addressed IDs later without changing on-disk format
  (the ID in framework.json can change during upgrade; the Ledger records all versions)

FUTURE PATH:
- If content-addressed IDs become needed (truly autonomous agents creating frameworks),
  you can transition to hash-derived IDs for authoring, validate deduplication at install.
  Everything on disk remains the same — the ID assignment is orthogonal to storage format.

ID NUMBERING SCHEME:
- Strictly sequential starting at FMWK-000 (FWK-0 itself).
- KERNEL: FMWK-001 through FMWK-009 (reserved, may not use all 9).
- Layer 1 (OS): FMWK-010 through FMWK-019 (reserved).
- Layer 2 (DoPeJar): FMWK-020 through FMWK-029 (reserved).
- Future agents/extensions: FMWK-030+
- Reason: Reserved ranges prevent ID gaps and make the system readable at a glance.
  If you discover you need 11 KERNEL frameworks instead of 9, you have headroom.
- Constraint: must not skip a number within a reserved range. If FMWK-015 fails to build,
  the range stays reserved until you decide explicitly to reclaim it.

NAMING REGEX (already resolved):
```
Framework: ^FMWK-[0-9]{3}$
Name: ^[a-z][a-z0-9-]{1,63}$
Full dir: FMWK-NNN-name

Spec Pack: ^SPEC-[0-9]{3}$
Full dir: SPEC-NNN-name

Pack: ^PC-[0-9]{3}$
Full dir: PC-NNN-name
```

**IMPLEMENTATION CHECKLIST:**
- [ ] framework.json requires "id" field (validated during authoring)
- [ ] Package Lifecycle gate checks ID uniqueness against installed frameworks (first gate, before anything else)
- [ ] Ledger records `framework_installed` event with final assigned ID + timestamp
- [ ] CLI tool: `show-framework-ids` lists all installed framework IDs (for operator visibility)

---

### Q2.1 — Governance Rules as Data: Concrete Format

**DECISION: Declarative JSON specs + Text-based justification + Operator audit log**

Governance rules exist to make memory trustworthy. Rules must be:
1. **Machine-readable** (gates can check them)
2. **Auditable** (operator can read and understand them)
3. **Enforceable** (gates fail if rules are violated)
4. **Not executable code** (no arbitrary code execution during install)

```json
{
  "id": "FMWK-003",
  "name": "memory",
  "governance_rules": [
    {
      "rule_id": "GOV-001",
      "description": "All learning artifacts must be consolidated before reaching 10 items",
      "category": "data-quality",
      "scope": "applies-to: PC-001-consolidation",
      "enforcement": {
        "type": "gate-check",
        "gate_stage": "pack-install",
        "check_type": "schema-validation",
        "schema_reference": "PC-004-learning-quality/consolidation-acceptance-criteria.json"
      },
      "audit_note": "Prevents runaway artifact accumulation. Quality measure validates consolidation before install."
    },
    {
      "rule_id": "GOV-002",
      "description": "All Ledger writes must go through Write Path, not direct append",
      "category": "write-integrity",
      "scope": "applies-to: FMWK-003",
      "enforcement": {
        "type": "architectural-boundary",
        "boundary_check": "no-pack-declares-direct-immudb-dependency",
        "validated_by": "dependency resolver at install time"
      },
      "audit_note": "Architectural constraint. No module pack can declare immudb as direct dependency."
    },
    {
      "rule_id": "GOV-003",
      "description": "Memory learning artifacts are owned by this framework; no other framework may modify them",
      "category": "ownership",
      "scope": "applies-to: PC-001, PC-002",
      "enforcement": {
        "type": "ownership-check",
        "enforced_by": "gate-pack-validation-ownership",
        "ledger_verification": "every artifact in this pack's write events must credit FMWK-003"
      },
      "audit_note": "Verified through Ledger event replay. No other framework can claim ownership of memory artifacts."
    }
  ]
}
```

**THE THREE ENFORCEMENT TYPES:**

1. **gate-check** — Gates validate this before install. Example: "schema must validate against quality-measure.json"
   - Checked at install time, synchronously, deterministically.
   - If check fails, package is rejected.

2. **architectural-boundary** — Structural constraint enforced by the install validator.
   - Example: "no direct immudb dependency"
   - Checked by inspecting pack declarations at install time.
   - If violated, package is rejected.

3. **ownership-check** — Verified through Ledger replay (post-install audit).
   - Example: "artifacts in this pack must be credited to this framework in Ledger events"
   - Checked retroactively by replaying events.
   - Cold-storage CLI can validate this without the kernel.

**WHY THIS DESIGN:**
- Rules are data, not code (safe, auditable, deterministic).
- Multiple enforcement strategies (gates for sync validation, Ledger for audit).
- Operator can read rules as plain English in the "description" field.
- Rules are self-documenting: "what rule, where does it apply, how is it enforced, why does it matter?"
- Extensible: new rule categories and enforcement types can be added as frameworks evolve.

**IMPLEMENTATION CHECKLIST:**
- [ ] governance_rules is optional array in framework.json (schema in FWK-0/PC-001-schemas)
- [ ] Each rule object has required: rule_id, description, enforcement type
- [ ] Gate runner interprets enforcement type and applies appropriate check
- [ ] Ledger records `governance_rule_validated` events during install
- [ ] Cold-storage CLI can validate ownership rules by replaying events

---

### Q3.3 — Versioning: Coexistence or Replacement on Filesystem?

**DECISION: Replace in place. Rollback from Ledger. No version directories.**

```
FILESYSTEM LAYOUT:
/governed/
  FMWK-003-memory/
    framework.json           ← points to v1.1.0 after upgrade
    SPEC-001-learning/
      ...
```

**UPGRADE PROCESS:**
1. Builder packages new version: `FMWK-003-memory` v1.1.0
2. Install gate validates: ID FMWK-003 exists. Is v1.1.0 > current v1.0.0? Yes → proceed.
3. Install replaces directories in place:
   - Remove old files (ownership tracking identifies exactly what)
   - Write new files (new hashes, new provenance)
   - Atomic: either full replace or full rollback
4. Ledger records:
   ```
   framework_uninstall_started  v1.0.0
   file_ownership_cleared       (all files from v1.0.0)
   framework_install_complete   v1.1.0
   file_ownership_recorded      (all files from v1.1.0)
   ```

**ROLLBACK (if needed):**
1. Operator commands: `rollback FMWK-003 to 1.0.0`
2. CLI tools connect directly to immudb, find v1.0.0's install events in Ledger
3. Replay: reconstruct exact files (paths, hashes, ownership) from Ledger
4. Write to filesystem (idempotent — hashes match)
5. Append rollback_initiated and framework_install_complete events
6. Ledger now has full history: v1.0.0 → v1.1.0 → v1.0.0 (with timestamps)

**WHY NOT COEXISTENCE:**
- Directory name doesn't encode version (cleaner paths, preserves rename safety)
- Every file is claimed by exactly one framework at exactly one version
- Ownership model remains simple
- Rollback is data operations (Ledger replay), not filesystem duplication

**WHY THIS WORKS:**
- Fast upgrade (replace, don't copy)
- Simple operator experience (upgrade, not "switch active version")
- Ledger is the source of truth for version history
- Rollback is always possible (Ledger has all past events)
- Cold-storage recovery can reconstruct any past version from Ledger

**FUTURE PATH:**
- If you need blue-green deployments (v1.0 and v1.1 active simultaneously for migration),
  that becomes a Layer 1+ feature: create a second framework FMWK-050-memory-v1.1,
  let them coexist temporarily, then deprecate FMWK-003-memory-v1.0 once all consumers migrate.
  Not a filesystem concern — a governance concern about multiple frameworks with overlapping responsibilities.

**IMPLEMENTATION CHECKLIST:**
- [ ] framework.json tracks current installed version
- [ ] Install gate checks: new version > current version (semver comparison)
- [ ] Uninstall gate clears ownership of all files from current version
- [ ] Install gate records all new files with new ownership
- [ ] Rollback CLI tool: `dopejarmocli rollback FMWK-003 1.0.0` reads Ledger, reconstructs files
- [ ] Ledger events include precise version numbers

---

### Q5.1 — KERNEL Decomposition: How Many Frameworks?

**DECISION: 7 frameworks (not 9). Single-purpose, minimal tight coupling.**

The nine primitives are architectural concerns. Frameworks are governance units. Not 1:1.

```
KERNEL PACKAGE CONTAINS:

FMWK-001-ledger
├── Primitive: Append-only event store
├── Responsibility: Event schema definitions, Ledger durability guarantees
├── Exposes: ledger-append-interface, ledger-query-interface
├── What it owns:
│   ├── SPEC-001-data: event schemas, event catalog (from FWK-0-OPEN-QUESTIONS Q7.3)
│   └── SPEC-002-durability: immudb integration specs, crash consistency guarantees
└── No LLM dependency. Pure infrastructure.

FMWK-002-write-path
├── Primitives: Write Path synchronous I/O, Graph folding logic, Signal Accumulation
├── Responsibility: Synchronous mutation, context accumulation into Graph
├── Exposes: write-path-interface (submit event, get folded state)
├── Depends on: FMWK-001 (Ledger append)
├── What it owns:
│   ├── SPEC-001-write-protocol: Write Path synchronous contract
│   ├── SPEC-002-fold-logic: How events fold into Graph state
│   └── SPEC-003-signal-accumulation: Methylation weighting, decay curves
└── Core invariant: Write Path → Ledger append (acknowledged) → Graph fold → return

FMWK-003-orchestration (HO2 + Work Orders)
├── Primitives: HO2 planning, Work Order queue, Execution dispatch
├── Responsibility: Plan work, queue work orders, dispatch to HO1, handle failures
├── Exposes: work-order-interface, orchestration-query-interface
├── Depends on: FMWK-001 (Ledger for work order events), FMWK-002 (Write Path for results)
├── What it owns:
│   ├── SPEC-001-work-order: Work order schema, state machine
│   ├── SPEC-002-planning: HO2 planning logic constraints
│   └── SPEC-003-dispatch: Execution dispatch rules
└── Contains: Work order state machine, planning heuristics, retry logic

FMWK-004-execution (HO1)
├── Primitive: LLM execution engine
├── Responsibility: Execute prompts, call LLM (local Ollama or external APIs), honor budget constraints
├── Exposes: execution-interface (execute-prompt contract)
├── Depends on: FMWK-003 (work order dispatch), FMWK-002 (Write Path for result events)
├── What it owns:
│   ├── SPEC-001-prompt-contract: Prompt contract schema, validation
│   ├── SPEC-002-routing: Which LLM (local vs external, by policy)
│   └── SPEC-003-resource-limits: Token budgets, cost tracking
└── Contains: LLM invocation, error handling, result folding

FMWK-005-graph (HO3 + HO4 + derived views)
├── Primitives: In-memory materialized Graph, query interface, derived views
├── Responsibility: Maintain current system state as materialized view, enable scoring/retrieval
├── Exposes: graph-query-interface, context-retrieval-interface
├── Depends on: FMWK-001 (Ledger replay), FMWK-002 (Write Path for live folding)
├── What it owns:
│   ├── SPEC-001-graph-schema: Node/edge structure, state shape
│   ├── SPEC-002-scoring: Retrieval scoring logic (methylation-weighted attention)
│   └── SPEC-003-queries: Query language for Graph state
└── Contains: Materialization, scoring, query execution

FMWK-006-package-lifecycle
├── Primitives: Install/uninstall gates, framework composition registry, version management
├── Responsibility: Validate packages, manage framework installation, maintain composition registry
├── Exposes: install-interface, query-composition-interface
├── Depends on: FMWK-001 (Ledger for install events), FWK-0 (gate definitions)
├── What it owns:
│   ├── SPEC-001-gates: Gate check specifications (from FWK-0, read-only reference)
│   ├── SPEC-002-package-schema: Package manifest schema
│   ├── SPEC-003-composition: Framework dependency resolution
│   └── SPEC-004-cli-tools: Command-line interface (scaffold, seal, validate, package, install, rollback)
└── Contains: Gate runner, package validator, composition registry builder, CLI entry points

FMWK-007-kernel-cli
├── Primitives: CLI fallback tools for operator recovery
├── Responsibility: Offline framework validation (no kernel needed, connects directly to immudb)
├── Exposes: (command-line tools only, no agent interface)
├── Depends on: (none — direct immudb connection, reads FWK-0 from governed filesystem)
├── What it owns:
│   ├── SPEC-001-cli-contracts: What each CLI tool does, its I/O contract
│   └── SPEC-002-cold-storage-validation: How to validate framework chain from Ledger without kernel
└── Contains: Standalone binaries (validate-filesystem, rollback, show-framework-ids, etc.)
```

**NOT A SEPARATE FRAMEWORK:**
- **Zitadel integration** → Goes into a Layer 1 framework (Identity Management)
- **Snapshot management** → Goes into FMWK-006 (part of lifecycle)
- **Routing policy** → Goes into a Layer 1 framework (FMWK-011-routing)
- **Storage trimming** → Goes into a Layer 1 framework (FMWK-010-storage-management)

**WHY 7 NOT 9:**
- Single responsibility: each framework has one clear governance boundary
- Minimal tight coupling: Write Path + Graph are separate frameworks but tightly choreographed
- Clear dependencies: acyclic (no circular dependencies)
- Operator-visible: "show frameworks" returns 7 items for KERNEL (plus Layer 1, plus Layer 2)
- Extensible: new frameworks in Layer 1 add capabilities without modifying KERNEL

**IMPLEMENTATION CHECKLIST:**
- [ ] KERNEL package contains exactly these 7 frameworks
- [ ] Each framework.json declares clear responsibility and interfaces
- [ ] Dependency graph: 007 ← 006 ← {001, 002, 003, 004, 005} with no cycles
- [ ] Each framework's spec pack is separate but coordinated at install time
- [ ] Internal package dependency resolution handles installation order

---

### C8.5 — Paths: ID-Only or ID+Name?

**DECISION: ID+Name in paths. Accept non-renameability. Rename = new framework.**

```
CURRENT DESIGN (KEEP):
/governed/
  FMWK-003-memory/
    framework.json
    SPEC-001-learning/
      PC-001-consolidation/
        consolidate-session.json

RATIONALE:
1. Path-readable provenance: You can read FMWK-003-memory/SPEC-001-learning/PC-001-consolidation/file.json
   and understand the entire hierarchy without opening metadata files.
2. Human-readable filesystem: Operators and builders can grep, find, and ls the filesystem and understand structure.
3. Self-documenting: "003" + "memory" tells you this is the third framework, about memory.

COST: Rename is not supported.
- If "memory" should become "episodic-memory", you create FMWK-050-episodic-memory as a new framework.
- Migrate consumers from FMWK-003 to FMWK-050 through gates (Ledger records the transition).
- Deprecate FMWK-003 once no other framework depends on it.
- Old path `/governed/FMWK-003-memory/` remains as a deprecated artifact in Ledger history.

WHY NOT ID-ONLY PATHS (/governed/FMWK-003/):
- Sacrifices path-readable provenance.
- Humans can't grep the filesystem for "memory" — they have to open framework.json.
- Remote debugging becomes harder: you see a hash reference in a Ledger event but need to look up the ID to understand what it is.
- Saves rename flexibility, but rename is rare and can be handled through new frameworks.

VERDICT: Human-readable paths > rename flexibility.
```

**IMPLEMENTATION CHECKLIST:**
- [ ] Enforce naming convention: `FMWK-NNN-name`, `SPEC-NNN-name`, `PC-NNN-name`
- [ ] Document: "Frameworks are not renamed. Create new framework if capability name changes."
- [ ] CLI warning if builder attempts to rename during upgrade: "Rename not supported. Create new framework instead."
- [ ] Operator docs: "To rename a framework, deprecate old one and install new one."

---

### Q9.1 — Hierarchy Extension Mechanism: Modify-in-place or Additive?

**DECISION: Additive extensions only. FWK-0 is immutable. Extensions are separate frameworks.**

```
ARCHITECTURE:

FWK-0 (FMWK-000) — Foundation (IMMUTABLE)
├── Defines: Framework hierarchy, gate system, filesystem conventions, metadata schemas
├── Never modified after GENESIS
└── Versioned in Ledger: if a change is needed, FWK-0 is a new package (new version)

Extension Framework (FMWK-XXX) — Adds capabilities WITHOUT changing FWK-0
├── Example: "I want to add a new pack type (container-pack) that FWK-0 doesn't know about"
├── Solution:
│   ├── Author FMWK-040-container-extension as a governance framework
│   ├── It REFERENCES FWK-0's schema but does NOT modify it
│   ├── It declares: "I define a new pack type: container-pack"
│   ├── It provides: new gate check implementations for container-pack validation
│   ├── It installs through normal gates (FWK-0 gates validate the extension framework itself)
│   └── Once installed, future packages can declare pack type: "container-pack"
│       and FMWK-040's gates will be invoked in addition to FWK-0 gates
└── Result: FWK-0 is unchanged. Extensions are additive frameworks.

CONCRETE EXAMPLE:

Current: FWK-0 defines pack types: [prompt_pack, module_pack, quality_measure, protocol_definition]

Future need: Support container-pack (Docker image + runtime spec)

WRONG APPROACH:
- Modify FWK-0's pack type schema to include container-pack ← This breaks FWK-0's immutability

RIGHT APPROACH:
```json
{
  "id": "FMWK-040",
  "name": "container-extension",
  "extends_framework": "FMWK-000",
  "new_pack_types": [
    {
      "pack_type": "container-pack",
      "schema_reference": "PC-001-container-schema/container-pack-schema.json",
      "gate_checks": [
        {
          "check_name": "container-image-valid",
          "enforced_by": "FMWK-040-container-extension/PC-002-gates/container-validation.json"
        }
      ]
    }
  ]
}
```

When FMWK-040 is installed:
1. FWK-0 gates validate FMWK-040's own structure (FMWK-040 is a normal framework)
2. FMWK-040 registers itself as an extension (records extension_registered event in Ledger)
3. Future package validators read Ledger and compose gate checks: FWK-0 gates + FMWK-040 gates
4. FWK-0 is unchanged; new capabilities are layered on top

WHY ADDITIVE ONLY:
- FWK-0 is the constitutional foundation. Amendments must not change the constitution.
- Every package submitted to gates must be validatable against the SAME FWK-0 gates.
- If FWK-0 changed, old packages would validate differently (breaks cold-storage validation property).
- Extensions are separate frameworks, subject to gates themselves, scoped to their responsibility.
- Operator can see exactly which extensions are installed and what they add.

GRANDFATHER CLAUSE:
- Frameworks installed under FWK-0 v1.0.0 are grandfathered into FWK-0 v1.0.0's rules.
- If FWK-0 updates to v2.0.0, new frameworks validate against v2.0.0 gates.
- Old frameworks remain valid under v1.0.0 rules (recorded in Ledger).
- Cold-storage validator respects version boundaries: "This package installed under FWK-0 v1.0.0, validate against v1.0.0 gates."
```

**IMPLEMENTATION CHECKLIST:**
- [ ] FWK-0 framework.json marks version explicitly (no accidental overwrites)
- [ ] Extension mechanism: frameworks can declare "extends_framework: FMWK-000"
- [ ] Package Lifecycle reads Ledger for installed extensions, composes gate checks
- [ ] Ledger records `extension_registered` events when FMWK-0XX extensions install
- [ ] Cold-storage CLI respects version boundaries during validation

---

### Q9.2 — Multi-Framework Package Dependency Resolution

**DECISION: Topological sort of internal dependency graph. Simple, deterministic, fast.**

```
EXAMPLE: KERNEL package contains FMWK-001 through FMWK-007 with dependencies:

FMWK-001 (ledger)
  ↑
  ├─ FMWK-002 (write-path) depends on FMWK-001
  │   ↑
  │   ├─ FMWK-003 (orchestration) depends on FMWK-001, FMWK-002
  │   │   ↑
  │   │   ├─ FMWK-004 (execution) depends on FMWK-003
  │   │
  │   ├─ FMWK-005 (graph) depends on FMWK-001, FMWK-002
  │
  ├─ FMWK-006 (package-lifecycle) depends on FMWK-001, FWK-0
  │
  └─ FMWK-007 (kernel-cli) depends on FWK-0

INSTALL ORDER (topological sort):
1. FMWK-001 (no internal dependencies)
2. FMWK-002 (depends on 001)
3. FMWK-003, FMWK-005 (both depend on 001+002, can run in parallel)
4. FMWK-004 (depends on 003)
5. FMWK-006, FMWK-007 (both depend on 001, no other internal dependencies)

ALGORITHM (Package Lifecycle):
1. Read all frameworks in package
2. Extract dependencies: for each FMWK, read framework.json, collect internal dependencies
3. Topological sort (Kahn's algorithm or DFS-based)
4. Check for cycles: if cycle detected, reject package ("Circular dependency detected")
5. Install in sorted order: each framework goes through full gate sequence before next starts
6. If any framework's gates fail, stop and reject entire package (atomic)

CIRCULAR DEPENDENCY DETECTION:
```
FMWK-010 depends on FMWK-011
FMWK-011 depends on FMWK-010
↓
Topological sort fails → reject package
↓
Ledger records: package_install_rejected reason: circular_dependency
```

PARALLELIZATION (future):
- If order allows (frameworks at same topological level), gates could run in parallel
- For v1: sequential is fine, simple, deterministic
- Leave parallelization to Layer 1+ as performance optimization

IMPLEMENTATION CHECKLIST:
- [ ] framework.json dependencies array lists framework_ids (FMWK-XXX values)
- [ ] Package manifest includes dependency graph at top level
- [ ] Install gate 1: validate manifest self-consistency (step 1-2)
- [ ] Install gate 2: topological sort (step 3)
- [ ] Install gate 3: cycle detection (step 4)
- [ ] Install sequence respects topological order (step 5)
- [ ] Package atomic: all or nothing (step 6)
```

---

## PART 2: NEW CRITICAL GAPS (NOT IN OPEN QUESTIONS)

These gaps will block progress if not addressed. They're architectural, not implementation details.

---

### GAP 1: The Bootstrap Chicken-Egg Problem — What Does GENESIS Actually Do?

**THE PROBLEM:**
FWK-0 documents describe "GENESIS package (hand-verified, creates governed filesystem + Ledger + hierarchy)" but GENESIS is neither a framework nor a package — it's a bootstrap ceremony. What are the concrete step-by-step operations?

**WHAT GENESIS MUST DO (in order):**

```
GENESIS SEQUENCE (happens ONCE, manually, before any gates run):

1. CREATE DOCKER VOLUMES (one-time infrastructure)
   ├── /governed/           (empty, pristine)
   ├── /staging/            (empty, ungoverned)
   ├── /snapshots/          (empty, no initial snapshot)
   └── immudb ledger_data   (empty, ready for events)

2. INITIALIZE IMMUDB (the Ledger foundation)
   ├── Start ledger container
   ├── Wait for gRPC ready on :3322
   ├── Append special event: genesis_started (timestamp, version)
   └── Root of hash chain established

3. CREATE GOVERNED FILESYSTEM STRUCTURE
   └── mkdir -p /governed/FMWK-000-framework/SPEC-001-hierarchy/
       ├── PC-001-schemas/
       ├── PC-002-gate-definitions/
       ├── PC-003-filesystem-convention/
       ├── PC-004-install-events/
       └── PC-005-composition/

4. POPULATE FWK-0 FILES (hand-verified, copied from source repo)
   ├── /governed/FMWK-000-framework/framework.json
   ├── /governed/FMWK-000-framework/SPEC-001-hierarchy/specpack.json
   ├── /governed/FMWK-000-framework/SPEC-001-hierarchy/PC-001-schemas/
   │   ├── pack.json
   │   ├── framework-schema.json
   │   ├── specpack-schema.json
   │   ├── pack-schema.json
   │   └── manifest-schema.json
   ├── /governed/FMWK-000-framework/SPEC-001-hierarchy/PC-002-gate-definitions/
   │   ├── pack.json
   │   ├── (gate check specifications as JSON)
   │   └── ...
   └── ... (all FWK-0 packs)

5. COMPUTE AND VERIFY HASHES (hand-verified process)
   ├── For every file in /governed/FMWK-000-framework:
   │   ├── Compute SHA256
   │   ├── Record in parent pack.json
   │   └── Write pack.json with complete file manifest
   ├── Verify process:
   │   ├── Independent human checks hashes against source
   │   └── Recompute hashes, confirm match

6. ASSEMBLE FWK-0 SELF-REFERENTIAL PACKAGE
   ├── Create manifest.json at root (not in /governed, in staging)
   ├── manifest.json describes FWK-0 package with all hashes
   ├── Compute total_sha256 of entire manifest
   └── Hand-verify total_sha256 matches expectations

7. RECORD BOOTSTRAP EVENTS TO LEDGER
   ├── genesis_started: timestamp, version
   ├── framework_installed: FMWK-000, version, file_count
   ├── ownership_recorded: FMWK-000, all files
   └── genesis_complete: timestamp, root_event_hash
   └── Wait for each append to acknowledge (synchronously from kernel if available, or direct immudb if not)

8. BUILD COMPOSITION REGISTRY (in-memory, ephemeral)
   └── Read all framework.json files from /governed
       └── (Currently just FMWK-000)

9. BOOTSTRAP KERNEL PROCESS
   ├── Start kernel container
   ├── Point to /governed volume (already has FWK-0)
   ├── Point to immudb for Ledger
   ├── Load Graph from last snapshot (none exists yet; create empty)
   ├── Replay Ledger events: genesis_started → ownership_recorded → genesis_complete
   ├── Validate FWK-0's own gates (self-referential check)
   │   └── Confirm framework.json valid
   │   └── Confirm all packs own their files
   │   └── Confirm all hashes match
   ├── If validation passes: continue to Phase 2 (KERNEL)
   ├── If validation fails: hard stop, log catastrophic error, wait for operator intervention

10. OPERATOR CONFIRMATION
    └── Operator manually verifies GENESIS was successful
        ├── Ledger has genesis events?
        ├── /governed/FMWK-000-framework exists and is valid?
        ├── Kernel is accepting connections?
        └── Proceed to Phase 2 or abort?
```

**KEY INSIGHT:**
GENESIS is NOT automated. It's a ceremony. A human (or a dedicated bootstrap agent) runs it once, verifies each step, and confirms success. Why?

1. **Root of trust**: If GENESIS is automated, who verifies it? You need a bootstrap agent, which is a program, which needs verification. You end up with infinite regress. The only root of trust is a human reviewing the generated files and hashes.

2. **FWK-0 as its own test**: FWK-0 defines gates. FWK-0 is validated by FWK-0's gates. This is circular, but it's resolved by hand-verification: "I as a human opened framework.json, checked its content, recomputed its hash, confirmed it matches. FWK-0 is valid."

3. **Atomic bootstrap**: If GENESIS fails at step 7 (Ledger append), the operator knows exactly where to resume. If it fails at step 4 (file copy), the operator knows the filesystem is corrupted and can start over.

**IMPLEMENTATION CHECKLIST:**
- [ ] GENESIS script exists (shell script or Python, deterministic, reviewed by Ray)
- [ ] Script performs steps 1-9 in order
- [ ] Each step is logged to stdout + audit log
- [ ] Hashes written to files are independently verifiable (include process, not just result)
- [ ] Script halts if any hash verification fails
- [ ] Operator must manually approve before proceeding to KERNEL phase
- [ ] bootstrap.sh script is the ONLY way to initialize the system (not `docker-compose up`)

---

### GAP 2: Builder Agent Context Window — What Fits?

**THE PROBLEM:**
The docs say "A builder agent holds the spec pack + FWK-0 in context and authors frameworks autonomously." But FWK-0 is ~800 lines, spec packs can be hundreds of lines, and a builder needs to generate prompts, modules, tests, schemas. Does it all fit in a reasonable context window?

**CONTEXT BUDGET (assuming Claude 3.5 with 200k context):**

```
RESERVATION (DO NOT TOUCH):
- System prompt: 15k tokens (safety, protocols, constraints)
- Tool calls/responses: varies, ~50k tokens for a typical session

AVAILABLE FOR WORK:
- ~135k tokens for: spec pack + FWK-0 + generated framework

ALLOCATION:
- FWK-0 reference: 1500-2000 tokens
  ├── Dense, structured, omit narrative
  ├── Focus on sections builder needs (layer definitions, gates)
  └── Omit appendices, examples, design rationale
- Spec pack: 2000-3000 tokens
  ├── Complete spec pack (builder needs full picture)
  ├── Builder instructions in detail
  └── Quality measures referenced but not inline
- Framework generation: 50k-80k tokens
  ├── Authored framework.json, specpack.json, all pack.json
  ├── All prompt contracts (if prompt_pack)
  ├── Schemas for quality measures
  ├── Module code if simple (module_pack)
  └── If complex module_pack: builder stops and asks for help

REMAINING: ~50k tokens for iteration, refinement, testing

IMPLICATION:
- Complex module packs (>5k tokens of code) should NOT be authored by builder agent in single pass
- Use a two-phase approach:
  1. Builder agent: scaffolds, schemas, prompts, quality measures
  2. Human (or specialized code agent): implements complex module_pack code
  3. Builder agent: reintegrates, validates, packages
```

**MITIGATION:**
FWK-0 should be **layer-stratified for selective reading**:

```
FWK-0 READING PATHS:

For Prompt Pack authors:
  → Read: Section 5.1 (pack schema)
          Section 5.2 (prompt_pack type requirements)
          Section 11 (self-referential validation)
  ← Omit: Sections 8-10 (composition, dark factory, build process)

For Module Pack authors:
  → Read: Section 5.1, 5.2 (pack schema + module_pack requirements)
          Section 5.3 (filesystem conventions)
  ← Omit: Everything else

For Protocol Pack authors:
  → Read: Section 8.1 (protocol definitions)
          Section 5.2 (protocol_definition type)
  ← Omit: Everything else

For Full Framework authors:
  → Read: All sections (but skim, don't memorize)

IMPLEMENTATION:
- FWK-0 has section headers with "READ IF YOU ARE AUTHORING: [pack-type]"
- Builder agent prompt includes: "Read Section X if building [pack-type], otherwise skip"
- Reduces required context from 1500 to 500-800 tokens for specialized packs
```

**IMPLEMENTATION CHECKLIST:**
- [ ] FWK-0 reorganized with reading paths for each pack type
- [ ] Builder agent prompt specifies: "Read sections X-Y for your pack type"
- [ ] Create FWK-0-QUICK-START.md (300-400 lines, builder's reference card)
- [ ] Test: builder agent in 200k context + spec pack + FWK-0 + generates valid framework

---

### GAP 3: Mock Providers — How Do They Actually Work?

**THE PROBLEM:**
The dark factory needs "mock Ollama, mock Ledger, mock Graph" to test frameworks. But what does "mock" mean operationally? Can they be dropped in as replacements, or do builders need to know they're mocks?

**MOCK PROVIDER ARCHITECTURE:**

```
IN STAGING ENVIRONMENT (where builder works):

Real services (builder sees):
- /governed/ (read-only copy of real governed filesystem from inspect interface)
- /staging/ (builder's workbench)

Mock services (behind adapter):
- Mock Ollama (HTTP :11434)
  ├── Implements same REST API as real Ollama
  ├── Prompt input → JSON output (no actual LLM call)
  ├── Returns canned responses based on prompt hash
  ├── Example:
  │   POST /api/generate
  │   Input: {model: "default", prompt: "consolidate memories"}
  │   Output: {response: "MOCK_RESPONSE_FOR_CONSOLIDATION"}
  └── Allows testing: does the orchestrator handle the response correctly?

- Mock Ledger (same gRPC :3322 as real)
  ├── Accepts Write Path appends (in-memory only)
  ├── Returns append acknowledgment immediately
  ├── Stores events in RAM (discarded after test)
  ├── Allows testing: does Write Path correctly append?
  └── Allows testing: do events have correct schema?

- Mock Graph (same interface as real)
  ├── Accepts events from Write Path
  ├── Folds them into in-memory state
  ├── Responds to queries (retrieval, scoring)
  ├── Allows testing: does folding logic work correctly?
  └── Allows testing: does retrieval scoring return sensible results?

The trick: Builders don't see a difference. They call the same APIs as the real system.
Mock implementations are behind a Docker adapter that replaces real containers with mock containers.

TEST SUITE (quality measures):

SMOKE TEST: Does the framework install?
├── Generate KERNEL CLI validate command
├── Point at framework directory in staging
├── Run: dopejarmocli validate /staging/FMWK-050-my-framework
├── Pass condition: all gates pass, no errors
└── Tests: metadata valid, hashes computed, no conflicts

INTEGRATION TEST: Do prompt contracts execute?
├── Start mock Ollama, mock Ledger, mock Graph (Docker containers)
├── Load framework files into mock /governed
├── Send work order to mock orchestration with a prompt contract from this framework
├── Expect: prompt executes, returns result (canned response), Ledger event appended
├── Pass condition: all steps succeed, result is in expected format
└── Tests: prompts don't crash orchestrator, responses fold into Graph correctly

E2E TEST: Does the framework work in a full system turn?
├── Start mock Ollama, mock Ledger, mock Graph, mock kernel
├── Load KERNEL + this framework
├── Simulate a complete turn: user input → memory retrieval → planning → execution → learning → response
├── Expect: system produces output without deadlock or error
├── Pass condition: all primitives cooperate, framework integrates properly
└── Tests: framework plays nicely with others, no hidden dependency bugs

EXECUTION (dark factory):

Builder agent sees:
```python
# In builder's context during build loop:

def run_quality_measures(framework_path):
    # SMOKE
    result = subprocess.run(
        ["dopejarmocli", "validate", framework_path],
        capture_output=True
    )
    assert result.returncode == 0, "Smoke test failed"

    # INTEGRATION (if prompt_pack)
    if framework_has_prompt_pack:
        docker_up([
            "mock-ollama",
            "mock-ledger",
            "mock-graph"
        ])
        result = run_integration_test(framework_path)
        assert result.passed, "Integration test failed"
        docker_down()

    # E2E (if full framework)
    if framework_has_all_packs:
        docker_up([
            "mock-kernel",
            "mock-ollama",
            "mock-ledger",
            "mock-graph"
        ])
        result = run_e2e_test(framework_path)
        assert result.passed, "E2E test failed"
        docker_down()
```

MOCK PROVIDER REPLACEABILITY:

The key property: A framework tested against mocks should work against real services
with high confidence (not 100%, but high). This is true if:

1. Mock implementations are deterministic (same input → same output)
2. Mock implementations respect the same schemas as real implementations
3. Mock implementations fail fast on invalid inputs (same as real)
4. Builder tests for error cases ("what if Ledger append fails?")

Testing against mocks doesn't catch:
- Timing bugs (mocks are instant, real system has latency)
- Scale bugs (mocks can handle 1000 events, real system might not)
- Concurrency bugs (mocks are single-threaded)

But those are caught in a controlled environment before operator review,
and the operator can further test before production use.
```

**IMPLEMENTATION CHECKLIST:**
- [ ] Mock Ollama Docker image exists (responds with canned output)
- [ ] Mock Ledger Docker image exists (in-memory event store)
- [ ] Mock Graph Docker image exists (folds events, responds to queries)
- [ ] Builder agent prompt describes how to invoke quality measures
- [ ] Staging directory has docker-compose-staging.yml with mocks
- [ ] Quality measure schema includes criterion definition (what is being tested)
- [ ] Builder agent reads quality measures and generates test execution code

---

### GAP 4: Bootstrap Sequence for KERNEL — What Happens Between "KERNEL Installed" and "DoPeJarMo Running"?

**THE PROBLEM:**
OPERATIONAL_SPEC describes KERNEL installation but not the activation sequence. After KERNEL files are on disk, what must happen before the kernel process can accept operator sessions?

**SEQUENCE (happens after KERNEL gates pass):**

```
KERNEL INSTALLATION COMPLETE
↓
Ledger has events:
  - package_install_started (KERNEL package)
  - framework_installed (FMWK-001)
  - framework_installed (FMWK-002)
  - ... (all 7 frameworks)
  - package_install_complete
↓
Filesystem has:
  - /governed/FMWK-001-ledger/
  - /governed/FMWK-002-write-path/
  - ... (all 7 frameworks)
  - All files in place, hashes verified
↓
KERNEL ACTIVATION SEQUENCE:

1. STOP OLD KERNEL (if running)
   └── Drain in-flight work orders
   └── Snapshot Graph to /snapshots/YYYYMMDD-HHMMSS.snapshot
   └── Append SESSION_END to Ledger
   └── Close all WebSocket connections

2. VALIDATE KERNEL INTEGRITY (cold-storage validation)
   └── CLI tool connects directly to immudb
   └── Walks the framework chain: FMWK-001 through FMWK-007
   └── Verifies each file's hash against Ledger
   └── Confirms no ownership conflicts
   └── If any check fails → operator must diagnose before proceeding

3. LOAD GRAPH FROM SNAPSHOT (if exists)
   └── Most recent snapshot from /snapshots/
   └── Load into RAM (ephemeral, not persisted to disk)
   └── If no snapshot (first boot) → create empty Graph

4. REPLAY LEDGER FROM SNAPSHOT POINT (if snapshot loaded)
   └── Read all events after snapshot timestamp from immudb
   └── Fold each event into Graph
   └── Result: Graph is current state as of latest event

5. VALIDATE COMPOSITION (check that all interfaces are satisfied)
   └── Read all framework.json files from /governed
   └── Build dependency graph: which framework depends on which
   └── Verify: every consumed interface has a provider
   └── Verify: no circular dependencies
   └── Verify: all external dependencies (references to FWK-0) are installed
   └── If any check fails → operator sees which framework is broken

6. INITIALIZE WRITE PATH
   └── Create connection to immudb gRPC
   └── Set synchronous mode: Write Path appends must be acknowledged before returning
   └── Test connection: append a ping event, confirm received
   └── If connection fails → kernel cannot start, hard stop

7. INITIALIZE HO1 (EXECUTION)
   └── Attempt connection to Ollama at localhost:11434
   └── If Ollama not available → log warning, continue with degraded service
   └── If connection succeeds: HO1 is ready for work orders

8. INITIALIZE ZITADEL (IDENTITY)
   └── Attempt connection to OIDC endpoint
   └── If Zitadel not available → log error, operator cannot authenticate
   └── If connection succeeds: ready to validate JWTs

9. BUILD COMPOSITION REGISTRY (in-memory)
   └── Iterate all frameworks in /governed
   └── Extract interfaces from framework.json
   └── Build: map of framework_id → exposes → [interfaces]
   └── Build: map of framework_id → consumes → [interfaces]
   └── Store in RAM (ephemeral)

10. START WEBSOCKET SERVER
    └── Listen on :8080
    └── Routes:
        ├── /operator → DoPeJarMo sessions (authenticated with Zitadel JWT)
        └── /user → DoPeJar sessions (if DoPeJar frameworks installed)

11. OPERATOR CONFIRMATION
    └── Operator connects via WebSocket
    └── Operator authenticates (Zitadel OIDC flow)
    └── Operator can query system state through DoPeJarMo
    └── Operator confirms: "System ready"

12. PROCEED TO PHASE 3 (DoPeJarMo Agent Interface installation)
    └── Operator installs first governed package via CLI
    └── Gates validate through the installed Package Lifecycle framework
    └── Composition registry updates with new framework
    └── System continues growing

RECOVERY FROM PARTIAL FAILURE:

If step 5 (composition validation) fails:
  - Operator sees exactly which framework is broken
  - Operator can: rollback that framework, reinstall it, or diagnose further
  - Does NOT block all other operations

If step 6 (Write Path) fails:
  - Kernel cannot start (cannot write = cannot do anything)
  - Operator restarts immudb container
  - Kernel retries step 6
  - If still fails: something is seriously wrong, needs investigation

If step 7 (HO1) fails:
  - Kernel starts anyway (Ollama is external, not critical)
  - System runs but cannot execute local work orders
  - Operator checks Ollama logs, restarts container if needed
  - System recovers without restart

If step 8 (Zitadel) fails:
  - Kernel starts
  - Operator cannot authenticate WebSocket sessions
  - Operator must restart Zitadel (or has OIDC federation issue)
  - System recovers without restart

If step 9 (Composition registry) fails:
  - Operator sees which framework.json failed to parse
  - Operator manually fixes or rolls back that framework
  - Kernel restarts composition registry build
  - System continues
```

**IMPLEMENTATION CHECKLIST:**
- [ ] KERNEL package gate includes: post-install composition validation
- [ ] kernel process has startup sequence (code, not documentation)
- [ ] Each startup step is logged with timestamp + success/failure
- [ ] Startup fails fast: if any critical step fails (Write Path, Ledger integrity), halt with error message
- [ ] Startup tolerates: Ollama not available, Zitadel delay (retry)
- [ ] Operator sees startup status via DoPeJarMo or logs
- [ ] Kernel-restart playbook documented for operators

---

### GAP 5: WebSocket Server — Part of KERNEL or Agent Interface?

**THE PROBLEM:**
OPERATIONAL_SPEC says kernel listens on :8080 for WebSocket. But WebSocket is an interactive, stateful protocol. Is that part of KERNEL (infrastructure) or part of the Agent Interface framework?

**DECISION: WebSocket is KERNEL infrastructure, not a framework.**

```
REASONING:

The kernel is a process. It accepts WebSocket connections. That's operational.
Agent Interface is a framework that uses those connections to provide interactive capabilities.

Think of it like Docker:
- Docker daemon listens on unix:/var/run/docker.sock (infrastructure)
- Docker CLI connects and sends commands (application)
- We don't call the socket a "framework"

ARCHITECTURE:

KERNEL process (monolithic binary):
  ├── Primitive 1: Ledger client (talks to immudb)
  ├── Primitive 2: Write Path
  ├── Primitive 3-4: Orchestration + Execution
  ├── Primitive 5: Graph
  ├── Infrastructure: WebSocket server
  │   └── Listener on :8080
  │   └── Routes:
  │       ├── /operator (DoPeJarMo)
  │       ├── /user (DoPeJar or other agents)
  │       ├── /internal (work order results, internal plumbing)
  │   └── Connection lifecycle: connect → authenticate → dispatch → stream → disconnect
  └── Framework Loader (reads /governed, loads installed frameworks)

FMWK-006-package-lifecycle:
  ├── Part of KERNEL binary (compiled in)
  ├── Implements: install, uninstall, rollback gates
  ├── Exposes: command-line tools (scaffold, seal, validate, package, install, rollback)
  └── Does NOT implement WebSocket — that's kernel infrastructure

FMWK-00X-agent-interface (DoPeJarMo Agent, Layer 1):
  ├── Framework (separate from KERNEL, installed after KERNEL)
  ├── Depends on: WebSocket (infrastructure, already exists)
  ├── Responsibility: DoPeJarMo agent logic (conversational, framework diagnostics, operator commands)
  ├── Exposes: /operator route becomes "DoPeJarMo is here, talk to him"
  └── Installed as normal framework through gates

WHY THIS SEPARATION:

1. Infrastructure stability: WebSocket is required for any agent interaction. If it were a framework,
   removing that framework would kill the only way to interact with the system (deadlock).

2. Recovery: If Agent Interface breaks, operator still has command-line tools. Those tools connect
   to immudb directly (not through WebSocket). The operator can diagnose and fix without a running agent.

3. Single responsibility: KERNEL is the runtime. Agent Interface is a capability framework.
   They have different governance.

4. Bootstrap: KERNEL must be running before any framework can be installed. WebSocket must exist
   so the operator can trigger framework installs. So WebSocket must be part of KERNEL.

CONCRETELY:

Step A: GENESIS + KERNEL bootstrap
  → Ledger exists, Write Path works, Graph exists, WebSocket listens
  → Kernel is ready but NOT interactive (no agent to talk to)
  → Operator has CLI tools (dopejarmocli) for governance operations

Step B: Install Agent Interface framework (via CLI)
  → Framework gates run, Agent Interface installs
  → Agent Interface framework code is loaded by kernel
  → WebSocket /operator route now dispatches to Agent Interface logic
  → Operator can interact conversationally with DoPeJarMo

IMPLEMENTATION:

KERNEL binary (monolithic, v1):
  - Compiles in: primitives, Write Path, Package Lifecycle, WebSocket server
  - Does NOT compile in: Agent Interface framework
  - All compiled-in code is in KERNEL's responsibility boundary (the 7 frameworks)
  - Framework code is loaded dynamically from /governed (FMWK-00X frameworks)

WebSocket server code is in KERNEL's binary but is not a separate framework.
It's infrastructure, like the TCP/IP stack.
```

**IMPLEMENTATION CHECKLIST:**
- [ ] KERNEL binary includes WebSocket server on :8080
- [ ] Routes are hardcoded: /operator, /user, /internal
- [ ] Connection lifecycle: WebSocket connect → Zitadel OIDC JWT validation → dispatch to framework agent
- [ ] Agent Interface framework is separate (FMWK-00X), not compiled in, installs in Phase 3
- [ ] Documentation: "WebSocket is infrastructure; agents are frameworks"

---

### GAP 6: Prompt Contracts — How Are They Tested Before Cognitive Stack?

**THE PROBLEM:**
Prompt contracts are the interface between builders and HO1. They define input schema, output schema, validation rules. But how do builders validate them before the full cognitive stack exists?

**ANSWER: Structural validation + mock execution**

```
A prompt contract is a JSON file. It looks like:

{
  "contract_id": "PCTR-001",
  "description": "Consolidate memories from this session",
  "boundary": "Input is one session, output is one learning artifact",
  "input_schema": {
    "type": "object",
    "properties": {
      "session_memory": { "type": "string", "description": "Raw session transcript" },
      "context_limit": { "type": "integer", "description": "Max tokens for consolidation" }
    },
    "required": ["session_memory"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "consolidation": { "type": "object", "description": "Structured learning artifact" }
    },
    "required": ["consolidation"]
  },
  "prompt_template": "You are a memory consolidator...",
  "validation_rules": [
    {
      "rule_id": "VAL-001",
      "name": "output-must-have-consolidation",
      "check": "output.consolidation is object and not empty"
    }
  ]
}

VALIDATION STRATEGIES:

1. STRUCTURAL VALIDATION (schema syntax)
   - Does input_schema parse as valid JSON Schema?
   - Does output_schema parse as valid JSON Schema?
   - Do they define required fields?
   - Gate: Contract must be structurally sound

2. TEMPLATE VALIDATION (prompt sanity)
   - Is prompt_template non-empty?
   - Does it mention the input fields? (heuristic check for "did builder forget to use the input?")
   - Is it > 100 chars, < 10k chars? (sanity check on length)
   - Gate: Template is minimally sane

3. SCHEMA CONSISTENCY (input/output alignment)
   - Does the output_schema match what the validation_rules expect?
   - Example: if VAL-001 checks output.consolidation, does output_schema declare consolidation?
   - Gate: Validation rules are checking fields that exist in output_schema

4. MOCK EXECUTION (actual behavior)
   - Builder provides test input (JSON matching input_schema)
   - Mock Ollama returns a canned response (matching output_schema)
   - Validation rules run against the response
   - Pass condition: validation rules accept the canned response
   - Example:
     - Test input: { "session_memory": "Hello world" }
     - Mock response: { "consolidation": { ... } }
     - Validation rule VAL-001 checks: is output.consolidation object? Yes → pass

   Builder writes test cases in quality measures:

   {
     "criterion_id": "PCTR-001-smoke",
     "description": "Prompt contract executes and validates",
     "test_cases": [
       {
         "input": { "session_memory": "test session" },
         "expected_output": { "consolidation": {} },
         "should_validate": true
       },
       {
         "input": { "session_memory": "" },
         "expected_output": { "consolidation": {} },
         "should_validate": false,
         "reason": "empty session should fail validation"
       }
     ]
   }

5. INTEGRATION (does it work with HO1 dispatcher)
   - Mock HO1 receives the prompt contract
   - Mock HO1 renders prompt_template with test input
   - Mock HO1 parses output, runs validation_rules
   - Pass condition: HO1 doesn't crash, returns structured result
   - Example (in Python pseudocode):

   def test_prompt_contract_with_mock_ho1(contract, test_input):
       mock_ho1 = MockHO1()

       # HO1 would normally call Ollama here
       # In test, it returns canned response
       canned_response = generate_canned_response(contract, test_input)

       # HO1 validates response
       validation_result = validate_against_rules(
           canned_response,
           contract['validation_rules']
       )

       assert validation_result.passed
       assert validation_result.output == expected

BUILDER WORKFLOW:

1. Write prompt contract (PCTR-001.json)
2. Validate structure (gate-check-1: is JSON, has schemas)
3. Write test cases in quality measures
4. Generate mock HO1 code that validates contracts
5. Run: "dopejarmocli test FMWK-050/PC-001-prompts/PCTR-001.json"
6. Mock HO1 executes against test cases
7. If all pass: contract is ready for real HO1
8. If any fail: builder adjusts prompt_template or validation_rules and retries
```

**IMPLEMENTATION CHECKLIST:**
- [ ] Prompt contract JSON schema in FWK-0/PC-001-schemas
- [ ] Validation rules are JSON (not code)
- [ ] Gate: prompt contract schema validation
- [ ] Gate: validation rules consistency check
- [ ] Quality measure framework allows test_cases for prompt contracts
- [ ] Mock HO1 in staging environment can execute test cases
- [ ] Builder agent knows how to write test cases
- [ ] dopejarmocli has `test PCTR` command

---

### GAP 7: The Missing Piece — What Does "All Prompt Contracts Must Be Discoverable" Mean?

**THE PROBLEM:**
OPERATIONAL_SPEC and BUILDER_SPEC talk about prompt contracts but don't define how the system discovers them. When HO1 needs to execute a work order, how does it find the right prompt contract?

**ANSWER: Framework registry + interface-to-contract mapping**

```
PROMPT CONTRACT DISCOVERY:

HO2 creates a work order:
{
  "work_order_id": "WO-00123",
  "requested_capability": "consolidate-session",
  "input": { "session_memory": "..." },
  "budget": { "tokens": 1000 }
}

HO1 must find the prompt contract that implements "consolidate-session".

Path 1: Direct declaration (in framework.json)
  Framework declares: "I implement this capability"

  ```json
  {
    "id": "FMWK-003",
    "capabilities": [
      {
        "capability_id": "consolidate-session",
        "contract_reference": "PCTR-001",
        "pack_location": "PC-001-consolidation"
      }
    ]
  }
  ```

Path 2: Interface-based discovery (future)
  Framework exposes protocol definition pack (protocol_definition type)
  HO1 reads the protocol definition, finds contract reference
  More flexible for polymorphism (multiple frameworks can expose same capability)

SYSTEM STARTUP (Composition Registry):

Kernel builds an in-memory registry:

```python
composition_registry = {
  'capabilities': {
    'consolidate-session': {
      'framework_id': 'FMWK-003',
      'contract_id': 'PCTR-001',
      'pack': 'PC-001-consolidation',
      'path': '/governed/FMWK-003-memory/SPEC-001-learning/PC-001-consolidation/consolidate-session.json'
    },
    'retrieve-memory': {
      'framework_id': 'FMWK-003',
      'contract_id': 'PCTR-002',
      'pack': 'PC-002-artifact-store',
      'path': '/governed/FMWK-003-memory/SPEC-001-learning/PC-002-artifact-store/retrieve-memory.json'
    }
  }
}
```

When HO1 gets work order:

```python
def execute_work_order(work_order):
    capability_name = work_order['requested_capability']

    # Look up contract
    contract_ref = composition_registry['capabilities'][capability_name]
    contract = load_json(contract_ref['path'])

    # Validate input
    input_valid = validate_json(
        work_order['input'],
        contract['input_schema']
    )
    assert input_valid, "Invalid input for contract"

    # Render prompt
    rendered_prompt = contract['prompt_template'].format(**work_order['input'])

    # Call LLM (mock or real)
    response = call_llm(rendered_prompt, contract)

    # Validate output
    output_valid = all(
        rule.check(response)
        for rule in contract['validation_rules']
    )
    assert output_valid, "Output failed validation"

    # Write result
    return {
      'work_order_id': work_order['work_order_id'],
      'result': response,
      'valid': True
    }
```

CAPABILITY DISCOVERY & REGISTRATION:

At startup (and after each install):

1. Read all installed frameworks from /governed
2. For each framework.json:
   ├── Extract "capabilities" array
   ├── For each capability:
   │   ├── Read contract JSON from pack
   │   ├── Validate contract structure
   │   └── Register in memory (composition_registry)
3. If any capability has conflict (two frameworks claim same capability):
   └── System gate fails, reject package
   └── Operator must resolve (one framework removes the capability claim)

FRAMEWORK MUST DECLARE:

```json
{
  "id": "FMWK-003",
  "name": "memory",
  "capabilities": [
    {
      "capability_id": "consolidate-session",
      "description": "Consolidate a single session into learning artifacts",
      "contract_id": "PCTR-001",
      "pack_id": "PC-001-consolidation",
      "requires_external_resources": false,
      "cost_estimate_tokens": 500
    },
    {
      "capability_id": "retrieve-memory",
      "description": "Retrieve relevant learning artifacts for query",
      "contract_id": "PCTR-002",
      "pack_id": "PC-002-artifact-store",
      "requires_external_resources": false,
      "cost_estimate_tokens": 100
    }
  ]
}
```

This gives HO2 visibility: what capabilities exist, what they cost, what they require.
HO2 uses this for planning (ChooseCapabilities heuristic from BUILDER_SPEC).
```

**IMPLEMENTATION CHECKLIST:**
- [ ] framework.json schema includes "capabilities" array (optional)
- [ ] Gate: validates capability -> contract -> pack reference chain
- [ ] Gate: detects capability conflicts (two frameworks claiming same ID)
- [ ] Composition registry includes capabilities map
- [ ] HO1 receives: { capability_id, input } and looks it up in registry
- [ ] HO1 loads contract JSON and executes work order
- [ ] Mock HO1 in staging uses same registry + lookup logic
- [ ] System gate fails if two frameworks declare same capability ID

---

## PART 3: 48-HOUR SPRINT RISKS — What Will Block Progress?

Ordered by impact if not addressed:

---

### RISK 1: FWK-0 Feedback Loop Doesn't Close (CRITICAL)

**What could go wrong:**
- Builder agent is tasked to "build FMWK-001-ledger"
- Builder reads FWK-0 to understand what a framework is
- Builder creates framework.json
- Gate validation runs: does it conform to FWK-0's schema?
- If schema is missing/wrong, builder can't validate locally
- Builder can't proceed because they can't tell if their work is correct

**Blocking condition:**
- FWK-0 schemas must exist BEFORE any builder can validate
- Specifically: framework-schema.json, specpack-schema.json, pack-schema.json must be complete and correct
- If ANY schema is incomplete during GENESIS, bootstrap is stuck

**Mitigation (DO THIS FIRST):**
- [ ] Before GENESIS: hand-verify all FWK-0 schemas
- [ ] Before builder start: run `dopejarmocli validate /governed/FMWK-000-framework` and confirm all gates pass
- [ ] Before assigning builder tasks: confirm FWK-0 gates pass against FWK-0 itself
- [ ] Create FWK-0 schema checklist (framework-schema.json must have X fields, specpack-schema.json must have Y, etc.)

**Signal of trouble:**
- Builder reports: "I can't tell if my framework.json is valid"
- Gate validation hangs or crashes
- FWK-0 self-referential validation fails

---

### RISK 2: ID Assignment Collision (HIGH)

**What could go wrong:**
- Multiple builders start simultaneously
- Builder A proposes FMWK-050-memory-v2
- Builder B proposes FMWK-050-attention
- Both submit to install lifecycle at the same time
- Package Lifecycle gate tries to install both, realizes FMWK-050 exists twice, rejects both packages

**Blocking condition:**
- No way for builders to know what IDs are available without a central registry
- Two independent builders with no coordination will eventually collide
- Rejection cascades through both builders' work (lost effort)

**Mitigation:**
- [ ] For 48-hour sprint: use RESERVED RANGES (see Q1.1)
  - Builder 1: use FMWK-030 through FMWK-039
  - Builder 2: use FMWK-040 through FMWK-049
  - Ray: manually assign ranges before builders start
- [ ] CLI tool: `dopejarmocli list-framework-ids` shows all installed IDs and reserved ranges
- [ ] Builder must check this before proposing ID (manual coordination, not automatic)
- [ ] For later: implement ID registry service if truly autonomous parallel builders needed

**Signal of trouble:**
- Builder says: "I don't know what ID to use"
- Multiple frameworks with same ID proposed
- Install rejects with "duplicate ID"

---

### RISK 3: Mock Providers Missing (HIGH)

**What could go wrong:**
- Builder writes framework, runs quality measures
- Quality measures try to call mock Ollama, mock Ledger, mock Graph
- Mock containers don't exist or don't implement full API
- Builder can't test, can't proceed

**Blocking condition:**
- Mock Ollama doesn't respond to /api/generate
- Mock Ledger crashes on append with schema mismatch
- Mock Graph doesn't fold events correctly
- Test suite fails with "connection refused" instead of meaningful error

**Mitigation:**
- [ ] Staging docker-compose.yml is complete BEFORE first builder task
- [ ] Mock implementations match KERNEL's API surface exactly (get this from BUILDER_SPEC)
- [ ] Test the mocks with a dry run: "can I call mock Ollama and get a response?"
- [ ] Include in FWK-0 a mock provider reference spec (what each mock implements)
- [ ] Builder agent prompt includes: "Use mocks in staging, not real services"

**Signal of trouble:**
- Builder reports: "Quality measures can't connect to Ollama"
- Mock container missing or fails to start
- Schema mismatch between real and mock

---

### RISK 4: Spec Pack Incompleteness (MEDIUM)

**What could go wrong:**
- Spec pack for FMWK-001-ledger is incomplete
- It says "create pack PC-001-schemas" but doesn't explain what schemas are needed
- Builder invents wrong schemas
- Gates fail because schemas don't match FWK-0's expectations
- Builder tries again, fails again, spins

**Blocking condition:**
- Spec pack is too vague ("create schemas" without listing them)
- Builder has to guess
- FWK-0's expectations are not captured in spec pack

**Mitigation:**
- [ ] Spec pack template (BUILDER_SPEC) is prescriptive, not suggestive
- [ ] Each KERNEL spec pack is written BEFORE builder starts
  - FMWK-001-ledger/specpack.json lists exactly which schemas are needed
  - FMWK-002-write-path/specpack.json lists exactly which protocols are needed
- [ ] Ray reviews each spec pack before assigning to builder
- [ ] Builder constraint: "Do exactly what specpack.json says, no more, no less"

**Signal of trouble:**
- Builder says: "I don't know what to build"
- Spec pack has vague phrases like "define appropriate schemas"
- Builder creates extra files not mentioned in spec pack

---

### RISK 5: Gate Definitions Missing or Buggy (MEDIUM)

**What could go wrong:**
- FWK-0/PC-002-gate-definitions/ doesn't exist or is incomplete
- Package Lifecycle framework has no way to validate installed frameworks
- Builders can't run dry-run gate checks
- Operator tries to install KERNEL, gates crash with "missing definition"

**Blocking condition:**
- Gate checks are hardcoded in Package Lifecycle (not in FWK-0 as data)
- No way to validate locally before submit
- Integration between FWK-0 (defining what gates are) and FMWK-006 (implementing gates) is broken

**Mitigation:**
- [ ] Gate definitions are JSON files in FWK-0/PC-002-gate-definitions/
  - framework-gate.json
  - specpack-gate.json
  - pack-gate.json
  - file-gate.json
  - package-gate.json
  - system-gate.json
- [ ] Each gate file specifies checks as declarative data (not code)
- [ ] Package Lifecycle reads these files at startup, builds gate runner
- [ ] Test: can the gate runner validate FWK-0 itself?

**Signal of trouble:**
- Package Lifecycle framework can't find gate definitions
- Gates crash with "undefined check"
- FWK-0 self-validation fails

---

### RISK 6: Ledger Append Timing (MEDIUM)

**What could go wrong:**
- Write Path tries to append to immudb, gets latency spike
- Write Path assumes synchronous append (acknowledged immediately)
- Ledger appends but kernel doesn't wait for ACK
- Power loss happens
- Ledger has the event, but kernel thinks it's lost
- State divergence on restart

**Blocking condition:**
- Write Path is not strictly synchronous
- Kernel proceeds before immudb acknowledges append
- Core architectural invariant is violated

**Mitigation:**
- [ ] Write Path implementation is synchronous: append → wait for ACK → return
- [ ] Timeout: if ACK takes >1 second, fail the operation (don't retry silently)
- [ ] Test: power loss simulator — shut down immudb mid-append, verify recovery
- [ ] Log: every append includes timestamp + ACK timestamp
- [ ] Operator sees: "Ledger append took X ms" (for performance debugging)

**Signal of trouble:**
- Write Path returns before Ledger ACK
- Appendix doesn't have consistent ordering
- Recovery after crash shows missing events

---

### RISK 7: Circular Dependency in KERNEL Frameworks (MEDIUM)

**What could go wrong:**
- FMWK-003 (orchestration) depends on FMWK-004 (execution)
- FMWK-004 depends on FMWK-003
- Topological sort fails
- Package Lifecycle rejects KERNEL package
- Bootstrap is blocked

**Blocking condition:**
- Framework dependency graph has cycle
- No valid installation order exists
- KERNEL cannot be installed

**Mitigation:**
- [ ] Design KERNEL framework dependencies with Ray BEFORE builder starts
  - [ ] Create dependency graph (on paper or in BUILDER_SPEC)
  - [ ] Verify: DAG (no cycles)
  - [ ] Verify: topological sort produces installation order
- [ ] Each framework's framework.json lists dependencies before builder task assigned
- [ ] Test: topological sort on KERNEL dependency graph passes

**Signal of trouble:**
- Topological sort fails with "cycle detected"
- Installation order is undefined
- Builder says: "I don't know which framework to build first"

---

### RISK 8: Operator Communication is Missing (LOW)

**What could go wrong:**
- KERNEL boots successfully
- Operator tries to connect via WebSocket
- Kernel is listening but doesn't understand operator commands
- "help" command doesn't exist
- Operator is confused

**Blocking condition:**
- Agent Interface framework doesn't exist yet
- Kernel has WebSocket but no agent on the other end
- Operator can't talk to the system

**Mitigation (not blocking, but needed for demo):**
- [ ] Until Agent Interface framework is installed, kernel returns helpful error
  - "WebSocket ready. No agent loaded. Install DoPeJarMo Agent Interface to proceed."
- [ ] CLI tools are available immediately after KERNEL
  - `dopejarmocli list-frameworks`
  - `dopejarmocli show-framework FMWK-001`
  - `dopejarmocli install /path/to/package.json`
- [ ] Operator can manage system without WebSocket (CLI is sufficient for 48-hour sprint)
- [ ] Agent Interface is installed as first governed package (Phase 3)

**Signal of trouble:**
- Operator feels lost after KERNEL boots
- No way to check system state
- Operator doesn't know what to do next

---

### RISK 9: Builder Context Window Exhaustion (MEDIUM)

**What could go wrong:**
- Builder agent is tasked to "build FMWK-002-write-path"
- Builder holds: FWK-0 (2k tokens) + FMWK-002 spec pack (3k tokens) + KERNEL overview (1k tokens)
- Builder starts writing framework.json, specpack.json, packs
- Builder hits token limit before finishing
- Builder request is incomplete, must be restarted

**Blocking condition:**
- Builder context exhaustion causes task failure
- Rework needed
- Timeline slips

**Mitigation:**
- [ ] Before assigning builder task: calculate token budget
  - FWK-0 excerpt for this framework: ~500 tokens
  - Spec pack: ~1500 tokens
  - Framework to author: varies by complexity
  - Reserve: 50k tokens for iteration/refinement
  - Total needed: ~60k for complex framework
- [ ] For complex frameworks: break into phases
  - Phase A: Author framework.json, specpack.json, pack.json structures
  - Phase B: Author prompt contracts (if prompt_pack)
  - Phase C: Author module code (if module_pack)
  - Phase D: Write quality measures
- [ ] Builder agent prompt includes: "If you run low on tokens, summarize progress and ask for continuation"

**Signal of trouble:**
- Builder output is truncated
- Builder says: "I'm running low on context"
- Partial framework submitted (incomplete spec packs)

---

### RISK 10: Governance Rules Are Too Vague (LOW)

**What could go wrong:**
- FMWK-001-ledger declares: "All events must be immutable"
- This is governance_rules[0] in framework.json
- Package Lifecycle reads this and... does nothing
- Gate doesn't know how to check immutability
- Rule is unenforceable

**Blocking condition:**
- Governance rules don't have concrete enforcement strategy
- Gates pass regardless of rule compliance
- Rules become documentation, not governance

**Mitigation:**
- [ ] See Q2.1 resolution: each governance rule has "enforcement" field
  - type: "gate-check" | "architectural-boundary" | "ownership-check"
  - For immutability: enforcement type is "ownership-check"
  - Checked by: replaying Ledger events and verifying framework owns those events
- [ ] Before assigning framework task: review governance rules
  - Can they be enforced? If not, rewrite them.
- [ ] Test: governance rule enforcement passes for FMWK-001

**Signal of trouble:**
- Governance rule has no enforcement strategy
- Gate doesn't check it
- Rule is aspirational, not enforced

---

## SUMMARY: TOP 3 BLOCKING RISKS

1. **FWK-0 Feedback Loop** — If FWK-0 schemas are incomplete, bootstrap cannot validate
   - FIX: Hand-verify all schemas BEFORE GENESIS

2. **KERNEL Circular Dependency** — If KERNEL frameworks have cycles, cannot install
   - FIX: Design dependency graph, verify DAG, communicate to builders BEFORE tasks

3. **Mock Providers Missing** — If mocks don't exist, builders can't test
   - FIX: Implement mock Ollama, Ledger, Graph in Docker BEFORE builder tasks

All others are manageable or deferrable.

---

## CHECKLIST FOR 48-HOUR SPRINT START

- [ ] FWK-0 self-validates (run gates against FMWK-000)
- [ ] All 7 KERNEL frameworks listed with dependencies (no cycles)
- [ ] KERNEL spec packs written and reviewed
- [ ] Mock providers implemented and tested
- [ ] ID ranges assigned to builders (no collisions possible)
- [ ] CLI tools ready (scaffold, seal, validate, package, install)
- [ ] Builder agent prompts finalized
- [ ] GENESIS script ready for manual execution
- [ ] Bootstrap playbook documented (for operator recovery)
- [ ] Operator quick-start: "What can I do after KERNEL boots?"

---

## FINAL WORDS

The 7 decisions above are pragmatic for v1. They unblock development. They're not perfect — but they're good enough to:
1. Get agents running in 48 hours
2. Preserve the ability to evolve later
3. Maintain the core property: pristine memory through governance

Every decision includes a forward path to refinement without breaking the foundation. FWK-0 is the constitutional layer. Decisions at this level are high-stakes but durable.

Good luck.
