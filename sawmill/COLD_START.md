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

This gives the agent: its role (spec/holdout/builder/evaluator), what it can read,
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

CANNOT read: D1, D3, D5, D6, D7, D8, D10, architecture/*, src/*

Writes:
  .holdouts/<FMWK>/D9_HOLDOUT_SCENARIOS.md
```

**Builder Agent (Turn D)**:
```
Reads (in this exact order):
  sawmill/<FMWK>/D10_AGENT_CONTEXT.md     ← orientation FIRST
  sawmill/<FMWK>/BUILDER_HANDOFF.md       ← task SECOND
  Files from BUILDER_HANDOFF Section 7    ← referenced code

On retry, also reads:
  sawmill/<FMWK>/EVALUATION_ERRORS.md     ← what failed

CANNOT read: .holdouts/*, EVALUATION_REPORT.md

Writes:
  src/<FMWK>/**
  sawmill/<FMWK>/RESULTS.md
  PR on branch build/<FMWK>
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

## The TASK.md File (Orchestrator → Spec Agent)

The orchestrator creates a `TASK.md` in each framework's sawmill directory before invoking the spec agent. This is the "work order" that tells the agent which framework to spec:

```markdown
# Task: <FMWK-ID>

## Framework
- ID: <FMWK-NNN>
- Name: <name>
- Layer: KERNEL | Layer 1 | Layer 2

## What to Spec
<one paragraph from BUILD-PLAN.md describing this framework>

## Owns
<from KERNEL frameworks table — what data/behavior this framework exclusively owns>

## Dependencies
<which frameworks must exist before this one>

## Constraints
<any framework-specific constraints from BUILD-PLAN.md or FWK-0-DRAFT.md>
```

---

## Handoff Diagram

```
                    ┌──────────────┐
                    │  TASK.md     │ ← orchestrator writes
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

| File | Spec (A) | Spec (B) | Holdout (C) | Builder (D) | Evaluator (E) |
|------|----------|----------|-------------|-------------|----------------|
| Context file* | AUTO | AUTO | AUTO | AUTO | AUTO |
| AGENT_BOOTSTRAP.md | READ | READ | READ | READ | - |
| architecture/* | READ | - | - | - | - |
| Templates/compressed/* | READ | READ | READ | - | - |
| TASK.md | READ | - | - | - | - |
| D1-D6 | WRITE | READ | D2+D4 only | - | - |
| D7-D8-D10 | - | WRITE | - | READ | - |
| BUILDER_HANDOFF | - | WRITE | - | READ | - |
| D9 (holdouts) | - | - | WRITE | NEVER | READ |
| src/ code | - | - | - | WRITE | READ (PR) |
| RESULTS.md | - | - | - | WRITE | NEVER |
| EVALUATION_REPORT | - | - | - | NEVER | WRITE |
| EVALUATION_ERRORS | - | - | - | READ (retry) | WRITE |

*Context file = CLAUDE.md / AGENTS.md / GEMINI.md (same content via symlinks)

---

## What the Orchestrator Does

The orchestrator's only job is to invoke agents in the right order with the right file paths. It does NOT:
- Interpret specs
- Make design decisions
- Modify agent outputs
- Skip gates

It DOES:
- Create TASK.md before Turn A
- Create symlinks (AGENTS.md, GEMINI.md → CLAUDE.md) if they don't exist
- Invoke each agent with its role file content in the prompt
- List the explicit files to read in the prompt (reinforces the Cold Start order)
- Wait for human gates where required
- Pass EVALUATION_ERRORS.md to builder on retry
- Track attempt count (max 3)
- Report final verdict

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
- [ ] Agent CLIs installed: `claude`, `codex`, `gemini` (whichever you're using)
- [ ] Codex fallback configured (if using Codex without symlinks): `project_doc_fallback_filenames = ["CLAUDE.md"]`
- [ ] Gemini context configured (if using Gemini without symlinks): `"contextFileName": ["GEMINI.md", "CLAUDE.md"]`
