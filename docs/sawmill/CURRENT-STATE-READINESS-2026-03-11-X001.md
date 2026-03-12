# CURRENT-STATE-READINESS-2026-03-11-X001

**Date**: 2026-03-11
**Auditor**: Claude Opus 4.6 (automated, evidence-driven)
**Scope**: Current state of Brain Factory / Sawmill readiness for first real build
**Method**: Run log analysis, validator testing, prompt-validator contract comparison, runtime checks

---

## 1. Executive truth

- **Codex can complete Turns A through D-build for the canary.** Three recent runs (20260311T232927Z, 20260311T235243Z, 20260312T002821Z) completed spec, plan, holdout, 13Q, review, and build. Builder wrote code, tests passed, evidence JSON was produced. All three failed at evidence validation — not at agent capability.
- **Every real run fails because of a one-field contract mismatch.** The evidence validator (`validate_evidence_artifacts.py`) requires an `attempt` field. The prompt templates (`turn_d_build.txt`, `turn_d_review.txt`, `turn_e_eval.txt`) do not list it. The `ATTEMPT` variable is not exported to the environment for the renderer. Every real builder, reviewer, and evaluator evidence artifact will fail validation.
- **Claude backend fails at authentication** ("Not logged in · Please run /login" — `turn_a_spec.attempt1.stdout.log` for run `20260311T214918Z`). Gemini backend times out at turn_a_spec (1800s).
- **Environment gaps remain**: PYTHONPATH unset, immudb not running, grpcio not installed, no `SAWMILL_*_AGENT` env vars set. These are secondary to the contract mismatch but block FMWK-001.
- **Mock runs pass.** 2 of 14 runs passed, both with mock backend (`20260311T212607Z`, `20260311T214837Z`).

---

## 2. Current state

| Area | Current truth | Evidence |
|------|--------------|----------|
| Canary codex completion | Codex completes Turns A-D build (code written, tests pass) | `runs/20260312T002821Z/logs/`: 8 log files, turn_d_build.stdout.log = 124KB, builder_evidence.json exists with valid structure |
| Evidence validation | Fails for ALL real runs — missing `attempt` field in evidence JSON | `python3 validate_evidence_artifacts.py --kind builder ...` → `FAIL: missing required fields: attempt` |
| Prompt-validator contract | 3 prompt templates list evidence schemas WITHOUT `attempt`; validator requires it for all 3 roles | `turn_d_build.txt` lines 22-36 (8 fields); `validate_evidence_artifacts.py` line 90-104 (9 fields) |
| ATTEMPT env var | Not exported; renderer cannot substitute `{{ATTEMPT}}` | `run.sh` exports `MAX_ATTEMPTS` (line 1036) but not `ATTEMPT` |
| Claude backend | Not authenticated on this machine | Run `20260311T214918Z` stdout: "Not logged in · Please run /login" |
| Gemini backend | Times out at 1800s on turn_a_spec | Runs `20260311T031741Z`, `20260311T053702Z`: `AGENT_TIMEOUT` |
| Mock backend | Works end-to-end | 2 passing runs: `20260311T212607Z`, `20260311T214837Z` |
| FMWK-001 staging | 33-line stub (`ledger.py`), 374 lines total, 8/16 files | `staging/FMWK-001-ledger/ledger/ledger.py`: all NotImplementedError |
| FMWK-001 specs | D1-D10 + handoff complete, 13Q stale (Mar 5) | `sawmill/FMWK-001-ledger/`: 14 files present |
| Runtime deps | PYTHONPATH unset, immudb down, grpcio missing | `echo $PYTHONPATH` → empty; `docker ps` → no immudb; `import grpcio` → ModuleNotFoundError |
| Total runs | 14 dirs: 2 passed (mock), 11 failed (7 codex, 2 claude, 2 gemini), 1 just completed (codex, failed) | `sawmill/FMWK-900-sawmill-smoke/runs/*/status.json` |

---

## 3. Primary readiness category

**TOOLING_GOVERNANCE**

- The pipeline machinery works. The agent (codex) can complete all turns and produce valid code. The failure is in the governance layer: the evidence validator rejects valid output because the prompt template doesn't tell the agent to include a field the validator requires.
- This is a contract mismatch between two pipeline components, not an agent capability problem, not an environment problem, and not a design problem.
- Fixing it requires changes to 3 prompt templates (add `attempt` field) and 1 line in `run.sh` (export `ATTEMPT`).

---

## 4. What is still not true

| Claim we still cannot make | Why not | Evidence |
|---------------------------|---------|----------|
| "A real run has passed end-to-end" | Evidence validation rejects all real output due to missing `attempt` field | All 11 non-mock runs: `state=failed` |
| "The evidence contract is internally consistent" | Prompt templates specify 8 fields (builder), 7 fields (reviewer), 6 fields (evaluator); validator requires 9, 8, 7 respectively — `attempt` missing from all three | `turn_d_build.txt:22-36` vs `validate_evidence_artifacts.py:90-104` |
| "Claude is a viable backend right now" | CLI not authenticated | Run `20260311T214918Z` stdout: "Not logged in" |
| "Gemini is a viable backend right now" | Times out at 1800s on turn_a_spec | Runs `20260311T031741Z`, `20260311T053702Z` |
| "FMWK-001 environment is ready" | PYTHONPATH unset, immudb down, grpcio missing | Runtime checks |
| "Turn E can pass" | Turn E evaluator evidence also requires `attempt` (validator line 195); same contract mismatch applies | `turn_e_eval.txt:17-27` vs `validate_evidence_artifacts.py:188-203` |

---

## 5. Backstage alignment check

| Area | Backstage matches truth? | Defect if any | Exact fix | Evidence |
|------|------------------------|---------------|-----------|----------|
| Pre-Execution Safety Audit | NO | States "NO-GO" with primary blocker as "agents cannot complete turn_a_spec." In fact, codex completes all turns; the blocker is evidence validation, not agent capability. | Update §1 and §8 to reflect that the blocker is the prompt-validator contract mismatch, not agent capability | Run `20260312T002821Z` completed A through D-build |
| FMWK-001 Readiness Audit | NO | States immudb port as 13322 | Change to 3322 | `docker-compose.yml` line 89: `"3322:3322"`; `config.py` line 47: `immudb_port=3322` |
| Source-of-Truth Audit | NO | States "No real agent has ever completed a Sawmill turn through run.sh" | Real agents (codex) have completed turns A, B, C, D-13Q, D-review, and D-build. They fail at evidence validation, not at turn execution. | Run logs show 8 completed steps |
| FWK-0-DRAFT.md sync | YES | Content identical (MD5: `83e60d...`). Mtime differs but content matches. | None needed | `md5 -q` both copies |
| Agent role files sync | YES | All 8 files present in docs/agents/ with matching MD5 | None needed | `md5 -q` comparisons |
| Run count in audits | NO | Published audits cite "11 canary runs"; actual count is 14 | Update or note snapshot date | `ls runs/` |

---

## 6. One next constrained move

**Fix the prompt-validator contract mismatch.**

Three changes, all in this repo:

1. In `sawmill/run.sh`: add `ATTEMPT` to the export list alongside `MAX_ATTEMPTS` (line 1036 and line 1790).
2. In `sawmill/prompts/turn_d_build.txt`: add `- attempt: {{ATTEMPT}}` to the evidence JSON schema (after line 23, the `run_id` field).
3. In `sawmill/prompts/turn_d_review.txt`: add `- attempt: {{ATTEMPT}}` to the evidence JSON schema (after line 26).
4. In `sawmill/prompts/turn_e_eval.txt`: add `- attempt: {{ATTEMPT}}` to the evidence JSON schema (after line 18).

Then re-run the canary with a real backend: `SAWMILL_BUILD_AGENT=codex ./sawmill/run.sh FMWK-900-sawmill-smoke`.

If it passes, the pipeline is unblocked for FMWK-001.

---

## 7. What to ignore right now

- Environment setup (PYTHONPATH, immudb, grpcio) — only matters for FMWK-001, not the canary contract fix.
- Claude and Gemini backend issues — codex works; fix the contract first.
- Published audit text corrections — factual drift in pages doesn't block the fix.
- Stale 13Q_ANSWERS.md in FMWK-001 — `--from-turn D` handles it; irrelevant until canary passes.
- PORTAL_MAP sync mechanism documentation — portal content is in sync; explaining the mechanism is polish.
