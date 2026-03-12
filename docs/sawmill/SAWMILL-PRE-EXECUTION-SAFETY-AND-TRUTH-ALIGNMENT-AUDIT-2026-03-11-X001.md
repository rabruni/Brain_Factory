# SAWMILL-PRE-EXECUTION-SAFETY-AND-TRUTH-ALIGNMENT-AUDIT-2026-03-11-X001

**Date**: 2026-03-11
**Auditor**: Claude Opus 4.6 (automated, evidence-driven)
**Scope**: Sawmill pipeline readiness for first real (non-mock) execution against FMWK-001-ledger
**Method**: Filesystem evidence, Backstage page verification, run log analysis, registry cross-reference, runtime dependency checks, hook inspection, MD5 content verification

---

## 1. Executive truth

- **Real agent execution has been attempted and has failed every time.** 14 run directories exist. Codex failed 7 times, Claude failed 2 times, Gemini timed out 2 times. Only 2 mock runs passed. One run is currently executing. The pipeline is not "untested with real agents" — it is "tested with all three real backends and failing."
- **Early runs failed at turn_a_spec** (10 of 11 early failures). Later codex runs completed all turns A through D-build but failed at evidence validation (EVIDENCE_VALIDATION_FAILED) due to a prompt-validator schema mismatch — the `attempt` field is required by the validator but not listed in the prompt templates.
- **Three runtime dependencies are missing for FMWK-001**: immudb is not running (port 3322), grpcio is not installed, and PYTHONPATH is unset. These will cause hard fails during real execution if integration tests are in scope.
- **No SAWMILL_*_AGENT environment variables are set.** Without explicit overrides, all roles default to mock. A "real run" started without env vars silently becomes a mock run.
- **Backstage content is largely in sync with source truth.** MD5 verification shows FWK-0-DRAFT.md and all agent role files are content-identical between source and docs. Two sync mechanisms exist (pre-commit hook via sync_portal_mirrors.py + MkDocs hook via sync_docs.py). The primary truth-alignment defects are in published audit pages that contain factual claims already outdated by subsequent runs.
- **Safety guards are real and substantive.** Preflight checks, backend validation, freshness enforcement, evidence validation, timeout protection, max-attempt limits, and role-based file access control (Claude-only) all function. The `--from-turn D` invalidation mechanism correctly handles stale artifact cleanup.
- **Non-Claude backends lack hook-based guardrails.** sawmill-guard.sh only fires for Claude Code's PreToolUse. Codex and Gemini isolation is instruction-enforced only.
- **The real blocker is a prompt-validator contract mismatch**, not agent capability. Codex completes all turns and produces passing code, but evidence validation rejects the output because the prompt templates omit the `attempt` field that the validator requires. Claude CLI is not authenticated on this machine. Gemini times out.

---

## 2. Dirty floor inventory

| Risk area | What is dirty / unsafe / ambiguous | Why it matters | Severity | Evidence |
|-----------|-----------------------------------|----------------|----------|----------|
| Real backend failures | All 11 non-mock runs failed. Codex: 7 failures. Claude: 2 failures. Gemini: 2 timeouts. | The pipeline cannot produce output with any real backend. Fixing the environment won't help if agents can't complete Turn A. | CRITICAL | `status.json` in all 14 run dirs under `sawmill/FMWK-900-sawmill-smoke/runs/` |
| No backend env vars set | All `SAWMILL_*_AGENT` variables unset; every role defaults to mock | A "real run" without explicit env vars silently produces a mock run | HIGH | `env \| grep SAWMILL` returns nothing |
| Stale 13Q_ANSWERS.md | `sawmill/FMWK-001-ledger/13Q_ANSWERS.md` dated 2026-03-05 (6 days old) | Could be mistaken for fresh Turn D output; `--from-turn D` invalidates it but only if flag is used | HIGH | File mtime Mar 5 19:53 |
| immudb not running | Docker shows no immudb container; port 3322 not listening | FMWK-001 integration tests require immudb for non-mock LedgerProvider | HIGH | `docker ps` shows no immudb; only zitadel-db is running |
| PYTHONPATH unset | Neither dopejar nor Brain_Factory root on `sys.path` | `platform_sdk` imports fail outside dopejar CWD; staging imports fail entirely | HIGH | `echo $PYTHONPATH` empty |
| grpcio not installed | `python3 -c "import grpcio"` fails with ModuleNotFoundError | immudb gRPC client requires grpcio; blocks real immudb integration | HIGH | Python import test |
| PROMPT_RENDER_FAILED | Mock run `20260311T151450Z` failed at turn_d_review with PROMPT_RENDER_FAILED | Even the mock path has failed at prompt rendering; indicates a transient or fixed template bug | MEDIUM | `status.json` for run `20260311T151450Z-e2729fcb4880` |
| 14 run directories | `sawmill/FMWK-900-sawmill-smoke/runs/` contains 14 dirs with 2 passed, 11 failed, 1 running | Operator confusion: which run is authoritative? Mixed states obscure pipeline health | MEDIUM | `ls sawmill/FMWK-900-sawmill-smoke/runs/` |
| Currently running execution | Run `20260312T002821Z` is `state: running`, codex backend, turn_a_spec | Active pipeline execution may conflict with manual operations or this audit | MEDIUM | `status.json` for run `20260312T002821Z-79f2f773ca6d` |
| BUILDER_HANDOFF.md age | `sawmill/FMWK-001-ledger/BUILDER_HANDOFF.md` dated 2026-03-01 (10 days old) | Turn B input; correctly survives `--from-turn D`. Content valid if D1-D10 haven't changed since generation. | LOW | File mtime Mar 1 22:04 |
| Missing serializer.py | `test_serializer.py` imports `ledger.serializer` which doesn't exist in staging | Pre-existing test references module builder must create; not a safety issue | LOW | `test_serializer.py` line 8 |
| Empty staging scaffold dirs | `platform_sdk/tier0_core/data/`, `scripts/`, `tests/integration/` are empty | Scaffolding noise from prior attempt | LOW | Directory listing |
| Session logs | `SESSION_LOG_2026-03-11.md`, `SESSION_2026-03-07.md` in sawmill/ | Operational noise; not consumed by pipeline | LOW | File listing |

---

## 3. Backstage truth-alignment defects

| Area | Backstage shows | Source/runtime truth shows | Authoritative source | Defect | Exact fix | Evidence |
|------|----------------|---------------------------|---------------------|--------|-----------|----------|
| Agent execution history | Published audits state "No real agent has ever completed a Sawmill turn through run.sh" | 11 real-backend runs attempted (codex x7, claude x2, gemini x2); all failed | Run logs (`status.json` per run) | Audits understate reality — real agents were attempted and failed, not merely "untested" | Update audit language to "Real agent execution has been attempted with all three backends and has failed every time" | All 14 run status.json files |
| Canary run count | Published audits cite "11 canary runs" | 14 run directories exist (2 passed, 11 failed, 1 running) | Filesystem (`runs/` listing) | Run count outdated within hours of publication | Note snapshot date in published audits or make count dynamic | `ls runs/` count |
| Latest canary status | RUN_VERIFICATION cites passing run `20260311T212607Z` as evidence | 5 subsequent runs all failed (4 codex, 1 claude); 1 currently running | Latest `status.json` files | Page creates false confidence by citing a passing run without noting subsequent failures | Add note that later runs with real backends failed, or timestamp the evidence claim | Chronological run comparison |
| immudb port | FMWK-001 Readiness Audit references "port 13322" | docker-compose.yml maps `3322:3322`; SDK `config.py` defaults to `immudb_port=3322` | `docker-compose.yml` line 89; `config.py` line 47 | Wrong port number in published audit | Fix to 3322 in FMWK-001-READINESS-AUDIT.md | Port comparison |
| ROLE_REGISTRY page | Shows metadata about registry; does not display any role/backend content | ROLE_REGISTRY.yaml has 8 roles with backends, policies, env overrides | Source YAML | Page is opaque — reader cannot verify registry content from Backstage alone | Either inline rendered registry content or note "inspect source file directly" | Backstage page content |
| PORTAL_MAP sync mechanism | PORTAL_MAP declares 29 `sync: mirror` entries | sync_docs.py handles only architecture/ and Templates/; pre-commit hook via sync_portal_mirrors.py handles all PORTAL_MAP mirrors on commit | Both mechanisms (pre-commit for commit-time, sync_docs.py for build-time) | No defect in content sync; documentation gap about which mechanism handles which mirrors | Document the two-mechanism model in PORTAL_MAP.yaml or an adjacent note | PORTAL_MAP.yaml, sync_docs.py SYNC_MAP, .githooks/pre-commit |
| FWK-0-DRAFT.md staleness | Source-of-Truth audit claims "11 days stale" based on mtime | MD5 hashes match: content is identical. Mtime differs because source was modified then reverted to same content | MD5 verification | Published audit has a false finding — file content IS in sync despite mtime difference | Correct the audit claim or note that mtime-based staleness detection produces false positives when files are reverted | `md5 -q` output: both `83e60d15539b34d5fb96f3f02ae159f3` |
| orchestrator.md presence | Source-of-Truth audit implies agents/ not auto-synced | orchestrator.md IS present in docs/agents/ with identical MD5 (`7ce490...`) to source | MD5 verification | Published audit creates impression of sync gap that doesn't exist | Correct audit finding | `md5 -q` output: both `7ce4908065243ca02c70d89eb275c74c` |

---

## 4. Safety guards already present

| Guardrail | What it protects against | Is it real? | Evidence |
|-----------|------------------------|-------------|----------|
| sawmill-guard.sh (PreToolUse hook) | Write/Edit operations outside role's file-ownership allowlist | YES — Claude backend only | `.claude/settings.json`; role-specific allowlists in hook |
| sawmill-state.sh (PreToolUse hook) | Orchestrator operating without pipeline state awareness | YES — Claude backend only | Injects `[PIPELINE STATE]` block |
| sawmill-stop.sh (Stop hook) | Orchestrator quitting with TASK.md but no downstream output | YES — Claude backend only | Blocks stop when dispatch incomplete |
| Preflight checks (run.sh) | Missing registries, CLIs, invalid timeout | YES — all backends | Lines 1819-1856; exits PREFLIGHT_MISSING_FILE or PREFLIGHT_MISSING_CLI |
| Backend validation (run.sh) | Backend not in `allowed_backends` for role | YES — all backends | `validate_selected_backend()` exits on invalid |
| CLI availability check (run.sh) | Backend CLI not installed | YES — all backends | `require_backend_cli()` calls `command -v` |
| Freshness policy (run.sh) | Stale outputs mistaken for fresh | YES — all backends | Sentinel written before agent runs; output must be newer |
| Evidence validation (run.sh) | Invalid evidence JSON structure | YES — all backends | `validate_evidence_artifacts.py` checks fields |
| Timeout mechanism (run.sh) | Runaway agent execution | YES — all backends | Default 1800s; exit 124 = AGENT_TIMEOUT |
| Max attempts (run.sh) | Infinite retry loops in Turn D/E | YES — all backends | MAX_ATTEMPTS=3 |
| `--from-turn D` invalidation | Stale D/E artifacts contaminating fresh run | YES — all backends | `invalidate_downstream_artifacts()` deletes all stage-D and stage-E artifacts |
| Holdout isolation (instruction + hook) | Builder reading acceptance tests | PARTIAL — hook-enforced for Claude only; instruction-enforced for Codex/Gemini | Builder role file + sawmill-guard.sh excludes `.holdouts/` |
| Evaluator isolation (instruction only) | Evaluator reading builder reasoning or specs | INSTRUCTION ONLY — no hook enforcement for any backend | Evaluator role file says "MUST NOT read" but no guard exists |
| Verdict parsing (run.sh) | Unparseable verdict line causing silent pass | YES — UNKNOWN triggers retry/escalate, never silent pass | `review_verdict()` and `evaluation_verdict()` regex; UNKNOWN escalates after MAX_ATTEMPTS |
| Pre-commit mirror sync | Source/docs divergence on commit | YES — for all PORTAL_MAP mirror entries | `.githooks/pre-commit` calls `sync_portal_mirrors.py` |

---

## 5. Required cleanup before first real run

1. **Diagnose why real agents fail at turn_a_spec.** This is the primary blocker. 10 of 11 failures occur at the very first turn. Read the stderr logs for a representative failure (e.g., `sawmill/FMWK-900-sawmill-smoke/runs/20260311T214918Z-eff7db0bedee/logs/turn_a_spec.stderr.log` for Claude, or `20260311T024504Z-19983a217182/logs/turn_a_spec.stderr.log` for Codex). The root cause may be: CLI authentication, prompt too large, role file not found, or agent capability gap. Until Turn A works with at least one real backend, no downstream turn will ever execute.

2. **Set backend environment variables explicitly before invoking run.sh:**
   ```
   export SAWMILL_BUILD_AGENT=claude
   export SAWMILL_REVIEW_AGENT=claude
   export SAWMILL_EVAL_AGENT=claude
   ```
   Without these, all roles default to mock. Consider whether spec-agent and holdout-agent should also use real backends or if `--from-turn D` makes this moot.

3. **Use `--from-turn D` to invalidate stale Turn D artifacts.** The stale `13Q_ANSWERS.md` (Mar 5) will be deleted. `BUILDER_HANDOFF.md` (Mar 1, Turn B output) correctly survives as input. Command: `./sawmill/run.sh FMWK-001-ledger --from-turn D`.

4. **Set PYTHONPATH before run:**
   ```
   export PYTHONPATH=/Users/raymondbruni/dopejar:$PYTHONPATH
   ```
   Verify: `python3 -c "from platform_sdk.tier0_core.errors import PlatformError; print('OK')"`. This must succeed before the builder agent can compile imports.

5. **Decide on immudb availability.** If FMWK-001 Turn D unit tests use mock storage (no live immudb), this can wait until Turn E holdout evaluation. If integration tests need a real connection: `cd /Users/raymondbruni/dopejar && docker compose up -d immudb` and `pip3 install grpcio`.

6. **Ensure no conflicting run is active.** Run `20260312T002821Z` shows `state: running`. Either wait for it to complete/fail or verify it is against FMWK-900 (canary) and won't conflict with an FMWK-001 run.

7. **Fix immudb port reference in FMWK-001-READINESS-AUDIT.md.** Change `13322` to `3322` (docker-compose.yml line 89: `"3322:3322"`; SDK config.py line 47: `immudb_port=3322`).

---

## 6. What can wait until after first real run

1. **Canary run directory cleanup** — 14 run dirs are operational records; don't affect FMWK-001.
2. **Published audit text corrections** — run counts, agent-execution history, FWK-0-DRAFT staleness claim. All factually outdated but don't affect pipeline execution.
3. **ROLE_REGISTRY Backstage page content rendering** — page is opaque but source YAML is correct and authoritative.
4. **Session log removal** — `SESSION_LOG_2026-03-11.md` is informational, not consumed by pipeline.
5. **PORTAL_MAP sync mechanism documentation** — the two-mechanism model works; explaining it is polish.
6. **Evaluator hook enforcement** — isolation is instruction-only. Adding a hook would strengthen it but is not blocking.
7. **Python version upgrade** — 3.9.6 is old but functional.
8. **Empty staging scaffold directories** — harmless; `--from-turn D` may clean them.
9. **Uncommitted dopejar changes** — Backstage-related (app-config.yaml, package.json), not pipeline-related.

---

## 7. Go / No-Go checklist

- [ ] Root cause of turn_a_spec failures identified (read stderr logs for at least one codex and one claude failure)
- [ ] At least one real backend can complete turn_a_spec on the canary (FMWK-900) before attempting FMWK-001
- [ ] `SAWMILL_BUILD_AGENT` set to a real backend (`claude` / `codex` / `gemini`)
- [ ] `SAWMILL_REVIEW_AGENT` set to a real backend
- [ ] `SAWMILL_EVAL_AGENT` set to a real backend
- [ ] `PYTHONPATH` includes `/Users/raymondbruni/dopejar`
- [ ] `python3 -c "from platform_sdk.tier0_core.errors import PlatformError"` succeeds
- [ ] `--from-turn D` flag will be used (confirmed stale 13Q invalidation)
- [ ] immudb availability decision made: needed for Turn D unit tests or deferred to Turn E?
- [ ] grpcio availability decision made: needed now or deferred?
- [ ] No conflicting active run (check `state` in latest run's `status.json`)
- [ ] Operator understands non-Claude backends lack hook-based file ownership guards
- [ ] Operator understands Bash tool can bypass sawmill-guard.sh even for Claude
- [ ] immudb port reference corrected from 13322 to 3322 in FMWK-001-READINESS-AUDIT.md

---

## 8. Final judgment

**NO-GO**

The environment can be cleaned up in under an hour (items 2-7 in Required Cleanup). The primary blocker is a **prompt-validator contract mismatch**: the evidence validator requires an `attempt` field that the prompt templates do not list, and `ATTEMPT` is not exported as an environment variable for the renderer. Codex has demonstrated it can complete all turns A through D-build and produce passing code — the agent capability is proven. Once the contract mismatch is resolved, the minimum path to GO is: (1) set backend env vars and PYTHONPATH, (2) run the canary with a real backend, (3) if it passes, attempt `./sawmill/run.sh FMWK-001-ledger --from-turn D`. Claude CLI must be authenticated separately (`/login`). Gemini timeout may require investigation.

---

## Appendix A: Complete run history

| Run ID | Backend | Failed at | Failure code | State |
|--------|---------|-----------|--------------|-------|
| `20260311T024504Z` | codex | turn_a_spec | AGENT_EXIT_NONZERO | failed |
| `20260311T024549Z` | codex | turn_a_spec | AGENT_EXIT_NONZERO | failed |
| `20260311T030459Z` | claude | turn_a_spec | AGENT_EXIT_NONZERO | failed |
| `20260311T031741Z` | gemini | turn_a_spec | AGENT_TIMEOUT | failed |
| `20260311T053702Z` | gemini | turn_a_spec | AGENT_TIMEOUT | failed |
| `20260311T055132Z` | codex | portal_stage | AGENT_EXIT_NONZERO | failed |
| `20260311T151450Z` | mock | turn_d_review | PROMPT_RENDER_FAILED | failed |
| `20260311T212607Z` | mock | (completed) | none | **passed** |
| `20260311T214837Z` | mock | (completed) | none | **passed** |
| `20260311T214918Z` | claude | turn_a_spec | AGENT_EXIT_NONZERO | failed |
| `20260311T221131Z` | codex | turn_a_spec | AGENT_EXIT_NONZERO | failed |
| `20260311T232927Z` | codex | turn_d_build | EVIDENCE_VALIDATION_FAILED | failed |
| `20260311T235243Z` | codex | turn_d_build | EVIDENCE_VALIDATION_FAILED | failed |
| `20260312T002821Z` | codex | turn_a_spec | (in progress) | **running** |

**Summary**: 14 runs. 2 passed (both mock). 11 failed (7 codex, 2 claude, 1 gemini, 1 mock). 1 running (codex).

---

## Appendix B: Evidence sources

| Evidence | Path / Command |
|----------|---------------|
| All run statuses | `sawmill/FMWK-900-sawmill-smoke/runs/*/status.json` |
| run.sh line count | `wc -l sawmill/run.sh` → 2,218 |
| immudb port (docker) | `docker-compose.yml` line 89: `"3322:3322"` |
| immudb port (SDK) | `platform_sdk/tier0_core/config.py` line 47: `immudb_port=3322` |
| FWK-0-DRAFT.md sync | `md5 -q` both copies → `83e60d15539b34d5fb96f3f02ae159f3` |
| orchestrator.md sync | `md5 -q` both copies → `7ce4908065243ca02c70d89eb275c74c` |
| Docker status | `docker compose ps` → only zitadel-db running |
| Python version | `python3 --version` → 3.9.6 |
| grpcio missing | `python3 -c "import grpcio"` → ModuleNotFoundError |
| PYTHONPATH | `echo $PYTHONPATH` → empty |
| Env vars | `env \| grep SAWMILL` → nothing |
| CLI tools | `which claude` → present (v2.1.73); `which codex` → present; `which gemini` → present |
| 13Q staleness | `stat` mtime → Mar 5 19:53 |
| BUILDER_HANDOFF age | `stat` mtime → Mar 1 22:04 |
| Pre-commit hook | `.githooks/pre-commit` → calls `sync_portal_mirrors.py` |
| sync_docs.py SYNC_MAP | `hooks/sync_docs.py` line 28-31 → architecture/ and Templates/ only |
| Backstage pages | 9 pages verified via WebFetch (all returned 200) |
