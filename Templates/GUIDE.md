# Dark Factory Template Guide

**Purpose:** How to use the D1-D10 template system to spec any component for agent-driven builds.
**Audience:** Humans writing specs today; agent orchestrators executing them tomorrow.
**Templates Directory:** This directory contains all templates and this guide.

---

## What This System Does

The D-template system turns design documents into fully-specified, agent-executable build plans. It does this through a pipeline of 10 documents (D1-D10) that progressively extract, analyze, decompose, and verify everything needed to build a software component — without the builder agent needing to make design decisions.

The key principle: **specs are source of truth, code is derived.** If the spec is complete, the build is deterministic. If the build fails, the failure traces back to a spec gap.

---

## The Pipeline

```
PHASE 1: EXTRACTION               PHASE 2: ANALYSIS        PHASE 3: BUILD PLANNING         PHASE 4: VERIFICATION
─────────────────────              ──────────────────        ───────────────────────          ─────────────────────
D1: Constitution (rules)           D6: Gap Analysis          D7: Plan (architecture)          D9: Holdout Scenarios
D2: Specification (scenarios)       ▲   (gate check)         D8: Tasks (decomposition)        (acceptance tests,
D3: Data Model (entities)           │                                                          hidden from builders)
D4: Contracts (boundaries)          │
D5: Research (decisions)    ────────┘                        D10: Agent Context
                            (gaps found during               (builder handbook)
                             D1-D5 feed into D6)
```

### Phase 1: Extraction (D1-D5)

Fill these by pulling information from your existing design documents. The work here is consolidation, not invention. When you can't find an answer in the design docs, that's a D6 gap — don't guess.

| Template | What to fill | Time estimate |
|----------|-------------|---------------|
| **D1: Constitution** | Immutable rules, boundary definitions, tooling constraints | 30 min |
| **D2: Specification** | GIVEN/WHEN/THEN scenarios from caller's perspective | 45-60 min |
| **D3: Data Model** | Entity schemas, field tables, relationship map | 30-45 min |
| **D4: Contracts** | Inbound/outbound/side-effect/error contracts | 30-45 min |
| **D5: Research** | Design decisions that required investigation, prior art | 30 min |

### Phase 2: Analysis (D6)

D6 is accumulated during Phase 1 — every time you can't find an answer in the design docs, you log it here. After Phase 1 is complete, resolve all gaps. **D6 is the gate: zero OPEN items before Phase 3 can begin.**

| Template | What to fill | Time estimate |
|----------|-------------|---------------|
| **D6: Gap Analysis** | Boundary analysis (9 categories), clarification log, summary | 30-60 min |

### Phase 3: Build Planning (D7, D8, D10)

Design the architecture, decompose into tasks, and write the builder's handbook. These only make sense after D6 is PASS.

| Template | What to fill | Time estimate |
|----------|-------------|---------------|
| **D7: Plan** | Architecture, components, file structure, testing strategy | 45-60 min |
| **D8: Tasks** | Phased tasks with dependencies, acceptance criteria | 30-45 min |
| **D10: Agent Context** | Commands, conventions, tool rules, submission protocol | 20-30 min |

### Phase 4: Verification (D9)

Written by the spec author (you), stored separately from the build. The builder agent never sees these. They're run after the build is delivered to verify the component actually works.

| Template | What to fill | Time estimate |
|----------|-------------|---------------|
| **D9: Holdout Scenarios** | 3-5 acceptance scenarios with executable verification | 30-45 min |

**Total time estimate: 4-6 hours per component** (with design docs already written).

---

## How to Start a New Component Spec

### Step 1: Create the directory

```
mkdir [component-name]/
cp Templates/D1_CONSTITUTION.md [component-name]/
cp Templates/D2_SPECIFICATION.md [component-name]/
cp Templates/D3_DATA_MODEL.md [component-name]/
cp Templates/D4_CONTRACTS.md [component-name]/
cp Templates/D5_RESEARCH.md [component-name]/
cp Templates/D6_GAP_ANALYSIS.md [component-name]/
cp Templates/D7_PLAN.md [component-name]/
cp Templates/D8_TASKS.md [component-name]/
cp Templates/D9_HOLDOUT_SCENARIOS.md [component-name]/
cp Templates/D10_AGENT_CONTEXT.md [component-name]/
```

### Step 2: Fill D1-D5 in order

Work through D1, then D2, then D3, D4, D5. As you go, log any gaps or unanswered questions into D6. Don't skip ahead — each document builds on the previous ones.

### Step 3: Resolve D6

Review all gaps and clarifications. Resolve them (get answers from stakeholders, make decisions, document assumptions). The gate is zero OPEN items.

### Step 4: Fill D7-D8-D10

Now that the spec is solid, design the architecture (D7), break it into tasks (D8), and write the builder handbook (D10).

### Step 5: Write D9 holdout scenarios

Write acceptance tests from the outside. These test what the component does, not how it does it. Store them separately from the builder's handoff.

### Step 6: Generate handoffs

Use D8 tasks to generate individual handoff documents following BUILDER_HANDOFF_STANDARD.md. Each handoff gets a prompt generated from BUILDER_PROMPT_CONTRACT.md. Dispatch to builder agents.

---

## Cross-Reference Map

Each document references others. Here's how they connect:

```
D1 (Constitution)
 ├── Referenced by: D7 (constitution check), D9 (rule verification), D10 (key patterns)
 └── Defines: Immutable rules that all other docs must comply with

D2 (Specification)
 ├── Referenced by: D3 (entity sources), D4 (contract scenarios), D8 (task scenarios), D9 (holdout coverage)
 └── Defines: What the component does (caller's perspective)

D3 (Data Model)
 ├── Referenced by: D4 (contract shapes), D7 (entity transforms), D8 (acceptance criteria)
 └── Defines: Entity schemas and relationships

D4 (Contracts)
 ├── Referenced by: D8 (contracts per task), D9 (contract verification)
 └── Defines: Inbound/outbound/side-effect/error boundaries

D5 (Research)
 ├── Referenced by: D7 (architecture justification), D10 (key patterns)
 └── Defines: Design decisions and their rationale

D6 (Gap Analysis)
 ├── Referenced by: D7 (gap resolution), D8 (blocked tasks)
 └── Defines: The gate — zero OPEN items before building

D7 (Plan)
 ├── Referenced by: D8 (task decomposition), D10 (architecture overview)
 └── Defines: Architecture, components, file structure

D8 (Tasks)
 ├── Referenced by: D9 (responsibility tracing), D10 (active components)
 └── Defines: Phased tasks with dependencies

D9 (Holdout Scenarios)
 ├── Referenced by: (reviewers only — never visible to builders)
 └── Defines: Independent acceptance verification

D10 (Agent Context)
 ├── Referenced by: (builders — first thing they read)
 └── Defines: Commands, conventions, tool rules
```

---

## Supporting Standards

These three documents define the build process itself — how handoffs are structured, how agents are prompted, and the machine-readable workflow:

| Document | What it defines | When to customize |
|----------|----------------|-------------------|
| **BUILDER_HANDOFF_STANDARD.md** | 10-section format for handoff documents, results file template, reviewer checklist | Customize critical constraints (Section 2) for your project |
| **BUILDER_PROMPT_CONTRACT.md** | Agent prompt template, 13-question gate, adversarial simulation sets | Customize mandatory rules, add project-specific variables |
| **AGENT_BUILD_PROCESS.yaml** | Machine-readable version of the above (for agent orchestrators) | Update paths, add custom prompt routes |
| **PRODUCT_SPEC_FRAMEWORK.md** | Conceptual overview of the 7 core deliverables and how they expand to D1-D10 | Reference doc — rarely needs customization |

---

## Human vs. Agent Workflow

### Today (Human + Agent collaboration)

1. **Human** fills D1-D6 (extraction + gap analysis)
2. **Human** fills D7-D8 (architecture + task decomposition)
3. **Human** writes D9 (holdout scenarios)
4. **Human** fills D10 (builder context)
5. **Human** generates handoffs from D8 tasks
6. **Agent** receives handoff, answers 13 questions, builds via DTT
7. **Human** reviews results, runs holdout scenarios

### Future (Agent orchestration)

1. **Orchestrator agent** reads design docs, fills D1-D6 (with human approval at D6 gate)
2. **Orchestrator agent** fills D7-D10 (with human approval of architecture)
3. **Orchestrator agent** generates handoffs and prompts automatically
4. **Builder agents** receive handoffs, answer 13Q gate, build via DTT
5. **Reviewer agent** validates results, runs holdout scenarios
6. **Human** reviews holdout results and makes accept/reject decision

### Design for the transition

The templates are structured so that both humans and agents can fill them. HTML comments (`<!-- -->`) provide guidance that humans read and agents can parse. Placeholder brackets (`[Component Name]`, `[YYYY-MM-DD]`) are machine-fillable. The AGENT_BUILD_PROCESS.yaml encodes the workflow for programmatic consumption.

---

## Decision Points (Human-in-the-Loop)

These are the places where a human currently makes judgment calls. As the system matures, some of these can be automated, but they're the last places to remove the human:

| Decision Point | Where | Why it needs human judgment |
|---------------|-------|----------------------------|
| D6 gate | Gap Analysis | Deciding whether assumptions are acceptable |
| D7 architecture | Plan | Choosing between valid architectural approaches |
| D8 task sizing | Tasks | Balancing parallelism vs. dependency complexity |
| D9 holdout design | Holdout Scenarios | Writing tests that catch what agents miss |
| 13Q gate review | Handoff dispatch | Verifying the agent understood the spec correctly |
| Holdout pass/fail | Post-build | Final accept/reject decision |

---

## Quick Reference: Template Metadata

Every D-template includes metadata at the top. Keep it consistent:

```
# D[N]: [Template Name] — [Component Name]

**Component:** [Component Name]
**Spec Version:** [X.Y.Z]
**Status:** [Draft | Review | Final]
```

Version all templates together. When D2 is updated, bump the version in D2 and in every document that references D2's version.
