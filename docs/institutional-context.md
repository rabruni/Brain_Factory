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

## Repository Layout

Two locations. Do not confuse them.

**Brain_Factory** (`/Users/raymondbruni/Cowork/Brain_Factory/`) — this repo. Architecture, sawmill pipeline, templates, AND code staging. Builders create code in `staging/<FMWK-ID>/` here.

**dopejar** (`/Users/raymondbruni/dopejar/`) — the runtime. Docker services, kernel, platform_sdk (46 modules). The builder imports from the SDK here but does not write to it during the sawmill.

| What | Path |
|------|------|
| Builder staging | `staging/<FMWK-ID>/` (relative to this repo root) |
| Platform SDK | `/Users/raymondbruni/dopejar/platform_sdk/` |
| Docker services | `/Users/raymondbruni/dopejar/docker-compose.yml` |
| Backstage catalog (runtime) | `/Users/raymondbruni/dopejar/catalog-info.yaml` |
| Backstage catalog (this repo) | `catalog-info.yaml` |

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

## Templates

Two formats: `Templates/` (full, for humans) and `Templates/compressed/` (for agents). When a full template changes, re-compress per `Templates/compressed/COMPRESSION_STANDARD.md`.

## Build Process (Sawmill)

This repo uses the Sawmill L3 dark factory process. Five turns:

- **Turn A** (Spec Agent): Design docs → D1-D6. Checkpoint: D6 zero OPEN items.
- **Turn B** (Plan Agent): D1-D6 → D7, D8, D10. Checkpoint: Constitution Check passes.
- **Turn C** (Holdout Agent): D2+D4 ONLY → D9. Parallel with Turn B.
- **Turn D** (Builder + Reviewer): D10 + Handoff → 13Q → reviewer PASS → Code + Tests.
- **Turn E** (Evaluator): D9 + PR code ONLY → Evaluation. Verdict: 2/3 per scenario, 90% overall.

### Operational Execution Model

The authoritative runtime contract for Sawmill execution is defined in
`sawmill/EXECUTION_CONTRACT.md`.

In short:

```
Human -> Claude orchestrator -> registry-resolved workers -> Sawmill artifacts and verdicts
```

- **Human** starts the run and resolves true authority conflicts or explicit escalations.
- Default execution is unattended and exception-driven. `./sawmill/run.sh --interactive` is the opt-in path for live checkpoints. Agents must not simulate approvals with piped stdin, `yes ''`, or other synthetic input.
- **Claude** is the orchestrator. Claude reads state, invokes `sawmill/run.sh`, supervises retries, and routes blockers.
- **Workers** are resolved from `sawmill/ROLE_REGISTRY.yaml`. Critical review/evaluation roles may use a max-capability policy.
- Claude-native subagents are optional tooling, not the authoritative Sawmill execution model.

The canonical role inventory and backend-routing metadata live in
`sawmill/ROLE_REGISTRY.yaml`. `sawmill/run.sh` consumes that registry at
runtime. Role behavior and isolation still live in `.claude/agents/*.md`.

### Operational Roles

| Role | Responsibilities |
|------|------------------|
| Orchestrator | Supervises the pipeline, starts worker turns, waits for gates, and routes retries/blockers |
| Worker | Executes role files for spec, planning, holdout, build, evaluation, and audit work under orchestration |

Agent role files: `.claude/agents/`

| Role | File | What it does |
|------|------|-------------|
| Orchestrator | `orchestrator.md` | HO2 supervisor. Reads state, decides next turn, dispatches workers, tracks gates/retries, reports verdict. |
| Spec Agent | `spec-agent.md` | Worker role for Turn A and Turn B outputs (D1-D10 + handoff). |
| Holdout Agent | `holdout-agent.md` | Worker role for Turn C holdout scenarios from D2+D4 only. |
| Builder | `builder.md` | Worker role for Turn D implementation after the 13Q review pass. |
| Reviewer | `reviewer.md` | Worker role for automated 13Q review and retry/escalate decisions before build. |
| Evaluator | `evaluator.md` | Worker role for Turn E holdout evaluation. |
| Auditor | `auditor.md` | Worker role for portal coherence audits and system checks. |
| Portal Steward | `portal-steward.md` | Worker role for portal maintenance in the runtime stage loop. |

To become any role, read its file: e.g., "you are the orchestrator" → read `.claude/agents/orchestrator.md`, follow its instructions.

The orchestrator dispatches worker roles through `sawmill/run.sh` or a direct worker CLI invocation using the target role file. `sawmill/ROLE_REGISTRY.yaml` is the canonical source for role files, default backends, allowed backends, and env override names. Do not assume Claude-native subagents are available; the authoritative contract is Claude supervision and Codex worker execution. For runtime ownership boundaries, use `sawmill/EXECUTION_CONTRACT.md`.

For the human-readable filesystem evidence checklist after a run, use `docs/sawmill/RUN_VERIFICATION.md`.

If a request requires the normal `sawmill/run.sh` path, direct worker invocation is not a substitute unless the human explicitly changes the request.

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
  TASK.md                   <- Orchestrator work-order / dispatch artifact
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
- Skip the automated 13Q review before building
- Auto-approve or synthesize human checkpoint input for `sawmill/run.sh` outside the supported `--interactive` mode
- Read holdouts if you're a builder
- Guess when you should ask
- Optimize governance for its own sake
