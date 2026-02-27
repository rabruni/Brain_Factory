---
title: "BUILD PLAN — GENESIS Through DoPeJar Alive"
status: PLAN — requires Ray approval before execution
version: "1.0"
created: "2026-02-26"
author: "Ray Bruni + Claude"
audience: "Ray, builder agents, operators"
timeline: "48 hours from approval"
depends_on:
  - NORTH_STAR.md
  - BUILDER_SPEC.md
  - OPERATIONAL_SPEC.md
  - FWK-0-DRAFT.md
  - FWK-0-PRAGMATIC-RESOLUTIONS.md
---

# BUILD PLAN — GENESIS Through DoPeJar Alive

## Executive Summary

This plan gets DoPeJarMo accepting operator sessions and DoPeJar responding to users within 48 hours of approval. It sequences every framework that needs to exist, identifies what can be parallelized, and flags the critical path items that will block everything if they slip.

The plan assumes:
- FWK-0 decisions from FWK-0-PRAGMATIC-RESOLUTIONS.md are approved (or adjusted)
- Docker topology is decided (4 services: kernel, immudb, ollama, zitadel)
- Authority docs (NORTH_STAR, BUILDER_SPEC, OPERATIONAL_SPEC) are stable
- Builder agents are Claude-class LLMs working from spec packs + FWK-0

---

## The Full Framework Inventory

Every framework that must exist for DoPeJar to be alive, in dependency order.

### Phase 0: GENESIS (hand-verified, human ceremony)

| ID | Name | What It Does |
|----|------|-------------|
| FMWK-000 | framework | FWK-0 itself. Defines what all frameworks are. Schemas, gates, filesystem conventions, install events, composition rules. |

**GENESIS is not a framework install.** It is a bootstrap ceremony that creates the governed filesystem, initializes the Ledger, and places FWK-0 on disk. Hand-verified. No gates run (gates don't exist yet). Root of trust is human review.

### Phase 1: KERNEL (hand-verified, single multi-framework package)

| ID | Name | Primitive(s) | Depends On | What It Does |
|----|------|-------------|-----------|-------------|
| FMWK-001 | ledger | Ledger | FMWK-000 | Event schema definitions, Ledger durability guarantees, immudb integration. |
| FMWK-002 | write-path | Write Path, Signal Accumulator | FMWK-001 | Synchronous mutation path. Append to Ledger, fold into Graph. Methylation value computation. |
| FMWK-003 | orchestration | HO2, Work Orders | FMWK-001, FMWK-002 | Mechanical planning, work order dispatch, LIVE ∩ REACHABLE computation, aperture determination. |
| FMWK-004 | execution | HO1, Prompt Contracts | FMWK-003, FMWK-002 | All LLM calls. Prompt contract enforcement. One mouth. Signal delta submission. |
| FMWK-005 | graph | HO3 (Graph) | FMWK-001, FMWK-002 | In-memory materialized view. Node/edge structure. Scoring/retrieval queries. Snapshot/replay. |
| FMWK-006 | package-lifecycle | Package Lifecycle, Framework Hierarchy | FMWK-001, FMWK-000 | Gate runner, install/uninstall, composition registry, scaffold/seal/validate/package CLI. |
| FMWK-007 | kernel-cli | CLI Tools | FMWK-000 | Offline validation. Connects directly to immudb. Rollback, list-frameworks, validate-filesystem. |

**KERNEL is delivered as ONE package containing 7 frameworks.** Installed via topological sort: 001 → 002 → {003, 005} → 004 → {006, 007}. Hand-verified because KERNEL creates the gate system itself.

**After KERNEL:** Core operational invariant holds. CLI tools available. Gates operational. No interactive agent yet — CLI only.

### Phase 2: Layer 1 — DoPeJarMo OS (gate-governed, via CLI)

| ID | Name | Depends On | What It Does |
|----|------|-----------|-------------|
| FMWK-010 | agent-interface | FMWK-003, FMWK-004, FMWK-006 | DoPeJarMo himself. Interactive agent session shell for operators. Conversational framework management, diagnostics, system state queries. First governed install. |
| FMWK-011 | routing | FMWK-003, FMWK-004 | LLM provider dispatch policy. Which models handle which work order types. Mechanical policy read by HO2. |
| FMWK-012 | storage-management | FMWK-001, FMWK-002, FMWK-005 | Ledger trimming using methylation values. Pressure-driven at write rate. Required because without it, Ledger fills disk → hard stop. |
| FMWK-013 | meta-learning-agent | FMWK-002, FMWK-003, FMWK-004, FMWK-005 | Decay, density normalization, session caps, Traveler Rule, bistable mode switching, consolidation, homeostasis monitoring. Cross-cutting governed agent. |

**Install order:** FMWK-010 first (via CLI — this is the first governed install). Then FMWK-011, FMWK-012, FMWK-013 through DoPeJarMo (operator installs interactively).

**After Layer 1:** DoPeJarMo fully operational. Operator can connect via WebSocket, interact conversationally, install/upgrade/rollback frameworks, view system state. No DoPeJar yet.

### Phase 3: Layer 2 — DoPeJar Product (gate-governed, through DoPeJarMo)

| ID | Name | Depends On | What It Does |
|----|------|-----------|-------------|
| FMWK-020 | memory | FMWK-002, FMWK-003, FMWK-004, FMWK-005, FMWK-013 | Learning artifacts, consolidation patterns, methylation-weighted Attention configuration. The "can't forget" promise. |
| FMWK-021 | intent | FMWK-003, FMWK-004, FMWK-005 | Intent lifecycle management. Proposal/authority boundary. Bridge mode scaffolding (with kill date). INTENT_DECLARED → SUPERSEDED/CLOSED/FORKED/ABANDONED. |
| FMWK-022 | conversation | FMWK-003, FMWK-004, FMWK-020, FMWK-021 | DoPeJar's personality (Donna + Pepper + JARVIS). Response generation. User-facing behavior. The product. |

**Install order:** FMWK-020 and FMWK-021 can install in parallel (no cross-dependency). FMWK-022 depends on both.

**After Layer 2:** DoPeJar alive. Users can connect via WebSocket, interact with DoPeJar. She remembers, understands what matters, gets things done.

---

## The Dependency Graph

```
FMWK-000 (framework/FWK-0)
  ↑
  ├── FMWK-001 (ledger)
  │     ↑
  │     ├── FMWK-002 (write-path)
  │     │     ↑
  │     │     ├── FMWK-003 (orchestration)
  │     │     │     ↑
  │     │     │     ├── FMWK-004 (execution)
  │     │     │     │     ↑
  │     │     │     │     ├── FMWK-010 (agent-interface)
  │     │     │     │     ├── FMWK-011 (routing)
  │     │     │     │     ├── FMWK-013 (meta-learning-agent)
  │     │     │     │     ├── FMWK-020 (memory)
  │     │     │     │     ├── FMWK-021 (intent)
  │     │     │     │     └── FMWK-022 (conversation)
  │     │     │     │
  │     │     │     ├── FMWK-010 (agent-interface)
  │     │     │     ├── FMWK-011 (routing)
  │     │     │     ├── FMWK-021 (intent)
  │     │     │     └── FMWK-022 (conversation)
  │     │     │
  │     │     ├── FMWK-005 (graph)
  │     │     │     ↑
  │     │     │     ├── FMWK-012 (storage-management)
  │     │     │     ├── FMWK-013 (meta-learning-agent)
  │     │     │     ├── FMWK-020 (memory)
  │     │     │     └── FMWK-021 (intent)
  │     │     │
  │     │     ├── FMWK-012 (storage-management)
  │     │     ├── FMWK-013 (meta-learning-agent)
  │     │     └── FMWK-020 (memory)
  │     │
  │     ├── FMWK-006 (package-lifecycle)
  │     └── FMWK-012 (storage-management)
  │
  ├── FMWK-006 (package-lifecycle)
  └── FMWK-007 (kernel-cli)
```

**Verified:** No cycles. Topological sort produces valid install order at every phase.

---

## 48-Hour Timeline

### Hour 0–4: FOUNDATIONS (Ray + Claude)

**Goal:** Everything a builder agent needs before it can start.

| Task | Owner | Deliverable | Blocks |
|------|-------|------------|--------|
| Approve/adjust 7 must-resolve decisions | Ray | Updated FWK-0-OPEN-QUESTIONS.md | Everything |
| Finalize FWK-0 JSON schemas | Claude | framework-schema.json, specpack-schema.json, pack-schema.json, manifest-schema.json | GENESIS |
| Write gate definition JSON files | Claude | framework-gate.json, specpack-gate.json, pack-gate.json, file-gate.json, package-gate.json, system-gate.json | Package Lifecycle |
| Write GENESIS bootstrap script | Claude | genesis.sh (shell script, deterministic, reviewable) | Phase 0 |
| Write KERNEL spec packs (all 7) | Claude | specpack.json for each KERNEL framework | Builder agents |
| Design mock provider containers | Claude | docker-compose-staging.yml with mock-ollama, mock-ledger, mock-graph | Dark factory |

**Critical path:** FWK-0 schemas must be complete before GENESIS can run. Spec packs must be written before builders can start.

### Hour 4–8: GENESIS + KERNEL SCAFFOLD (Ray + Claude)

**Goal:** Governed filesystem exists, FWK-0 on disk, KERNEL frameworks scaffolded.

| Task | Owner | Deliverable | Blocks |
|------|-------|------------|--------|
| Run GENESIS ceremony | Ray (with Claude assist) | /governed/FMWK-000-framework/ populated, Ledger initialized, bootstrap events recorded | Everything after |
| Validate FWK-0 self-referential test | Ray | FWK-0 passes its own gates | Builder confidence |
| Scaffold KERNEL frameworks (directories + stubs) | Claude | /staging/FMWK-001 through FMWK-007 with framework.json, specpack.json stubs | Builder agents |

### Hour 8–24: KERNEL BUILD (Parallel builder agents)

**Goal:** All 7 KERNEL frameworks authored, tested, packaged.

Builder agents work in parallel on independent frameworks. Dependencies between KERNEL frameworks are resolved at package assembly, not authoring.

| Task | Builder | Est. Complexity | Can Parallelize With |
|------|---------|----------------|---------------------|
| FMWK-001 ledger | Agent A | Medium — event schemas, durability specs | All others |
| FMWK-002 write-path | Agent B | High — fold logic, signal accumulation, synchronous contract | FMWK-001 (needs event schemas as reference) |
| FMWK-003 orchestration | Agent C | High — work order state machine, planning heuristics, scoring formula | FMWK-001, FMWK-002 (needs interfaces as reference) |
| FMWK-004 execution | Agent D | Medium — prompt contract enforcement, LLM routing, budget tracking | FMWK-003 (needs work order schema) |
| FMWK-005 graph | Agent E | Medium — node/edge schemas, query interface, snapshot format | FMWK-002 (needs fold logic interface) |
| FMWK-006 package-lifecycle | Agent F | High — gate runner, install logic, composition registry, CLI tools | FMWK-001 (needs Ledger event interface) |
| FMWK-007 kernel-cli | Agent G | Low — standalone validation tools, cold-storage walkthrough | Independent |

**Parallelization strategy:**
- Hour 8-12: Start FMWK-001, FMWK-007 (no internal dependencies)
- Hour 8-16: Start FMWK-002, FMWK-005, FMWK-006 (depend only on FMWK-001 interfaces, can use stubs)
- Hour 12-20: Start FMWK-003, FMWK-004 (depend on 001+002 interfaces)
- Hour 20-24: Assemble KERNEL package, run gate validation, fix failures

**Each builder agent receives:**
1. FWK-0 reference (relevant sections only, ~500-800 tokens)
2. Framework spec pack (specpack.json with builder instructions)
3. Interface stubs for dependencies (what the depended-on framework exposes)
4. Scaffold (generated directory structure and metadata stubs)

**Each builder agent delivers:**
1. Complete framework.json with governance rules, interfaces, dependencies
2. All spec packs with complete specpack.json
3. All packs with pack.json, files, computed hashes
4. Quality measures with test cases
5. Sealed package (hashes computed, manifest ready)

### Hour 24–28: KERNEL INSTALL + VERIFICATION (Ray + Claude)

**Goal:** KERNEL installed, core operational invariant holds, CLI tools working.

| Task | Owner | Deliverable | Blocks |
|------|-------|------------|--------|
| Assemble KERNEL package (manifest.json) | Claude | Single package containing 7 frameworks | Install |
| Hand-verify KERNEL package | Ray | Human review of critical schemas and interfaces | Install |
| Install KERNEL via GENESIS CLI | Ray | KERNEL frameworks in /governed/, Ledger events recorded | Layer 1 |
| Run cold-storage validation | Claude (CLI) | All framework chains validate against Ledger | Confidence |
| Start kernel process | Ray | Kernel accepting connections, Write Path operational, Graph built | Layer 1 |
| Smoke test: scaffold/seal/validate/package CLI | Claude | CLI tools return expected results | Builder confidence for Layer 1 |

### Hour 28–36: LAYER 1 BUILD (Parallel builder agents)

**Goal:** DoPeJarMo OS frameworks authored, tested, packaged.

| Task | Builder | Est. Complexity | Install Order |
|------|---------|----------------|--------------|
| FMWK-010 agent-interface | Agent H | High — conversational agent, WebSocket dispatch, framework diagnostics | FIRST (via CLI) |
| FMWK-011 routing | Agent I | Low — policy definition, provider mapping | After 010 (through DoPeJarMo) |
| FMWK-012 storage-management | Agent J | Medium — trimming logic, methylation-based selection, disk pressure | After 010 |
| FMWK-013 meta-learning-agent | Agent K | High — decay curves, normalization, Traveler Rule, consolidation, homeostasis | After 010 |

**Parallelization:** All 4 can be authored in parallel. Install must be sequential: 010 first, then 011-013 in any order.

**After FMWK-010 install:** Operator can interact with DoPeJarMo via WebSocket. This is the first interactive milestone.

### Hour 36–44: LAYER 2 BUILD (Parallel builder agents)

**Goal:** DoPeJar product frameworks authored, tested, packaged.

| Task | Builder | Est. Complexity | Install Order |
|------|---------|----------------|--------------|
| FMWK-020 memory | Agent L | High — learning artifacts, consolidation, Attention config, epigenetic layer | Parallel with 021 |
| FMWK-021 intent | Agent M | Medium — lifecycle state machine, proposal/authority, bridge mode | Parallel with 020 |
| FMWK-022 conversation | Agent N | Medium — personality definition, response generation, user-facing prompts | After 020 + 021 |

### Hour 44–48: INTEGRATION + DOPEJAR ALIVE (Ray + Claude)

**Goal:** Full system operational. DoPeJar responding to users.

| Task | Owner | Deliverable | Blocks |
|------|-------|------------|--------|
| Install Layer 2 frameworks through DoPeJarMo | Ray | FMWK-020, 021, 022 installed, gates passed | DoPeJar |
| Validate full system composition | Claude (CLI) | All interfaces satisfied, no conflicts | DoPeJar |
| Connect as user, test DoPeJar interaction | Ray | DoPeJar responds, remembers, demonstrates personality | Milestone |
| Run Two Sarahs test scenario | Ray + Claude | Context reconstruction works, methylation scoring produces correct ranking | Validation |
| Cold-storage validation of full system | Claude (CLI) | Entire governed filesystem validates against Ledger | Confidence |

---

## Critical Path

The critical path is the longest chain of dependent tasks. If any task on this chain slips, the entire timeline slips.

```
FWK-0 schemas (H0-4)
  → GENESIS ceremony (H4-6)
    → KERNEL spec packs written (H4-8)
      → KERNEL builders start (H8)
        → FMWK-002 write-path complete (H8-20) ← HIGHEST RISK
          → KERNEL package assembled (H20-24)
            → KERNEL installed (H24-28)
              → FMWK-010 agent-interface built (H28-34)
                → DoPeJarMo operational (H34)
                  → FMWK-022 conversation built (H36-44)
                    → DoPeJar alive (H44-48)
```

**Highest risk item:** FMWK-002 (write-path). This framework implements the core architectural invariant (synchronous Ledger append + Graph fold). It touches the most critical pieces (Ledger integration, fold logic, signal accumulation). If the write-path spec pack is unclear or the builder gets stuck, everything downstream is blocked.

**Mitigation:** Write the write-path spec pack with extreme precision. Include concrete examples of fold operations. Provide interface stubs that the builder can code against. Review the builder's output before assembling KERNEL.

---

## What Can Be Deferred (NOT in 48-hour scope)

These are important but not required for "DoPeJar alive":

| Item | Why Deferred | When Needed |
|------|-------------|-------------|
| Zitadel integration | Auth can use API keys for local dev. OIDC adds complexity. | Before multi-user deployment |
| External LLM routing (beyond Ollama) | Ollama local is sufficient for demo | Before production use |
| Full E2E test suite for dark factory | Smoke tests sufficient for initial build | Before autonomous builder agents |
| Storage Management trimming logic | Disk won't fill in 48 hours | Before sustained operation |
| Homeostasis monitoring in MLA | System won't have enough signal for homeostasis to matter | Before sustained multi-session use |
| Bridge Mode kill date enforcement | Bridge mode is fine for initial testing | Before real intent mode is needed |
| Standards-as-frameworks (ISO compliance) | No standards to enforce yet | Before external agent integration |
| Snapshot optimization | Basic snapshot works; optimization is performance | Before scale testing |
| WebSocket TLS | Local-only, no public exposure | Before network exposure |

---

## Framework Spec Pack Authoring Priority

Before builders can start, spec packs must be written. Priority order based on critical path:

| Priority | Framework | Why This Order |
|----------|-----------|---------------|
| P0 | FMWK-002 write-path | Critical path bottleneck. Must be precise. |
| P0 | FMWK-001 ledger | Foundation for everything. Event schemas define the system. |
| P1 | FMWK-006 package-lifecycle | Gate runner must work for governed installs. |
| P1 | FMWK-003 orchestration | Work order state machine needed for all dispatch. |
| P2 | FMWK-004 execution | Prompt contract enforcement. Can stub against HO2. |
| P2 | FMWK-005 graph | Materialized view. Can stub against Write Path. |
| P3 | FMWK-007 kernel-cli | Independent. Lowest coupling. |
| P3 | FMWK-010 agent-interface | Can start after KERNEL spec packs done. |
| P4 | FMWK-011 routing | Simple policy. Low complexity. |
| P4 | FMWK-012 storage-management | Deferrable for 48 hours. |
| P4 | FMWK-013 meta-learning-agent | Complex but not on critical path for "alive." |
| P5 | FMWK-020 memory | Product framework. Needs KERNEL interfaces defined. |
| P5 | FMWK-021 intent | Product framework. Needs orchestration interface. |
| P5 | FMWK-022 conversation | Product framework. Last in chain. |

---

## Builder Agent Handoff Template

Each builder agent receives a standardized handoff:

```
## Builder Handoff: FMWK-{NNN}-{name}

### Your Mission
Build the {name} framework for DoPeJarMo.

### What You Receive
1. FWK-0 reference: [relevant sections only]
2. Your spec pack: {specpack.json content}
3. Interface stubs for your dependencies: {dependency interfaces}
4. Scaffold: {generated directory structure}

### What You Deliver
1. Complete framework.json
2. All spec packs (specpack.json)
3. All packs (pack.json + files)
4. Quality measures with test cases
5. Sealed package (all hashes computed)

### Constraints
- Read FWK-0 sections {X, Y, Z} before starting
- Your framework ID is FMWK-{NNN}
- Your dependencies are: {list}
- Your interfaces must expose: {list}
- Do NOT create primitives. Assemble FROM primitives.
- Do NOT modify the governed filesystem. Work in staging.
- Test against mock providers before submitting.

### Acceptance Criteria
- framework.json validates against FWK-0 schema
- All packs have correct hashes
- All gate checks pass (dry run)
- Quality measure test cases all pass
- No undeclared files, no missing files
```

---

## Risk Register (48-Hour Sprint)

| Risk | Severity | Likelihood | Mitigation | Owner |
|------|----------|-----------|-----------|-------|
| FWK-0 schemas incomplete | Critical | Medium | Hand-verify before GENESIS | Ray + Claude |
| KERNEL circular dependency | Critical | Low | Verify DAG before builders start | Claude |
| Mock providers missing/broken | High | Medium | Build mocks before builders start | Claude |
| Write-path spec pack unclear | High | Medium | Write with extreme precision, review | Claude + Ray |
| Builder context exhaustion | Medium | Medium | Phase complex frameworks, stratify FWK-0 | Claude |
| Gate definitions missing | Medium | Low | Write all gate JSONs in Hour 0-4 | Claude |
| ID collision between builders | Low | Low | Reserved ranges, no parallel builds in same range | Ray |
| Ollama connection issues | Low | Medium | Test Docker networking before build | Claude |
| immudb initialization fails | Medium | Low | Test GENESIS script on clean Docker | Claude |

---

## Success Criteria

### Minimum Viable (must hit)
- [ ] GENESIS complete, FWK-0 on governed filesystem
- [ ] KERNEL installed, CLI tools operational
- [ ] FMWK-010 agent-interface installed, DoPeJarMo accepting operator sessions
- [ ] At least one Layer 2 framework installed (FMWK-020 memory)
- [ ] Cold-storage validation passes for entire system

### Full Target (aspiration for 48 hours)
- [ ] All Layer 1 frameworks installed
- [ ] All Layer 2 frameworks installed (FMWK-020, 021, 022)
- [ ] DoPeJar responding to user queries
- [ ] Two Sarahs test scenario passes
- [ ] Full system cold-storage validation passes

### Stretch (if time permits)
- [ ] Dark factory mock environment operational
- [ ] One framework built entirely by autonomous builder agent
- [ ] Zitadel authentication integrated
- [ ] DoPeJar demonstrates consolidation (MLA triggered)

---

## Open Decisions for Ray

Before execution begins, Ray needs to approve or adjust:

1. **7 must-resolve decisions** from FWK-0-PRAGMATIC-RESOLUTIONS.md — approve, modify, or reject each
2. **KERNEL decomposition** — 7 frameworks as proposed, or different split?
3. **Framework ID ranges** — reserved ranges as proposed (001-009, 010-019, 020-029)?
4. **48-hour timeline** — realistic? Which milestones are hard requirements vs nice-to-have?
5. **Deferral list** — anything on the "deferred" list that must be in scope?
6. **Builder agent strategy** — how many parallel agents? Which LLM? Handoff format?
7. **Zitadel** — include in 48 hours or defer to dev-mode API keys?
