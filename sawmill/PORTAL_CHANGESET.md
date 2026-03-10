# Portal Changeset — 2026-03-09 (run 3)

> Written by the **portal-steward** role after alignment workflow.

## Changes Applied

### 1. Added source-truth execution contract

**What:** Created `sawmill/EXECUTION_CONTRACT.md` and added the mirrored TechDocs page `docs/sawmill/EXECUTION_CONTRACT.md`.

**Why:** The runtime execution chain and ownership split needed a single operational source of truth.

### 2. Updated runtime and orchestration source docs

**What:** Updated `AGENTS.md`, `sawmill/COLD_START.md`, `.claude/agents/orchestrator.md`, `architecture/BUILD-PLAN.md`, and the `sawmill/run.sh` header to point back to the new execution-contract source.

**Why:** These files were restating the execution model independently. They now summarize and link back instead of competing.

### 3. Reconciled portal ownership docs

**What:** Updated `PORTAL_TRUTH_MODEL.md`, `docs/PORTAL_CONSTITUTION.md`, `.claude/agents/portal-steward.md`, and `SYSTEM_EXECUTION_PLAN.md` to split ownership correctly:

- `run.sh` owns stage-local status updates and framework-local stage audits
- `portal-steward` owns portal maintenance only
- `auditor` owns diagnosis only
- `.githooks/pre-commit` is the primary mirror-sync path

**Why:** The docs were still implying `portal-steward` was part of the per-stage runtime loop, which is false in the current system.

### 4. Extended mirror-sync and portal map coverage

**What:** Updated `.githooks/pre-commit`, `docs/PORTAL_MAP.yaml`, and `mkdocs.yml` so the new execution-contract source is mirrored and rendered automatically.

**Why:** Pre-commit remains the primary mirror-sync mechanism, so the new source-truth file had to be included there.

### 5. Refreshed portal health status

**What:** Updated `docs/PORTAL_STATUS.md` to reflect the new mirror count, nav count, and execution-contract alignment work.

## Source-Truth Conflicts

None detected. No source-vs-source contradictions found during this run.
