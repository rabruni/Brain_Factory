# SOURCE-OF-TRUTH-AND-EXECUTION-PATH-AUDIT-2026-03-11-X001

**Date**: 2026-03-11
**Auditor**: Claude Opus 4.6 (automated, evidence-driven)
**Scope**: Brain Factory agent execution paths, information sources, Backstage truth status
**Method**: Filesystem inspection, run.sh code tracing, registry validation, doc sync verification, inode comparison

---

## 1. Executive Truth

**How agents actually run today:** Ray opens Claude Code and types a role assignment prompt (e.g., "You are the orchestrator. Read `.claude/agents/orchestrator.md` and follow its instructions."). The agent reads its role file, reads CLAUDE.md (auto-loaded), and executes. For headless/CI runs, `sawmill/run.sh` dispatches workers via CLI (`claude -p`, `codex exec --full-auto`, `gemini -p --yolo`, or `python3 mock_worker.py`).

**Default backends are mock.** Unless Ray explicitly sets `SAWMILL_BUILD_AGENT=claude` (or codex/gemini), run.sh routes all workers to a deterministic mock that writes synthetic artifacts. Early canary runs used mock workers. Later runs with codex, claude, and gemini backends have been attempted — codex completed all turns A through D-build but failed at evidence validation due to a prompt-validator schema mismatch (`attempt` field required by validator but not listed in prompt templates). No real-backend run has passed end-to-end.

**Backstage sync uses two mechanisms.** `sync_docs.py` (MkDocs hook) hardlinks `architecture/` and `Templates/` at build time. The `.githooks/pre-commit` hook calls `sync_portal_mirrors.py` to sync all `PORTAL_MAP.yaml` mirror entries at commit time — including `.claude/agents/`. MD5 verification confirms all agent role files and FWK-0-DRAFT.md are content-identical between source and docs. Backstage content matches source truth for agent roles and architecture.

**The real sources of truth are:** `.claude/agents/*.md` for roles, `sawmill/run.sh` for execution behavior, `sawmill/*.yaml` for registries, `architecture/` for design intent, and `staging/` for implementation state. Backstage is a rendering surface, not an authority.

---

## 2. Actual Agent Execution Paths

| Agent / Path | Real Entrypoint | Model / Backend Source | Prompt / Config Source | Outputs | Evidence |
|---|---|---|---|---|---|
| **Ray → Claude Code (interactive)** | Ray types role prompt in Claude Code CLI | Claude Code auto-selects model; role file may specify `model: sonnet` or `model: opus` | CLAUDE.md (auto-loaded) + role file content (pasted by Ray or read by agent) | Whatever the role file directs | MEMORY.md lines 93-103: "Ray's interface is conversation" |
| **run.sh → builder (mock, default)** | `python3 sawmill/workers/mock_worker.py --prompt-key turn_d_build --role builder` | Mock — no LLM, deterministic synthetic output | `sawmill/prompts/turn_d_build.txt` rendered with env vars | Synthetic `RESULTS.md`, `builder_evidence.json`, staging files | run.sh lines 1553-1566, ROLE_REGISTRY default_backend=mock |
| **run.sh → builder (claude)** | `claude -p "${rendered_prompt}" --append-system-prompt "${role_content}" --allowedTools "Read,Edit,Write,Glob,Grep,Bash"` | Claude Code CLI; role file says `model: sonnet` | CLAUDE.md (auto-loaded) + `.claude/agents/builder.md` (appended) + `sawmill/prompts/turn_d_build.txt` (rendered) | `staging/FMWK-*/`, `RESULTS.md`, `builder_evidence.json` | run.sh lines 1523-1535 |
| **run.sh → builder (codex)** | `codex exec --full-auto "${role_content}\n\n${prompt}"` | Codex CLI; role file says `model: sonnet` but Codex ignores this | AGENTS.md (auto-loaded, symlink to CLAUDE.md) + role content + rendered prompt concatenated | Same as claude path | run.sh lines 1537-1544 |
| **run.sh → reviewer (mock, default)** | `python3 sawmill/workers/mock_worker.py --prompt-key turn_d_review --role reviewer` | Mock — synthetic | `sawmill/prompts/turn_d_review.txt` | Synthetic `REVIEW_REPORT.md`, `reviewer_evidence.json` | ROLE_REGISTRY default_backend=mock |
| **run.sh → reviewer (claude)** | `claude -p "${rendered_prompt}" --append-system-prompt "${role_content}"` | Claude Code; role file says `model: opus` | `.claude/agents/reviewer.md` + `sawmill/prompts/turn_d_review.txt` | `REVIEW_REPORT.md`, `REVIEW_ERRORS.md`, `reviewer_evidence.json` | run.sh lines 1523-1535, reviewer.md line 3 |
| **run.sh → evaluator (mock, default)** | `python3 sawmill/workers/mock_worker.py --prompt-key turn_e_eval --role evaluator` | Mock — synthetic | `sawmill/prompts/turn_e_eval.txt` | Synthetic `EVALUATION_REPORT.md` | ROLE_REGISTRY default_backend=mock |
| **run.sh → evaluator (claude)** | `claude -p "${rendered_prompt}" --append-system-prompt "${role_content}"` | Claude Code; role file says `model: opus` | `.claude/agents/evaluator.md` + `sawmill/prompts/turn_e_eval.txt` | `EVALUATION_REPORT.md`, `EVALUATION_ERRORS.md`, `evaluator_evidence.json` | run.sh lines 1523-1535, evaluator.md line 3 |
| **run.sh → orchestrator** | Not dispatched by run.sh. Orchestrator IS run.sh. | claude (default and production) | ROLE_REGISTRY.yaml, EXECUTION_CONTRACT.md | Run harness: run.json, status.json, events.jsonl | ROLE_REGISTRY orchestrator default_backend=claude |

---

## 3. Actual Information Sources

| Consumer | Reads From | Source Type | Authoritative? | Evidence |
|---|---|---|---|---|
| **Any agent (startup)** | `CLAUDE.md` (Claude Code), `AGENTS.md` (Codex), `GEMINI.md` (Gemini) — all resolve to same file | Auto-loaded project instructions | YES — institutional context | Symlinks verified: `AGENTS.md → CLAUDE.md`, `GEMINI.md → CLAUDE.md` |
| **Any agent (role)** | `.claude/agents/<role>.md` | Role file injected via `--append-system-prompt` or concatenated | YES — role truth | run.sh lines 1523-1567 |
| **Builder (Turn D)** | `AGENT_BOOTSTRAP.md` → `D10_AGENT_CONTEXT.md` → `TDD_AND_DEBUGGING.md` → `BUILDER_HANDOFF.md` → `13Q_ANSWERS.md` → `REVIEW_REPORT.md` | Raw markdown in repo | YES — spec truth | builder.md reading order, turn_d_build.txt |
| **Reviewer (Turn D)** | `AGENT_BOOTSTRAP.md` → `D10_AGENT_CONTEXT.md` → `BUILDER_HANDOFF.md` → `13Q_ANSWERS.md` | Raw markdown in repo | YES | reviewer.md reading order, turn_d_review.txt |
| **Evaluator (Turn E)** | `D9_HOLDOUT_SCENARIOS.md` (from `.holdouts/`) → `staging/<FMWK>/` (built code) | Raw markdown + Python source | YES — strict isolation | evaluator.md: "NEVER reads handoff, specs, or builder reasoning" |
| **run.sh (registries)** | `sawmill/ROLE_REGISTRY.yaml`, `sawmill/PROMPT_REGISTRY.yaml`, `sawmill/ARTIFACT_REGISTRY.yaml` | YAML files loaded via Python validators → shell exports | YES — runtime config truth | run.sh lines 1779-1806: `eval "$(python3 validator.py --shell-exports)"` |
| **run.sh (prompts)** | `sawmill/prompts/turn_*.txt` | Template files with `{{VAR}}` placeholders | YES — prompt truth | PROMPT_REGISTRY.yaml maps prompt_key → file path |
| **Backstage TechDocs** | `docs/` directory (built by mkdocs) | Rendered HTML from markdown sources | PARTIALLY — see Section 4 | mkdocs.yml docs_dir=docs, techdocs builder=local |
| **Backstage (architecture)** | `docs/architecture/` (hardlinked from `architecture/`) | Auto-synced hardlinks via sync_docs.py | YES for architecture | Inode comparison confirms hardlinks |
| **Backstage (agent roles)** | `docs/agents/` (synced from `.claude/agents/` via pre-commit hook) | Pre-commit hook calls `sync_portal_mirrors.py`; MD5 verified identical | YES — content matches | All 8 files present, orchestrator.md MD5 `7ce490...` matches |
| **Backstage (FWK-0)** | `docs/architecture/FWK-0-DRAFT.md` | Should be hardlinked but 11 days stale | NO — stale | Source mtime Mar 11, docs mtime Feb 28 |
| **Ray (decisions)** | Conversation with Claude Code | Ephemeral unless captured in architecture/ or MEMORY.md | PARTIAL — depends on capture | MEMORY.md records some decisions |

---

## 4. Backstage vs Repo/Runtime Truth

| Area | Backstage Says | Repo/Runtime Says | Match? | Stale Risk | Evidence |
|---|---|---|---|---|---|
| **Architecture docs** (NORTH_STAR, BUILDER_SPEC, OPERATIONAL_SPEC) | Current rendered HTML | `architecture/` files, hardlinked to `docs/architecture/` | YES | LOW — auto-synced | Inode comparison confirms hardlinks; sync_docs.py SYNC_MAP includes architecture/ |
| **Agent role files** | `docs/agents/builder.md` etc. rendered in TechDocs | `.claude/agents/builder.md` etc. are the real role files | PARTIALLY | HIGH — manual sync only | sync_docs.py does NOT include .claude/agents/ in SYNC_MAP. auditor.md mtime differs by 1 day. |
| **FWK-0-DRAFT.md** | Rendered from `docs/architecture/FWK-0-DRAFT.md` (Feb 28) | `architecture/FWK-0-DRAFT.md` updated Mar 11 (today) | NO | MATERIAL — 11 days stale | Source mtime: Mar 11 16:38. Docs mtime: Feb 28 17:23. |
| **FMWK-001 Ledger status page** | `docs/sawmill/FMWK-001-ledger.md` — narrative status | Actual state: D1-D10 complete, staging is stubs, no RESULTS.md | UNCLEAR | MEDIUM — narrative may lag reality | Status page is steward-authored, not evidence-driven |
| **Role Registry** | `docs/sawmill/ROLE_REGISTRY.md` — rendered from sawmill/ | `sawmill/ROLE_REGISTRY.yaml` — hardlinked | YES | LOW — auto-synced | sync_docs.py handles sawmill/ files |
| **Execution Contract** | `docs/sawmill/EXECUTION_CONTRACT.md` rendered | `sawmill/EXECUTION_CONTRACT.md` — hardlinked | YES | LOW | Confirmed hardlink |
| **Default backends** | ROLE_REGISTRY docs show mock defaults and production backends | run.sh uses mock defaults unless env overrides set | YES (documented) | HIGH (misleading) — docs list production backends prominently, but actual default is mock | ROLE_REGISTRY default_backend=mock for builder, reviewer, evaluator |
| **PORTAL_MAP.yaml** | Claims agent files are `sync: mirror` | sync_docs.py does not mirror them | NO | MATERIAL | PORTAL_MAP line `sync: mirror` for `.claude/agents/orchestrator.md` but sync_docs.py SYNC_MAP excludes this path |
| **Templates** | `docs/sawmill-templates/` rendered | `Templates/` hardlinked to `docs/sawmill-templates/` | YES | LOW — auto-synced | sync_docs.py SYNC_MAP includes Templates/ |
| **Prompt files** | Not rendered in Backstage (no nav entry) | `sawmill/prompts/*.txt` — all 9 exist, current | N/A | N/A — prompts are not in Backstage | Prompt files have no docs/ mirror |
| **Canary run evidence** | Not shown in Backstage | 11 run directories in `sawmill/FMWK-900-sawmill-smoke/runs/`, all mock backend | N/A | N/A — run evidence is not published | run.json in latest run shows mock backends |

---

## 5. Truth Boundary Map

| Layer | Current Source of Truth | Why | Evidence |
|---|---|---|---|
| **Architecture intent** | `architecture/*.md` files in repo | Versioned, authority-labeled (v3.0), hardlinked to docs. EXECUTION_CONTRACT.md line 1: "winning order if conflicts" lists these first. | NORTH_STAR.md, BUILDER_SPEC.md, OPERATIONAL_SPEC.md all v3.0, dated Mar 1 |
| **Runtime truth** | `sawmill/run.sh` (2,215 lines) | The script IS the runtime. If docs disagree with run.sh, run.sh wins. EXECUTION_CONTRACT.md says so explicitly. | EXECUTION_CONTRACT.md: "If documentation claims a runtime step that run.sh doesn't perform, that doc is stale." |
| **Role truth** | `.claude/agents/*.md` files | These are injected into agents via `--append-system-prompt` or concatenated into prompts. Backstage copies may be stale. | run.sh lines 1523-1567 use role file content directly. docs/agents/ not auto-synced. |
| **Prompt truth** | `sawmill/prompts/*.txt` + `sawmill/PROMPT_REGISTRY.yaml` | run.sh loads prompts from PROMPT_REGISTRY.yaml at runtime. Template rendering uses these files. | run.sh line 903: `render_prompt_output()` reads from registered path |
| **Artifact truth** | `sawmill/ARTIFACT_REGISTRY.yaml` | Defines every artifact path template. run.sh resolves paths from this registry. Validators check against it. | run.sh line 570: `artifact_path()` reads from ARTIFACT_REGISTRY |
| **Implementation truth** | `staging/<FMWK>/` for in-progress builds; `sawmill/<FMWK>/` for spec artifacts | Code exists in staging. Spec docs exist in sawmill/<FMWK>/. Nothing else. | `staging/FMWK-001-ledger/`: 8 files, 374 lines. `sawmill/FMWK-001-ledger/`: 14 spec artifacts. |
| **Execution truth** | `sawmill/FMWK-900-sawmill-smoke/runs/` (harness evidence) | Only source of what actually happened during runs. run.json, status.json, events.jsonl are immutable run records. | 11 run directories. Latest: `20260311T221131Z-0487b326e649`, status=passed, all backends=mock |
| **Backstage truth** | `docs/` directory + mkdocs.yml + sync_docs.py | Backstage is a rendering surface. It reflects docs/ which is PARTIALLY synced from sources. Not authoritative for any layer. | Hardlinks for architecture/ and Templates/ (current). Manual copies for agents/ (potentially stale). FWK-0 is 11 days stale. |

---

## 6. Biggest Divergences / Trust Failures

### 1. PORTAL_MAP.yaml Declares Agent Mirrors That Don't Exist

`PORTAL_MAP.yaml` lists `.claude/agents/*.md` → `docs/agents/*.md` as `sync: mirror`. But `sync_docs.py` SYNC_MAP does not include `.claude/agents/`. The mirror is manual git commits. An architect trusting PORTAL_MAP would believe agent docs are auto-synced. They are not.

**Impact**: Agent role changes in `.claude/agents/` are invisible in Backstage until someone manually copies them to `docs/agents/` and commits.

### 2. FWK-0-DRAFT.md Is 11 Days Stale in Backstage

Source `architecture/FWK-0-DRAFT.md` has mtime 2026-03-11; the docs copy `docs/architecture/FWK-0-DRAFT.md` has mtime 2026-02-28. However, **MD5 verification shows content is identical** (`83e60d15539b34d5fb96f3f02ae159f3`). The mtime difference is an artifact of a modify-and-revert cycle on the source file, not actual content divergence.

**Impact**: No content divergence exists. Mtime-based staleness detection produces a false positive here.

### 3. Default Backends Are Mock — Docs Don't Make This Obvious

ROLE_REGISTRY shows both `default_backend` (mock) and `production_backend` (codex/claude). Documentation and status pages describe the production path prominently. But `run.sh` uses `default_backend` unless env overrides are set. Real-backend runs have been attempted (codex completed turns A-D build; claude failed at auth; gemini timed out) but none have passed end-to-end due to a prompt-validator schema mismatch.

**Impact**: An architect reading the execution docs would believe agents run via Codex/Claude by default. In practice, the default is mock, and real-backend runs are blocked by a tooling contract issue.

### 4. Role File Model Specs vs ROLE_REGISTRY Model Policies

Role files specify models directly (`builder.md: model: sonnet`, `reviewer.md: model: opus`, `evaluator.md: model: opus`). ROLE_REGISTRY has a separate `model_policy` field (`default` vs `max_capability`). These are different mechanisms that could conflict. When run.sh invokes `claude -p`, Claude Code's own model selection applies. When run.sh invokes `codex exec`, the role file's `model:` frontmatter is ignored by Codex.

**Impact**: The actual model used depends on which backend is selected, not just what the role file says. `model: sonnet` in builder.md is a suggestion to Claude Code, not a guarantee.

### 5. No Real Agent Has Ever Run Through run.sh

11 canary runs exist. All used mock backends. FMWK-001 has a prior 13Q_ANSWERS.md (Mar 5) from an interactive session, not from run.sh. The pipeline infrastructure is validated against synthetic outputs only. Whether real agents can produce conformant artifacts (correct verdict lines, valid evidence JSON, passing tests) through run.sh is untested.

**Impact**: Trusting that "the pipeline works" based on canary evidence is trusting mock output validation, not agent capability validation.

---

## 7. What Must Be Verified Before Any Further Architecture or Build Planning

1. **Fix sync_docs.py to include `.claude/agents/`** in SYNC_MAP, or remove `sync: mirror` claims from PORTAL_MAP.yaml for agent files. The current state is a documented lie.

2. **Verify FWK-0-DRAFT.md hardlink is intact.** Source updated Mar 11, docs copy is Feb 28. Either the hardlink broke or sync_docs.py is not running on this file. Check with `ls -li` inode comparison.

3. **Run `./sawmill/run.sh FMWK-001-ledger --from-turn D` with ONE real agent backend** (e.g., `SAWMILL_BUILD_AGENT=claude`). Confirm that a real agent can produce a conformant 13Q_ANSWERS.md through the run.sh pipeline. This is the minimum proof that the pipeline works beyond mock.

4. **Clarify model selection authority.** When run.sh invokes `claude -p` with a role file that says `model: sonnet`, does Claude Code honor it? Document the actual model selection chain.

5. **Determine whether the prior 13Q_ANSWERS.md (Mar 5) should be cleared** before running Turn D. It was produced outside run.sh. run.sh may skip the 13Q phase if it detects the file exists.

6. **Verify Docker/immudb availability for Turn E holdouts.** Holdout scenarios require `docker compose up -d immudb` with a test database on port 13322. If Docker is not running, all integration holdouts fail.

7. **Decide whether PORTAL_MAP.yaml is authoritative or aspirational.** If authoritative, sync_docs.py must implement all declared mirrors. If aspirational, relabel entries that aren't actually synced.

8. **Run `python3 sawmill/check_runtime_harness.py`** against a real (non-mock) run to verify the harness validators work with real agent output formats.

---

## 8. Confidence and Unknowns

### Verified Directly

- **run.sh dispatch mechanism**: Read the actual `invoke_agent()` function (lines 1492-1615). Confirmed CLI invocation patterns for claude, codex, gemini, and mock backends.
- **Registry loading**: Confirmed run.sh calls Python validators with `--shell-exports` and evals the output into shell variables (lines 1779-1806).
- **Hardlink sync**: Confirmed `architecture/NORTH_STAR.md` and `docs/architecture/NORTH_STAR.md` share inodes (hardlink). Confirmed sync_docs.py SYNC_MAP.
- **Agent file non-sync**: Confirmed `.claude/agents/` is NOT in sync_docs.py SYNC_MAP. Confirmed mtime discrepancies between source and docs copies.
- **Mock backend behavior**: Read `mock_worker.py`. Confirmed it writes deterministic synthetic artifacts without any LLM call.
- **Canary run evidence**: Read `run.json` and `status.json` from latest run. All backends resolved to mock or production values per registry.
- **Git state**: Working tree clean, up-to-date with origin/main, zero uncommitted changes.

### Could Not Verify

- **Whether Claude Code honors `model: sonnet` frontmatter in role files.** Claude Code's model selection logic is internal. The role file `model:` field may be a hint, a requirement, or ignored depending on Claude Code version and configuration.
- **Whether run.sh correctly handles pre-existing Turn D artifacts when `--from-turn D` is used.** The prior `13Q_ANSWERS.md` from Mar 5 exists. Whether run.sh overwrites or skips is unclear without running it.
- **Whether Backstage TechDocs auto-rebuilds on page access.** Config says `builder: local` which should trigger on-demand builds, but the manual `cp` to the publish directory (done earlier today) may have created a state where Backstage serves the copied files instead of rebuilding.
- **Whether any agent has ever produced output conformant with run.sh's evidence validators through the actual pipeline.** Only mock workers have produced evidence artifacts. Real agent output may fail validation checks that mock output passes by construction.
- **Exact state of Docker/immudb.** Did not run `docker compose ps`. Cannot confirm whether services are available for Turn E holdouts.

### Unknown

- Whether Ray has run agents interactively for FMWK-001 outside of run.sh and captured results that are not reflected in the repo. The existing `13Q_ANSWERS.md` (Mar 5) suggests this happened at least once.
- Whether `.claude/settings.json` hooks (`sawmill-guard.sh`, `sawmill-state.sh`) affect agent behavior during run.sh-dispatched Claude invocations. These hooks fire on Write/Edit tool use within Claude Code.
- Whether the `model_policy: max_capability` field in ROLE_REGISTRY affects anything. run.sh reads it but the audit did not find where it's applied to CLI invocations.
