---
title: "FWK-0 — The Framework Framework (ROUGH DRAFT)"
status: DRAFT — NOT AUTHORITY
version: "0.2"
last_updated: "2026-02-26"
author: "Ray Bruni + Claude"
audience: "Builder agents authoring frameworks for DoPeJarMo. Humans reviewing framework design."
depends_on:
  - NORTH_STAR.md
  - BUILDER_SPEC.md
  - OPERATIONAL_SPEC.md
notes: >
  This is a rough draft capturing decisions made during design sessions.
  It is NOT an authority document. It will be refined, validated, and
  promoted to authority status through review. Outstanding questions
  are tracked in FWK-0-OPEN-QUESTIONS.md.
---

# FWK-0 — The Framework Framework

## Why FWK-0 Exists

DoPeJar is pristine memory. Good memory reduces compute. If the system reconstructs the perfect context every turn — exactly what's relevant, nothing that isn't — then smaller, cheaper models produce results as good as or better than larger, expensive models guessing from decaying context windows. Storage costs are dropping. Compute costs are rising. A system that trades storage for compute is swimming with the economic current.

The governance architecture (Ledger, gates, provenance chains) exists because pristine memory requires it. Without governance, memory corrupts silently and you're back to throwing compute at the problem. The governance is plumbing — nobody builds a house because they love plumbing. They build it because they need water to work reliably. We are not building a governance system. We just need governance to make the memory trustworthy.

**DRIFT WARNING TO BUILDER AGENTS:** If you are reading this document and thinking "governance system" — stop. Read NORTH_STAR's Drift Warning. This is a memory system. The governance makes the memory pristine. The pristine memory makes cheaper models viable. The economics justify the architecture. Do not optimize the governance for its own sake. Every governance decision serves one question: does this make the memory more trustworthy?

FWK-0 is also the contract that makes the dark factory work. Builder agents (and eventually DoPeJar herself) assemble frameworks autonomously. FWK-0 ensures that every framework — regardless of who built it — has the same shape, passes the same gates, follows the same provenance chain. The manufacturing process is standardized. The factory scales because the contract is stable.

## What FWK-0 Is

FWK-0 is the first artifact authored in the DoPeJarMo system. It defines what a framework is, how frameworks are structured, how they are packaged, how they are installed, and how they compose into a running system. Every framework — including FWK-0 itself — must conform to the shape FWK-0 defines.

FWK-0 is three things simultaneously:

1. **Specification** — the schemas, filesystem conventions, gate definitions, and event types that make frameworks concrete and machine-validatable.
2. **Reference implementation** — FWK-0 is itself a framework. Its own metadata files validate against the schemas it defines. Its own directory layout follows the conventions it declares. Its own gates pass the checks it specifies.
3. **Authoring guide** — a builder who needs to create a new framework reads FWK-0 and knows exactly what to write, where to put it, what gates it will face, and how to declare interfaces to other frameworks.

**Design constraint:** FWK-0 must be readable by a builder agent in a single context window while also holding a framework's spec pack. Dense and structured, not narrative.

---

## 1. Preamble — How to Read This Document and How to Author a Framework

### Reading Order

If you are a **builder agent assembling a framework**: read Section 2 (ID Conventions) first, then read the layer definition for each layer you're building (Sections 3–6), then read Section 7 (Package) to understand how to assemble your deliverable, then read Section 8 (Interface & Composition) to understand how your framework connects to others.

If you are a **gate validation tool**: read the Gate subsection of each layer definition (Sections 3–6), then the full gate sequence in Section 7.

If you are **verifying system integrity from cold storage**: read Section 7 (Package) for the Ledger event catalog, then walk the provenance chain bottom-up through Sections 6–3.

### Authoring Workflow (The Golden Path)

To create a new framework:

1. Work in the **staging directory** (not the governed filesystem).
2. Define your framework metadata (Section 3 schema).
3. Define your spec pack(s) (Section 4 schema).
4. Create your packs — prompt packs, module packs, quality measures, protocol definitions (Section 5 schema).
5. Write the files within each pack.
6. Assemble into a package with manifest.json (Section 7 schema).
7. Submit to the install lifecycle. Gates validate at every layer. All pass → installed. Any fail → rejected.

You do not need to understand the full OS. You need your framework's spec pack and this document.

---

## 2. ID Conventions

All identifiers follow predictable patterns. IDs are assigned at authoring time by the builder, validated at install time by gates.

| Entity | Pattern | Example | Notes |
|--------|---------|---------|-------|
| Framework | `FMWK-NNN` | `FMWK-000`, `FMWK-001` | Three-digit zero-padded. Sequential. |
| Spec Pack | `SPEC-NNN` | `SPEC-001`, `SPEC-002` | Scoped within framework. |
| Pack | `PC-NNN` | `PC-001`, `PC-002` | Scoped within spec pack. |
| Prompt Contract | `PCTR-NNN` | `PCTR-001` | Scoped within framework. |
| Package Version | `semver` | `1.0.0`, `1.1.0` | Major.Minor.Patch. |

### Naming Convention for Filesystem

Directories encode the hierarchy chain for human-readable provenance:

```
FMWK-NNN-<name>/SPEC-NNN-<name>/PC-NNN-<name>/
```

Example:
```
FMWK-003-memory/SPEC-001-learning/PC-001-consolidation/
```

A file's provenance is readable from its path without opening any metadata file.

### Uniqueness Rules

- Framework IDs are globally unique across the system.
- Spec Pack IDs are unique within their parent framework.
- Pack IDs are unique within their parent spec pack.
- Prompt Contract IDs are unique within their parent framework.
- The combination of framework ID + spec pack ID + pack ID + filename is the globally unique identifier for any file in the governed filesystem.

> **OPEN QUESTION:** Are IDs purely sequential, or should they be content-addressed (hash-derived)? Sequential is simpler. Content-addressed gives you collision-free IDs across independent builders. See FWK-0-OPEN-QUESTIONS.md.

---

## 3. Framework Layer

A framework is a single-responsibility capability in DoPeJarMo. It declares what it does, what rules govern it, what interfaces it exposes, what interfaces it consumes, and what it depends on.

### 3.0 Framework Decomposition Standard

Before authoring a framework, apply these three tests to confirm the boundary is correct. All three must be satisfied. These tests apply at every layer — KERNEL, Layer 1, Layer 2, and beyond.

**Test 1 — Splitting Test:** A framework MUST be independently authorable. A builder agent, given only a spec pack and FWK-0, can produce a complete framework without needing to co-author another framework simultaneously. If two things must be written together to work, they are one framework.

**Test 2 — Merging Test:** If two candidate frameworks are operational modes of the same capability — different behaviors of the same underlying mechanism — they MUST be merged into one framework with separate spec packs. Spec packs within a framework handle modal variation. Frameworks handle capability boundaries.

**Test 3 — Ownership Test:** A framework MUST have exclusive data ownership. No shared schemas, no shared event types, no shared graph node types between frameworks. If two frameworks need the same data, one owns it and the other consumes it through a declared interface. Shared ownership is a decomposition error.

**Application to KERNEL (6 frameworks):**

| Framework | ID | Owns | Rationale |
|-----------|-----|------|-----------|
| Ledger | FMWK-001 | Append-only store, event schemas, hash chain | Independent storage primitive. Builder can author from event schema spec alone. |
| Write Path | FMWK-002 | Synchronous mutation, fold logic, snapshot | Owns the Ledger→Graph consistency invariant. Tightly coupled to Ledger at runtime but independently authorable — Write Path's spec is "given events, fold into Graph." |
| Orchestration (HO2) | FMWK-003 | Work order planning, dispatch, context computation, aperture | Mechanical only. Reads Graph, plans work. No LLM. Independently authorable from a spec pack defining dispatch rules. |
| Execution (HO1) | FMWK-004 | LLM calls, prompt contract enforcement, signal delta submission | All cognitive work. Independently authorable — "given a work order and a prompt contract, execute and return." |
| Graph (HO3) | FMWK-005 | In-memory directed graph, node/edge schemas, query interface | Pure storage. Independently authorable — "given fold events from Write Path, maintain queryable state." |
| Package Lifecycle | FMWK-006 | Gates, install/uninstall, staging CLI tools, composition registry | Merges previous "kernel-cli" into Package Lifecycle (merging test: CLI tools are operational modes of the packaging capability, not a separate capability). |

**Why 6, not 7:** The splitting test fails for a standalone "kernel-cli" framework — CLI tools cannot be authored independently from the gate logic they invoke. The merging test confirms they are operational modes (CLI = user-facing mode, gates = validation mode) of the same packaging capability.

**Why not fewer:** Signal Accumulator is fold logic inside Write Path, not a separate framework (merging test — it's an operational mode of folding). Work Order is a data structure owned by Orchestration (ownership test — HO2 owns the lifecycle). Prompt Contract is a schema owned by Execution (ownership test — HO1 enforces them).

### 3.1 Schema — framework.json

Every framework contains a `framework.json` at its root directory.

```json
{
  "id": "FMWK-003",
  "name": "memory",
  "version": "1.0.0",
  "description": "Learning artifacts, consolidation patterns, methylation-weighted Attention configuration",

  "scope": {
    "responsibility": "Single sentence: what this framework does",
    "boundary": "What this framework does NOT do"
  },

  "governance_rules": [
    {
      "rule_id": "GOV-001",
      "description": "All consolidation must be dispatched through work orders",
      "enforcement": "gate"
    }
  ],

  "interfaces": {
    "exposes": [
      {
        "interface_id": "IF-001",
        "name": "attention-query",
        "protocol_pack": "PC-003",
        "description": "Query interface for retrieving methylation-weighted context"
      }
    ],
    "consumes": [
      {
        "interface_id": "IF-001",
        "from_framework": "FMWK-002",
        "description": "Write Path event submission"
      }
    ]
  },

  "dependencies": [
    {
      "framework_id": "FMWK-002",
      "reason": "Requires KERNEL primitives for Ledger access and HO1 execution"
    }
  ],

  "spec_packs": ["SPEC-001-learning", "SPEC-002-attention"]
}
```

> **OPEN QUESTION:** What is the concrete structure of a governance rule? Is it declarative (checked by gates) or executable (code that runs during validation)? See FWK-0-OPEN-QUESTIONS.md.

### 3.2 Filesystem — Where Frameworks Live

```
/governed/
  FMWK-NNN-<name>/
    framework.json          ← framework metadata
    SPEC-NNN-<name>/        ← spec pack directories
      ...
```

- Every framework gets exactly one directory under `/governed/`.
- The directory name encodes the framework ID and human-readable name.
- `framework.json` sits at the framework directory root.
- Spec pack directories are immediate children of the framework directory.

### 3.3 Gate — Framework Validation

When a package is submitted for install, the framework gate checks:

| Check | Question | Pass Condition |
|-------|----------|----------------|
| Schema validity | Does framework.json conform to the FWK-0 schema? | All required fields present, correct types. |
| Scope declaration | Is the responsibility a single, bounded capability? | Non-empty scope.responsibility and scope.boundary. |
| Dependency resolution | Do all declared dependencies exist in the governed filesystem? | Every framework_id in dependencies is installed. |
| Interface consumption | Does every consumed interface have a provider? | Every entry in interfaces.consumes maps to an installed framework's interfaces.exposes. |
| ID uniqueness | Is this framework ID unused (new install) or matches existing (upgrade)? | No ID collision with a different framework. |
| No conflict | Does this framework's scope overlap with an existing framework? | No two frameworks declare the same responsibility. |

All checks are deterministic. No LLM involvement. Binary pass/fail.

---

## 4. Spec Pack Layer

A spec pack describes what needs to be built to deliver part of a framework's capability. It is "the architecture a builder reads to know what to assemble."

### 4.1 Schema — specpack.json

Every spec pack contains a `specpack.json` at its root directory.

```json
{
  "id": "SPEC-001",
  "name": "learning",
  "parent_framework": "FMWK-003",
  "description": "Learning artifact storage, retrieval, and consolidation",

  "packs": [
    {
      "pack_id": "PC-001",
      "name": "consolidation",
      "type": "prompt_pack",
      "description": "Prompt contracts for memory consolidation work orders"
    },
    {
      "pack_id": "PC-002",
      "name": "artifact-store",
      "type": "module_pack",
      "description": "Code for learning artifact CRUD operations"
    },
    {
      "pack_id": "PC-003",
      "name": "attention-protocol",
      "type": "protocol_definition",
      "description": "Interface contract for Attention queries"
    },
    {
      "pack_id": "PC-004",
      "name": "learning-quality",
      "type": "quality_measure",
      "description": "Validation schemas and acceptance criteria for learning artifacts"
    }
  ],

  "builder_instructions": "Assemble consolidation prompts first. Wire artifact-store to Write Path. Expose attention-protocol as the query interface. Validate all artifacts against learning-quality schemas."
}
```

### 4.2 Filesystem — Where Spec Packs Live

```
/governed/
  FMWK-NNN-<name>/
    framework.json
    SPEC-NNN-<name>/
      specpack.json           ← spec pack metadata
      PC-NNN-<name>/          ← pack directories
        ...
```

- Every spec pack gets exactly one directory under its parent framework.
- The directory name encodes the spec pack ID and human-readable name.
- `specpack.json` sits at the spec pack directory root.
- Pack directories are immediate children of the spec pack directory.

### 4.3 Gate — Spec Pack Validation

| Check | Question | Pass Condition |
|-------|----------|----------------|
| Schema validity | Does specpack.json conform to the FWK-0 schema? | All required fields present, correct types. |
| Parent reference | Does parent_framework reference a valid, installed framework? | Framework exists in governed filesystem. |
| Pack declaration | Are all child packs declared in the packs array? | Every pack directory has a corresponding entry. No undeclared packs. |
| Pack type validity | Are all pack types recognized? | Each type is one of: prompt_pack, module_pack, quality_measure, protocol_definition, or a type registered by a framework extension. |
| Completeness | Does this spec pack + its packs constitute a buildable unit? | At least one pack declared. |

---

## 5. Pack Layer

A pack is a collection of related files that serve a single purpose within a spec pack. Packs are typed — the type determines what the pack contains and what type-specific gate checks apply.

### 5.1 Base Schema — pack.json

Every pack contains a `pack.json` at its root directory.

```json
{
  "id": "PC-001",
  "name": "consolidation",
  "parent_spec_pack": "SPEC-001",
  "parent_framework": "FMWK-003",
  "type": "prompt_pack",

  "files": [
    {
      "filename": "consolidate-session.json",
      "sha256": "a1b2c3d4...",
      "description": "Prompt contract for session consolidation"
    },
    {
      "filename": "consolidate-entity.json",
      "sha256": "e5f6a7b8...",
      "description": "Prompt contract for entity-level consolidation"
    }
  ]
}
```

### 5.2 Pack Types and Type-Specific Requirements

Each pack type has additional requirements beyond the base schema:

**prompt_pack** — Contains prompt contract files (JSON). Each file must conform to the Prompt Contract schema (defined by KERNEL). Gate checks: every file parses as valid JSON, every file contains required prompt contract fields (contract_id, boundary, input_schema, output_schema, prompt_template, validation_rules).

**module_pack** — Contains code files. Gate checks: all declared files exist, hashes match. No additional structural requirements imposed by FWK-0 (code quality is the framework's governance responsibility, not FWK-0's).

**quality_measure** — Contains validation schemas and acceptance criteria (JSON). Gate checks: every file parses as valid JSON, schemas are well-formed.

**protocol_definition** — Contains interface contracts that other frameworks can consume. Gate checks: every file declares an interface_id that matches the parent framework's interfaces.exposes entries.

> **OPEN QUESTION:** Should pack types be structurally different schemas (different required fields per type) or a base schema with a type flag and type-specific validation in gates? See FWK-0-OPEN-QUESTIONS.md.

### 5.3 Filesystem — Where Packs Live

```
/governed/
  FMWK-NNN-<name>/
    framework.json
    SPEC-NNN-<name>/
      specpack.json
      PC-NNN-<name>/
        pack.json               ← pack metadata
        consolidate-session.json ← pack files
        consolidate-entity.json
        ...
```

- Every pack gets exactly one directory under its parent spec pack.
- The directory name encodes the pack ID and human-readable name.
- `pack.json` sits at the pack directory root.
- All pack files are immediate children of the pack directory (no subdirectories within a pack).

> **OPEN QUESTION:** Should packs allow subdirectories for complex module packs (e.g., Python packages with __init__.py)? Or must all files be flat within the pack directory? See FWK-0-OPEN-QUESTIONS.md.

### 5.4 Gate — Pack Validation

| Check | Question | Pass Condition |
|-------|----------|----------------|
| Schema validity | Does pack.json conform to the FWK-0 schema? | All required fields present, correct types. |
| Parent references | Do parent_spec_pack and parent_framework reference valid entities? | Both exist in governed filesystem. |
| File manifest | Does every declared file exist in the pack directory? | All files present. No extra undeclared files. |
| Hash integrity | Does every file's SHA256 match the declared hash? | All hashes match. |
| Single ownership | Is every file in this pack NOT claimed by any other pack? | No ownership conflicts across the entire governed filesystem. |
| Type-specific checks | Does the pack pass checks for its declared type? | See type-specific requirements above. |

---

## 6. File Layer

Files are the leaf nodes of the hierarchy. They are the actual artifacts — prompt templates, code modules, validation schemas, interface definitions. Files don't have their own metadata file; their metadata lives in the parent pack's `pack.json`.

### 6.1 Schema

Files are described by entries in their parent pack's `pack.json` files array:

```json
{
  "filename": "consolidate-session.json",
  "sha256": "a1b2c3d4e5f6...",
  "description": "Prompt contract for session consolidation"
}
```

### 6.2 Filesystem — Where Files Live

```
/governed/
  FMWK-NNN-<name>/
    SPEC-NNN-<name>/
      PC-NNN-<name>/
        <filename>              ← the actual file
```

A file's full path encodes its entire provenance chain:
```
/governed/FMWK-003-memory/SPEC-001-learning/PC-001-consolidation/consolidate-session.json
           ↑ framework      ↑ spec pack      ↑ pack              ↑ file
```

You can read the hierarchy from the path. No metadata lookup required for basic provenance.

### 6.3 Gate — File Validation

| Check | Question | Pass Condition |
|-------|----------|----------------|
| Existence | Does the file exist at the expected path? | File present on disk. |
| Hash match | Does the file's computed SHA256 match its declared hash in pack.json? | Hashes match. |
| Single ownership | Is this file claimed by exactly one pack across the entire governed filesystem? | Exactly one pack declares this file. |
| Correct location | Is the file in the directory matching its parent pack's filesystem path? | Path matches hierarchy. |

---

## 7. Package — The Delivery Unit

A package is an atomic delivery container. It carries one or more frameworks through the gate system into the governed filesystem. The package provides atomicity (all frameworks install or none do). Each framework within the package provides single responsibility and governance.

**Package ≠ Framework.** A framework is the logical unit — single-responsibility capability with governance rules and explicit interfaces. A package is the delivery unit — an envelope that ensures atomic installation. A package may contain one framework (common case) or multiple frameworks that must be installed together (e.g., KERNEL contains multiple primitive frameworks that depend on each other).

### 7.1 Schema — manifest.json

The package manifest is the top-level descriptor. It lives at the package root (in staging, before install).

```json
{
  "package_id": "PKG-kernel-1.0.0",
  "version": "1.0.0",
  "created": "2026-02-25T00:00:00Z",
  "description": "KERNEL — nine primitive frameworks + Write Path + Package Lifecycle tools",

  "frameworks": [
    {
      "framework_id": "FMWK-001",
      "framework_name": "ledger",
      "framework_json_sha256": "abc123...",
      "spec_packs": [
        {
          "id": "SPEC-001",
          "specpack_json_sha256": "def456...",
          "packs": [
            {
              "id": "PC-001",
              "pack_json_sha256": "ghi789...",
              "files": [
                { "path": "event-schema.json", "sha256": "a1b2c3d4..." }
              ]
            }
          ]
        }
      ]
    },
    {
      "framework_id": "FMWK-002",
      "framework_name": "write-path",
      "framework_json_sha256": "jkl012...",
      "spec_packs": [ "..." ]
    }
  ],

  "external_dependencies": [
    {
      "framework_id": "FMWK-000",
      "minimum_version": "1.0.0"
    }
  ],

  "total_files": 42,
  "total_sha256": "xyz999..."
}
```

The manifest lists all contained frameworks. Each framework's contents mirror the logical hierarchy. `total_sha256` is a hash of the entire contents block. External dependencies reference frameworks that must already be installed (not contained in this package). Internal dependencies between frameworks within the same package resolve at install time.

**Single-framework packages** are the common case and look the same — the `frameworks` array has one entry.

### 7.2 The Full Gate Sequence

When a package is submitted to the install lifecycle, gates run in this order:

```
1. Package self-consistency
   └── manifest.json parseable? All declared files present? All hashes match?
   └── total_sha256 verifies?
   └── Internal dependencies between frameworks within the package resolvable?
   └── FAIL → reject, log gate_failed event

2. For EACH framework in the package:
   a. Framework gate (Section 3.3)
      └── FAIL → reject entire package, log gate_failed event
   b. Spec pack gates (Section 4.3) — one per spec pack
      └── FAIL → reject entire package, log gate_failed event
   c. Pack gates (Section 5.4) — one per pack
      └── FAIL → reject entire package, log gate_failed event
   d. File gates (Section 6.3) — one per file
      └── FAIL → reject entire package, log gate_failed event

3. System gate (post-install verification)
   └── Entire governed filesystem consistent?
   └── All interface contracts satisfied across all installed frameworks?
   └── No ownership conflicts?
   └── FAIL → rollback all frameworks in package, log system_verify_failed event
```

Any failure at any step → entire package rejected. All frameworks in the package are rejected together. Atomic. No partial installs. A multi-framework package never results in some frameworks installed and others not.

### 7.3 Ledger Event Catalog — Install Lifecycle

Every install lifecycle action writes events to the Ledger. These events are what make cold-storage validation possible.

| Event Type | When | Fields |
|------------|------|--------|
| `package_install_started` | Package submitted to install lifecycle | package_id, framework_ids[], version, timestamp |
| `gate_passed` | A gate check succeeds | package_id, framework_id, gate_name, layer, entity_id, timestamp |
| `gate_failed` | A gate check fails | package_id, framework_id, gate_name, layer, entity_id, reason, timestamp |
| `framework_installed` | One framework within package placed on filesystem | package_id, framework_id, file_count, timestamp |
| `ownership_recorded` | Ownership entries created for framework's files | package_id, framework_id, file_count, timestamp |
| `package_install_complete` | All frameworks installed, system verified | package_id, framework_ids[], version, timestamp |
| `package_install_rolled_back` | System gate failed, all frameworks reverted | package_id, reason, timestamp |
| `package_uninstall_started` | Removal initiated | package_id, framework_ids[], timestamp |
| `package_uninstall_complete` | All frameworks removed, ownership cleared, system verified | package_id, framework_ids[], timestamp |

> **OPEN QUESTION:** Uninstall process — does removal run gates in reverse? Does it check for dependent frameworks before allowing removal? See FWK-0-OPEN-QUESTIONS.md.

### 7.4 Dependency Resolution

Packages declare two kinds of dependencies:

**External dependencies** — frameworks that must already be installed in the governed filesystem. Checked before gate validation begins. If not met, the package is rejected immediately.

**Internal dependencies** — dependencies between frameworks within the same package. These resolve during installation (framework A within the package depends on framework B within the same package). The install lifecycle processes frameworks in dependency order within the package.

The install lifecycle checks:

1. Every external dependency framework is installed and meets the minimum version requirement.
2. Every internal dependency is resolvable within the package.
3. Every consumed interface (from framework.json interfaces.consumes) has a provider — either among installed frameworks or within the same package.

If any dependency is not met, the package is rejected before gate checks run.

---

## 8. Interface & Composition Model

Individual frameworks are microservice-scoped. The system works because frameworks declare interfaces and consume each other's interfaces. This section defines how frameworks compose into a running system.

### 8.1 Protocol Definition Packs

A protocol definition pack (type: `protocol_definition`) declares an interface that a framework exposes. It contains one or more interface contract files that specify:

- Interface ID
- Input contract (what callers provide)
- Output contract (what the interface returns)
- Behavioral guarantees (synchronous/async, idempotency, error handling)

Other frameworks consume these interfaces by declaring them in `framework.json`'s `interfaces.consumes` section. The gate system validates that every consumed interface has a corresponding protocol definition pack in an installed framework.

### 8.2 The Composition Registry

The composition registry is not a separate service or database. It is a **derived view of the governed filesystem** — the kernel reads the installed frameworks' `framework.json` files at startup and builds an in-memory map of:

- What frameworks are installed
- What interfaces each framework exposes
- What interfaces each framework consumes
- Whether all interface contracts are satisfied

This is what the operator sees when they ask DoPeJarMo about system state. It's also what the system gate checks during post-install verification.

### 8.3 Boot Phases

The boot sequence is not a flat list of frameworks. It is phases, where each phase has a property and may contain multiple frameworks.

```
Phase 0: GENESIS package (hand-verified)
  Property: bootstrap — no gates, human-verified
  Contains: FWK-0 framework + filesystem initialization + Ledger initialization
  Result: governed filesystem exists, Ledger exists, FWK-0 is installed

Phase 1: KERNEL package (hand-verified)
  Property: bootstrap — validated against FWK-0 gates, but hand-verified
  Contains: multiple frameworks implementing the nine primitives + Write Path + Package Lifecycle tools
  Delivered as: single package, multiple frameworks, atomic install
  Result: install lifecycle operational, CLI tools available, core operational invariant holds

Phase 2: Layer 1 — DoPeJarMo OS packages (gate-governed)
  Property: governed — full gate validation
  Packages (one or more, packaging decision TBD):
    - DoPeJarMo Agent Interface (first governed install, via CLI)
    - Storage Management
    - Meta-Learning Agent
    - Routing
  Result: DoPeJarMo fully operational, operator can interact

Phase 3: Layer 2 — DoPeJar Product packages (gate-governed)
  Property: governed — full gate validation, installed through DoPeJarMo
  Packages (one or more, packaging decision TBD):
    - Memory
    - Intent
    - Conversation
  Result: DoPeJar alive, users can interact

Phase N: Additional agents and capabilities (gate-governed)
  Property: governed — any agent, not just DoPeJar
  Any builder (human, agent, or DoPeJar herself) can author new frameworks,
  package them, and submit through the install lifecycle.
  DoPeJarMo is a multi-tenant cognitive OS — not a single-product runtime.
```

> **RESOLVED:** KERNEL decomposes into 6 frameworks: FMWK-001 (ledger), FMWK-002 (write-path), FMWK-003 (orchestration), FMWK-004 (execution), FMWK-005 (graph), FMWK-006 (package-lifecycle). See Section 3.0 for the decomposition standard and rationale.

### 8.4 Framework-to-Framework Communication

Frameworks do not call each other directly. All inter-framework communication flows through the primitives:

- **Data exchange:** through the Ledger (Write Path) and Graph (HO3). A framework writes events; another framework reads the resulting Graph state.
- **Execution requests:** through Work Orders. A framework asks HO2 to plan work; HO2 dispatches to HO1; HO1 executes under prompt contracts that may belong to a different framework.
- **Interface contracts:** protocol definition packs declare what a framework offers. Consuming frameworks reference these at install time for gate validation, but at runtime the interaction flows through primitives.

No framework has a direct function call to another framework. Reading published artifacts (protocol definitions, schemas) from the governed filesystem is permitted — that's reading published specifications, not calling functions. Runtime data exchange flows through primitives only.

---

## 9. Hierarchy Extensibility

The initial hierarchy is Framework → Spec Pack → Pack → File. This is not permanently rigid. FWK-0 defines the initial hierarchy AND the mechanism for evolving it.

### 9.1 Extension Mechanism

Structural changes to the hierarchy (adding a new layer type, modifying validation at a layer, changing the filesystem convention) are themselves governed through the framework system. A hierarchy extension is proposed as a framework, validated through gates, and installed. The existing hierarchy validates the extension. Once installed, the extension modifies how future frameworks are validated.

This is the constitutional amendment model: the constitution defines the process for amending itself. The governance quality stays consistent because the extension mechanism is itself governed.

### 9.2 Grandfather and Modernization Clauses

When the hierarchy evolves, existing frameworks may not conform to the new structure. FWK-0 supports:

- **Grandfather clauses** — frameworks installed under a previous hierarchy version remain valid under the rules that existed when they were installed. Their provenance chain is verified against the hierarchy version recorded in their Ledger entry.
- **Modernization clauses** — governance policies (installed as frameworks) that define migration paths for bringing older frameworks into compliance with the current hierarchy. Modernization is governed — it's a package update, not a filesystem edit.

The intent is that the governance quality stays consistent or improves over time. The hierarchy can evolve without breaking existing provenance chains.

> **OPEN QUESTION:** What is the concrete mechanism for a hierarchy extension? Does it modify FWK-0's schemas directly (dangerous — changes the foundation), or does it add supplementary schemas that extend FWK-0 (safer — additive only)? See FWK-0-OPEN-QUESTIONS.md.

---

## 10. The Build Process (Dark Factory)

Frameworks are built by builder agents in an autonomous pipeline. The build process is a first-class concern of FWK-0, not an afterthought.

### 10.1 The Build Loop

```
1. Agent receives: spec pack + FWK-0 reference
2. Agent scaffolds framework in isolated build environment
3. Agent writes packs (prompts, modules, quality measures, protocols)
4. Agent seals hashes, assembles package
5. Agent validates package against gates (dry run)
6. Agent runs quality measures against mock providers
   - Smoke: does it install? Do gates pass?
   - Integration: do prompt contracts execute correctly?
   - E2E: does a full turn work with this framework active?
7. Tests fail → agent diagnoses, fixes, returns to step 3
8. Tests pass → agent submits package to real governed system
9. Real gates validate → operator reviews → install or reject
```

Steps 2-8 happen with no human involvement. The agent iterates until quality measures pass. The package that arrives at the governed system's gates has already been tested.

### 10.2 Build Environment

Building happens OUTSIDE the governed system entirely. The build environment is isolated — separate container, potentially separate machine. Zero shared state with the governed system. The only interface between them is the package submission.

The build environment provides:

- **Staging directory** — ungoverned workbench where the builder works
- **FWK-0 reference** — read-only copy of FWK-0 schemas and conventions
- **Inspect capability** — read-only view of installed frameworks on the governed filesystem (for pattern-matching and dependency checking)
- **Mock providers** — mock Ollama, mock Ledger, mock Graph. Enough to exercise prompt contracts and validate behavior without running the real cognitive stack
- **KERNEL CLI tools:**
  - `scaffold FMWK-NNN-<name>` — generate directory structure and metadata stubs
  - `seal <pack-path>` — compute and write file hashes into pack.json
  - `validate <path>` — run gate checks against a layer or full package (dry run)
  - `package <framework-path>` — assemble manifest.json, compute total_sha256

### 10.3 Quality Measures as Test Suites

Quality measure packs (type: `quality_measure`) are not just validation schemas checked at install time. They are structured test definitions that builder agents execute during the build loop.

A quality measure contains:

- **Criterion ID** — unique identifier for this quality check
- **Description** — what this criterion validates
- **Evaluation method** — structural check, prompt-based evaluation, or both
- **Acceptance threshold** — what constitutes passing
- **Reference standard** — the standards framework this criterion implements (if any)

### 10.4 Standards as Frameworks

Standards (e.g., ISO/IEC/IEEE 29148:2018 for requirements engineering) can be installed as governance-only frameworks. A standards framework contains:

- Quality measure packs encoding the standard's requirements as checkable criteria
- Protocol definition packs declaring what interfaces a compliant framework must expose
- No module packs — standards produce no runtime behavior

When a builder agent assembles a framework that declares a dependency on a standards framework, the quality measures from the standard are included in the build loop's test suite. Standards become structural, not aspirational.

### 10.5 Self-Improvement Loop

DoPeJar (or any agent running on DoPeJarMo) can identify gaps in her own capabilities, author a spec for a new framework or improvement, and submit it to the build pipeline. The dark factory processes it. The operator reviews the result.

```
DoPeJar identifies gap → spec authored → builder agent assembles →
dark factory tests → package submitted → gates validate →
operator reviews → approved → DoPeJar gains new capability
```

The system grows itself through governed installation, not self-modification. Every improvement has a framework. Every framework has provenance. Every change is a Ledger entry. The operator sees exactly what changed and can roll it back.

### 10.6 External Agent Integration

External agents (Claude, Codex, or any future LLM agent) can use DoPeJarMo as a memory and governance extension. The integration model is simple: if the external agent decides something is important, it sends it to DoPeJar. DoPeJar processes it through her normal Write Path — structures it into a learning artifact, submits to Ledger, folds into Graph.

The external agent doesn't need to understand DoPeJarMo's internal architecture. It needs to know how to say "remember this." The protocol definition for external agent integration defines the submission interface.

> **OPEN QUESTION:** What is the minimal integration protocol for external agents? Event submission API? Structured format? Authentication? See FWK-0-OPEN-QUESTIONS.md.

---

## 11. FWK-0 as Its Own First Instance

FWK-0 is FMWK-000. It must conform to everything defined above.

### FWK-0's Directory Layout

```
/governed/
  FMWK-000-framework/
    framework.json
    SPEC-001-hierarchy/
      specpack.json
      PC-001-schemas/
        pack.json
        framework-schema.json       ← JSON Schema for framework.json
        specpack-schema.json        ← JSON Schema for specpack.json
        pack-schema.json            ← JSON Schema for pack.json
        manifest-schema.json        ← JSON Schema for manifest.json
      PC-002-gate-definitions/
        pack.json
        package-gate.json           ← gate check specifications
        framework-gate.json
        specpack-gate.json
        pack-gate.json
        file-gate.json
        system-gate.json
      PC-003-filesystem-convention/
        pack.json
        layout.json                 ← canonical path conventions
        naming-rules.json           ← ID format rules
      PC-004-install-events/
        pack.json
        event-catalog.json          ← Ledger event type definitions
      PC-005-composition/
        pack.json
        boot-phases.json            ← phase definitions
        interface-protocol.json     ← protocol definition pack schema
```

### Self-Referential Validation

FWK-0 passes its own gates:

- `framework.json` validates against `framework-schema.json` (PC-001)
- `specpack.json` validates against `specpack-schema.json` (PC-001)
- Every `pack.json` validates against `pack-schema.json` (PC-001)
- The directory layout matches `layout.json` (PC-003)
- All IDs follow `naming-rules.json` (PC-003)
- All file hashes are correct
- Single ownership holds for every file
- FWK-0's own package manifest (used during GENESIS bootstrap) passes the package gate

If any of these checks fail, FWK-0 is incomplete. The self-referential test is the acceptance criterion for FWK-0 itself.

---

## Appendix: Complete Governed Filesystem Layout

```
/governed/                                      ← governed filesystem root (Docker volume)
│
├── FMWK-000-framework/                         ← FWK-0 itself
│   ├── framework.json
│   └── SPEC-001-hierarchy/
│       ├── specpack.json
│       ├── PC-001-schemas/
│       │   ├── pack.json
│       │   └── (schema files)
│       ├── PC-002-gate-definitions/
│       │   ├── pack.json
│       │   └── (gate spec files)
│       ├── PC-003-filesystem-convention/
│       │   ├── pack.json
│       │   └── (convention files)
│       ├── PC-004-install-events/
│       │   ├── pack.json
│       │   └── (event catalog files)
│       └── PC-005-composition/
│           ├── pack.json
│           └── (composition spec files)
│
├── FMWK-001-<kernel-framework-1>/              ← KERNEL frameworks (one per primitive/capability)
│   ├── framework.json
│   └── SPEC-NNN-<name>/
│       └── ...
│
├── FMWK-002-<kernel-framework-2>/
│   └── ...
│
├── ...                                          ← additional KERNEL frameworks
│
├── FMWK-0NN-agent-interface/                   ← Layer 1: DoPeJarMo OS frameworks
├── FMWK-0NN-storage-management/
├── FMWK-0NN-meta-learning-agent/
├── FMWK-0NN-routing/
│
├── FMWK-0NN-memory/                            ← Layer 2: DoPeJar product frameworks
├── FMWK-0NN-intent/
└── FMWK-0NN-conversation/

/staging/                                        ← staging directory (separate Docker volume)
│
└── (builder workbench — ungoverned, no structure enforced)

/snapshots/                                      ← snapshot directory (separate Docker volume)
│
└── (Graph state snapshots — format defined by KERNEL)
```

The governed filesystem is a flat list of framework directories. No nesting of frameworks within frameworks. The hierarchy is WITHIN each framework (framework → spec packs → packs → files), not BETWEEN frameworks.

---

## Appendix B: Design Session Insights (2026-02-26)

These insights emerged during design sessions and capture intent, philosophy, and constraints that must inform all downstream decisions. They are appended, not integrated, to preserve the draft's structure while ensuring nothing is lost.

### B.1 — The Economic Argument (Core Motivation)

DoPeJar is pristine memory. Good memory reduces compute. If the system reconstructs the perfect context every turn — exactly what's relevant, nothing that isn't — then smaller, cheaper models produce results as good as or better than larger, expensive models guessing from decaying context windows.

Storage costs are dropping. Compute costs are rising. A system that trades storage for compute is swimming with the economic current. This is not theoretical — the industry trend toward memory management over raw reasoning advancement validates this architecture.

Inspiration: Sapiens HRM (Hierarchical Reasoning Models). DoPeJarMo does not implement HRM directly. It builds the memory infrastructure that makes hierarchical reasoning possible with standard LLMs. The hierarchy lives in the data (frameworks, methylation scoring, intent namespaces, consolidation tiers), not in the model architecture. The LLM just needs to be good enough to structure at write time and execute at read time. HO1 doesn't need to be brilliant. It needs to be reliable under prompt contracts with perfect context.

The aperture system (NORTH_STAR) is the direct parallel: HRM's adaptive depth iterates through neural computation (expensive). DoPeJar's adaptive depth is determined by accumulator state (counter reads) and inspection (one constrained LLM call). The recurrent part — signal accumulation across turns and sessions — is counter arithmetic, not LLM calls. Energy efficiency comes from the memory, not the reasoning.

### B.2 — Package ≠ Framework (Structural Decision)

Package is the atomic delivery container. Framework is the logical governance unit. A package may contain one framework (common case) or multiple frameworks that must be installed together (e.g., KERNEL contains multiple primitive frameworks that depend on each other).

This distinction matters because:
- GENESIS, KERNEL, and DoPeJarMo Agent Interface are boot PHASES containing multiple frameworks each, not single frameworks.
- A framework is microservice-scoped: single responsibility, explicit interfaces. A package is a deployment envelope.
- The gate sequence runs per-framework within a package. The entire package is rejected on any single framework failure.

### B.3 — Hierarchy Extensibility (Constitutional Amendment Model)

The initial hierarchy (Framework → Spec Pack → Pack → File) is not permanently rigid. FWK-0 defines the initial hierarchy AND the mechanism for evolving it. Extensions are additive — separate frameworks that layer new capabilities on top of FWK-0 without modifying FWK-0 itself.

Grandfather clauses: frameworks installed under a previous hierarchy version remain valid under the rules that existed when they were installed. Modernization clauses: governance policies that define migration paths for bringing older frameworks into compliance.

### B.4 — Context Reconstruction Is the Feature

Previous builds treated "no persistent context across LLM calls" as a limitation. This is wrong. The complete prompt is reconstructed with accuracy every single turn. That IS the feature. Every turn gets exactly the right context — scored, ranked, provenance-tracked — rather than a decaying window of recent chat history.

This is what makes DoPeJar "can't forget, can't drift" actually true. The system doesn't remember by carrying state forward. It remembers by reconstructing the perfect context from pristine memory every time.

### B.5 — Standards as Frameworks

Standards (e.g., ISO/IEC/IEEE 29148:2018) can be installed as governance-only frameworks. A standards framework contains quality measure packs encoding the standard's requirements as checkable criteria, protocol definition packs declaring what interfaces a compliant framework must expose, and no module packs. Standards produce no runtime behavior — they produce governance.

When a builder agent assembles a framework that declares a dependency on a standards framework, the quality measures from the standard are included in the build loop's test suite. Standards become structural, not aspirational.

### B.6 — Multi-Tenant OS

DoPeJarMo is a multi-tenant cognitive OS — not a single-product runtime. Any agent can be built on DoPeJarMo, not just DoPeJar. External agents (Claude, Codex, or any future LLM agent) can use DoPeJarMo as a memory and governance extension. The integration model is simple: if the external agent decides something is important, it sends it to DoPeJar. DoPeJar processes it through her normal Write Path.

### B.7 — The Dark Factory Is First-Class

The build process is not an afterthought. Builder agents (and eventually DoPeJar herself) assemble frameworks autonomously in an isolated build environment with mock providers. The build loop (scaffold → build → test → fix → package → submit) runs with no human involvement. The package that arrives at the governed system's gates has already been tested. The dark factory is what makes DoPeJarMo self-improving.

### B.8 — The Drift Warning (Reinforced)

Every previous build failed because builder agents over-indexed on governance and lost the product. The governance is plumbing. Nobody builds a house because they love plumbing. They build it because they need water to work reliably. If you are reading FWK-0 and thinking "governance system" — stop. Read NORTH_STAR's Drift Warning. This is a memory system that happens to need governance.

### B.9 — Pragmatic Decisions for 48-Hour Sprint

Seven must-resolve questions were analyzed and given concrete v1 answers (captured in FWK-0-PRAGMATIC-RESOLUTIONS.md). Key decisions:
- ID assignment: builder proposes, gates validate uniqueness at install, reserved ranges prevent collisions
- Governance rules: declarative JSON with three enforcement types (gate-check, architectural-boundary, ownership-check)
- Versioning: replace in place, rollback from Ledger replay
- KERNEL decomposition: 6 frameworks (ledger, write-path, orchestration, execution, graph, package-lifecycle). CLI merged into package-lifecycle per decomposition standard (Section 3.0).
- Paths: ID+name (FMWK-NNN-name), rename = new framework
- Hierarchy extension: additive only, FWK-0 is immutable after GENESIS
- Multi-framework dependency: topological sort, cycle detection

Seven new gaps were also surfaced: GENESIS bootstrap sequence, builder context window budget, mock provider architecture, KERNEL activation sequence, WebSocket ownership (KERNEL infrastructure, not framework), prompt contract testing strategy, and capability discovery/registration.
