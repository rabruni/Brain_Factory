# DoPeJarMo — Institutional Context

> Read this before doing anything. This is the shared context for all agents working on this repository.
> This file is also available as `AGENTS.md` (Codex) and `GEMINI.md` (Gemini CLI) via symlinks.

## What This Is

**DoPeJar** is a personal AI companion that remembers you — can't forget, can't drift.
**DoPeJarMo** is the governed operating system that hosts DoPeJar. An interactive agent session shell.
**Brain Factory** is the architecture repository. Design authority, build process, and specification templates.

## The Drift Warning

This is the third rebuild. Previous attempts failed because agents over-indexed on governance and lost the product. The governance is plumbing — it makes memory trustworthy. DoPeJar is the product. If you're thinking "governance system," stop and read `architecture/NORTH_STAR.md`.

## Authority Chain

When you encounter ambiguity, resolve it by walking UP:

| Document | Authority | What it decides |
|----------|-----------|----------------|
| `architecture/NORTH_STAR.md` | Design authority | WHY — resolves all ambiguity |
| `architecture/BUILDER_SPEC.md` | Build authority | WHAT — primitive definitions |
| `architecture/OPERATIONAL_SPEC.md` | Operational authority | HOW — runtime behavior |
| `architecture/FWK-0-DRAFT.md` | Framework authority | Framework schemas, gates, filesystem |
| `architecture/BUILD-PLAN.md` | Current plan | What gets built, in what order |
| `architecture/AGENT_CONSTRAINTS.md` | Agent governance | How agents stay on track |

Never resolve ambiguity by inventing an answer.

## Agent Entry Point

Read `AGENT_BOOTSTRAP.md` first. It provides orientation before you encounter detail.

## The Nine Primitives

Assemble from these. Do NOT create new primitives.

1. Ledger — append-only hash-chained event store
2. Signal Accumulator — methylation values (0.0-1.0) on Graph nodes
3. HO1 (Execution) — all LLM calls, stateless, sole Write Path entry
4. HO2 (Orchestration) — mechanical only, NO LLM, reads Graph, plans work
5. HO3 (Graph) — in-memory materialized view, pure storage
6. Work Order — atom of dispatched work
7. Prompt Contract — governed LLM interaction template
8. Package Lifecycle — staging > gates > filesystem
9. Framework Hierarchy — Framework > Spec Pack > Pack > File

## Core Invariant

LLM structures at write time. HO2 retrieves mechanically at read time. Never reverse. If you're adding execution to HO3 — STOP. You are drifting.

## KERNEL Frameworks (6)

| ID | Name | Owns |
|----|------|------|
| FMWK-001 | ledger | Append-only store, event schemas, hash chain |
| FMWK-002 | write-path | Synchronous mutation, fold logic, snapshot |
| FMWK-003 | orchestration | Work order planning, dispatch, context computation |
| FMWK-004 | execution | LLM calls, prompt contract enforcement |
| FMWK-005 | graph | In-memory directed graph, query interface |
| FMWK-006 | package-lifecycle | Gates, install/uninstall, CLI tools, composition registry |

## Template Compression Standard

Templates exist in two formats:
- `Templates/` — full human-readable versions. Humans author and review these.
- `Templates/compressed/` — 73% fewer tokens, same information. Agents read ONLY these.

Rules: `Templates/compressed/COMPRESSION_STANDARD.md`. When a full template changes, re-compress using those rules and verify by generating output from the compressed version.

## Build Process (Sawmill)

This repo uses the Sawmill L3 dark factory process. Five turns:

- **Turn A** (Spec Agent): Design docs → D1-D6. Gate: D6 zero OPEN items.
- **Turn B** (Plan Agent): D1-D6 → D7, D8, D10. Gate: Constitution Check passes.
- **Turn C** (Holdout Agent): D2+D4 ONLY → D9. Parallel with Turn B.
- **Turn D** (Builder): D10 + Handoff → Code + Tests. Gate: 13Q + all tests pass.
- **Turn E** (Evaluator): D9 + PR code ONLY → Evaluation. Gate: 2/3 per scenario, 90% overall.

Agent definitions: `.claude/agents/`
Templates: `Templates/`
Holdouts: `.holdouts/` (NEVER shown to builder agents)

## Isolation Rules

- Builder NEVER sees `.holdouts/` or D9.
- Evaluator NEVER sees handoff, specs, or builder reasoning.
- Holdout Agent sees D2+D4 ONLY.
- Cleared context means a fresh session — no memory of prior turns.

## Sawmill Working Directory

```
sawmill/<FMWK-ID>/          <- Spec packs, handoffs, results per framework
  TASK.md                   <- Orchestrator assigns work here
  D1-D6                     <- Spec agent output (Turn A)
  D7, D8, D10               <- Plan agent output (Turn B)
  BUILDER_HANDOFF.md         <- Builder's task (Turn B output)
  RESULTS.md                 <- Builder's results (Turn D output)
  EVALUATION_REPORT.md       <- Evaluator's verdict (Turn E output)
  EVALUATION_ERRORS.md       <- One-line failures for retry

.holdouts/<FMWK-ID>/        <- Holdout scenarios (Turn C output, NEVER shown to builder)

sawmill/COLD_START.md        <- Full agent reading chain (what to read, in what order)
sawmill/run.sh               <- Orchestrator script (invokes agents, enforces gates)
```

## Repository Structure

```
AGENT_BOOTSTRAP.md          <- Read first
CLAUDE.md                   <- This file
architecture/               <- Authority documents
Templates/                  <- D1-D10 + process standards (full, for humans)
Templates/compressed/       <- Same templates, 73% fewer tokens (for agents)
sawmill/                    <- Build pipeline working directory
.claude/agents/             <- Specialist agent definitions
.holdouts/                  <- Holdout scenarios (isolated)
docs/                       <- TechDocs rendering (mirrors architecture/ and Templates/)
catalog-info.yaml           <- Backstage entity
mkdocs.yml                  <- TechDocs config
```

## Naming Conventions

- Frameworks: `FMWK-NNN-name` (e.g., `FMWK-001-ledger`)
- Spec Packs: `SPEC-NNN-name`
- Packs: `PC-NNN-name`
- Name regex: `^[a-z][a-z0-9-]{1,63}$`
- Filenames: UPPERCASE_UNDERSCORE for templates and authorities

## Commit Messages

Use imperative, scoped messages: `docs(templates): clarify D6 gate criteria`

## What You Must Not Do

- Create new primitives (assemble from the nine)
- Add execution logic to HO3 (pure storage only)
- Write directly to the Ledger (use Write Path)
- Skip the 13Q gate before building
- Read holdouts if you're a builder
- Guess when you should ask
- Optimize governance for its own sake
