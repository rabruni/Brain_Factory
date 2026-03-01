# Brain Factory — DoPeJarMo Architecture

Architecture authority documents, build process specifications, D1-D10 templates, agent role definitions, and Sawmill pipeline infrastructure for the DoPeJarMo governed operating system and DoPeJar personal AI companion.

## Document Authority Chain

| Document | Authority | Scope |
|---|---|---|
| [NORTH STAR](architecture/NORTH_STAR.md) | Design authority (highest) | Why the system works the way it does. Resolves all ambiguity. |
| [BUILDER SPEC](architecture/BUILDER_SPEC.md) | Build authority | What to build. Nine primitives, Write Path, dispatch sequence, boot order. |
| [OPERATIONAL SPEC](architecture/OPERATIONAL_SPEC.md) | Operational authority | How it runs. Boot, failure, recovery, Docker topology, session transport. |
| [Framework Registry](architecture/FRAMEWORK_REGISTRY.md) | Framework authority | Framework segregation, build order, coding boundaries. (Consolidated into BUILD-PLAN.md) |

## Institutional Context

The [Institutional Context](institutional-context.md) (CLAUDE.md) is the single source of truth auto-loaded by every agent CLI. It provides: project identity, drift warning, nine primitives, core invariant, 6 KERNEL frameworks, Sawmill overview, isolation rules, and repository structure.

## Build Process (Sawmill)

| Document | Purpose |
|---|---|
| [Sawmill Analysis](architecture/SAWMILL_ANALYSIS.md) | L3 dark factory — spec-driven build process with agent isolation and holdout gates. |
| [Cold Start Protocol](sawmill/COLD_START.md) | Exact reading chain for every agent type. File visibility matrix. CLI invocation commands. |

## Agent Roles

Four specialist agents execute the Sawmill pipeline:

| Agent | Turn | What it does |
|---|---|---|
| [Spec Agent](agents/spec-agent.md) | A + B | Extracts specifications (D1-D6), then build plans (D7-D8-D10) |
| [Holdout Agent](agents/holdout-agent.md) | C | Writes acceptance tests the builder never sees (D9) |
| [Builder](agents/builder.md) | D | Implements code from specs. 13Q gate, then DTT. |
| [Evaluator](agents/evaluator.md) | E | Runs holdout scenarios against built code. PASS/FAIL verdict. |

## Template Compression

[Compression Standard](compressed/COMPRESSION_STANDARD.md) — 8-rule method for reducing template tokens by 73% while preserving generation fidelity. Agents read compressed versions only. Humans author and review full versions.

## Docker Topology (Decided)

Four services: `kernel`, `ledger` (immudb), `ollama`, `zitadel`. See [OPERATIONAL_SPEC Docker Topology](architecture/OPERATIONAL_SPEC.md) for full details.
