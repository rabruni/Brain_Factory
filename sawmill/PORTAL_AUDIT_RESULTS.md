# Portal Audit Results

Date: 2026-03-07 (second pass — current working tree state)
Auditor: Claude Opus 4.6 (auditor role, direct reads, no subagents)
Scope: Full portal coherence audit — all 5 checks per `.claude/agents/auditor.md`
Files read: 104 inventoried + cross-reference sources
Files missing: 0
Orphan docs files: 3

---

## Fixed Since Prior Audit (same day)

These findings from the first audit pass are now resolved in the working tree:

- **Former C-1 (docs/agents/builder.md stale)**: NOW SYNCED. `diff` shows zero differences between `.claude/agents/builder.md` and `docs/agents/builder.md`. Both have `model: sonnet` and 5 inputs.
- **Former C-4 (docs/sawmill/COLD_START.md stale)**: NOW SYNCED. `diff` shows zero differences. Builder reading order has 5 items in both. Visibility matrix has Orchestrator column in both.
- **Former C-9 (agent-onboarding builder diagram missing AGENT_BOOTSTRAP.md)**: NOW FIXED. `docs/agent-onboarding.md:L205`: `BOOT["AGENT_BOOTSTRAP.md<br/>(orientation FIRST)"]` — present as step 1.

---

## Critical Findings (contradictions, broken paths)

**C-1. docs/agents/evaluator.md stale — missing `model: opus` directive**

`diff` output: source lines 3-4 (`model: opus` + blank line) absent from docs.

- `.claude/agents/evaluator.md:L3`: `model: opus`
- `docs/agents/evaluator.md:L1`: `# Evaluator Agent — Turn E` — no `model:` line

---

**C-2. docs/agents/orchestrator.md stale — missing Dispatch Protocol section (19 lines)**

`diff` output: source lines 139-157 absent from docs.

- `.claude/agents/orchestrator.md:L139`: `## Dispatch Protocol`
- `.claude/agents/orchestrator.md:L141`: `"Runtime hooks enforce file-ownership lanes per role."`
- `.claude/agents/orchestrator.md:L144`: `"1. Write the target role name to sawmill/.active-role"`
- `docs/agents/orchestrator.md:L139`: `## Authority Chain` — Dispatch Protocol section entirely absent

---

**C-3. docs/sawmill-templates/BUILDER_HANDOFF_STANDARD.md stale — lists 10 sections, source has 13**

`diff` output: 3 specific differences.

- `Templates/compressed/BUILDER_HANDOFF_STANDARD.md:L12`: `"## Required Sections (ALL 13, in this exact order, no exceptions)"`
- `docs/sawmill-templates/BUILDER_HANDOFF_STANDARD.md:L12`: `"## Required Sections (ALL 10, in this exact order, no exceptions)"`
- `Templates/compressed/BUILDER_HANDOFF_STANDARD.md:L14`: Critical Constraints includes `"TDD discipline (Templates/TDD_AND_DEBUGGING.md — delete code written before tests)"`
- `docs/sawmill-templates/BUILDER_HANDOFF_STANDARD.md:L14`: Critical Constraints ends at `"baseline snapshot."` — TDD discipline absent
- `Templates/compressed/BUILDER_HANDOFF_STANDARD.md:L23-25`: sections 11 (Verification Discipline), 12 (Mid-Build Checkpoint), 13 (Self-Reflection)
- `docs/sawmill-templates/BUILDER_HANDOFF_STANDARD.md`: these 3 sections absent entirely

---

**C-4. evaluator.md and builder.md use `/.holdouts/` (absolute root) — should be `.holdouts/` (relative)**

Leading slash means filesystem root, not repo root.

- `.claude/agents/evaluator.md:L11`: `"D9 Holdout Scenarios (from /.holdouts/)"`
- `.claude/agents/evaluator.md:L23`: `"Read holdout scenarios from /.holdouts/."`
- `.claude/agents/builder.md:L18`: `"D9 (holdout scenarios) — stored in /.holdouts/, off-limits"`
- `sawmill/run.sh:L146`: `HOLDOUT_DIR=".holdouts/${FMWK}"` — relative, correct
- `sawmill/COLD_START.md:L178`: `".holdouts/<FMWK>/D9_HOLDOUT_SCENARIOS.md"` — relative, correct

---

**C-5. Agent role count contradicts across 7 files**

Three different numbers appear (7, 6, 4).

- `CLAUDE.md:L96-104`: 7 roles (orchestrator, spec-agent, holdout-agent, builder, evaluator, auditor, portal-steward)
- `mkdocs.yml:L27-33`: 7 roles (same set)
- `docs/agent-onboarding.md:L35-42`: 6 roles (omits portal-steward)
- `sawmill/COLD_START.md:L128`: `"its role (orchestrator/spec/holdout/builder/evaluator/auditor)"` — 6 roles (omits portal-steward)
- `sawmill/COLD_START.md:L355`: `".claude/agents/ has all 4 role files (spec-agent, holdout-agent, builder, evaluator)"` — 4 roles
- `sawmill/run.sh:L276-278`: preflight checks 4 files (spec-agent, holdout-agent, builder, evaluator) — omits orchestrator, auditor, portal-steward
- `docs/status.md:L15`: `"5-step process, 4 agents"` — 4 agents

---

**C-6. Visibility matrices differ between COLD_START.md and agent-onboarding.md**

Both are current (source = docs for both). Different row sets.

- `sawmill/COLD_START.md:L298`: has `AGENT_BOOTSTRAP.md` row — `"| AGENT_BOOTSTRAP.md | READ | READ | READ | READ | READ | - |"`
- `docs/agent-onboarding.md:L283-298`: AGENT_BOOTSTRAP.md row absent
- `docs/agent-onboarding.md:L286`: has `"| DEPENDENCIES.yaml | read | - | - | - | - | - |"` row
- `docs/agent-onboarding.md:L298`: has `"| docs/status.md | read | - | - | - | - | - |"` row
- `sawmill/COLD_START.md`: DEPENDENCIES.yaml and docs/status.md rows absent

---

**C-7. CLI invocation commands differ between docs and run.sh**

Three discrepancies.

Codex — AGENTS.md injection:
- `sawmill/COLD_START.md:L73-78`: explicitly injects `"$(cat AGENTS.md)"` into prompt
- `docs/agent-onboarding.md:L315-318`: same — explicitly injects AGENTS.md
- `sawmill/run.sh:L242-245`: sends only `"${role_content}\n\n${prompt}"` — does NOT inject AGENTS.md (relies on auto-load per L236 comment)

Gemini — `--output-format json`:
- `sawmill/COLD_START.md:L92`: includes `--output-format json`
- `docs/agent-onboarding.md:L324`: includes `--output-format json`
- `sawmill/run.sh:L253-256`: omits `--output-format json`

SAWMILL_ACTIVE_ROLE env var:
- `sawmill/run.sh:L230`: `SAWMILL_ACTIVE_ROLE="$role_name"` — set on every invocation
- Checked: `sawmill/COLD_START.md`, `docs/agent-onboarding.md` — NOT FOUND in either

---

**C-8. AGENT_BUILD_PROCESS.yaml Critical Constraints lists 10 items — full template lists 11**

- `Templates/BUILDER_HANDOFF_STANDARD.md:L53`: `"11. **TDD and debugging discipline.** Follow Templates/TDD_AND_DEBUGGING.md for all coding. Delete code written before tests."`
- `Templates/compressed/BUILDER_HANDOFF_STANDARD.md:L14`: constraint list includes `"TDD discipline"`
- `Templates/AGENT_BUILD_PROCESS.yaml:L89-99`: 10 mandatory_constraints — "TDD and debugging discipline" absent

---

**C-9. BUILDER_PROMPT_CONTRACT.md compressed version diverges from full**

- `Templates/BUILDER_PROMPT_CONTRACT.md:L9`: has `## Version History` — compressed does NOT
- `Templates/compressed/BUILDER_PROMPT_CONTRACT.md`: has `## CRITICAL_REVIEW_REQUIRED (MANDATORY)` — full template does NOT have this as a standalone section (it exists only in `builder.md:L32`)

---

## Gaps (info in one path but not the other)

**G-1. DEPENDENCIES.yaml not reachable via human path (TechDocs)**

- Agent path: `.claude/agents/orchestrator.md:L104`: `"1. sawmill/DEPENDENCIES.yaml — what to build and in what order"`
- Human path: `mkdocs.yml` — no nav entry for DEPENDENCIES.yaml. Checked all 49 nav entries — NOT FOUND.

---

**G-2. Session resume pattern undocumented in human-facing docs**

- `sawmill/run.sh:L542`: `--output-format json | jq -r '.session_id'`
- `sawmill/run.sh:L584-594`: `--resume "$BUILDER_SESSION"`
- `docs/agent-onboarding.md:L305-324`: basic CLI examples only — no `--resume`, no session management
- `sawmill/COLD_START.md:L69`: documents `--resume` flag exists but does not show the Turn D pattern

---

**G-3. TDD_AND_DEBUGGING.md path missing `Templates/` prefix in agent-onboarding.md**

- `docs/agent-onboarding.md:L207`: `TDD["TDD_AND_DEBUGGING.md<br/>(HOW to code THIRD)"]` — no `Templates/` prefix
- `.claude/agents/builder.md:L13`: `"Templates/TDD_AND_DEBUGGING.md"` — has prefix
- `sawmill/run.sh:L530`: `"Templates/TDD_AND_DEBUGGING.md"` — has prefix

---

**G-4. No model directive for 3 of 5 pipeline roles**

- `.claude/agents/builder.md:L3`: `model: sonnet`
- `.claude/agents/evaluator.md:L3`: `model: opus`
- Checked `.claude/agents/orchestrator.md`, `spec-agent.md`, `holdout-agent.md` — no `model:` line in any

---

**G-5. CLAUDE.md sawmill directory structure omits 3 produced artifacts**

- `CLAUDE.md:L122-136`: lists TASK.md, D1-D6, D7, D8, D10, BUILDER_HANDOFF.md, RESULTS.md, EVALUATION_REPORT.md, EVALUATION_ERRORS.md
- Actual `sawmill/FMWK-001-ledger/` also contains: `13Q_ANSWERS.md`, `SOURCE_MATERIAL.md`, `GATE_CHECKLIST.md` — none listed

---

**G-6. BUILDER_PROMPT_CONTRACT.md uses `_staging/` — all other files use `staging/`**

- `Templates/BUILDER_PROMPT_CONTRACT.md:L129`: `"| [STAGING_PATH] | Build staging directory | _staging/ |"`
- `CLAUDE.md:L45`, `builder.md:L72`, `run.sh:L147`, `COLD_START.md:L196`: all use `staging/<FMWK-ID>/`

---

**G-7. Orphan files in docs/ not in mkdocs.yml nav**

- `docs/PORTAL_MAP.yaml` — used by portal-steward for validation
- `docs/validate_portal_map.py` — Python utility script
- `docs/PORTAL_TRUTH_MODEL.md` — `# Portal Truth Model` — documentation file, not in nav

---

**G-8. run.sh verdict grep pattern overly permissive**

- `sawmill/run.sh:L682`: `grep -qiE "Final\s*[Vv]erdict.*PASS"`
- `.claude/agents/evaluator.md:L77-79`: mandates exactly `"Final verdict: PASS"` or `"Final verdict: FAIL"`
- Risk: `.*PASS` would match `"Final verdict: FAIL — some tests PASS"`

---

## Stale Content (outdated counts, names, structures)

**S-1. docs/status.md: "4 agents" — repository has 7 defined roles**

- `docs/status.md:L15`: `"Sawmill Pipeline<br/>5-step process, 4 agents,<br/>templates, compression"`
- `.claude/agents/`: 7 role files

---

**S-2. COLD_START.md setup checklist: "all 4 role files" — actual is 7**

- `sawmill/COLD_START.md:L355`: `".claude/agents/ has all 4 role files (spec-agent, holdout-agent, builder, evaluator)"`
- `docs/sawmill/COLD_START.md:L355`: identical text (both synced, both stale)
- Actual: 7 files in `.claude/agents/`

---

**S-3. DEPENDENCIES.yaml omits FMWK-000 dependencies without documenting why**

- `architecture/BUILD-PLAN.md:L47`: `"FMWK-001 | ledger | Ledger | FMWK-000"`
- `architecture/BUILD-PLAN.md:L52`: `"FMWK-006 | package-lifecycle | ... | FMWK-001, FMWK-000"`
- `sawmill/DEPENDENCIES.yaml:L8`: `"FMWK-001-ledger: []"`
- `sawmill/DEPENDENCIES.yaml:L13`: `"FMWK-006-package-lifecycle: [FMWK-001-ledger]"`
- `sawmill/DEPENDENCIES.yaml:L2`: `"Source of truth: architecture/BUILD-PLAN.md"` — claims alignment but omits FMWK-000

Omission is systematic (FMWK-000 is GENESIS, not a pipeline framework), but undocumented.

---

**S-4. Backstage entity count unverifiable from this repo**

- `docs/status.md:L16`: `"17 entities, zero errors"`
- `catalog-info.yaml` (Brain_Factory): 1 entity (brain-factory Component)
- `/Users/raymondbruni/dopejar/catalog-info.yaml` and `platform_sdk/catalog-info.yaml`: exist on disk but content not readable from this audit session
- Prior validation (MEMORY.md, 2026-03-01) confirmed 17 entities — may be stale if catalogs changed since

---

## Confirmed Consistent

1. **KERNEL framework count**: 6 across `CLAUDE.md:L69`, `BUILD-PLAN.md:L43-54`, `DEPENDENCIES.yaml:L7-13`, `COLD_START.md:L116`, `agent-onboarding.md:L29`, `status.md:L159`. Same 6 IDs and names.

2. **Nine primitives**: identical across `CLAUDE.md:L51-63`, `AGENT_BOOTSTRAP.md:L31-46`. Same 9, same order.

3. **Handoff section count**: 13 across `Templates/BUILDER_HANDOFF_STANDARD.md` (sections 1-13), `Templates/compressed/BUILDER_HANDOFF_STANDARD.md:L12` ("ALL 13"), `Templates/AGENT_BUILD_PROCESS.yaml:L82-136` (sections 1-13).

4. **Orchestrator reading order**: consistent between `.claude/agents/orchestrator.md:L104-107` and `docs/agent-onboarding.md:L302-304`. Same 4 items, same order.

5. **Staging path**: `staging/<FMWK-ID>/` consistent across `CLAUDE.md:L45`, `builder.md:L72`, `run.sh:L147`, `COLD_START.md:L196`, `agent-onboarding.md:L368`.

6. **All mkdocs.yml nav targets exist**: 49/49 entries resolve to existing files in docs/.

7. **All authority documents exist**: 10/10 in architecture/.

8. **All agent role files exist**: 7/7 in .claude/agents/.

9. **All templates exist**: full 16/16, compressed 13/13.

10. **Entry point symlinks correct**: AGENTS.md → CLAUDE.md, GEMINI.md → CLAUDE.md (confirmed via `ls -la`).

11. **FMWK-001 artifact state matches status.md claims**: Turns A (D1-D6), B (D7, D8, D10, BUILDER_HANDOFF.md), C (D9 in .holdouts/) all present. 13Q_ANSWERS.md present. No RESULTS.md — consistent with Turn D not started.

12. **run.sh require_files match agent outputs**: Turn A checks D1-D6, Turn B checks D7/D8/D10/HANDOFF, Turn C checks D9 in .holdouts/, Turn D checks 13Q_ANSWERS.md and RESULTS.md, Turn E checks EVALUATION_REPORT.md.

13. **Holdout isolation enforced**: D9 exists only in `.holdouts/FMWK-001-ledger/`, not in `sawmill/FMWK-001-ledger/`.

14. **Model assignment consistent across source files**: builder.md `model: sonnet`, evaluator.md `model: opus`, agent-onboarding.md documents both at L202/L240, status.md decision log records at L164.

15. **Framework dependencies match (KERNEL-to-KERNEL)**: BUILD-PLAN.md and DEPENDENCIES.yaml agree on all inter-KERNEL dependencies. Only FMWK-000 (GENESIS) omission differs (see S-3).

16. **D1-D10 compressed templates synced**: 11 of 13 template pairs match. Only BUILDER_HANDOFF_STANDARD and BUILDER_PROMPT_CONTRACT diverge (see C-3, C-9).

17. **Architecture docs mirrors synced**: all 10 files in docs/architecture/ match their architecture/ sources.

18. **Builder reading order consistent across 4 sources**: `.claude/agents/builder.md:L11-15`, `sawmill/COLD_START.md:L183-188`, `sawmill/run.sh:L527-532`, `docs/agent-onboarding.md:L204-209` — all show 5 items: AGENT_BOOTSTRAP.md, D10, TDD_AND_DEBUGGING.md, BUILDER_HANDOFF.md, Section 7 files.

19. **5 of 7 agent role mirrors synced**: builder, spec-agent, holdout-agent, auditor, portal-steward docs copies match source. Evaluator and orchestrator diverge (C-1, C-2).

20. **COLD_START source and docs mirror synced**: `diff` shows zero differences.

---

## Summary

| Category | Count | Change from prior audit |
|----------|-------|------------------------|
| Critical findings | 9 | was 12, 3 fixed |
| Gaps | 8 | unchanged |
| Stale content | 4 | unchanged |
| Confirmed consistent | 20 | was 18, +2 new |

**Remaining drift pattern**: docs/ mirrors for evaluator.md (missing `model: opus`) and orchestrator.md (missing Dispatch Protocol section) still lag. docs/sawmill-templates/BUILDER_HANDOFF_STANDARD.md still shows 10 sections vs 13.

**Role count inflation still not propagated**: COLD_START setup checklist, run.sh preflight, agent-onboarding role table, and status.md still reference old counts (4 or 6 vs actual 7).
