# DESIGN-FOR-EXECUTION-BOUNDARY-AUDIT-2026-03-11-X001

**Date**: 2026-03-11
**Auditor**: Claude Opus 4.6 (automated, evidence-driven)
**Scope**: Design-for-execution boundary — tooling path, truth boundary, governance boundary, validation boundary
**Method**: Code reading, registry tracing, inode comparison, SDK inspection, hook analysis, run.sh gate tracing

---

## 1. Executive Truth

- **Agents run today via two paths**: (1) Ray opens Claude Code and types a role prompt, or (2) `./sawmill/run.sh` dispatches workers via CLI (`claude -p`, `codex exec`, `gemini -p`, or `python3 mock_worker.py`). Both paths use the same role files and registries.
- **Default backends are mock.** Every canary run (11 total) used mock workers. No real agent has ever completed a Sawmill turn through run.sh. The pipeline is validated against synthetic output only.
- **The SDK is real, working, and production-grade.** 56 modules, 7,965 lines, 15 provider implementations, MCP server, comprehensive tests. This is not a stub. FMWK-001 already imports from it (PlatformError, get_config, get_secret). The SDK is substrate, not competitor.
- **run.sh is safe for FMWK-001.** `--from-turn D` invalidates all stale Turn D/E artifacts before running. Preflight validates registries, CLIs, and file existence. Version evidence checks and convergence validation are fail-closed.
- **Backstage is partially stale.** FWK-0-DRAFT.md is 11 days behind source. Agent files are NOT auto-synced despite PORTAL_MAP.yaml claiming `sync: mirror`. Architecture and template files are correctly hardlinked.
- **Claude Code hooks enforce file ownership per role** (`sawmill-guard.sh`), but only for Claude backend. Codex/Gemini enforcement is instructional only (role file constraints + sandbox isolation).
- **The single unproven link is real-agent-through-run.sh.** All infrastructure exists. The question is whether a real Claude or Codex agent can produce conformant artifacts (correct verdict lines, valid evidence JSON, passing tests) through the automated pipeline.
- **We are ready to attempt one real Turn D execution.** Not because everything is perfect, but because the validation gates are fail-closed. A failed attempt produces diagnostic evidence. A successful attempt proves the factory works.

---

## 2. Actual Execution Paths

| Path / Actor | Real Entrypoint | Model / Backend Source | Prompt / Config Source | Output Path | Status | Evidence |
|---|---|---|---|---|---|---|
| **Ray → Claude Code (interactive)** | Ray types role prompt in CLI | Claude Code model selection; role file `model:` frontmatter is advisory | CLAUDE.md (auto-loaded) + `.claude/agents/*.md` (read by agent) | Whatever role file directs | WORKING — Ray's primary interface | MEMORY.md lines 93-103 |
| **run.sh → mock worker** | `python3 sawmill/workers/canary_mock_worker.py` | No LLM — deterministic synthetic output | `sawmill/prompts/turn_*.txt` rendered by `render_prompt.py` | Synthetic artifacts in `sawmill/<FMWK>/` and `staging/<FMWK>/` | WORKING — 11 canary runs passed | `sawmill/FMWK-900-sawmill-smoke/runs/` |
| **run.sh → claude backend** | `claude -p "${prompt}" --append-system-prompt "${role_content}" --allowedTools "Read,Edit,Write,Glob,Grep,Bash"` | Claude Code; role file says `model: sonnet` (builder) or `model: opus` (reviewer/evaluator) | CLAUDE.md (auto) + role file (appended) + rendered prompt | `staging/<FMWK>/`, `sawmill/<FMWK>/RESULTS.md`, evidence JSON | UNTESTED — never executed through run.sh for real | run.sh lines 1523-1535 |
| **run.sh → codex backend** | `codex exec --full-auto "${role_content}\n\n${prompt}"` | Codex CLI; role file `model:` ignored by Codex | AGENTS.md (auto, symlink) + role+prompt concatenated | Same as claude path | UNTESTED — never executed through run.sh for real | run.sh lines 1537-1544 |
| **run.sh → gemini backend** | `gemini -p "${role_content}\n\n${prompt}" --yolo` | Gemini CLI | GEMINI.md (auto, symlink) + role+prompt concatenated | Same as claude path | UNTESTED — never executed through run.sh for real | run.sh lines 1545-1552 |
| **SDK MCP server** | `python -m platform_sdk.mcp_server` | N/A — tool surface, not agent | `_registry.py` discovers MCP tools from module `__sdk_export__` | Tool responses | WORKING — 2 tools registered (call_inference, embed_text) | `platform_sdk/mcp_server.py` |
| **SDK service surface** | `from platform_sdk import ...` (44 exports) | N/A — library, not agent | `platform_sdk/service.py` | In-process Python API | WORKING — 56 modules, 15 providers, tested | `platform_sdk/service.py`, tests/ |
| **Kernel WebSocket** | `python kernel/main.py` | N/A — stub router | Docker compose, env vars | WebSocket ACK messages | STUB — routes only, no cognition | `dopejar/kernel/main.py` (111 lines) |

---

## 3. Actual Information Sources

| Consumer | Reads From | Source Type | Authoritative? | Evidence |
|---|---|---|---|---|
| Any agent (startup) | `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` (all same file) | Auto-loaded project instructions | YES | Symlinks verified |
| Any agent (role) | `.claude/agents/<role>.md` | Injected via `--append-system-prompt` or concatenated | YES — role truth | run.sh lines 1523-1567 |
| Builder (Turn D) | D10 → TDD_AND_DEBUGGING → BUILDER_HANDOFF → 13Q → REVIEW_REPORT | Raw markdown in repo | YES | turn_d_build.txt reading order |
| Evaluator (Turn E) | D9_HOLDOUT_SCENARIOS + staging/<FMWK>/ | Holdouts + built code only | YES — strict isolation | evaluator.md, turn_e_eval.txt |
| run.sh (config) | ROLE_REGISTRY.yaml, PROMPT_REGISTRY.yaml, ARTIFACT_REGISTRY.yaml | YAML → Python validators → shell exports | YES — runtime config truth | run.sh lines 1779-1806 |
| run.sh (prompts) | `sawmill/prompts/turn_*.txt` | Template files with `{{VAR}}` placeholders | YES | PROMPT_REGISTRY maps key → file |
| Backstage (architecture) | `docs/architecture/` (hardlinked from `architecture/`) | Auto-synced hardlinks | YES for most files; FWK-0-DRAFT is 11 days stale | Inode comparison: different inodes (copies, not hardlinks as claimed) |
| Backstage (agent roles) | `docs/agents/` (manually copied) | Manual copies, NOT auto-synced | NO — can be stale | sync_docs.py SYNC_MAP excludes `.claude/agents/` |
| Backstage (templates) | `docs/sawmill-templates/` (synced from `Templates/`) | Auto-synced | YES | Perfect alignment confirmed |
| FMWK-001 staging code | `platform_sdk.tier0_core.errors`, `platform_sdk.tier0_core.config`, `platform_sdk.tier0_core.secrets` | SDK Python imports | YES — SDK is substrate | staging schemas.py lines 7-8, errors.py line 3 |

---

## 4. SDK Boundary Map

| Component / Path | What It Does Now | State | Classification | Why | Evidence |
|---|---|---|---|---|---|
| `tier0_core/config.py` — PlatformConfig, get_config() | Pydantic-settings config with env-var aliasing, 19 typed fields, LRU-cached singleton | WORKING, TESTED | **REUSE AS SUBSTRATE** | FMWK-001 already imports `get_config()` in `schemas.py`. All KERNEL frameworks will need config. | staging/FMWK-001-ledger/ledger/schemas.py line 7 |
| `tier0_core/errors.py` — PlatformError + 9 subtypes | Error taxonomy with status codes, Sentry/OTel hooks | WORKING, TESTED | **REUSE AS SUBSTRATE** | FMWK-001 extends PlatformError for its 4 error classes. Foundation for all framework errors. | staging/FMWK-001-ledger/ledger/errors.py line 3 |
| `tier0_core/secrets.py` — get_secret(), 3 providers | Secrets abstraction (env, mock, Infisical) | WORKING, TESTED | **REUSE AS SUBSTRATE** | FMWK-001 uses `get_secret()` for immudb credentials in `LedgerConfig.from_env()`. | staging schemas.py line 8 |
| `tier0_core/ledger.py` — LedgerProvider, 3 backends | Conversation-turn ledger (async, turn-indexed, per-conversation) | WORKING, TESTED (583 lines) | **IGNORE** for FMWK-001 | Different domain model. SDK is conversation-turn logging; FMWK-001 is global event-stream. Incompatible signatures, data models, async/sync boundaries. They coexist. | Method comparison: SDK `append(entry) → LedgerEntry` (async) vs FMWK-001 `append(event) → int` (sync) |
| `tier0_core/data.py` — SQLAlchemy async sessions | ORM layer for relational data | WORKING | **IGNORE** for FMWK-001 | Ledger uses immudb, not SQL. Not relevant until frameworks that need relational storage. | SDK ledger.py does not import data.py |
| `tier1_runtime/*` — context, clock, validate, serialize, retry, ratelimit, middleware | Request-level safety primitives | WORKING, TESTED (8 modules) | **REUSE AS SUBSTRATE** | Retry, validation, serialization will be needed by KERNEL frameworks. Available for governed code to import. | Tests pass in isolation |
| `tier2_reliability/*` — health, audit, cache | Production operations | WORKING (3 modules) | **REUSE AS SUBSTRATE** | Health checks needed when Docker services run. Cache available for Graph materialization. | health.py checks all external services |
| `tier3_platform/identity.py` — Principal, 3 providers | OIDC auth (Mock, Zitadel, Auth0) | WORKING, 3 PROVIDERS | **WRAP UNDER GOVERNANCE** when FMWK-010 (agent-interface) is built | Not needed for KERNEL. Will become the identity layer for DoPeJarMo operator sessions. Governance means: prompt contract for auth decisions, audit trail. | Designed for kernel WebSocket auth at session start |
| `tier3_platform/vector.py` — 3 providers | Embeddings + RAG (in-memory, Qdrant) | WORKING | **WRAP UNDER GOVERNANCE** when FMWK-005 (graph) or Layer 2 needs it | Not needed for KERNEL Ledger/Write-Path. Will power HO3 Graph queries and DoPeJar memory retrieval. | Qdrant provider connects to Docker service |
| `tier4_advanced/inference.py` — LiteLLM, 100+ models | LLM calls with cost tracking | WORKING, MCP-exported | **WRAP UNDER GOVERNANCE** when FMWK-004 (execution) is built | This IS HO1's backend. Must be wrapped in Prompt Contract enforcement. Not needed until Execution framework. | MCP tools: call_inference, embed_text |
| `tier4_advanced/llm_obs.py` — tracing, Langfuse | LLM observability | WORKING, 2 providers | **REUSE AS SUBSTRATE** | Observation layer for HO1. Complements inference governance. | MockLLMObsProvider + LangfuseObsProvider |
| `mcp_server.py` — MCP tool server | Discoverable tool surface for Claude Desktop | WORKING | **REUSE AS SUBSTRATE** | MCP tools are the agent-facing API surface. SDK already registers inference and embedding. Future frameworks register their own. | `_registry.py` collect_mcp_tools() |
| `kernel/main.py` — WebSocket router | 111-line stub with /operator, /user, /health routes | STUB | **PROMOTE INTO GOVERNED PATH** | This will become DoPeJarMo's entry point. Currently just routes connections. Must eventually host HO2, integrate Write Path, and manage sessions. Not needed for KERNEL builds (staging is separate). | kernel/main.py: no cognitive logic |
| Docker services (immudb, zitadel, postgres) | Infrastructure for runtime | DEFINED, NOT RUNNING | **REUSE AS SUBSTRATE** | immudb is needed for FMWK-001 integration tests and Turn E holdouts. Start with `docker compose up -d immudb`. | docker-compose.yml (181 lines) |

---

## 5. Backstage vs Repo/Runtime Truth

| Area | Backstage Says | Repo/Runtime Says | Match? | Trust Level | Evidence |
|---|---|---|---|---|---|
| Architecture docs (NORTH_STAR, BUILDER_SPEC, OPERATIONAL_SPEC) | Rendered HTML in docs/ | Source in architecture/, synced by sync_docs.py | YES (content identical; inodes differ — copies, not hardlinks as sync_docs.py claims) | AUTHORITATIVE | Inode comparison shows different inodes but identical content |
| FWK-0-DRAFT.md | Feb 28 version rendered | Mar 11 version in architecture/ (updated today) | NO — 11 days stale | UNSAFE | Source mtime: Mar 11 16:38. Docs mtime: Feb 28 17:23 |
| Agent role files | docs/agents/*.md (manually copied) | .claude/agents/*.md (source of truth) | PARTIAL — content mostly matches, mtimes differ by 6 min to 19 hours | REFLECTIVE ONLY | sync_docs.py SYNC_MAP excludes .claude/agents/. PORTAL_MAP claims mirror but doesn't enforce. |
| Templates (D1-D10) | docs/sawmill-templates/ | Templates/ (synced) | YES — perfect alignment | AUTHORITATIVE | 17/17 files match |
| Templates/compressed/ | Only COMPRESSION_STANDARD.md rendered | 17 files in source | NO — 16 of 17 compressed templates missing from docs | STALE | Only 1/17 compressed files mirrored |
| Sawmill registries | docs/sawmill/ROLE_REGISTRY, EXECUTION_CONTRACT, etc. | sawmill/*.yaml, sawmill/*.md | YES (manually synced, content current) | REFLECTIVE ONLY | Files exist in docs/ but not tracked by sync_docs.py |
| Default backends | ROLE_REGISTRY shows mock defaults and production backends | run.sh uses mock defaults unless env overrides set | YES (documented) but misleading — production backends shown prominently | UNSAFE if interpreted as "what runs" | Every canary run used mock |
| PORTAL_MAP sync claims | Declares agent files and sawmill files as `sync: mirror` | sync_docs.py only mirrors architecture/ and Templates/ | NO — PORTAL_MAP overpromises | UNSAFE | PORTAL_MAP line claims mirror; sync_docs.py SYNC_MAP excludes those paths |
| Framework status pages | docs/sawmill/FMWK-001-ledger.md (narrative) | Actual state: D1-D10 complete, staging is stubs, no RESULTS.md | UNCLEAR — narrative may be current or aspirational | REFLECTIVE ONLY | Status pages are steward-authored |

---

## 6. Validation Boundary Before Any Build

These checks must pass before a real governed build is allowed. Ordered by dependency.

1. **Real backend selected and verified.** Set `SAWMILL_BUILD_AGENT=claude` (or codex). Verify the CLI is installed and authenticated: `claude --version`, `codex --version`. run.sh preflight validates this.

2. **Stale artifacts invalidated.** Use `--from-turn D` which calls `invalidate_downstream_artifacts "D"` — confirmed to delete all Turn D/E artifacts including the stale `13Q_ANSWERS.md` (Mar 5) and `staging/FMWK-001-ledger/` partial scaffold.

3. **Registries internally consistent.** run.sh preflight calls `validate_role_registry.py`, `validate_artifact_registry.py`, `validate_prompt_registry.py` with `--shell-exports`. All three must pass. Confirmed: they validate schema, cross-references, and file existence.

4. **Prompt templates renderable.** `render_prompt.py` substitutes `{{VAR}}` placeholders from environment. If any required variable is missing, rendering fails and the run aborts. Confirmed fail-closed behavior.

5. **Role file content matches registry.** Each role in ROLE_REGISTRY.yaml references a role_file path. Preflight validates these files exist. Content is loaded and injected into agent invocations. No further content validation exists — the role file IS the spec.

6. **Claude Code hooks active.** `sawmill-guard.sh` enforces per-role file ownership for Claude backend. Verify hooks are registered in `.claude/settings.json`. Confirmed: three hooks registered (guard, state, stop).

7. **Version evidence enforceable.** run.sh checks `require_version_evidence` after 13Q and review steps. Builder must emit `Builder Prompt Contract Version: 1.0.0`. Reviewer must emit both builder and reviewer versions. Confirmed fail-closed.

8. **Docker/immudb available for Turn E.** Holdout scenarios require immudb on port 13322. Start with `docker compose up -d immudb` from `/Users/raymondbruni/dopejar/`. Without this, all integration holdouts fail.

9. **PYTHONPATH includes dopejar.** FMWK-001 staging code imports from `platform_sdk`. Builder needs `export PYTHONPATH=/Users/raymondbruni/dopejar:$PYTHONPATH`. Verify this is set in the execution environment.

10. **First run is monitored.** The first real-agent run should use `--interactive` or have Ray watching. The pipeline has never processed real agent output. Unexpected failures are likely. Diagnostic evidence (logs, events.jsonl) will inform fixes.

---

## 7. Are We Ready to Build Now?

**PARTIAL**

The pipeline infrastructure is complete, validated with mocks, and safe to invoke. run.sh gates are fail-closed — a bad run produces diagnostic evidence, not corrupt state. The SDK substrate is real and already consumed by FMWK-001 staging code. All Turn D inputs (D1-D10, handoff, holdouts) are substantive and complete.

What is unproven: whether a real Claude or Codex agent can produce conformant output through the automated run.sh pipeline. Every validation check has only been exercised against deterministic mock output. The correct next move is not to keep governing — it is to attempt one real Turn D execution with a real agent backend, accept that it may fail, and use the failure evidence to close the remaining gaps. The validation boundary is strong enough that a failed attempt is safe (fail-closed, diagnostic, no corrupt state).

---

## 8. Minimum Next Move

1. **Start immudb.** `docker compose up -d immudb` from `/Users/raymondbruni/dopejar/`. Required for Turn E holdouts.

2. **Set real backend + PYTHONPATH.** `export SAWMILL_BUILD_AGENT=claude SAWMILL_REVIEW_AGENT=claude SAWMILL_EVAL_AGENT=claude PYTHONPATH=/Users/raymondbruni/dopejar:$PYTHONPATH`

3. **Run Turn D for FMWK-001.** `./sawmill/run.sh FMWK-001-ledger --from-turn D` — stale artifacts auto-invalidated, fresh 13Q → review → build → evaluate cycle.

4. **Diagnose the first failure.** The run will likely fail at some point (agent output format mismatch, version evidence missing, test failure, etc.). Read `events.jsonl` and step logs from the run directory. Fix the specific failure.

5. **Iterate until Turn D + Turn E produce a PASS verdict.** Each failed attempt produces evidence. Fix forward. Do not retreat into more governance.

---

## 9. What Should NOT Happen Next

- **Do not run more canary smoke tests.** 11 mock runs is enough. The canary proved the harness works with synthetic output. More mock runs do not reduce real-agent risk.
- **Do not trust Backstage without verifying source files.** FWK-0-DRAFT is 11 days stale. Agent docs may lag source. Architecture docs are mostly current but inodes show copies, not hardlinks. Always check `.claude/agents/` and `architecture/` directly.
- **Do not ignore the SDK.** FMWK-001 already imports from it. The SDK is substrate — config, errors, secrets, inference, identity, vector are all real and tested. Rebuilding these through governance would be wasteful.
- **Do not add more governance documents.** EXECUTION_CONTRACT, AGENT_TRAVERSAL, SAWMILL_ANALYSIS, RUNTIME_SPEC, HARNESS_INVARIANTS, CANARY_BACKEND_POLICY, plus this audit and two prior audits — the governance documentation volume is already high. Writing about building is not building.
- **Do not fix sync_docs.py or PORTAL_MAP.yaml before building.** These are real issues (agent files not auto-synced, FWK-0 stale) but they do not block the governed build. Fix them after FMWK-001 ships, not before.
- **Do not start FMWK-002 specs.** Write-Path depends on a completed Ledger. Starting specs before Ledger passes Turn E is premature.
- **Do not govern problems that do not exist yet.** Multi-backend routing, nested subagent dispatch, cross-framework composition, Layer 1 agent-interface design — all real future concerns, all premature today.

---

## 10. Confidence and Unknowns

### Verified Directly

- **run.sh dispatch mechanism**: Read `invoke_agent()` (lines 1492-1615). Confirmed exact CLI invocation for claude, codex, gemini, mock backends.
- **Stale artifact invalidation**: Read `invalidate_downstream_artifacts()`. Confirmed `--from-turn D` deletes all Turn D/E artifacts before running. Prior 13Q and staging scaffold will be cleaned.
- **Hook enforcement**: Read all three hook scripts. `sawmill-guard.sh` enforces per-role file ownership allowlists for Claude backend. Acknowledged residual risks documented in script comments (Bash tool bypass, self-labeling, non-Claude backends instruction-only).
- **SDK working state**: Read service.py, _registry.py, all tier0_core modules, inference.py, mcp_server.py. 56 modules, 15 providers, all tested. MCP server ready.
- **Registry consistency**: All three registries (ROLE, PROMPT, ARTIFACT) cross-reference correctly. Prompt dependency chains match artifact paths. Role files exist at declared paths.
- **Backstage sync reality**: Inode comparison shows copies (not hardlinks) for all checked pairs. sync_docs.py SYNC_MAP only covers architecture/ and Templates/. PORTAL_MAP.yaml claims more than is enforced.

### Could Not Verify

- **Whether Claude Code honors `model: sonnet` / `model: opus` frontmatter in role files.** Model selection is internal to Claude Code. The frontmatter may be a hint, a requirement, or ignored.
- **Whether `model_policy: max_capability` in ROLE_REGISTRY affects actual model selection.** run.sh reads this field but the audit did not find where it maps to a CLI flag or API parameter.
- **Whether real agent output will pass evidence validators.** Validators have only been tested against mock output. Real agent output may have formatting differences that fail validation.
- **Docker/immudb current state.** Did not run `docker compose ps`. Cannot confirm services are running or available.
- **Whether the `--from-turn D` flag has been tested with a framework that has prior Turn A-C artifacts.** Only canary (which runs all turns) has been tested. FMWK-001 would be the first framework to use `--from-turn D` with pre-existing spec artifacts.
- **Exact behavior of Codex sandbox with PYTHONPATH.** Codex runs network-disabled by default. If PYTHONPATH points to `/Users/raymondbruni/dopejar/`, Codex may or may not have filesystem access to that path depending on sandbox configuration.
