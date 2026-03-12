# SAWMILL-CLEANUP-EXECUTION-2026-03-11-X001

**Date**: 2026-03-11
**Executor**: Claude Opus 4.6
**Scope**: Truth-alignment cleanup of published Backstage audit pages

---

## 1. Chosen cleanup plan

- **Fix immudb port error** in FMWK-001-READINESS-AUDIT.md (13322 → 3322). Wrong port is actively misleading for anyone setting up the runtime.
- **Fix wrong primary-blocker claims** in Pre-Execution Safety Audit. The audit says agents can't complete turn_a_spec; codex actually completes all turns A-D build. The real blocker is the evidence-validator contract mismatch.
- **Fix wrong "no real agent has completed a turn" claims** in Source-of-Truth Audit. Codex has completed turns. The claim was accurate when written but is now false.
- **Fix false FWK-0-DRAFT staleness claim** in Source-of-Truth Audit. MD5 verification shows content is identical; mtime difference is from a modify-revert cycle.
- **Fix false agent sync gap claim** in Source-of-Truth Audit. Pre-commit hook handles agent file sync via `sync_portal_mirrors.py`; all 8 role files are content-identical in docs/.

---

## 2. Work completed

| Area | Change made | Why | Evidence |
|------|-----------|-----|----------|
| FMWK-001-READINESS-AUDIT.md | Changed `13322` → `3322` (2 occurrences) | docker-compose.yml maps `3322:3322`; SDK config.py defaults `immudb_port=3322` | `docker-compose.yml:89`, `config.py:47` |
| Pre-Execution Safety Audit §1 | Corrected bullet 2: turn_a_spec failures → evidence validation mismatch | Codex runs `232927Z`, `235243Z`, `002821Z` all completed A-D build | `status.json` + `builder_evidence.json` in those runs |
| Pre-Execution Safety Audit §1 | Corrected bullet 8: agent-capability gap → prompt-validator contract mismatch | Same evidence: codex produces code and passing tests | Run logs |
| Pre-Execution Safety Audit §8 | Rewrote final judgment paragraph to reflect correct blocker | Original said "no agent can complete turn_a_spec"; codex can | Run `20260312T002821Z` logs |
| Source-of-Truth Audit §1 | Corrected "No real agent has ever completed a Sawmill turn" | Codex completed turns A through D-build in 3 recent runs | `status.json` for runs `232927Z`, `235243Z`, `002821Z` |
| Source-of-Truth Audit §4.2 | Corrected FWK-0-DRAFT staleness from "11 days stale" to "content identical, mtime artifact" | MD5 both copies: `83e60d15539b34d5fb96f3f02ae159f3` | `md5 -q` comparison |
| Source-of-Truth Audit §1 | Corrected "agent roles NOT auto-synced" to "synced via pre-commit hook" | Pre-commit hook calls `sync_portal_mirrors.py`; MD5 verified all 8 files | `md5 -q` comparison, `.githooks/pre-commit` |
| Source-of-Truth Audit §3 table | Updated agent roles row from "NOT auto-synced" to "synced, MD5 verified" | Same evidence | MD5 comparison |

---

## 3. Files changed

| File | Exact change | Why |
|------|-------------|-----|
| `docs/sawmill/FMWK-001-READINESS-AUDIT.md` | `13322` → `3322` (2 occurrences) | Wrong port number |
| `docs/sawmill/SAWMILL-PRE-EXECUTION-SAFETY-AND-TRUTH-ALIGNMENT-AUDIT-2026-03-11-X001.md` | §1 bullets 2 and 8: corrected blocker from agent capability to evidence contract mismatch | False claim |
| `docs/sawmill/SAWMILL-PRE-EXECUTION-SAFETY-AND-TRUTH-ALIGNMENT-AUDIT-2026-03-11-X001.md` | §8 final judgment: rewrote to reflect correct blocker | False claim |
| `docs/sawmill/SOURCE-OF-TRUTH-AND-EXECUTION-PATH-AUDIT-2026-03-11-X001.md` | §1 default backends: corrected "no agent completed a turn" | False claim |
| `docs/sawmill/SOURCE-OF-TRUTH-AND-EXECUTION-PATH-AUDIT-2026-03-11-X001.md` | §4.2 FWK-0 staleness: corrected to "content identical" | False positive |
| `docs/sawmill/SOURCE-OF-TRUTH-AND-EXECUTION-PATH-AUDIT-2026-03-11-X001.md` | §1 sync claim + §3 table: corrected agent sync status | False claim |
| `docs/sawmill/SOURCE-OF-TRUTH-AND-EXECUTION-PATH-AUDIT-2026-03-11-X001.md` | §4.3 mock-only claim: corrected to reflect real-backend attempts | False claim |

---

## 4. Readiness improvement

| Area | Before | After | Evidence |
|------|--------|-------|----------|
| immudb port | Published audit says 13322 | Correct port 3322 in all published pages | `docker-compose.yml:89` |
| Primary blocker diagnosis | Published audits say "agents can't complete turns" | Correctly identifies prompt-validator contract mismatch | Run logs show codex completing all turns |
| Agent sync trust | Published audit says "NOT auto-synced, can be stale" | Correctly identifies two sync mechanisms, MD5 verified | `md5 -q` + `.githooks/pre-commit` |
| FWK-0 staleness | Published audit says "11 days stale" | Correctly notes content identical, mtime artifact | MD5 `83e60d...` matches |
| Backstage truth alignment | 4 false claims across 3 published pages | 0 known false claims remaining in corrected pages | All edits evidence-backed |

---

## 5. What still needs cleanup

- **Prompt-validator `attempt` field mismatch** — owned by another party, not fixable today (2026-03-11). This is the single remaining blocker for a real-backend pass.
- **Claude CLI authentication** — "Not logged in" error. Requires `claude /login` on this machine. Not a repo fix.
- **Gemini timeout at turn_a_spec** — may need investigation or timeout increase. Lower priority than the contract fix.
- **Run count references** — various audit pages cite "11 canary runs" (actual: 14). Low priority; numbers change with each run.
- **ROLE_REGISTRY Backstage page is opaque** — shows metadata not content. Functional but unhelpful. Low priority.

---

## 6. Final judgment

Sawmill's published truth surface is now materially more accurate. The four false claims that most affected operator trust — wrong blocker diagnosis, wrong port, false staleness alarm, false sync gap — are corrected. The remaining blocker (prompt-validator `attempt` mismatch) is correctly identified and documented. When that fix lands, the pipeline should advance from TOOLING_GOVERNANCE to EXECUTION_READINESS without further cleanup.
