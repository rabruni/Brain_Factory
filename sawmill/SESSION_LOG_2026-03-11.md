# Sawmill Session Log — 2026-03-11

## Purpose

This file records the exact Sawmill state at reboot time so the work can resume without reconstruction.

This log is a human-readable operational record.
It does **not** replace the harness truth model.

## What Was Accomplished

### Harness and runtime truth model

The Sawmill harness is now substantially implemented and treated as the runtime baseline:

- Normative spec exists:
  - `architecture/SAWMILL_RUNTIME_SPEC_v0.1.md`
- Harness utilities exist:
  - `sawmill/project_run_status.py`
  - `sawmill/validate_evidence_artifacts.py`
  - `sawmill/check_runtime_harness.py`
- `run.sh` remains the canonical entry path.
- Runs now create:
  - `run.json`
  - `status.json`
  - `events.jsonl`
  - per-step stdout/stderr logs
- Manual intervention is part of the truth model and invalidates governed PASS.

### Worker/backend stabilization work

External worker backends failed repeatedly during canary validation:

- `codex` failed with connectivity / startup errors
- `claude` failed because the local CLI required interactive login
- `gemini` hung and timed out

To get deterministic progress without changing the harness model, the existing `mock` backend path was extended for canary use.

Current deterministic worker files:

- `sawmill/workers/mock_worker.py`
- `sawmill/workers/canary_mock_worker.py`

Important implementation detail:

- `run.sh` was **not** changed for backend authority in this last step.
- Because `run.sh` only dispatches the existing `mock` backend, the deterministic canary worker is routed through `mock`, not a new backend key.
- `mock_worker.py` is now a thin wrapper over `canary_mock_worker.py`.

### Current canary backend configuration

The following canary roles were switched to the deterministic `mock` backend in:

- `sawmill/ROLE_REGISTRY.yaml`

Current role defaults for the canary path:

- `spec-agent` -> `mock`
- `holdout-agent` -> `mock`
- `builder` -> `mock`
- `reviewer` -> `mock`
- `evaluator` -> `mock`
- `portal-steward` -> `mock`

This was done to isolate the next true blocker beyond external AI connectivity.

## Latest Real Run

Latest run directory:

- `sawmill/FMWK-900-sawmill-smoke/runs/20260311T151450Z-e2729fcb4880`

### What this run proved

The deterministic worker path successfully moved the canary far beyond the original Turn A backend failure.

This governed run successfully completed:

- Turn A (spec)
- portal stage after Turn A
- Turn B (plan)
- Turn C (holdout)
- portal stage after Turn B/C
- Turn D 13Q

So the current deterministic backend strategy **did work** for:

- spec-agent
- holdout-agent
- builder 13Q
- portal-steward

### Current blocker exposed by that run

The run failed before reviewer execution in Turn D.

Failure point:

- `turn_d_review`

Recorded failure code:

- `PROMPT_RENDER_FAILED`

Observed cause:

- `sawmill/prompts/turn_d_review.txt` contains `{{ATTEMPT}}`
- the prompt renderer failed because `ATTEMPT` was not available at render time

Relevant prompt placeholders still present:

- `sawmill/prompts/turn_d_review.txt`
- `sawmill/prompts/turn_d_build.txt`
- `sawmill/prompts/turn_e_eval.txt`

All still contain:

- `{{ATTEMPT}}`

## Exact State of the Latest Failed Run

The run directory contains:

- `run.json`
- `events.jsonl`
- `logs/`
- `status.json.bak`

Important:

- `status.json` is currently **missing**
- this happened because the harness checker rebuild step removed it and the projection rebuild failed

That means two things are true at once:

1. The governed run itself failed at Turn D review prompt rendering.
2. The harness checker exposed a projection/path consistency bug because `status.json` could not be rebuilt from `events.jsonl` for this failed run.

### Last known projected state

From `status.json.bak` before rebuild:

- `current_turn = D`
- `current_step = turn_d_review`
- `current_role = reviewer`
- `current_backend = mock`
- `state = running`
- `latest_failure_code = PROMPT_RENDER_FAILED`
- `governed_path_intact = true`

This state is stale only because projection rebuild failed; it is not a trustworthy terminal projection.

### Last causal events in `events.jsonl`

The final events of the latest run are:

- `turn_started` for Turn D
- `prompt_rendered` for `turn_d_13q`
- `agent_invoked` for `turn_d_13q`
- `agent_exited` for `turn_d_13q`
- `output_verified` for `turn_d_13q`
- `prompt_rendered` for `turn_d_review` with `failure_code = PROMPT_RENDER_FAILED`
- `run_failed` with `failure_code = PROMPT_RENDER_FAILED`

This is important because it means the deterministic workers are no longer the immediate problem.
The next blocker is in the runtime prompt/render/projection path.

## Current Interpretation

At this point, the next blocker is **not**:

- Codex connectivity
- Claude login
- Gemini timeout
- Turn A backend instability

The next blocker is:

1. prompt rendering for `turn_d_review`
2. harness projection/rebuild on that failure path

This is good progress: the pipeline is now failing later and more honestly.

## Resume Checklist

After reboot, resume in this order.

### 1. Re-establish repo state

From repo root:

```bash
pwd
git status --short
```

Expected repo root:

- `/Users/raymondbruni/Cowork/Brain_Factory`

### 2. Re-open the core runtime truth files

Read these first:

- `CLAUDE.md`
- `architecture/SAWMILL_RUNTIME_SPEC_v0.1.md`
- `sawmill/SESSION_LOG_2026-03-11.md`
- `sawmill/run.sh`
- `sawmill/PROMPT_REGISTRY.yaml`
- `sawmill/ROLE_REGISTRY.yaml`

### 3. Re-inspect the latest failed run

Run:

```bash
ls -la sawmill/FMWK-900-sawmill-smoke/runs/20260311T151450Z-e2729fcb4880
python3 - <<'PY'
from pathlib import Path
run = Path("sawmill/FMWK-900-sawmill-smoke/runs/20260311T151450Z-e2729fcb4880")
for line in (run / "events.jsonl").read_text().splitlines()[-12:]:
    print(line)
PY
```

### 4. Reconfirm the prompt-render blocker

Run:

```bash
rg -n "ATTEMPT" sawmill/prompts/turn_d_review.txt sawmill/prompts/turn_d_build.txt sawmill/prompts/turn_e_eval.txt
```

### 5. Reconfirm the projection failure

Run:

```bash
python3 sawmill/project_run_status.py project-status --run-dir sawmill/FMWK-900-sawmill-smoke/runs/20260311T151450Z-e2729fcb4880
```

Expected current outcome:

- non-zero failure

### 6. Reconfirm harness checker behavior

Run:

```bash
python3 sawmill/check_runtime_harness.py --run-dir sawmill/FMWK-900-sawmill-smoke/runs/20260311T151450Z-e2729fcb4880
```

Expected current outcome:

- fail, because projection rebuild currently fails on this run

## What To Work On Next

## Closeout — Harness Baseline Frozen

The following root causes were fixed after the failed Turn D review run:

- unsupported `{{ATTEMPT}}` placeholder in Turn D/E prompt templates
- projector rejection of `run_failed` after failed `prompt_rendered`

Successful governed canary run:

- run id: `20260311T212607Z-9ef3153f5266`
- final_state: `passed`
- governed_path_intact: `true`
- harness_validation_result: `PASS`

The Sawmill harness layer is now considered stable for v0.1.

The next engineering target is **not** more worker stabilization.

The next engineering target is:

### Primary blocker

Fix the Turn D review prompt/render path so `turn_d_review` can render and execute.

### Secondary blocker

Fix the failure/projection path so `status.json` can always be rebuilt from `events.jsonl`, even after prompt-render failures.

### Only after that

Re-run the canary and push it through:

- review
- build
- evaluation

using the same deterministic worker strategy already in place.

## Files Most Relevant To Resume

### Runtime/harness

- `architecture/SAWMILL_RUNTIME_SPEC_v0.1.md`
- `sawmill/run.sh`
- `sawmill/project_run_status.py`
- `sawmill/check_runtime_harness.py`
- `sawmill/validate_evidence_artifacts.py`

### Worker/backend stabilization

- `sawmill/ROLE_REGISTRY.yaml`
- `sawmill/workers/mock_worker.py`
- `sawmill/workers/canary_mock_worker.py`

### Prompt/render path

- `sawmill/prompts/turn_d_review.txt`
- `sawmill/prompts/turn_d_build.txt`
- `sawmill/prompts/turn_e_eval.txt`
- `sawmill/PROMPT_REGISTRY.yaml`

### Latest governed run evidence

- `sawmill/FMWK-900-sawmill-smoke/runs/20260311T151450Z-e2729fcb4880/`

## Current Bottom Line

The session is at a much better place than before reboot:

- Turn A worker stabilization is solved for canary purposes
- the canary now gets through A, B, C, portal sync, and Turn D 13Q
- the next blocker is a real runtime prompt/projection problem, not external AI service instability

That is the exact point to resume from.
