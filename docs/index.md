# Brain Factory — DoPeJarMo Architecture

Architecture authority documents, build process specifications, and D1-D10 templates for the DoPeJarMo governed operating system and DoPeJar personal AI companion.

## Document Authority Chain

| Document | Authority | Scope |
|---|---|---|
| [NORTH STAR](architecture/NORTH_STAR.md) | Design authority (highest) | Why the system works the way it does. Resolves all ambiguity. |
| [BUILDER SPEC](architecture/BUILDER_SPEC.md) | Build authority | What to build. Nine primitives, Write Path, dispatch sequence, boot order. |
| [OPERATIONAL SPEC](architecture/OPERATIONAL_SPEC.md) | Operational authority | How it runs. Boot, failure, recovery, Docker topology, session transport. |
| FRAMEWORK_REGISTRY | Framework authority | Framework segregation, build order, coding boundaries. (Pending) |

## Build Process

| Document | Purpose |
|---|---|
| [Sawmill Analysis](architecture/SAWMILL_ANALYSIS.md) | L3 dark factory — spec-driven build process with agent isolation and holdout gates. |

## Docker Topology (Decided)

Four services: `kernel`, `ledger` (immudb), `ollama`, `zitadel`. See [OPERATIONAL_SPEC §Docker Topology](architecture/OPERATIONAL_SPEC.md) for full details.
