# Sawmill Run Verification

This page is the portal-steward-owned verification checklist for Sawmill runs.

It does **not** replace runtime source truth. The runtime authority remains:

- `sawmill/run.sh`
- `sawmill/ROLE_REGISTRY.yaml`
- `sawmill/PROMPT_REGISTRY.yaml`
- `sawmill/ARTIFACT_REGISTRY.yaml`
- `sawmill/EXECUTION_CONTRACT.md`

Use this page when you want the shortest path to answering:

- Did the run really happen?
- Which stage completed?
- Did the reviewer/evaluator loop run?
- Did the portal update?
- Did the pipeline end in PASS or FAIL?

## Canonical Run Command

Normal unattended path:

```bash
./sawmill/run.sh FMWK-900-sawmill-smoke
```

Interactive exception path:

```bash
./sawmill/run.sh FMWK-900-sawmill-smoke --interactive
```

## Verification Order

Check evidence in this order.

### 1. Framework artifact directory

Look in:

- `sawmill/<FMWK-ID>/`

Expected progression:

- Turn A: `D1_CONSTITUTION.md` through `D6_GAP_ANALYSIS.md`
- Turn B: `D7_PLAN.md`, `D8_TASKS.md`, `D10_AGENT_CONTEXT.md`, `BUILDER_HANDOFF.md`
- Turn D review loop:
  - `13Q_ANSWERS.md`
  - `REVIEW_REPORT.md`
  - `REVIEW_ERRORS.md`
- Turn D build:
  - `RESULTS.md`
- Turn E:
  - `EVALUATION_REPORT.md`
  - `EVALUATION_ERRORS.md`
- Stage audit:
  - `CANARY_AUDIT.md`

### 2. Holdout directory

Look in:

- `.holdouts/<FMWK-ID>/`

Expected file:

- `D9_HOLDOUT_SCENARIOS.md`

### 3. Staging directory

Look in:

- `staging/<FMWK-ID>/`

Expected result:

- built code owned by the framework
- non-empty directory when Turn D succeeded

### 4. Reviewer loop evidence

The reviewer loop happened only if all three are present:

- `sawmill/<FMWK-ID>/13Q_ANSWERS.md`
- `sawmill/<FMWK-ID>/REVIEW_REPORT.md`
- `sawmill/<FMWK-ID>/REVIEW_ERRORS.md`

Interpretation:

- the last non-empty line `Review verdict: PASS` means build was allowed to proceed
- the last non-empty line `Review verdict: RETRY` means one attempt was consumed before implementation
- the last non-empty line `Review verdict: ESCALATE` means the run should have stopped for human intervention

### 5. Evaluation evidence

The evaluation loop happened only if both are present:

- `sawmill/<FMWK-ID>/EVALUATION_REPORT.md`
- `sawmill/<FMWK-ID>/EVALUATION_ERRORS.md`

Interpretation:

- the last non-empty line `Final verdict: PASS` means the framework completed successfully
- the last non-empty line `Final verdict: FAIL` means the attempt failed and the retry loop should continue or exhaust

### 6. Portal evidence

Check these files:

- `docs/sawmill/<FMWK-ID>.md`
- `docs/PORTAL_STATUS.md`
- `sawmill/PORTAL_CHANGESET.md`

Expected meaning:

- `docs/sawmill/<FMWK-ID>.md` reflects current stage completion
- `docs/PORTAL_STATUS.md` shows portal health for the run
- `sawmill/PORTAL_CHANGESET.md` records what portal-steward changed this run

### 7. Portal validator

Run:

```bash
python3 docs/validate_portal_map.py
```

Expected result:

- PASS

## PASS / FAIL Interpretation

Treat the run as **PASS** only when all of these are true:

- `EVALUATION_REPORT.md` exists
- the last verdict is `Final verdict: PASS`
- `CANARY_AUDIT.md` exists and passes
- `docs/sawmill/<FMWK-ID>.md` reflects the completed state
- `docs/validate_portal_map.py` passes

Treat the run as **FAIL** when any of these happen:

- a required artifact for the current stage is missing
- `REVIEW_REPORT.md` ends with `Review verdict: ESCALATE`
- `EVALUATION_REPORT.md` ends with `Final verdict: FAIL` after retry exhaustion
- `CANARY_AUDIT.md` records failure
- portal validation fails

## Fast Human Checklist

For a quick manual verification:

1. Open `sawmill/<FMWK-ID>/EVALUATION_REPORT.md`
2. Confirm the last line is `Final verdict: PASS`
3. Open `sawmill/<FMWK-ID>/CANARY_AUDIT.md`
4. Confirm it passed
5. Open `docs/sawmill/<FMWK-ID>.md`
6. Confirm the page reflects the final state
7. Run `python3 docs/validate_portal_map.py`

If all seven checks pass, the run is complete and the portal reflects the filesystem state.

## Fast Agent Checklist

For an orchestrator or reviewer summarizing a run:

1. Read `sawmill/<FMWK-ID>/REVIEW_REPORT.md`
2. Read `sawmill/<FMWK-ID>/EVALUATION_REPORT.md`
3. Read `sawmill/<FMWK-ID>/CANARY_AUDIT.md`
4. Read `docs/sawmill/<FMWK-ID>.md`
5. Read `docs/PORTAL_STATUS.md`
6. Read `sawmill/PORTAL_CHANGESET.md`
7. Report only what those artifacts prove

## Ownership

This page is a **narrative** page owned by `portal-steward`.

It explains how to verify runtime evidence. It does not define runtime behavior.
