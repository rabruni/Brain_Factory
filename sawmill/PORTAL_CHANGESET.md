# Portal Changeset — 2026-03-07 (run 2)

> Written by the **portal-steward** role after alignment workflow.

## Changes Applied

### 1. Synced mirror: `docs/agents/builder.md`

**What:** Updated mirror to match source `.claude/agents/builder.md`.

**Why:** Source added `model: sonnet` header, expanded Inputs list from 3 to 5 items (added `AGENT_BOOTSTRAP.md` as #1 and `Templates/TDD_AND_DEBUGGING.md` as #3). Mirror was stale.

**Lines changed:** Lines 1-15 — added model line, expanded reading order.

### 2. Synced mirror: `docs/sawmill/COLD_START.md`

**What:** Updated mirror to match source `sawmill/COLD_START.md`.

**Why:** Source expanded Builder Agent (Turn D) reading order to 5 items (added AGENT_BOOTSTRAP.md, TDD_AND_DEBUGGING.md, renumbered). Source added Orchestrator column to Cross-Agent File Visibility Matrix. Mirror was stale.

**Lines changed:** Lines 184-187 (builder reading order), lines 295-309 (visibility matrix).

### 3. Updated narrative: `docs/agent-onboarding.md`

**What:** Added `AGENT_BOOTSTRAP.md` node to builder reading order Mermaid diagram. Updated flow chain from `CTX → D10 → TDD → HO → REF` to `CTX → BOOT → D10 → TDD → HO → REF`.

**Why:** Builder source now reads AGENT_BOOTSTRAP.md first. Narrative diagram was missing this step.

**Lines changed:** Lines 204-221 — Mermaid graph updated.

### 4. Added to portal map: `sawmill/DEPENDENCIES.yaml`

**What:** Added new entry to `docs/PORTAL_MAP.yaml` as infrastructure mirror (source only, no docs/ copy).

**Why:** New source-truth file for framework dependency graph. Already referenced by narrative pages (agent-onboarding.md, orchestrator.md, auditor.md) but was not tracked in the portal map.

**Entry added:** `source: sawmill/DEPENDENCIES.yaml`, `sync: mirror` (no mirror path — infrastructure, not rendered content).

### 5. Updated `docs/PORTAL_STATUS.md`

**What:** Refreshed portal health report. Mirror count 36 → 37. Documented all drift fixes.

## Source-Truth Conflicts

None detected. No source-vs-source contradictions found during this run.
