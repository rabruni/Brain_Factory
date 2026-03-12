# READINESS-DECISION-2026-03-11-X001

**Date**: 2026-03-11 (re-verified 2026-03-12)
**Auditor**: Claude Opus 4.6 (automated, evidence-driven)
**Scope**: Is the pipeline still TOOLING_GOVERNANCE or has it advanced to EXECUTION_READINESS?
**Re-check result**: No change. All blocking conditions identical. `attempt` still missing from 3 prompts, `ATTEMPT` still not exported, 2/14 mock-only passes.

---

## 1. Decision

**STILL_TOOLING_GOVERNANCE**

---

## 2. Why

- The prompt-validator contract mismatch identified in CURRENT-STATE-READINESS-2026-03-11-X001 is **unfixed**. All three evidence prompt templates (`turn_d_build.txt`, `turn_d_review.txt`, `turn_e_eval.txt`) still omit `attempt` from the required evidence JSON schema. The validator (`validate_evidence_artifacts.py` lines 96, 160, 195) still requires it.
- `ATTEMPT` is still not exported in `run.sh`. Only `MAX_ATTEMPTS` appears in the export lists (lines 1036, 1790). The prompt renderer (`render_prompt.py`) uses environment variables; `{{ATTEMPT}}` cannot resolve.
- No new runs have passed since the last audit. 14 total runs: 2 passed (both mock), 12 failed. The 3 most recent codex runs all completed Turns A through D-build but failed at `EVIDENCE_VALIDATION_FAILED`.
- This is a governance-layer defect, not an agent-capability defect. The codex builder produces correct code, passing tests, and structurally valid evidence — but the evidence is rejected because of a field the prompt never asked for.
- Until this contract mismatch is fixed, every real run will fail at evidence validation regardless of agent quality, environment state, or framework target.

---

## 3. What is true now

| Area | Truth | Evidence |
|------|-------|----------|
| Agent capability | Codex completes Turns A-D build, writes code, tests pass | `runs/20260312T002821Z`: 8 log files, `builder_evidence.json` present, `staging/FMWK-900-sawmill-smoke/` has code |
| Evidence output | Builder produces valid JSON with 8 of 9 required fields | `builder_evidence.json`: has `run_id`, `handoff_hash`, `q13_answers_hash`, `behaviors`, `full_test_command`, `full_test_result`, `files_changed`, `results_hash` |
| Missing field | `attempt` absent from all evidence JSON | `python3 validate_evidence_artifacts.py ...` → `FAIL: missing required fields: attempt` |
| Prompt templates | 3 templates omit `attempt` | `grep -n attempt sawmill/prompts/turn_d_build.txt` → no matches |
| ATTEMPT env var | Not exported | `grep 'export.*ATTEMPT' run.sh` → only `MAX_ATTEMPTS` |
| Run history | 2/14 passed (mock only) | `status.json` survey: 2 passed, 12 failed |
| Mock path | Works end-to-end | Runs `20260311T212607Z`, `20260311T214837Z`: `state=passed` |
| FMWK-001 specs | D1-D10 + handoff complete | `ls sawmill/FMWK-001-ledger/` → 14 files |

---

## 4. What is not yet true

| Claim not yet true | Why | Evidence |
|-------------------|-----|----------|
| "Prompt and validator agree on evidence schema" | `attempt` missing from all 3 prompt templates; required by validator | `turn_d_build.txt:22-36` (8 fields) vs `validate_evidence_artifacts.py:90-104` (9 fields) |
| "ATTEMPT is available to the prompt renderer" | Not exported in run.sh | Lines 1036, 1790: export lists include `MAX_ATTEMPTS` but not `ATTEMPT` |
| "A real agent run has passed" | Contract mismatch causes every real run to fail | 12/12 non-mock runs: `state=failed` |
| "The pipeline is execution-ready" | Cannot pass evidence validation with any real backend | Blocked by above |

---

## 5. Backstage alignment

| Area | Match? | Defect if any | Evidence |
|------|--------|---------------|----------|
| Current State Readiness page | YES | Correctly identifies TOOLING_GOVERNANCE and the contract mismatch | Page live, content matches repo state |
| Pre-Execution Safety Audit | NO | States primary blocker is "agents cannot complete turn_a_spec"; actual blocker is evidence validation contract mismatch | Codex completes turn_a_spec in 3 recent runs |
| Source-of-Truth Audit | NO | States "No real agent has ever completed a Sawmill turn"; codex has completed turns A through D-build | Run logs for `20260312T002821Z` |
| FMWK-001 Readiness Audit | NO | States immudb port as 13322; actual is 3322 | `docker-compose.yml:89`, `config.py:47` |

---

## 6. One next readiness question

Does fixing the `attempt` field in the three prompt templates and exporting `ATTEMPT` in `run.sh` cause the canary to pass with a real backend?

---

## 7. Publish info
