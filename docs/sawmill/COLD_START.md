# Sawmill Cold Start — Agent Communication Path

**Status**: AUTHORITY (binding on all agents and orchestrators)
**Date**: 2026-02-28

---

## Purpose

This document defines the exact reading chain for every agent type. When an agent cold-starts (fresh session, no memory of prior turns), it reads files in this exact order. No state missed, no constraint missed.

The filesystem is the message bus. Agents communicate through files at known paths. No agent passes data directly to another.

---

## How Each Agent Loads Context (Entry Points Are Different)

Each CLI tool reads its own context file automatically on startup. They are NOT interchangeable:

| Agent CLI | Auto-reads on startup | Config to add fallbacks |
|-----------|----------------------|------------------------|
| **Claude Code** | `CLAUDE.md` (project root + parent dirs) | Built-in, no config needed |
| **Codex CLI** | `AGENTS.md` (project root + parent dirs) | `~/.codex/config.toml` → `project_doc_fallback_filenames = ["CLAUDE.md"]` |
| **Gemini CLI** | `GEMINI.md` (project root + parent dirs) | `~/.gemini/settings.json` → `"contextFileName": ["GEMINI.md", "AGENTS.md"]` |

### What this means for the Sawmill

The orchestrator cannot assume every agent reads `CLAUDE.md`. The institutional context must exist in the file each agent actually reads. Three options:

**Option A — Symlinks (recommended)**:
```bash
# In project root:
CLAUDE.md         ← the real file (source of truth)
AGENTS.md → CLAUDE.md   ← symlink for Codex
GEMINI.md → CLAUDE.md   ← symlink for Gemini
```
One source of truth, three entry points. All agents get identical institutional context.

**Option B — Agent config** (per-developer setup):
```toml
# ~/.codex/config.toml
project_doc_fallback_filenames = ["CLAUDE.md"]
```
```json
// ~/.gemini/settings.json
{ "contextFileName": ["GEMINI.md", "CLAUDE.md"] }
```
Requires each developer to configure their tools. Fragile.

**Option C — Prompt injection** (orchestrator sends context):
The orchestrator reads `CLAUDE.md` and injects its contents into the prompt for every agent. Works but duplicates context and burns tokens.

---

## Agent Invocation Reference

How the orchestrator invokes each agent programmatically:

### Claude Code
```bash
claude -p "<prompt>" \
  --allowedTools "Read,Edit,Write,Glob,Grep,Bash" \
  --append-system-prompt "$(cat .claude/agents/<role>.md)"
```
- Auto-reads: `CLAUDE.md` (always, built-in)
- Headless flag: `-p` (or `--print`)
- System prompt: `--append-system-prompt` (adds to default) or `--system-prompt` (replaces)
- Output: `--output-format json` for machine-readable
- Session resume: `--resume <session_id>` or `--continue`

### Codex CLI
```bash
codex exec --full-auto \
  "$(cat AGENTS.md)

$(cat .claude/agents/<role>.md)

<task prompt>"
```
- Auto-reads: `AGENTS.md` (or configured fallbacks)
- Headless flag: `codex exec` (non-interactive)
- Automation: `--full-auto` (no approval prompts)
- Output: `--json` for machine-readable
- Sandbox: runs in network-disabled sandbox by default
- No `--system-prompt` flag — all instructions go in the prompt itself
- Working directory: `--cd <path>` or `-C <path>`

### Gemini CLI
```bash
gemini -p "<prompt with role file and task>" \
  --yolo \
  --output-format json
```
- Auto-reads: `GEMINI.md` (or configured `contextFileName`)
- Headless flag: `-p` (or `--prompt`)
- Automation: `--yolo` or `-y` (auto-approve all actions)
- Output: `--output-format json` for machine-readable
- Model select: `-m gemini-2.5-pro`
- No `--system-prompt` flag — instructions go in the prompt or context file

---

## The Complete Communication Path

When an agent cold-starts, this is the full chain from "I exist" to "I know what to do":

### Layer 0: Automatic Context (agent reads without being told)

```
Claude  → reads CLAUDE.md automatically
Codex   → reads AGENTS.md automatically (or CLAUDE.md if configured/symlinked)
Gemini  → reads GEMINI.md automatically (or CLAUDE.md if configured/symlinked)
```

This gives the agent: project identity, drift warning, nine primitives, core invariant,
6 KERNEL frameworks, Sawmill overview, isolation rules, repo structure, naming conventions.

The agent now knows WHAT PROJECT it's in and WHAT THE RULES ARE.

### Layer 1: Role Assignment (orchestrator tells the agent its role)

The orchestrator sends the agent's role file content in the prompt:

```
Orchestrator passes → .claude/agents/<role>.md content
```

This gives the agent: its role (orchestrator/spec/holdout/builder/evaluator/auditor), what it can read,
what it CANNOT read, its process steps, its gate requirements,
and its Cold Start Reading Order (the exact files to read next).

The agent now knows WHO IT IS and WHAT IT'S ALLOWED TO DO.

### Layer 2: Task-Specific Context (agent reads per its role's reading order)

Each role has a different set of files to read. The role file's Cold Start section
lists them explicitly. The orchestrator's prompt also lists them as reinforcement.

**Spec Agent (Turn A)**:
```
Reads (in order):
  architecture/NORTH_STAR.md          ← WHY
  architecture/BUILDER_SPEC.md        ← WHAT
  architecture/OPERATIONAL_SPEC.md    ← HOW
  architecture/FWK-0-DRAFT.md        ← framework rules
  architecture/BUILD-PLAN.md          ← current plan
  sawmill/<FMWK>/TASK.md              ← which framework to spec
  catalog-info.yaml                    ← system relationships and build annotations
  sawmill/<FMWK>/SOURCE_MATERIAL.md   ← detailed spec material (if it exists)
  Templates/compressed/D1-D6          ← output format (compressed for agents)

Writes:
  sawmill/<FMWK>/D1-D6
```

**Spec Agent (Turn B)**:
```
Reads:
  sawmill/<FMWK>/D1-D6                ← own approved Turn A output
  Templates/compressed/D7, D8, D10    ← output format (compressed for agents)
  Templates/compressed/BUILDER_HANDOFF_STANDARD.md
  Templates/compressed/BUILDER_PROMPT_CONTRACT.md

Writes:
  sawmill/<FMWK>/D7, D8, D10, BUILDER_HANDOFF.md
```

**Holdout Agent (Turn C)** — STRICT ISOLATION:
```
Reads (ONLY these two):
  sawmill/<FMWK>/D2_SPECIFICATION.md
  sawmill/<FMWK>/D4_CONTRACTS.md
  Templates/compressed/D9_HOLDOUT_SCENARIOS.md

CANNOT read: D1, D3, D5, D6, D7, D8, D10, architecture/*, staging/*

Writes:
  .holdouts/<FMWK>/D9_HOLDOUT_SCENARIOS.md
```

**Builder Agent (Turn D)**:
```
Reads (in this exact order):
  AGENT_BOOTSTRAP.md                      ← orientation and invariants FIRST
  sawmill/<FMWK>/D10_AGENT_CONTEXT.md     ← framework orientation SECOND
  Templates/TDD_AND_DEBUGGING.md          ← HOW to code THIRD
  sawmill/<FMWK>/BUILDER_HANDOFF.md       ← task FOURTH
  Files from BUILDER_HANDOFF Section 7    ← referenced code

On retry, also reads:
  sawmill/<FMWK>/EVALUATION_ERRORS.md     ← what failed

CANNOT read: .holdouts/*, EVALUATION_REPORT.md

Writes:
  staging/<FMWK>/**
  sawmill/<FMWK>/RESULTS.md
  PR on branch build/<FMWK>

Note: Staging is in Brain_Factory, not dopejar. The builder imports from
`/Users/raymondbruni/dopejar/platform_sdk/` but writes code to `staging/` in this repo.
```

**Evaluator Agent (Turn E)** — STRICT ISOLATION:
```
Reads (ONLY these):
  .holdouts/<FMWK>/D9_HOLDOUT_SCENARIOS.md
  PR branch code (clean worktree)

CANNOT read: D1-D8, D10, BUILDER_HANDOFF, RESULTS.md, architecture/*

Writes:
  sawmill/<FMWK>/EVALUATION_REPORT.md
  sawmill/<FMWK>/EVALUATION_ERRORS.md
```

---

## The TASK.md Dispatch Artifact (Orchestrator → Spec Agent)

The orchestrator emits `TASK.md` in each framework's sawmill directory before invoking the spec agent. This file is a dispatch artifact, not spec work:

```text
WORK_ORDER
framework: <FMWK-NNN-name>
turn: A
target_role: spec-agent
action: generate D1-D6
summary: <one paragraph from BUILD-PLAN.md describing this framework>
owns: <exclusive ownership from the KERNEL frameworks table>
dependencies:
  - <framework dependencies>
constraints:
  - <framework-specific constraints from BUILD-PLAN.md or FWK-0-DRAFT.md>
expected_outputs:
  - sawmill/<FMWK-NNN-name>/D1_CONSTITUTION.md
  - sawmill/<FMWK-NNN-name>/D2_SPECIFICATION.md
  - sawmill/<FMWK-NNN-name>/D3_DATA_MODEL.md
  - sawmill/<FMWK-NNN-name>/D4_CONTRACTS.md
  - sawmill/<FMWK-NNN-name>/D5_RESEARCH.md
  - sawmill/<FMWK-NNN-name>/D6_GAP_ANALYSIS.md
gate: D6 zero OPEN items + human approval
retry: 0
```

---

## Handoff Diagram

```
                    ┌──────────────┐
                    │  TASK.md     │ ← orchestrator emits dispatch
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Spec Agent  │ Turn A
                    │  (D1-D6)     │
                    └──────┬───────┘
                           │ D1-D6 files in sawmill/<FMWK>/
                           │
              ┌────────────┤ GATE: Ray approves D1-D6
              │            │
     ┌────────▼─────┐  ┌───▼──────────┐
     │ Holdout Agent│  │  Spec Agent  │ Turn B
     │ Turn C (D9)  │  │  (D7-D8-D10) │
     │ reads D2+D4  │  │  reads D1-D6 │
     └────────┬─────┘  └───┬──────────┘
              │            │
              │            │ BUILDER_HANDOFF.md + D10
              │            │
              │     ┌──────▼───────┐
              │     │   Builder    │ Turn D
              │     │   (Code)     │
              │     │ 13Q → DTT   │
              │     └──────┬───────┘
              │            │ PR branch + RESULTS.md
              │            │
              │     ┌──────▼───────┐
              └────►│  Evaluator   │ Turn E
                    │  D9 + PR     │
                    └──────┬───────┘
                           │
                    EVALUATION_REPORT.md
                           │
                    ┌──────▼───────┐
                    │  PASS → merge │
                    │  FAIL → retry │ (max 3, then back to spec)
                    └──────────────┘
```

---

## Cross-Agent File Visibility Matrix

| File | Orchestrator | Spec (A) | Spec (B) | Holdout (C) | Builder (D) | Evaluator (E) |
|------|--------------|----------|----------|-------------|-------------|----------------|
| Context file* | AUTO | AUTO | AUTO | AUTO | AUTO | AUTO |
| AGENT_BOOTSTRAP.md | READ | READ | READ | READ | READ | - |
| architecture/* | READ | READ | - | - | - | - |
| Templates/compressed/* | - | READ | READ | READ | - | - |
| TASK.md | WRITE | READ | - | - | - | - |
| D1-D6 | READ | WRITE | READ | D2+D4 only | - | - |
| D7-D8-D10 | READ | - | WRITE | - | READ | - |
| BUILDER_HANDOFF | READ | - | WRITE | - | READ | - |
| D9 (holdouts) | NEVER | - | - | WRITE | NEVER | READ |
| staging/ code | - | - | - | - | WRITE | READ (PR) |
| RESULTS.md | READ | - | - | - | WRITE | NEVER |
| EVALUATION_REPORT | READ | - | - | - | NEVER | WRITE |
| EVALUATION_ERRORS | READ | - | - | - | READ (retry) | WRITE |

*Context file = CLAUDE.md / AGENTS.md / GEMINI.md (same content via symlinks)

---

## What the Orchestrator Does

The orchestrator is HO2. It reads state and dispatches work. Worker agents are HO1 executions reached through `run.sh` or a subagent/tool call.

It does NOT:
- Interpret specs
- Make design decisions
- Modify agent outputs
- Fix specs directly
- Implement code directly
- Evaluate deliverables directly except for routing/reporting evaluator outcomes
- Create standalone plans beyond dispatch/work-order artifacts
- Skip gates

It DOES:
- Read dependencies, blocker status, and framework artifacts to derive state
- Emit `TASK.md` as a `WORK_ORDER` artifact before Turn A
- Create symlinks (AGENTS.md, GEMINI.md → CLAUDE.md) if they don't exist
- Invoke each agent with its role file content in the prompt
- List the explicit files to read in the prompt (reinforces the Cold Start order)
- Wait for human gates where required
- Pass `EVALUATION_ERRORS.md` to builder on retry
- Track attempt count (max 3)
- Report `STATUS` / `VERDICT`

The orchestrator emits only:
- `WORK_ORDER` / `DISPATCH` blocks (including `TASK.md`)
- `STATUS` / `VERDICT` blocks

No freeform spec edits, code edits, or evaluation content.

---

## Setup Checklist (One-Time)

Before running the Sawmill for the first time:

- [ ] `CLAUDE.md` exists at project root with institutional context
- [ ] `AGENTS.md` symlinked to `CLAUDE.md` (for Codex)
- [ ] `GEMINI.md` symlinked to `CLAUDE.md` (for Gemini)
- [ ] `.claude/agents/` has all 4 role files (spec-agent, holdout-agent, builder, evaluator)
- [ ] `Templates/` has all D1-D10 templates + handoff standards (full, for humans)
- [ ] `Templates/compressed/` has all compressed templates (for agents)
- [ ] `.holdouts/` directory exists
- [ ] `sawmill/` directory exists
- [ ] Git hooks activated: `git config core.hooksPath .githooks` (syncs source → docs/ on commit)
- [ ] Agent CLIs installed: `claude`, `codex`, `gemini` (whichever you're using)
- [ ] Codex fallback configured (if using Codex without symlinks): `project_doc_fallback_filenames = ["CLAUDE.md"]`
- [ ] Gemini context configured (if using Gemini without symlinks): `"contextFileName": ["GEMINI.md", "CLAUDE.md"]`
