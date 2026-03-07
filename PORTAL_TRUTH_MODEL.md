# Portal Truth Model

This file defines how to resolve authority when files in the Brain Factory repo disagree.

## Purpose

The repo contains four different kinds of documentation surfaces:

1. source truth
2. mirrors
3. narrative
4. status and audit artifacts

Confusion happens when a file from one layer is treated like a file from another.

## Layer 1: Source Truth

Source-truth files define reality. If they disagree with docs, source truth wins.

### 1.1 Architectural authority

Use the repo authority chain in this order:

1. `architecture/NORTH_STAR.md`
2. `architecture/BUILDER_SPEC.md`
3. `architecture/OPERATIONAL_SPEC.md`
4. `architecture/FWK-0-DRAFT.md`
5. `architecture/BUILD-PLAN.md`
6. `architecture/AGENT_CONSTRAINTS.md`

### 1.2 Operational source truth

These files define how agents, templates, and the Sawmill actually work:

- `.claude/agents/*`
- `sawmill/COLD_START.md`
- `sawmill/DEPENDENCIES.yaml`
- `sawmill/run.sh`
- `Templates/*`
- `Templates/compressed/*`

If two source-truth files disagree, that is a real source conflict. Do not resolve it in a mirror or a narrative page.

## Layer 2: Mirrors

Mirrors are rendered copies of source truth for TechDocs. They do not decide anything.

Examples:

- `docs/agents/builder.md`
- `docs/agents/orchestrator.md`
- `docs/sawmill/COLD_START.md`

Rule:

- source changes first
- mirrors sync second

If a mirror differs from its source, the mirror is wrong.

## Layer 3: Narrative

Narrative pages explain the system to humans. They may summarize, orient, or sequence information, but they must not contradict source truth.

Examples:

- `docs/index.md`
- `docs/agent-onboarding.md`
- `docs/dopejar-catalog.md`
- `docs/PORTAL_CONSTITUTION.md`

Rule:

- narrative sits on top of source truth
- every important claim should point down to a source artifact

## Layer 4: Status and Audit Artifacts

Status and audit files report on alignment. They are never authoritative.

Examples:

- `docs/PORTAL_STATUS.md`
- `sawmill/PORTAL_CHANGESET.md`
- `sawmill/PORTAL_AUDIT_RESULTS.md`

Rule:

- reports can be stale
- reports do not override source truth

## Ownership Model

- source owners fix source-truth conflicts
- `portal-steward` syncs mirrors, fixes narrative drift, updates portal status
- `auditor` reports drift and contradictions

## When Files Disagree

1. Source truth vs mirror: source truth wins.
2. Source truth vs narrative: source truth wins.
3. Mirror vs narrative: the source-backed mirror wins.
4. Report vs anything else: the report loses.
5. Source truth vs source truth: escalate and fix the source conflict.

## Practical Heuristic

Ask one question:

Does this file define reality, mirror reality, explain reality, or report on reality?

That tells you whether the file is:

- source truth
- mirror
- narrative
- status or audit

## Backstage and TechDocs

Backstage renders the human-facing surface. It is presentation, not authority.

- `mkdocs.yml` controls TechDocs navigation
- `docs/` contains mirrors, narrative, and status pages
- `catalog-info.yaml` defines the Backstage entity

If Backstage or TechDocs disagrees with source truth, source truth wins and the portal surface must be updated.
