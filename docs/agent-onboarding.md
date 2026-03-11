# Agent Onboarding

**Status**: NARRATIVE GUIDANCE
**Authority label**: narrative
**Date**: 2026-03-10

This page explains how an agent should start and operate in Sawmill.
For runtime truth, defer to `sawmill/run.sh` and `sawmill/EXECUTION_CONTRACT.md`.

## Single Normal Entry Path

Use this path unless the human explicitly requests otherwise:

```bash
./sawmill/run.sh <FMWK-ID>
```

Interactive checkpoints are opt-in only:

```bash
./sawmill/run.sh <FMWK-ID> --interactive
```

Direct worker CLI dispatch is exception-only and not equivalent to a requested
`run.sh` pipeline execution.

## Startup Context Chain

1. Auto-loaded institutional context (`CLAUDE.md` via CLI conventions)
2. `AGENT_BOOTSTRAP.md` orientation and invariants
3. Role file in `.claude/agents/<role>.md`
4. Runtime-rendered task prompt for the specific turn

## Turn Ownership and Routing

- Turn A: `spec-agent`
- Turn B: `spec-agent` (planning outputs)
- Turn C: `holdout-agent`
- Turn D: `builder` -> `reviewer` -> `builder`
- Turn E: `evaluator`

Routing is registry-governed:

- `sawmill/ROLE_REGISTRY.yaml`
- `sawmill/PROMPT_REGISTRY.yaml`
- `sawmill/ARTIFACT_REGISTRY.yaml`

## Runtime Verdict Semantics

- Reviewer verdict line: `Review verdict: PASS|RETRY|ESCALATE`
- Evaluator verdict line: `Final verdict: PASS|FAIL`
- Shared attempt budget across Turn D/E loop: 3 attempts
- Pipeline endpoint: PASS or FAIL
- Merge/release actions are outside runtime scope

## Stop vs Improvise

Stop and escalate when:

- source-of-truth conflict appears across authority files
- required input artifact is missing
- prompt/role ownership does not match registry
- verdict output is malformed or unparseable

Do not improvise around missing authority or hidden assumptions.

## Fast Start Checklist

1. Confirm framework task artifact exists (`sawmill/<FMWK-ID>/TASK.md`)
2. Run `./sawmill/run.sh <FMWK-ID>`
3. Verify filesystem evidence in `docs/sawmill/RUN_VERIFICATION.md`
4. Report only what artifacts prove
