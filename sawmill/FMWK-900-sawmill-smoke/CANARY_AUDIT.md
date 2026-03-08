# Canary Audit — FMWK-900-sawmill-smoke

Stage: Post-verification
Date: 2026-03-08T03:24:02Z
Pass: 30
Fail: 0

## Results

| Status | Check |
|--------|-------|
| PASS | Status page exists |
| PASS | mkdocs.yml refs FMWK |
| PASS | PORTAL_MAP refs FMWK |
| PASS | D1 |
| PASS | D2 |
| PASS | D3 |
| PASS | D4 |
| PASS | D5 |
| PASS | D6 |
| PASS | Portal: A DONE |
| PASS | D7 |
| PASS | D8 |
| PASS | D10 |
| PASS | Handoff |
| PASS | Portal: B DONE |
| PASS | D9 |
| PASS | Portal: C DONE |
| PASS | RESULTS |
| PASS | staging |
| PASS | Portal: D DONE |
| PASS | EVAL_REPORT |
| PASS | Portal: E PASS |
| PASS | Portal→D1 |
| PASS | Portal→D6 |
| PASS | Portal→D7 |
| PASS | Portal→Handoff |
| PASS | Portal→D9 |
| PASS | Portal→RESULTS |
| PASS | Portal→staging |
| PASS | Portal→EVAL |

## Limitation: Guard Hook Coverage

This canary used Codex agents (gpt-5.4) instead of Claude agents because Claude
cannot spawn nested Claude sessions inside Claude Code (CLAUDECODE env var / exit 137).

Codex agents comply with role write restrictions via instructions only — they do not
trigger Claude Code hooks. The `sawmill-guard.sh` PreToolUse hook, which enforces
per-role file ownership (e.g. builder can only write to `staging/` and `sawmill/*/RESULTS.md`),
only fires when agents use Claude's Write/Edit tools.

**What this canary verified:**
- Pipeline orchestration (run.sh dispatches 5 turns in order, gates between them)
- Artifact generation (real agents produced D1-D10, code, holdouts, evaluation)
- Portal synchronization (status page updated mechanically after each stage)
- Audit enforcement (forward + reverse consistency checks, failure detection on missing artifacts)

**What this canary did NOT verify:**
- Guard hook enforcement (`sawmill-guard.sh` role-based write restrictions)

To verify guard hooks, run the canary with Claude agents (`SAWMILL_SPEC_AGENT=claude`
etc.) from a terminal outside Claude Code, or add a dedicated hook-enforcement test
that invokes `sawmill-guard.sh` directly with simulated tool inputs per role.

## Verdict

**PASS** — all 30 checks passed
