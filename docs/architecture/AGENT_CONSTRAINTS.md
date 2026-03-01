# Agent Constraints — How Builder Agents Stay On Track

**Status**: AUTHORITY (binding on all builder agents)
**Date**: 2026-02-28
**Last synced**: 2026-03-01
**Author**: Ray Bruni + Claude
**Depends on**: NORTH_STAR.md, BUILDER_SPEC.md, SAWMILL_ANALYSIS.md, FWK-0-DRAFT.md

---

## Why This Document Exists

Every previous DoPeJarMo build failed because agents drifted. Not because they were broken — because they were unconstrained. An agent without boundaries will optimize for what it finds interesting (governance architecture) instead of what matters (DoPeJar). This document defines the constraint surfaces that keep agents productive.

---

## The Three Constraint Layers

Agents are constrained at three levels. Each layer catches different failure modes.

### Layer 1: Document Authority Chain (what agents read)

Agents don't get to read everything and decide what matters. The authority chain is explicit and non-negotiable:

```
NORTH_STAR.md        → WHY (design authority, resolves all ambiguity)
BUILDER_SPEC.md      → WHAT (build authority, primitive definitions)
OPERATIONAL_SPEC.md  → HOW (operational authority, runtime behavior)
FWK-0-DRAFT.md       → FRAMEWORK RULES (what frameworks look like)
BUILD-PLAN.md        → CURRENT PLAN (what gets built, in what order)
```

**Constraint**: An agent that encounters ambiguity resolves it by walking UP the chain: FWK-0 → OPERATIONAL_SPEC → BUILDER_SPEC → NORTH_STAR. An agent NEVER resolves ambiguity by inventing an answer.

**Constraint**: An agent reads AGENT_BOOTSTRAP.md FIRST. This is the single entry point. It provides orientation before the agent encounters any detail that might cause drift.

### Layer 2: Sawmill Pipeline (what agents do)

The Sawmill is not a suggestion — it is the constraint system. Each turn has:
- **Role**: Which agent type performs this work
- **Inputs**: ONLY these documents (nothing else)
- **Outputs**: ONLY these deliverables (nothing else)
- **Gates**: Must pass before next turn starts
- **Human approval**: Required at specified points

**Constraint**: Agents cannot skip turns. Agents cannot combine turns. Agents cannot read documents not listed in their turn's inputs.

**Constraint**: The 13Q gate in Turn D (Build) forces the builder to prove comprehension BEFORE writing code. The human reviews 13Q answers and explicitly greenlights. No greenlight = no code.

**Constraint**: The holdout isolation in Turn C/E means the builder NEVER sees acceptance tests, and the evaluator NEVER sees the builder's reasoning. This prevents teaching-to-the-test and confirmation bias.

### Layer 3: Constitutional Rules (what agents must not violate)

Every framework has a D1 Constitution with ALWAYS/ASK/NEVER boundaries. These are non-negotiable:

- **ALWAYS**: Agent does this without asking (e.g., "always append to Ledger through Write Path")
- **ASK FIRST**: Agent must get human approval (e.g., "ask before adding a new dependency")
- **NEVER**: Agent refuses even if instructed (e.g., "never write directly to HO3")

**Constraint**: The Framework Decomposition Standard (FWK-0-DRAFT Section 3.0) is constitutional. Every framework's D1 must include the three decomposition test articles. Agents cannot create frameworks that fail these tests.

---

## How Backstage/TechDocs Enforces Discovery

TechDocs (MkDocs) serves the architecture docs through Backstage. This is the discovery layer — how agents and humans find the right document at the right time.

### What's in TechDocs

| Section | Contents | Who reads it |
|---------|----------|-------------|
| Architecture | NORTH_STAR, BUILDER_SPEC, OPERATIONAL_SPEC, FWK-0, BUILD-PLAN | All agents, humans |
| Templates | D1-D10, BUILDER_HANDOFF_STANDARD, BUILDER_PROMPT_CONTRACT | Sawmill agents |
| Open Questions | FWK-0-OPEN-QUESTIONS, FWK-0-PRAGMATIC-RESOLUTIONS | Spec agents, humans |

### How TechDocs Constrains

1. **Single source of truth**: Documents live in `architecture/` and `Templates/`. TechDocs renders them. Agents read from the repo, not from memory. If the doc doesn't say it, it doesn't exist.

2. **Catalog entity**: `catalog-info.yaml` registers Brain Factory as a Backstage component. This means the project is discoverable, its docs are browsable, and its lifecycle is tracked.

3. **Sync hook**: `hooks/sync_docs.py` ensures `docs/architecture/` mirrors `architecture/` and `docs/sawmill-templates/` mirrors `Templates/`. One source, one rendering.

---

## Agent-Specific Constraints

### Spec Agent (Turn A)

- Reads: design documents (architecture authority chain)
- Produces: D1-D6
- MUST extract, not invent. If a design doc doesn't answer a question, the agent flags it in D6 — never guesses.
- MUST apply controlled redundancy checks (D2 boundaries vs D1 NEVER, D4 errors vs D6 gaps)
- CANNOT proceed past D6 gate if any item is OPEN

### Plan Agent (Turn B)

- Reads: D1-D6 from Turn A
- Produces: D7, D8, D10
- MUST trace every D8 task to a D2 scenario and D4 contract
- MUST verify D10 tooling rules match D1 tooling constraints
- MUST run Constitution Check against every D1 article
- CANNOT invent scope beyond what D2 defines

### Holdout Agent (Turn C)

- Reads: D2 + D4 ONLY. Nothing else.
- Produces: D9
- MUST NOT see D7 (architecture), D8 (tasks), or D10 (builder context)
- Tests behavior from caller's perspective, not implementation details
- Minimum 3 scenarios covering happy path, error path, and cross-boundary integration

### Builder Agent (Turn D)

- Reads: D10 FIRST, then Builder Handoff (generated from D7+D8)
- Produces: code, tests, Results file
- MUST answer 13Q gate BEFORE writing any code
- MUST wait for human greenlight after 13Q
- MUST follow DTT (Design-Test-Then-implement) per behavior
- MUST NOT read D9 holdouts
- Gets maximum 3 attempts. After 3 failures, handoff returns to spec author.

### Evaluator Agent (Turn E)

- Reads: D9 holdouts + PR branch code. NOTHING ELSE.
- Produces: evaluation report
- MUST NOT see builder reasoning, handoff, or results file
- Runs each scenario 3 times. 2/3 pass = scenario passes.
- 90% overall pass rate required.
- On failure: one-line description of WHAT failed, not HOW to fix it.

---

## Drift Detection Signals

These are the warning signs that an agent is drifting:

| Signal | What it means | Corrective action |
|--------|--------------|-------------------|
| Agent discusses governance as "the product" | Drift toward governance optimization | Re-read NORTH_STAR Drift Warning |
| Agent invents scope not in D2 | Scope creep | Constrain to D2 scenarios |
| Agent skips 13Q gate | Bypassing comprehension check | Stop build, enforce gate |
| Agent reads documents outside its turn's inputs | Context contamination | Restart agent with clean context |
| Agent adds "nice to have" features | Gold-plating | Constrain to handoff spec |
| Agent creates new primitives | Architectural violation | Reread BUILDER_SPEC: "assemble from primitives" |
| Agent writes directly to HO3 | Core invariant violation | Stop immediately. Fix architecture. |
| Builder sees holdouts | Evaluation integrity compromised | Restart Turn D with new builder |

---

## The Override Protocol

Agents are constrained, not rigid. When an agent encounters a situation the constraints don't cover:

1. **Stop.** Do not proceed with a guess.
2. **Flag.** Write the issue into D6 (if spec turn) or the Results file (if build turn).
3. **Ask.** Surface the question to the human with options, not open-ended requests.
4. **Wait.** Do not continue until the human decides.

The human can override any constraint. But the agent cannot override constraints on its own. The asymmetry is intentional — humans own decisions, agents own execution.

---

## How This Connects to FWK-0

When frameworks are installed through the governed lifecycle, the constraint model extends:

- **Gate enforcement**: Governance rules in `framework.json` include mechanical checks (KERNEL) and cognitive checks (Layer 1+). See FWK-0-DRAFT Section 3.1 and Q2.1 resolution.
- **Resource budgets**: Framework envelope constrains what a builder's framework can consume. Pack allocations must fit within the envelope. Gate validates at install time.
- **Decomposition standard**: The three tests (splitting, merging, ownership) in FWK-0-DRAFT Section 3.0 prevent agents from creating frameworks with wrong boundaries.
- **Additive extensions only**: Q9.1 resolution — agents cannot modify FWK-0 or cross-extend other frameworks. Only add via spec packs + version bump.

The constraint system is fractal: documents constrain agents → gates constrain frameworks → the Ledger constrains history. Each layer makes the next one trustworthy.
