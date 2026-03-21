# run.sh — Functional Areas

`sawmill/run.sh` is a ~2,500-line bash wrapper that glues together Python services. This page maps every function to its area so we know what to extract next.

## Functional Area Table

| # | Area | Functions | What it does |
|---|------|-----------|-------------|
| 1 | **CLI & Config** | `usage`, arg parsing, `validate_agent_timeout`, color defs, mode selection | Parse `--from-turn`, `--interactive`, `--audit`. Set operator mode. |
| 2 | **Registry Loading** | `load_role_registry`, `load_artifact_registry`, `load_stage_artifact_metadata`, `load_prompt_registry`, `load_prompt_contract_versions` | Validate + eval shell exports from 4 YAML registries. Backend resolution, allowed-backends check. |
| 3 | **Artifact Resolution** | `artifact_path`, `artifact_kind`, `artifact_exists`, `ensure_artifact_exists`, `ensure_artifact_ids`, `export_artifact_paths`, `stage_all_artifacts`, `stage_required_artifacts`, `stage_is_complete`, `stage_has_any_artifacts`, `artifact_newer_than`, `artifact_present_for_state` | Map artifact IDs → filesystem paths via `{FMWK}` templates. Check existence, stage completeness. |
| 4 | **Artifact Invalidation** | `invalidate_artifact`, `invalidate_downstream_artifacts` | Delete artifacts for rerun from a given turn. |
| 5 | **Prompt Management** | `prompt_file`, `prompt_expected_artifacts`, `prompt_required_artifacts`, `prompt_freshness_policy`, `prompt_role`, `prompt_turn`, `render_prompt_output`, `ensure_prompt_inputs`, `verify_prompt_outputs`, `snapshot_prompt_outputs`, `cleanup_prompt_sentinel` | Resolve prompt metadata, render templates via `render_prompt.py`, verify outputs exist and are fresh. |
| 6 | **Evidence & Hashing** | `compute_evidence_hash`, `export_evidence_hashes`, `hash_file`, `validate_evidence_artifact`, `validate_builder_evidence`, `validate_reviewer_evidence`, `validate_evaluator_evidence`, `validate_final_evidence_suite` | Pre-compute SHA-256 hashes, call `validate_evidence_artifacts.py`. |
| 7 | **Run Harness (Event Log)** | `initialize_run_harness`, `new_run_id`, `new_event_id`, `iso_timestamp`, `emit_event`, `record_run_failed`, `record_escalation`, `record_manual_intervention`, `project_status_now`, `current_status_field`, `build_run_metadata_file` | Create run dir, init status.json, emit events to events.jsonl, project status via `project_run_status.py`. |
| 8 | **Agent Invocation** | `invoke_agent`, `invoke_prompt`, `launch_prompt_background`, `require_backend_cli`, `run_with_timeout`, `stop_background_pid`, `write_invocation_payload`, `write_invocation_meta`, `emit_liveness_records` | Build invocation metadata, delegate to `runner.py`, poll liveness, parse result.json, emit exit events. |
| 9 | **Verdict Parsing** | `review_verdict`, `evaluation_verdict`, `extract_exact_version_evidence`, `require_version_evidence` | Parse last line of reports for PASS/RETRY/ESCALATE/FAIL. Extract contract version strings. |
| 10 | **Portal & Audit** | `update_portal_state`, `run_portal_steward`, `run_stage_audit`, `validate_convergence` | Update status page, run portal-steward agent, run ~30 canary audit checks, validate final convergence. |
| 11 | **Pipeline Orchestration** | Turn A → B+C parallel → D retry loop → E eval, standalone E path, audit mode path | Turn sequencing: skip logic, input checks, invoke workers, handle verdicts, retry/escalate. |
| 12 | **Preflight** | File checks, CLI availability, symlink creation, factory contract validation | Verify everything exists before starting. |

## What stays in bash

Only #1 (CLI) and #11 (pipeline orchestration) need to be bash — they're the thin wrapper that parses args and calls Python in order.

## What moves to Python

Everything else. Areas 2-10 and 12 are already calling Python scripts or doing work that Python handles better (JSON manipulation, YAML parsing, hash computation, filesystem walks, event emission).

## Existing Python services

These already exist and handle the real work:

| Script | Area(s) it serves |
|--------|-------------------|
| `runner.py` | 8 — Agent invocation |
| `project_run_status.py` | 7 — Event log, status projection |
| `render_prompt.py` | 5 — Prompt template rendering |
| `validate_evidence_artifacts.py` | 6 — Evidence hash validation |
| `validate_role_registry.py` | 2 — Role registry validation |
| `validate_artifact_registry.py` | 3 — Artifact registry validation |
| `validate_prompt_registry.py` | 5 — Prompt registry validation |
| `resolve_stage_artifacts.py` | 3, 4 — Stage artifact resolution |
| `validate_factory_contracts.py` | 12 — Preflight contract check |
| `sync_portal_mirrors.py` | 10 — Portal mirror sync |
| `run_with_timeout.py` | 8 — Timeout wrapper |
| `backend_adapters.py` | 8 — Backend CLI adapters |
