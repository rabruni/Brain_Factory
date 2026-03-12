# Sawmill Backstage Coverage Audit

- **Repo doc path**: `docs/sawmill/FMWK-001-BACKSTAGE-COVERAGE-AUDIT-2026-03-11.md`
- **TechDocs path**: `sawmill/FMWK-001-BACKSTAGE-COVERAGE-AUDIT-2026-03-11/`
- **Timestamp**: 2026-03-11
- **Scope**: Sawmill-related repo surfaces vs Backstage coverage
- **Mode**: Inspection-only. No changes made to code, pipeline, or implementation files.

---

## 1. Purpose

Determine whether Backstage accurately reflects the sawmill-related repo reality. Identify what is covered, what is missing, what is stale, and what needs cleanup to bring Backstage into alignment with the repo.

---

## 2. Scope Inspected

- All files under `sawmill/` (25 top-level files, 4 subdirectories)
- All files under `sawmill/FMWK-001-ledger/` (14 spec/plan artifacts)
- All files under `sawmill/FMWK-900-sawmill-smoke/` (2 files + 19 run directories)
- All files under `sawmill/prompts/` (9 prompt templates)
- All files under `sawmill/workers/` (2 worker scripts)
- All files under `.holdouts/FMWK-001-ledger/` (1 holdout scenario)
- All files under `staging/FMWK-001-ledger/` (8 code files)
- All files under `.claude/agents/` (8 role files)
- Architecture files with sawmill relevance (5 files)
- All mkdocs.yml nav entries
- All PORTAL_MAP.yaml entries
- All `docs/sawmill/` files (22 files)
- All `docs/agents/` files (8 files)
- All `docs/architecture/` files (12 files)

---

## 3. Repo Surfaces Inspected

### sawmill/ top-level (25 files)

| File | Category | In Backstage? |
|------|----------|--------------|
| `run.sh` (2,234 lines) | Pipeline engine | NO (referenced from other pages) |
| `boot-orchestrator.sh` | Pipeline bootstrap | NO |
| `ROLE_REGISTRY.yaml` | Registry | YES (mirror at `docs/sawmill/ROLE_REGISTRY.yaml`) |
| `PROMPT_REGISTRY.yaml` | Registry | NO |
| `ARTIFACT_REGISTRY.yaml` | Registry | NO |
| `DEPENDENCIES.yaml` (19 lines) | Registry | NO (PORTAL_MAP entry exists, no mirror path) |
| `EXECUTION_CONTRACT.md` | Document | YES (mirror at `docs/sawmill/EXECUTION_CONTRACT.md`) |
| `COLD_START.md` | Document | YES (mirror at `docs/sawmill/COLD_START.md`) |
| `AGENT_TRAVERSAL.md` | Document | YES (mirror at `docs/sawmill/AGENT_TRAVERSAL.md`) |
| `validate_evidence_artifacts.py` | Validator | NO |
| `validate_role_registry.py` | Validator | NO |
| `validate_artifact_registry.py` | Validator | NO |
| `validate_prompt_registry.py` | Validator | NO |
| `render_prompt.py` | Utility | NO |
| `resolve_stage_artifacts.py` | Utility | NO |
| `sync_portal_mirrors.py` | Utility | NO |
| `run_with_timeout.py` | Utility | NO |
| `extract_heartbeats.py` | Utility | NO |
| `check_runtime_harness.py` | Utility | NO |
| `project_run_status.py` | Utility | NO |
| `PORTAL_CHANGESET.md` | Portal artifact | NO (internal) |
| `PORTAL_AUDIT_RESULTS.md` | Portal artifact | NO (internal) |
| `SESSION_2026-03-07.md` | Session log | NO (ephemeral) |
| `SESSION_LOG_2026-03-11.md` | Session log | NO (ephemeral) |
| `SUPERPOWERS_GAP_ANALYSIS.md` | Analysis | NO |

### sawmill/prompts/ (9 files)

| File | In Backstage? |
|------|--------------|
| `turn_a_spec.txt` | NO |
| `turn_b_plan.txt` | NO |
| `turn_c_holdout.txt` | NO |
| `turn_d_13q.txt` | NO |
| `turn_d_build.txt` | NO |
| `turn_d_review.txt` | NO |
| `turn_e_eval.txt` | NO |
| `audit_run.txt` | NO |
| `portal_stage.txt` | NO |

### sawmill/workers/ (2 files)

| File | In Backstage? |
|------|--------------|
| `mock_worker.py` | NO |
| `canary_mock_worker.py` | NO |

### sawmill/FMWK-001-ledger/ (14 files)

| File | In Backstage? |
|------|--------------|
| `TASK.md` | NO (working artifact) |
| `D1_CONSTITUTION.md` | NO (working artifact) |
| `D2_SPECIFICATION.md` | NO (working artifact) |
| `D3_DATA_MODEL.md` | NO (working artifact) |
| `D4_CONTRACTS.md` | NO (working artifact) |
| `D5_RESEARCH.md` | NO (working artifact) |
| `D6_GAP_ANALYSIS.md` | NO (working artifact) |
| `D7_PLAN.md` | NO (working artifact) |
| `D8_TASKS.md` | NO (working artifact) |
| `D10_AGENT_CONTEXT.md` | NO (working artifact) |
| `BUILDER_HANDOFF.md` | NO (working artifact) |
| `13Q_ANSWERS.md` | NO (working artifact) |
| `SOURCE_MATERIAL.md` | NO (working artifact) |
| `GATE_CHECKLIST.md` | NO (working artifact) |

Note: these 14 files are summarized in the FMWK-001 status page (`docs/sawmill/FMWK-001-ledger.md`) and the Readiness Audit. They are working artifacts, not reference documents. **Question for Ray**: should they remain internal-only, or should an architect be able to read them via Backstage?

### sawmill/FMWK-900-sawmill-smoke/ (2 files + 19 run dirs)

| Surface | In Backstage? |
|---------|--------------|
| `TASK.md` | NO (working artifact) |
| `CANARY_AUDIT.md` | NO |
| 19 run directories with `run.json`, `status.json`, `events.jsonl` | NO |

### architecture/ sawmill-related (5 files)

| File | In Backstage? | In PORTAL_MAP? |
|------|--------------|---------------|
| `SAWMILL_ANALYSIS.md` | YES (mirror) | YES |
| `SAWMILL_RUNTIME_SPEC_v0.1.md` | NO | NO |
| `SAWMILL_NEXT_PHASE.md` | NO | NO |
| `CANARY_BACKEND_POLICY.md` | NO | NO |
| `HARNESS_INVARIANTS.md` | NO | NO |

### docs/architecture/ orphan (1 file)

| File | Source exists? | In PORTAL_MAP? |
|------|---------------|---------------|
| `GROUND_TRUTH_AUDIT.md` | NO source in `architecture/` | NO |

---

## 4. Backstage Pages Compared

### Audits nav (9 pages, all in docs/sawmill/ or docs/architecture/)

| Nav title | Doc file | PORTAL_MAP entry? | Stale? |
|-----------|----------|-------------------|--------|
| FMWK-001 SDK Boundary Audit | `sawmill/FMWK-001-SDK-BOUNDARY-AUDIT-2026-03-11.md` | NO | No |
| Cleanup Execution (X001) | `sawmill/SAWMILL-CLEANUP-EXECUTION-2026-03-11-X001.md` | NO | Run count stale (says 14, actual 19) |
| Readiness Decision (X001) | `sawmill/READINESS-DECISION-2026-03-11-X001.md` | NO | No |
| Current State Readiness (X001) | `sawmill/CURRENT-STATE-READINESS-2026-03-11-X001.md` | NO | Run count stale (says 14, actual 19) |
| Pre-Execution Safety Audit (X001) | `sawmill/SAWMILL-PRE-EXECUTION-...-X001.md` | NO | Run count stale (says 14, actual 19) |
| Design-for-Execution Boundary (X001) | `sawmill/DESIGN-FOR-EXECUTION-...-X001.md` | NO | Says "11 canary runs passed" (misleading, only 2 mock passed) |
| Source-of-Truth Audit (X001) | `sawmill/SOURCE-OF-TRUTH-...-X001.md` | NO | Run count stale (says 11, actual 19) |
| FMWK-001 Readiness Audit | `sawmill/FMWK-001-READINESS-AUDIT.md` | NO | No |
| Ground-Truth Audit | `architecture/GROUND_TRUTH_AUDIT.md` | NO | Run count stale (says 11, actual 19) |

**Key finding**: None of the 9 audit pages are in PORTAL_MAP. They were created directly in `docs/` and added to mkdocs.yml nav only. The sync mechanisms (pre-commit hook, mkdocs hook) do not track them.

### How It Works nav (7 pages)

| Nav title | Doc file | PORTAL_MAP entry? | Mirror source? | Stale? |
|-----------|----------|-------------------|---------------|--------|
| Pipeline Overview | `sawmill/PIPELINE_VISUAL.md` | YES (narrative) | N/A (narrative) | Not checked |
| Agent Onboarding | `agent-onboarding.md` | YES (narrative) | N/A | Not checked |
| Cold Start Protocol | `sawmill/COLD_START.md` | YES (mirror) | `sawmill/COLD_START.md` | Not checked |
| Execution Contract | `sawmill/EXECUTION_CONTRACT.md` | YES (mirror) | `sawmill/EXECUTION_CONTRACT.md` | Not checked |
| Agent Traversal | `sawmill/AGENT_TRAVERSAL.md` | YES (mirror) | `sawmill/AGENT_TRAVERSAL.md` | Not checked |
| Sawmill Role Registry | `sawmill/ROLE_REGISTRY.md` | YES (narrative) | N/A | Not checked |
| Run Verification | `sawmill/RUN_VERIFICATION.md` | YES (narrative) | N/A | Not checked |

All 7 pages are in PORTAL_MAP. Sync mechanisms cover them.

### Framework Builds nav (7 pages)

| Nav title | Doc file | PORTAL_MAP entry? | Stale? |
|-----------|----------|-------------------|--------|
| FMWK-001 Ledger | `sawmill/FMWK-001-ledger.md` | YES (status) | No |
| FMWK-002 Write-Path | `sawmill/FMWK-002-write-path.md` | YES (status) | Not checked |
| FMWK-003 Orchestration | `sawmill/FMWK-003-orchestration.md` | YES (status) | Not checked |
| FMWK-004 Execution | `sawmill/FMWK-004-execution.md` | YES (status) | Not checked |
| FMWK-005 Graph | `sawmill/FMWK-005-graph.md` | YES (status) | Not checked |
| FMWK-006 Package-Lifecycle | `sawmill/FMWK-006-package-lifecycle.md` | YES (status) | Not checked |
| FMWK-900 Sawmill Smoke | `sawmill/FMWK-900-sawmill-smoke.md` | YES (status) | **YES — severely stale** |

### Agent Roles nav (8 pages)

All 8 agent role mirrors are in PORTAL_MAP as `sync: mirror`. Pre-commit hook syncs them. CANARY_AUDIT.md confirms "Mirrors synced: 44/44".

---

## 5. Proven in Sync

1. **Agent role mirrors (8 files).** All `.claude/agents/*.md` files have corresponding `docs/agents/*.md` mirrors. PORTAL_MAP tracks them. Pre-commit hook via `sync_portal_mirrors.py` keeps them synced. CANARY_AUDIT confirms "Mirrors synced: 44/44".

2. **Core sawmill documents (3 files).** `COLD_START.md`, `EXECUTION_CONTRACT.md`, and `AGENT_TRAVERSAL.md` all have mirrors in `docs/sawmill/`, PORTAL_MAP entries, and nav references.

3. **ROLE_REGISTRY.yaml mirror.** Source and docs/ copy verified in sync (diff shows no differences). PORTAL_MAP tracks it.

4. **Architecture mirrors (11 files).** All 11 architecture files in PORTAL_MAP have corresponding `docs/architecture/` mirrors and mkdocs.yml nav entries. Pre-commit hook covers them.

5. **Framework Builds status pages (7 files).** All framework status pages exist in `docs/sawmill/` and are in both PORTAL_MAP and mkdocs.yml nav.

6. **How It Works pages (7 pages).** All present in PORTAL_MAP and mkdocs.yml nav.

7. **All mkdocs.yml nav entries resolve to existing files.** No dead links.

---

## 6. Missing from Backstage

### High priority (referenced by other artifacts or architecturally relevant)

| Repo surface | Why it matters | Referenced by |
|-------------|---------------|---------------|
| `sawmill/ARTIFACT_REGISTRY.yaml` | Defines all 22 artifact paths, owners, and stages. Architects need this to understand what Sawmill produces. | run.sh, validate_artifact_registry.py |
| `sawmill/PROMPT_REGISTRY.yaml` | Defines all 10 prompt dependency chains. Architects need this to understand turn sequencing. | run.sh, validate_prompt_registry.py |
| `architecture/SAWMILL_RUNTIME_SPEC_v0.1.md` | Referenced by ARTIFACT_REGISTRY as `standard_ref` for 3 evidence artifacts (builder, reviewer, evaluator). Defines the evidence contract. | ARTIFACT_REGISTRY.yaml (3 entries) |
| `sawmill/FMWK-900-sawmill-smoke/CANARY_AUDIT.md` | Latest audit results for canary runs. Shows 4 FAIL checks. Only machine-generated audit artifact. | Cleanup Execution audit page references it |

### Medium priority (sawmill-related architecture documents)

| Repo surface | Why it matters |
|-------------|---------------|
| `architecture/CANARY_BACKEND_POLICY.md` | Defines which backends are allowed for canary vs production runs |
| `architecture/HARNESS_INVARIANTS.md` | Defines runtime invariants the harness must maintain |
| `architecture/SAWMILL_NEXT_PHASE.md` | Documents what comes after the current sawmill phase |

### Lower priority (internal tooling — useful for onboarding but not critical)

| Repo surface | Why it matters |
|-------------|---------------|
| `sawmill/validate_evidence_artifacts.py` | Defines the evidence JSON schema for all 3 roles. Currently only readable by reading the Python source. |
| 9 prompt templates in `sawmill/prompts/` | Define what agents are told. Currently only readable by reading the .txt files. |
| 19 run directories in `sawmill/FMWK-900-sawmill-smoke/runs/` | Run history with structured data. No visibility. |

---

## 7. Stale or Misleading in Backstage

### Severely stale

| Page | What it says | What repo shows | Impact |
|------|-------------|-----------------|--------|
| **FMWK-900 status page** | "Not started", all 5 stages "PENDING" | 19 run directories exist, 2 passed (mock), codex completed through Turn D, latest run ID `20260312T035812Z` | **Most misleading page in Backstage.** An architect reading this would conclude the canary has never run. |

### Run count drift (4 pages)

| Page | Claims | Actual | Impact |
|------|--------|--------|--------|
| Ground Truth Audit | "11 runs in runs/ directory" | 19 | Stale snapshot |
| Source-of-Truth Audit | "11 canary runs" | 19 | Stale snapshot |
| Pre-Execution Safety Audit | "14 runs" | 19 | Stale snapshot |
| Current State Readiness | "14 runs" | 19 | Stale snapshot |

### Misleading characterization (1 page)

| Page | Claims | Actual | Impact |
|------|--------|--------|--------|
| Design-for-Execution Audit | "11 canary runs passed" | 2 of 19 passed (both mock) | Inverts the pass/fail ratio. Reads as if all 11 passed. |

---

## 8. Naming/Path Drift

| Issue | Detail | Impact |
|-------|--------|--------|
| **Orphan audit page** | `docs/architecture/GROUND_TRUTH_AUDIT.md` has no source file in `architecture/`. It was written directly to `docs/`. All other `docs/architecture/` files are mirrors of `architecture/` sources. | Breaks the mirror pattern. If someone edits `architecture/` expecting it to propagate, the Ground Truth Audit won't be there. |
| **Audit pages not in PORTAL_MAP** | All 9 audit pages were created directly in `docs/sawmill/` and added to mkdocs.yml nav, but none are registered in `PORTAL_MAP.yaml`. | Sync mechanisms don't track them. If PORTAL_MAP validation is tightened, they'll be invisible. |
| **DEPENDENCIES.yaml mirror gap** | PORTAL_MAP declares `sawmill/DEPENDENCIES.yaml` as `sync: mirror` but specifies no `mirror:` path. Per PORTAL_MAP schema, this means "portal infra, no docs/ copy." | Valid by schema but inconsistent with the other 3 registries (ROLE_REGISTRY has a mirror; PROMPT and ARTIFACT have none and aren't in PORTAL_MAP at all). |
| **Audit naming inconsistency** | Some audits use `(X001)` suffix (6 pages). Others don't (3 pages: Ground-Truth, FMWK-001 Readiness, SDK Boundary). | Minor — no functional impact but reduces scanability. |

---

## 9. SDK-Related Coverage Gaps

| Gap | Detail |
|-----|--------|
| **SDK Boundary Audit exists and is current** | `docs/sawmill/FMWK-001-SDK-BOUNDARY-AUDIT-2026-03-11.md` covers the replace/wrap/promote/coexist question with evidence. Published today. In nav. |
| **No page surfaces the SDK import dependencies** | FMWK-001 staging imports `PlatformError`, `get_config`, `get_secret` from the SDK. This is documented in the SDK Boundary Audit but not in the FMWK-001 status page or any "How It Works" page. |
| **No page documents the immudb_adapter.py plan** | BUILDER_HANDOFF specifies creating `platform_sdk/tier0_core/data/immudb_adapter.py` in staging. This is the FMWK-001 adapter for immudb, distinct from the SDK's existing `ImmudbProvider`. No Backstage page explains this planned file or its relationship to the SDK. |
| **SAWMILL_RUNTIME_SPEC_v0.1.md not published** | This architecture document is referenced by ARTIFACT_REGISTRY as the `standard_ref` for all 3 evidence artifacts. It presumably defines the evidence JSON contract. Not in Backstage, not in PORTAL_MAP. |

---

## 10. Recommended Backstage Cleanup Sequence

These are documentation alignment actions only. No code changes.

### Step 1: Fix the most misleading page

Update `docs/sawmill/FMWK-900-sawmill-smoke.md` to reflect that 19 canary runs exist, 2 passed (mock), and codex has completed through Turn D. The current "Not started" / all "PENDING" state is the single most inaccurate page in Backstage.

### Step 2: Add run-count snapshot dates to audit pages

For the 4 audit pages with stale run counts, either:
- (a) Add a "snapshot date" note next to each count, or
- (b) Replace specific counts with a reference to `ls sawmill/FMWK-900-sawmill-smoke/runs/`

This prevents perpetual drift.

### Step 3: Fix the misleading claim in Design-for-Execution Audit

Change "11 canary runs passed" to accurately reflect that only 2 of 19 runs passed (both mock).

### Step 4: Publish the 2 missing registries

Add `PROMPT_REGISTRY.yaml` and `ARTIFACT_REGISTRY.yaml` to `docs/sawmill/`, PORTAL_MAP, and mkdocs.yml nav (under "How It Works" alongside the existing Role Registry). These define the prompt dependency chains and artifact ownership — essential for understanding Sawmill.

### Step 5: Publish SAWMILL_RUNTIME_SPEC_v0.1.md

Add mirror to `docs/architecture/`, PORTAL_MAP, and mkdocs.yml nav. It's referenced by ARTIFACT_REGISTRY as the standard for evidence artifacts.

### Step 6: Register audit pages in PORTAL_MAP

Add all 9+ audit pages to PORTAL_MAP as `sync: narrative` entries. This brings them under the sync mechanism's awareness.

### Step 7: Resolve the Ground Truth Audit orphan

Either:
- (a) Create `architecture/GROUND_TRUTH_AUDIT.md` as the source and make `docs/architecture/GROUND_TRUTH_AUDIT.md` a mirror, or
- (b) Register it in PORTAL_MAP as a `sync: narrative` page (authored directly in docs/)

### Step 8: Decide on remaining architecture files

`CANARY_BACKEND_POLICY.md`, `HARNESS_INVARIANTS.md`, `SAWMILL_NEXT_PHASE.md` exist in `architecture/` with no Backstage presence. Decide: publish, or acknowledge as internal-only.

---

## 11. Questions for Ray

1. **FMWK-900 status page**: This is the most misleading page in Backstage ("Not started", all "PENDING" despite 19 runs). Should it be manually updated now, or is it expected to be auto-updated by run.sh on the next run?

2. **Spec pack visibility**: The 14 FMWK-001 spec/plan artifacts (D1-D10, BUILDER_HANDOFF, etc.) are in `sawmill/FMWK-001-ledger/` but not visible in Backstage. Should an architect be able to read them through TechDocs, or are they correctly internal-only?

3. **Audit page PORTAL_MAP registration**: None of the 9 audit pages are in PORTAL_MAP. Should they be registered (as narrative entries), or are they intentionally outside the sync mechanism?

4. **Ground Truth Audit home**: `docs/architecture/GROUND_TRUTH_AUDIT.md` has no source file in `architecture/`. It's an orphan. Should it get a source file, or should it be registered as a narrative page in PORTAL_MAP?

5. **Stale run counts**: 4 published pages cite run counts that are already outdated (11, 14 — actual is 19). Should future audit pages avoid specific counts, or include a snapshot date, or something else?

6. **architecture/ unpublished files**: 4 sawmill-related architecture files exist with no Backstage presence (CANARY_BACKEND_POLICY, HARNESS_INVARIANTS, SAWMILL_NEXT_PHASE, SAWMILL_RUNTIME_SPEC_v0.1). Publish, or keep internal?

---

## 12. Appendix

### Exact repo paths inspected

```
# Sawmill top-level (25 files)
sawmill/run.sh
sawmill/boot-orchestrator.sh
sawmill/ROLE_REGISTRY.yaml
sawmill/PROMPT_REGISTRY.yaml
sawmill/ARTIFACT_REGISTRY.yaml
sawmill/DEPENDENCIES.yaml
sawmill/EXECUTION_CONTRACT.md
sawmill/COLD_START.md
sawmill/AGENT_TRAVERSAL.md
sawmill/validate_evidence_artifacts.py
sawmill/validate_role_registry.py
sawmill/validate_artifact_registry.py
sawmill/validate_prompt_registry.py
sawmill/render_prompt.py
sawmill/resolve_stage_artifacts.py
sawmill/sync_portal_mirrors.py
sawmill/run_with_timeout.py
sawmill/extract_heartbeats.py
sawmill/check_runtime_harness.py
sawmill/project_run_status.py
sawmill/PORTAL_CHANGESET.md
sawmill/PORTAL_AUDIT_RESULTS.md
sawmill/SESSION_2026-03-07.md
sawmill/SESSION_LOG_2026-03-11.md
sawmill/SUPERPOWERS_GAP_ANALYSIS.md

# Sawmill prompts (9 files)
sawmill/prompts/turn_a_spec.txt
sawmill/prompts/turn_b_plan.txt
sawmill/prompts/turn_c_holdout.txt
sawmill/prompts/turn_d_13q.txt
sawmill/prompts/turn_d_build.txt
sawmill/prompts/turn_d_review.txt
sawmill/prompts/turn_e_eval.txt
sawmill/prompts/audit_run.txt
sawmill/prompts/portal_stage.txt

# Sawmill workers (2 files)
sawmill/workers/mock_worker.py
sawmill/workers/canary_mock_worker.py

# FMWK-001-ledger spec pack (14 files)
sawmill/FMWK-001-ledger/TASK.md
sawmill/FMWK-001-ledger/D1_CONSTITUTION.md
sawmill/FMWK-001-ledger/D2_SPECIFICATION.md
sawmill/FMWK-001-ledger/D3_DATA_MODEL.md
sawmill/FMWK-001-ledger/D4_CONTRACTS.md
sawmill/FMWK-001-ledger/D5_RESEARCH.md
sawmill/FMWK-001-ledger/D6_GAP_ANALYSIS.md
sawmill/FMWK-001-ledger/D7_PLAN.md
sawmill/FMWK-001-ledger/D8_TASKS.md
sawmill/FMWK-001-ledger/D10_AGENT_CONTEXT.md
sawmill/FMWK-001-ledger/BUILDER_HANDOFF.md
sawmill/FMWK-001-ledger/13Q_ANSWERS.md
sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md
sawmill/FMWK-001-ledger/GATE_CHECKLIST.md

# FMWK-900 canary (2 files + 19 run dirs)
sawmill/FMWK-900-sawmill-smoke/TASK.md
sawmill/FMWK-900-sawmill-smoke/CANARY_AUDIT.md
sawmill/FMWK-900-sawmill-smoke/runs/ (19 directories)

# Holdouts (1 file)
.holdouts/FMWK-001-ledger/D9_HOLDOUT_SCENARIOS.md

# Staging (8 files)
staging/FMWK-001-ledger/ledger/__init__.py
staging/FMWK-001-ledger/ledger/errors.py
staging/FMWK-001-ledger/ledger/ledger.py
staging/FMWK-001-ledger/ledger/schemas.py
staging/FMWK-001-ledger/tests/__init__.py
staging/FMWK-001-ledger/tests/unit/__init__.py
staging/FMWK-001-ledger/tests/integration/__init__.py
staging/FMWK-001-ledger/tests/unit/test_serializer.py

# Agent roles (8 files)
.claude/agents/orchestrator.md
.claude/agents/spec-agent.md
.claude/agents/holdout-agent.md
.claude/agents/builder.md
.claude/agents/reviewer.md
.claude/agents/evaluator.md
.claude/agents/auditor.md
.claude/agents/portal-steward.md

# Architecture sawmill-related (5 files)
architecture/SAWMILL_ANALYSIS.md
architecture/SAWMILL_RUNTIME_SPEC_v0.1.md
architecture/CANARY_BACKEND_POLICY.md
architecture/HARNESS_INVARIANTS.md
architecture/SAWMILL_NEXT_PHASE.md
```

### Exact Backstage pages compared

```
# Audits nav (9 pages)
docs/sawmill/FMWK-001-SDK-BOUNDARY-AUDIT-2026-03-11.md
docs/sawmill/SAWMILL-CLEANUP-EXECUTION-2026-03-11-X001.md
docs/sawmill/READINESS-DECISION-2026-03-11-X001.md
docs/sawmill/CURRENT-STATE-READINESS-2026-03-11-X001.md
docs/sawmill/SAWMILL-PRE-EXECUTION-SAFETY-AND-TRUTH-ALIGNMENT-AUDIT-2026-03-11-X001.md
docs/sawmill/DESIGN-FOR-EXECUTION-BOUNDARY-AUDIT-2026-03-11-X001.md
docs/sawmill/SOURCE-OF-TRUTH-AND-EXECUTION-PATH-AUDIT-2026-03-11-X001.md
docs/sawmill/FMWK-001-READINESS-AUDIT.md
docs/architecture/GROUND_TRUTH_AUDIT.md

# How It Works nav (7 pages)
docs/sawmill/PIPELINE_VISUAL.md
docs/agent-onboarding.md
docs/sawmill/COLD_START.md
docs/sawmill/EXECUTION_CONTRACT.md
docs/sawmill/AGENT_TRAVERSAL.md
docs/sawmill/ROLE_REGISTRY.md
docs/sawmill/RUN_VERIFICATION.md

# Framework Builds nav (7 pages)
docs/sawmill/FMWK-001-ledger.md
docs/sawmill/FMWK-002-write-path.md
docs/sawmill/FMWK-003-orchestration.md
docs/sawmill/FMWK-004-execution.md
docs/sawmill/FMWK-005-graph.md
docs/sawmill/FMWK-006-package-lifecycle.md
docs/sawmill/FMWK-900-sawmill-smoke.md

# Agent Roles nav (8 pages)
docs/agents/orchestrator.md
docs/agents/spec-agent.md
docs/agents/holdout-agent.md
docs/agents/builder.md
docs/agents/reviewer.md
docs/agents/evaluator.md
docs/agents/auditor.md
docs/agents/portal-steward.md

# Architecture (sawmill-related, 1 page)
docs/architecture/SAWMILL_ANALYSIS.md

# PORTAL_MAP.yaml and mkdocs.yml (cross-referenced)
docs/PORTAL_MAP.yaml
mkdocs.yml
```
