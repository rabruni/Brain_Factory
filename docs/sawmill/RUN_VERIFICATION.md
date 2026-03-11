# Sawmill Run Verification

**Status**: NARRATIVE CHECKLIST
**Authority label**: narrative
**Date**: 2026-03-10

This page is a steward-owned verification checklist.
Runtime authority remains:

- `sawmill/run.sh`
- `sawmill/EXECUTION_CONTRACT.md`
- `sawmill/ROLE_REGISTRY.yaml`
- `sawmill/PROMPT_REGISTRY.yaml`
- `sawmill/ARTIFACT_REGISTRY.yaml`

## Canonical Command

Normal path:

```bash
./sawmill/run.sh <FMWK-ID>
```

Interactive exception path:

```bash
./sawmill/run.sh <FMWK-ID> --interactive
```

### Canary Backend Override

The Turn A worker backend was temporarily switched from Codex to Claude
due to Codex CLI connectivity failures observed during the first governed canary.

This override is configuration-only and does not modify the Sawmill runtime harness.

Additional Note:
The Claude CLI backend required interactive login on the canary host.
For canary execution only, the backend was switched to a non-interactive API-backed worker (Gemini) so the governed pipeline can execute without manual login steps.

## Successful Governed Canary

- run id: `20260311T212607Z-9ef3153f5266`
- final state: `passed`
- governed_path_intact: `true`
- harness checker: `PASS`

This successful pass used deterministic mock/canary worker backends for controlled pipeline validation.

This validates the runtime truth model, not external backend reliability.

## Verification Order

### 1. Core artifact directories

Check:

- `sawmill/<FMWK-ID>/`
- `sawmill/<FMWK-ID>/runs/<run-id>/`
- `.holdouts/<FMWK-ID>/`
- `staging/<FMWK-ID>/`

Harness artifacts required per run:

- `run.json`
- `status.json`
- `events.jsonl`
- `logs/<step>.stdout.log`
- `logs/<step>.stderr.log`

Expected artifacts by turn:

- Turn A: `D1_CONSTITUTION.md` ... `D6_GAP_ANALYSIS.md`
- Turn B: `D7_PLAN.md`, `D8_TASKS.md`, `D10_AGENT_CONTEXT.md`, `BUILDER_HANDOFF.md`
- Turn C: `.holdouts/<FMWK-ID>/D9_HOLDOUT_SCENARIOS.md`
- Turn D review: `13Q_ANSWERS.md`, `REVIEW_REPORT.md`, `REVIEW_ERRORS.md`
- Turn D build: `RESULTS.md`, `builder_evidence.json`
- Turn D review evidence: `reviewer_evidence.json`
- Turn E: `EVALUATION_REPORT.md`, `EVALUATION_ERRORS.md`, `evaluator_evidence.json`
- Stage audit: `CANARY_AUDIT.md`

### 2. Turn D contract-version evidence (required)

Verify these exact lines exist and are parseable exactly once:

- In `13Q_ANSWERS.md`:
  - `Builder Prompt Contract Version: <version>`
- In `REVIEW_REPORT.md`:
  - `Builder Prompt Contract Version Reviewed: <version>`
  - `Reviewer Prompt Contract Version: <version>`

These values must match the active template contract versions consumed by runtime.

### 3. Verdict line parsing evidence

Runtime parses the last non-empty line of each verdict artifact.
Confirm final lines are exactly:

- `REVIEW_REPORT.md`: `Review verdict: PASS|RETRY|ESCALATE`
- `EVALUATION_REPORT.md`: `Final verdict: PASS|FAIL`

### 4. Harness/state convergence evidence

Check `status.json` against `events.jsonl`:

- `run_id` matches the run directory
- `state` is one of:
  - `running`
  - `retrying`
  - `escalated`
  - `failed`
  - `passed`
  - `invalidated`
- if `governed_path_intact=false`, final PASS is not allowed unless operator mode explicitly permits intervention
- docs/sawmill status page reflects:
  - current run id
  - runtime state
  - governed-path state

Required rebuild check:

```bash
cp sawmill/<FMWK-ID>/runs/<RUN-ID>/status.json /tmp/<RUN-ID>.status.json.bak
rm sawmill/<FMWK-ID>/runs/<RUN-ID>/status.json
python3 sawmill/project_run_status.py project-status --run-dir sawmill/<FMWK-ID>/runs/<RUN-ID>
diff -u /tmp/<RUN-ID>.status.json.bak sawmill/<FMWK-ID>/runs/<RUN-ID>/status.json
```

If literal diff is too strict for local formatting reasons, semantic JSON equality is still REQUIRED.

### 5. Portal evidence

Check:

- `docs/sawmill/<FMWK-ID>.md`
- `docs/PORTAL_STATUS.md`
- `sawmill/PORTAL_CHANGESET.md`

Portal may be unchanged when already current; unchanged content alone is not failure.

### 6. Required validation commands

```bash
python3 docs/lint_runtime_claims.py
python3 docs/validate_portal_map.py
python3 sawmill/validate_role_registry.py --registry sawmill/ROLE_REGISTRY.yaml
python3 sawmill/validate_artifact_registry.py --registry sawmill/ARTIFACT_REGISTRY.yaml --roles sawmill/ROLE_REGISTRY.yaml
python3 sawmill/validate_prompt_registry.py --registry sawmill/PROMPT_REGISTRY.yaml --roles sawmill/ROLE_REGISTRY.yaml --artifacts sawmill/ARTIFACT_REGISTRY.yaml
python3 sawmill/check_runtime_harness.py --run-dir sawmill/<FMWK-ID>/runs/<RUN-ID>
python3 sawmill/validate_evidence_artifacts.py --kind builder --artifact sawmill/<FMWK-ID>/builder_evidence.json --run-id <RUN-ID> --attempt <ATTEMPT> --handoff sawmill/<FMWK-ID>/BUILDER_HANDOFF.md --q13-answers sawmill/<FMWK-ID>/13Q_ANSWERS.md --results sawmill/<FMWK-ID>/RESULTS.md
python3 sawmill/validate_evidence_artifacts.py --kind reviewer --artifact sawmill/<FMWK-ID>/reviewer_evidence.json --run-id <RUN-ID> --attempt <ATTEMPT> --q13-answers sawmill/<FMWK-ID>/13Q_ANSWERS.md
python3 sawmill/validate_evidence_artifacts.py --kind evaluator --artifact sawmill/<FMWK-ID>/evaluator_evidence.json --run-id <RUN-ID> --attempt <ATTEMPT> --holdouts .holdouts/<FMWK-ID>/D9_HOLDOUT_SCENARIOS.md --staging-root staging/<FMWK-ID>
bash -n sawmill/run.sh
```

## PASS / FAIL Interpretation

Treat run as PASS only when all are true:

- `EVALUATION_REPORT.md` exists
- last verdict line is `Final verdict: PASS`
- required Turn D version evidence is present and coherent
- required evidence JSON files validate
- `status.json` is derivable from `events.jsonl`
- harness acceptance checks pass
- required stage audit evidence passes
- portal map validation passes
- runtime-claim lint passes

Treat run as FAIL when any are true:

- required stage artifact missing
- reviewer verdict is `ESCALATE`
- evaluator verdict is `FAIL` after retry exhaustion
- required version evidence missing/malformed/mismatched
- evidence JSON missing, malformed, or contradictory
- manual intervention occurred and runtime state is `invalidated`
- portal map validation fails
- runtime-claim lint fails

## Scope Clarifier

Sawmill runtime ends in PASS or FAIL.
Merge/release actions are out-of-scope for runtime verification.
