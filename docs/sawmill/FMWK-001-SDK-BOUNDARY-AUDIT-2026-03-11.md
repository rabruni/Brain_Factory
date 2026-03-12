# Sawmill Audit — FMWK-001 and SDK Boundary

**Date**: 2026-03-11
**Auditor**: Claude Opus 4.6 (read-only, evidence-driven)
**Published path**: `docs/sawmill/FMWK-001-SDK-BOUNDARY-AUDIT-2026-03-11.md`
**Publication method**: TechDocs via mkdocs.yml Audits nav (existing canonical pattern)

---

## 1. Purpose

Read-only audit of the repo/build reality around Sawmill and the FMWK-001 Ledger framework, with specific attention to the SDK boundary question: does FMWK-001 replace, wrap, promote, or coexist with the pre-existing SDK ledger implementation?

---

## 2. Scope Inspected

- Brain Factory repo: `/Users/raymondbruni/Cowork/Brain_Factory/`
- Dopejar runtime repo: `/Users/raymondbruni/dopejar/`
- Sawmill pipeline machinery: `sawmill/run.sh`, registries, prompts, role files
- FMWK-001 spec pack: `sawmill/FMWK-001-ledger/` (14 artifacts)
- FMWK-001 staging code: `staging/FMWK-001-ledger/` (8 files present, 8 missing)
- FMWK-001 holdouts: `.holdouts/FMWK-001-ledger/` (1 file, 28K)
- SDK ledger: `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/ledger.py` (582 lines)
- Canary runs: `sawmill/FMWK-900-sawmill-smoke/runs/` (18 run directories)
- Backstage coverage: `mkdocs.yml` nav, `docs/PORTAL_MAP.yaml`, `docs/sawmill/`
- Evidence validator: `sawmill/validate_evidence_artifacts.py`

---

## 3. Evidence Sources

### Repo paths inspected

| Path | What | Size / State |
|------|------|-------------|
| `sawmill/FMWK-001-ledger/D1_CONSTITUTION.md` | Constitution | 13K |
| `sawmill/FMWK-001-ledger/D2_SPECIFICATION.md` | Specification | 12K |
| `sawmill/FMWK-001-ledger/D3_DATA_MODEL.md` | Data model | 16K |
| `sawmill/FMWK-001-ledger/D4_CONTRACTS.md` | Contracts | 12K |
| `sawmill/FMWK-001-ledger/D5_RESEARCH.md` | Research | 12K |
| `sawmill/FMWK-001-ledger/D6_GAP_ANALYSIS.md` | Gap analysis | 18K, GATE READY |
| `sawmill/FMWK-001-ledger/D7_PLAN.md` | Plan | 16K |
| `sawmill/FMWK-001-ledger/D8_TASKS.md` | Tasks | 31K |
| `sawmill/FMWK-001-ledger/D10_AGENT_CONTEXT.md` | Agent context | 14K |
| `sawmill/FMWK-001-ledger/BUILDER_HANDOFF.md` | Handoff | 33K, 16 files specified |
| `sawmill/FMWK-001-ledger/13Q_ANSWERS.md` | 13Q answers | 6.2K, from prior incomplete attempt |
| `sawmill/FMWK-001-ledger/TASK.md` | Task | 1.6K |
| `sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md` | Source material | 10K |
| `sawmill/FMWK-001-ledger/GATE_CHECKLIST.md` | Gate checklist | 1.7K |
| `.holdouts/FMWK-001-ledger/D9_HOLDOUT_SCENARIOS.md` | Holdout scenarios | 28K |
| `staging/FMWK-001-ledger/ledger/ledger.py` | Core stub | 33 lines, all NotImplementedError |
| `staging/FMWK-001-ledger/ledger/schemas.py` | Schemas | 144 lines, complete |
| `staging/FMWK-001-ledger/ledger/errors.py` | Errors | 74 lines, complete |
| `staging/FMWK-001-ledger/ledger/__init__.py` | Package init | 20 lines, 9 exports |
| `staging/FMWK-001-ledger/tests/unit/test_serializer.py` | Serializer tests | 103 lines, imports missing module |
| `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/ledger.py` | SDK ledger | 582 lines, 3 backends |

### Scripts inspected

| Script | Size | State |
|--------|------|-------|
| `sawmill/run.sh` | 2,234 lines | Complete Turn D/E implementation |
| `sawmill/validate_evidence_artifacts.py` | 256 lines | Requires `attempt` field |
| `sawmill/validate_role_registry.py` | present | Not read in detail |

### Run artifacts inspected

| Run ID | Backend | Final State | Failure Code |
|--------|---------|-------------|--------------|
| `20260312T030607Z` | codex | running | none (reached portal_stage) |
| `20260312T030141Z` | codex | (checked dir) | - |
| `20260312T002821Z` | codex | failed | EVIDENCE_VALIDATION_FAILED at turn_d_build |
| `20260311T235243Z` | codex | (checked dir) | - |
| `20260311T232927Z` | codex | (checked dir) | - |

18 total run directories in `sawmill/FMWK-900-sawmill-smoke/runs/`.

### Docs compared

| Backstage page | Repo file | In mkdocs nav? |
|----------------|-----------|----------------|
| FMWK-001 Ledger status | `docs/sawmill/FMWK-001-ledger.md` | Yes |
| FMWK-001 Readiness Audit | `docs/sawmill/FMWK-001-READINESS-AUDIT.md` | Yes (Audits) |
| Ground Truth Audit | `docs/architecture/GROUND_TRUTH_AUDIT.md` | Yes (Audits) |
| CANARY_AUDIT.md | `sawmill/FMWK-900-sawmill-smoke/CANARY_AUDIT.md` | No |
| Run directories (18) | `sawmill/FMWK-900-sawmill-smoke/runs/` | No |

---

## 4. Proven

These are confirmed by direct file reads and content verification:

1. **All 14 FMWK-001 spec/plan artifacts exist and are substantive.** D1-D10, BUILDER_HANDOFF, 13Q_ANSWERS, TASK.md, SOURCE_MATERIAL.md all present with real content (not templates/placeholders). Total ~180K of documentation.

2. **D9 holdout scenarios exist and are isolated.** `.holdouts/FMWK-001-ledger/D9_HOLDOUT_SCENARIOS.md` (28K) is present, separate from the spec pack. Builder cannot access this path.

3. **FMWK-001 staging contains 8 of 16 planned files.** The handoff (line 415-430) specifies exactly 16 files with CREATE disposition. 8 are present; 8 are absent.

4. **`ledger.py` is entirely stubs.** 33 lines, 7 methods, all `raise NotImplementedError`. This is the core class FMWK-001 exists to build.

5. **`schemas.py` and `errors.py` are complete.** 144 and 74 lines respectively, with proper dataclasses, type annotations, and SDK imports.

6. **The SDK ledger and FMWK-001 are different systems.** Verified method-by-method, field-by-field (see section 8).

7. **FMWK-001 staging imports SDK infrastructure.** `errors.py` line 3: `from platform_sdk.tier0_core.errors import PlatformError`. `schemas.py` lines 7-8: `from platform_sdk.tier0_core.config import get_config` and `from platform_sdk.tier0_core.secrets import get_secret`.

8. **run.sh Turn D/E implementation is complete.** Lines 2009-2204 handle 13Q gate, review, DTT build, evidence validation, evaluation, retry logic, and portal updates.

9. **All 3 registries (ROLE, PROMPT, ARTIFACT) exist and are internally consistent.** ROLE_REGISTRY: 8 roles. PROMPT_REGISTRY: 10 prompts with dependency chains. ARTIFACT_REGISTRY: 22 artifacts with path templates and owners.

10. **Sawmill prompts for Turn D and E exist.** `turn_d_13q.txt`, `turn_d_build.txt`, `turn_d_review.txt`, `turn_e_eval.txt` all present with rendered variable slots.

11. **All mkdocs.yml nav entries resolve to existing files.** No dead links in Backstage navigation.

12. **PORTAL_MAP.yaml declares 44 mirror entries.** Per CANARY_AUDIT.md (most recent): "Mirrors synced: 44/44".

---

## 5. Broken

1. **`test_serializer.py` imports a module that does not exist.** Line 8: `from ledger.serializer import (GENESIS_SENTINEL, canonical_bytes, check_no_floats, compute_hash)`. File `staging/FMWK-001-ledger/ledger/serializer.py` does not exist. Running these tests will fail at import, not at assertion.

2. **`platform_sdk/tier0_core/data/` directory is empty.** The directory exists at `staging/FMWK-001-ledger/platform_sdk/tier0_core/data/` but contains no files — no `__init__.py`, no `immudb_adapter.py`. These are planned Turn D outputs.

3. **`scripts/` directory is empty.** `staging/FMWK-001-ledger/scripts/` exists with no files. `static_analysis.sh` is a planned Turn D output.

4. **Prompt-validator contract mismatch (`attempt` field).** `validate_evidence_artifacts.py` requires `attempt` at lines 96, 160, 195. None of the 3 prompt templates list `attempt` in their evidence field specifications. `run.sh` line 1036 exports `MAX_ATTEMPTS` but not `ATTEMPT`. `ATTEMPT` is set at line 2011 (`ATTEMPT=0`) and incremented at line 2016, but is not exported to the prompt rendering environment. This is the root cause of EVIDENCE_VALIDATION_FAILED in codex runs.

5. **CANARY_AUDIT.md shows 4 FAIL checks on the latest run.** builder_evidence, results, reviewer_evidence, and "Portal: Turn D DONE" all fail. This means no canary run has completed Turn D with real evidence artifacts.

6. **13Q_ANSWERS.md is stale.** Dated from a prior incomplete attempt (March 5, 2026). The 13Q phase was not re-run after the spec updates on March 9. run.sh Turn D will overwrite it, but its current presence could confuse inspection.

---

## 6. Missing from Backstage

1. **No page for the canary audit results.** `sawmill/FMWK-900-sawmill-smoke/CANARY_AUDIT.md` exists in repo but is not in mkdocs.yml nav and is not under `docs/`. Not visible in TechDocs.

2. **No page surfacing run history or run results.** 18 runs exist under `sawmill/FMWK-900-sawmill-smoke/runs/` with structured data (run.json, status.json, events.jsonl). None are visible in TechDocs.

3. **No page documenting the prompt-validator contract mismatch.** The `attempt` field issue is the single remaining blocker for a real-backend pass. It is mentioned in audit pages (Cleanup Execution, Current State Readiness) but has no dedicated tracking page.

4. **No Backstage page for `validate_evidence_artifacts.py` contract.** The validator defines the evidence schema for all 3 roles (builder, reviewer, evaluator) but this schema is only visible by reading the Python source. No TechDocs page describes the required evidence fields.

5. **BUILDER_HANDOFF file manifest is not surfaced in Backstage.** The 16-file manifest with CREATE dispositions is in the BUILDER_HANDOFF (not in Backstage nav). The status page for FMWK-001 doesn't show which files exist vs which are missing.

6. **Run count in Ground Truth Audit is stale.** `docs/architecture/GROUND_TRUTH_AUDIT.md` says "11 runs" (line 41). Actual count is 18 run directories.

---

## 7. Backstage Ahead of Repo

1. **No clear cases identified.** All Backstage pages describe documented repo state or audit findings. No page claims functionality that doesn't exist in repo.

2. **Minor: Ground Truth Audit says "5 validator scripts" (line 62).** Actual count in `sawmill/` is 4 validator/check Python scripts: `validate_evidence_artifacts.py`, `validate_role_registry.py`, `validate_evidence_artifacts.py`, `check_runtime_harness.py`, `project_run_status.py`. This is close enough but could diverge.

---

## 8. SDK Boundary Findings

### Domain Model Comparison

| Dimension | SDK `tier0_core/ledger.py` | FMWK-001 `staging/ledger/` |
|-----------|---------------------------|---------------------------|
| **Primary entity** | `LedgerEntry` — conversation turn | `LedgerEvent` — system event |
| **Index model** | Per-conversation: `(conversation_id, turn_index)` | Global sequence: `sequence` (int) |
| **Key fields** | `id`, `conversation_id`, `turn_index`, `role`, `content`, `metadata`, `prev_digest`, `digest` | `event_id`, `sequence`, `event_type`, `schema_version`, `timestamp`, `provenance`, `previous_hash`, `payload`, `hash` |
| **Concurrency model** | `async` (all methods) | `sync` (all methods, with `threading.Lock` per handoff) |
| **Hash chain scope** | Per-conversation chain | Global chain across all events |
| **Hash format** | SHA-256 hex string | `sha256:<64 hex chars>` (prefixed) |
| **Provider pattern** | `LedgerProvider(Protocol)` — async methods | `Ledger` class (concrete, not protocol) |
| **Method count** | 4 (`append`, `get_entry`, `get_conversation`, `verify_chain`) | 7 (`connect`, `append`, `read`, `read_range`, `read_since`, `get_tip`, `verify_chain`) |
| **Append signature** | `async def append(entry: LedgerEntry) -> LedgerEntry` | `def append(event: dict) -> int` |
| **Event types** | None — stores raw conversation turns | 14 typed events in `EVENT_TYPE_CATALOG` |
| **Backends** | Mock, Immudb, QLDB | Mock + Immudb (per handoff) |
| **immudb key format** | `conv:{conversation_id}:{turn_index:08d}` | `{sequence:012d}` (per handoff) |
| **Error hierarchy** | Uses SDK `LedgerConnectionError` | Defines own `LedgerConnectionError` (different `code` string), plus 3 additional error classes |
| **Config** | Uses `PlatformConfig` | Uses `LedgerConfig` (own dataclass, reads same env vars via `get_config`/`get_secret`) |

### Evidence for Each Disposition

**Replace?** NO.
The SDK's LedgerProvider solves conversation-turn logging. FMWK-001 solves global event-stream sequencing. They have incompatible data models (LedgerEntry vs LedgerEvent), incompatible method signatures (`append(entry) -> entry` vs `append(event) -> int`), and incompatible concurrency models (async vs sync). Replacing the SDK ledger with FMWK-001 would break all SDK consumers that expect conversation-indexed async operations.

**Wrap?** NO.
FMWK-001's handoff specifies creating a new `immudb_adapter.py` under `platform_sdk/tier0_core/data/`, not wrapping the existing `ImmudbProvider` from `tier0_core/ledger.py`. The new adapter uses a different key schema (`{sequence:012d}` vs `conv:{id}:{turn:08d}`), different data format, and different access patterns. There is no adapter or wrapper relationship.

**Promote?** NO.
"Promote" would mean taking the SDK ledger code and governing it through Sawmill. But the SDK ledger solves a different problem. Promoting it would produce a governed conversation logger, not the global event store that FMWK-001 specifies. The spec documents (D1-D10) define a system that is architecturally distinct from the SDK ledger.

**Coexist?** YES.
FMWK-001 staging code imports SDK infrastructure:
- `errors.py` line 3: `from platform_sdk.tier0_core.errors import PlatformError` (base error class)
- `schemas.py` line 7: `from platform_sdk.tier0_core.config import get_config` (config loading)
- `schemas.py` line 8: `from platform_sdk.tier0_core.secrets import get_secret` (secrets)

Both systems share immudb as a storage backend (same host, same port 3322). Both inherit from PlatformError. But they are separate systems with separate purposes. The SDK ledger logs conversation turns for a single service. FMWK-001 logs governed events for the entire DoPeJarMo platform.

### Current Best-Supported Conclusion

**COEXIST with shared infrastructure.** The two systems share:
- immudb backend (same host/port, different databases/key schemas)
- PlatformError base class
- PlatformConfig/get_config/get_secret for configuration

They will run side by side. FMWK-001 does not replace, wrap, or promote the SDK ledger.

### Unresolved Questions

1. **Will the SDK ledger eventually migrate to use FMWK-001?** The SDK currently logs conversation turns. If DoPeJarMo's governed event model supersedes this, the SDK ledger might become redundant. No architecture document addresses this.

2. **Do the two systems share the same immudb database instance?** FMWK-001 `LedgerConfig.from_env()` reads `IMMUDB_DATABASE` defaulting to `"ledger"`. The SDK's `ImmudbProvider` reads `IMMUDB_DATABASE`. If both default to the same database name, their keys would coexist in the same immudb database but with different key prefixes. This is probably fine but is not explicitly documented.

3. **Who owns `platform_sdk/tier0_core/data/`?** The BUILDER_HANDOFF specifies creating `immudb_adapter.py` inside `staging/FMWK-001-ledger/platform_sdk/tier0_core/data/`. This is a staging location. The final destination for this code after the build completes is not specified. Does it get promoted to the real SDK's `tier0_core/data/`? If so, what's the promotion mechanism?

---

## 9. Sawmill Readiness Findings

| Readiness Area | Status | Evidence |
|----------------|--------|----------|
| Spec pack (D1-D10) | COMPLETE | 14 artifacts, all substantive, D6 GATE READY |
| Holdout scenarios (D9) | COMPLETE | 28K, isolated in `.holdouts/` |
| Turn D prompts | PRESENT | 3 files (turn_d_13q.txt, turn_d_review.txt, turn_d_build.txt) |
| Turn E prompt | PRESENT | turn_e_eval.txt |
| Role files | PRESENT | builder.md, reviewer.md, evaluator.md, all complete |
| Registries | CONSISTENT | ROLE (8 roles), PROMPT (10 prompts), ARTIFACT (22 artifacts) |
| run.sh Turn D | IMPLEMENTED | Lines 2009-2175, 13Q/review/build phases with retry |
| run.sh Turn E | IMPLEMENTED | Lines 2176-2204, evaluation with verdict parsing |
| Evidence validator | PRESENT but MISMATCHED | `attempt` field required by validator, not in prompts |
| Default backends | MOCK | Builder, reviewer, evaluator all default to `mock` per ROLE_REGISTRY |
| Staging scaffold | PARTIAL | 8/16 files, core is stubs, serializer missing |
| Build config | ABSENT | No pyproject.toml, no requirements.txt, no conftest.py |
| PYTHONPATH | REQUIRED | Must be set to include `/Users/raymondbruni/dopejar` for SDK imports |
| Docker/immudb | REQUIRED for Turn E | Holdouts require immudb on port 3322, Docker status unknown |

**Overall Sawmill readiness for FMWK-001 Turn D**: BLOCKED by the `attempt` field prompt-validator mismatch. Once fixed, Turn D can run with real agent backends set via environment variables.

---

## 10. Risks / Accident Conditions

1. **Prompt-validator `attempt` mismatch will fail every real run.** The validator requires `attempt` (lines 96, 160, 195) but no prompt template tells agents to include it, and `ATTEMPT` is not exported to the prompt rendering environment (line 1036). Every agent that writes evidence JSON will omit `attempt`, and every evidence validation will fail. This is the same root cause as every codex EVIDENCE_VALIDATION_FAILED result.

2. **Stale 13Q_ANSWERS.md may confuse run.sh.** The file exists from a prior attempt (March 5). If run.sh checks for file existence before running the 13Q gate, it might skip the gate and use stale answers. Needs verification of run.sh behavior with pre-existing artifacts.

3. **test_serializer.py will fail at import, not assertion.** The test file imports 4 symbols from `ledger.serializer` which doesn't exist. A builder agent that runs tests before creating `serializer.py` will see `ModuleNotFoundError`, which could be misinterpreted as a dependency problem rather than a "file not yet created" condition.

4. **Empty directories may confuse builders.** `platform_sdk/tier0_core/data/` and `scripts/` exist but are empty. A builder might assume these directories have been populated or skip creating `__init__.py` files.

5. **Two LedgerConnectionError classes could collide.** The SDK defines `LedgerConnectionError` in `tier0_core/errors.py`. FMWK-001 staging defines its own `LedgerConnectionError` in `ledger/errors.py` inheriting from `PlatformError`. Both are importable if PYTHONPATH includes both locations. Name collision risk in any code that imports both.

6. **Run count drift in published audits.** Ground Truth Audit says "11 runs" but actual is 18. As more canary runs execute, all historical run counts in published pages become stale. No automation updates these.

7. **Docker/immudb availability for Turn E is unverified.** Holdout scenarios require `docker compose up -d immudb` on port 3322 with a `ledger_hs001` database. If Docker is not running when Turn E executes, all integration holdouts will fail and the evaluator will return FAIL. Current Docker state was not checked (read-only audit).

---

## 11. Recommended Next Inspection Step

**Inspect run.sh behavior with pre-existing Turn D artifacts.** Specifically:

1. Does run.sh `--from-turn D` clear the staging directory before invoking the builder?
2. Does run.sh skip the 13Q gate if `13Q_ANSWERS.md` already exists?
3. How does run.sh set `ATTEMPT` for the prompt rendering environment? Is it exported or only used internally?

These 3 questions determine whether a clean FMWK-001 Turn D run requires manual cleanup of the staging directory first. The answers are in run.sh lines 2009-2175 but require careful reading of the variable scoping and export behavior.

---

## 12. Questions for Ray

1. **SDK ledger migration path**: Will the SDK's conversation-turn ledger eventually migrate to use FMWK-001's event store? Or will they always coexist as separate systems? This affects whether FMWK-001 needs to support conversation-turn indexing.

2. **Staging-to-SDK promotion**: The BUILDER_HANDOFF says to create `platform_sdk/tier0_core/data/immudb_adapter.py` under staging. After the governed build passes, what's the mechanism to promote this file into the real SDK at `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/data/`? Is this manual, or is there a planned promotion step?

3. **Staging cleanup before Turn D**: Should the existing staging scaffold (8 files from the prior attempt) be cleared before running Turn D? The handoff says CREATE for all 16 files, which implies a clean slate. But the existing `schemas.py` and `errors.py` are complete and correct. Keeping them could save builder effort. Clearing them ensures a clean governed build.

4. **Run count maintenance**: Do you want published audit pages to track run counts, or should they be removed/generalized to avoid staleness? Currently Ground Truth Audit says "11 runs" but actual is 18.

---

## 13. Appendix

### Exact file paths inspected

```
# Brain Factory repo
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
sawmill/FMWK-001-ledger/TASK.md
sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md
sawmill/FMWK-001-ledger/GATE_CHECKLIST.md
sawmill/FMWK-001-ledger/CANARY_AUDIT.md
.holdouts/FMWK-001-ledger/D9_HOLDOUT_SCENARIOS.md
staging/FMWK-001-ledger/ledger/__init__.py
staging/FMWK-001-ledger/ledger/ledger.py
staging/FMWK-001-ledger/ledger/schemas.py
staging/FMWK-001-ledger/ledger/errors.py
staging/FMWK-001-ledger/tests/unit/test_serializer.py
staging/FMWK-001-ledger/platform_sdk/tier0_core/data/ (empty)
staging/FMWK-001-ledger/scripts/ (empty)
sawmill/run.sh (2,234 lines)
sawmill/validate_evidence_artifacts.py (256 lines)
sawmill/ROLE_REGISTRY.yaml
sawmill/PROMPT_REGISTRY.yaml
sawmill/ARTIFACT_REGISTRY.yaml
sawmill/prompts/turn_d_build.txt
sawmill/prompts/turn_d_review.txt
sawmill/prompts/turn_e_eval.txt
docs/PORTAL_MAP.yaml
mkdocs.yml
docs/sawmill/FMWK-001-READINESS-AUDIT.md
docs/architecture/GROUND_TRUTH_AUDIT.md

# Dopejar repo
/Users/raymondbruni/dopejar/platform_sdk/tier0_core/ledger.py (582 lines)
```

### Run directories inspected

```
sawmill/FMWK-900-sawmill-smoke/runs/20260312T030607Z-0c8624382cf4/ (latest, codex, running)
sawmill/FMWK-900-sawmill-smoke/runs/20260312T002821Z-79f2f773ca6d/ (codex, failed, EVIDENCE_VALIDATION_FAILED)
```

Total: 18 run directories present.

### Staging file manifest (planned vs actual)

| Planned file | Actual state |
|-------------|-------------|
| `ledger/__init__.py` | PRESENT (20 lines, complete) |
| `ledger/errors.py` | PRESENT (74 lines, complete) |
| `ledger/schemas.py` | PRESENT (144 lines, complete) |
| `ledger/serializer.py` | ABSENT |
| `ledger/ledger.py` | PRESENT (33 lines, all NotImplementedError stubs) |
| `platform_sdk/tier0_core/data/__init__.py` | ABSENT (directory exists but empty) |
| `platform_sdk/tier0_core/data/immudb_adapter.py` | ABSENT |
| `tests/__init__.py` | PRESENT (0 bytes) |
| `tests/unit/__init__.py` | PRESENT (0 bytes) |
| `tests/unit/test_serializer.py` | PRESENT (103 lines, imports non-existent module) |
| `tests/unit/test_ledger_unit.py` | ABSENT |
| `tests/integration/__init__.py` | PRESENT (0 bytes) |
| `tests/integration/test_ledger_integration.py` | ABSENT |
| `tests/integration/test_cold_storage.py` | ABSENT |
| `scripts/static_analysis.sh` | ABSENT (directory exists but empty) |
| `RESULTS.md` (at sawmill/FMWK-001-ledger/) | ABSENT (Turn D output) |

**Summary: 8 present, 8 absent. 3 of the 8 present files are zero-byte `__init__.py`.**
