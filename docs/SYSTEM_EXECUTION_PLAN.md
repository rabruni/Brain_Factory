# System Execution Plan

This page mirrors `SYSTEM_EXECUTION_PLAN.md`.

## Goal

Get to a state where the human only:

1. says `go`
2. approves explicit gates
3. is consulted on failure or source conflict

Everything else is system-owned.

The first proof is a canary:

- `FMWK-900-sawmill-smoke`

The first real build after the canary passes is:

```bash
./sawmill/run.sh FMWK-001-ledger --from-turn D
```

## One-System Rule

Sawmill is only trustworthy when these three layers agree:

1. Source truth
   - `.claude/agents/*`
   - `sawmill/*`
   - `Templates/*`
   - `sawmill/run.sh`
2. Portal / Backstage
   - `docs/*`
   - `mkdocs.yml`
   - status pages
3. Runtime constraints
   - hooks
   - runner behavior
   - role contracts

If any of these disagree, the stage fails.

## Current Status

### In place

- Sawmill runner exists: `sawmill/run.sh`
- Turn roles exist: orchestrator, spec-agent, holdout-agent, builder, evaluator
- Governance roles exist: auditor, portal-steward
- Templates exist for D1-D10, handoff, builder process, and TDD
- Hooks exist and have been exercised for:
  - guarded writes
  - state injection
  - stop blocking
- Portal governance exists:
  - `PORTAL_TRUTH_MODEL.md`
  - `docs/PORTAL_CONSTITUTION.md`
  - `docs/PORTAL_MAP.yaml`

### Still missing

- One system-owned completion loop
- A canary framework that proves the whole governed system
- Automatic portal sync and canary audit as part of stage completion
- One clean current-state audit after the system loop is wired

## Artifact Model

### Framework artifacts created during a run

- `sawmill/<FMWK-ID>/TASK.md`
- `sawmill/<FMWK-ID>/D1_CONSTITUTION.md`
- `sawmill/<FMWK-ID>/D2_SPECIFICATION.md`
- `sawmill/<FMWK-ID>/D3_DATA_MODEL.md`
- `sawmill/<FMWK-ID>/D4_CONTRACTS.md`
- `sawmill/<FMWK-ID>/D5_RESEARCH.md`
- `sawmill/<FMWK-ID>/D6_GAP_ANALYSIS.md`
- `sawmill/<FMWK-ID>/D7_PLAN.md`
- `sawmill/<FMWK-ID>/D8_TASKS.md`
- `sawmill/<FMWK-ID>/D10_AGENT_CONTEXT.md`
- `sawmill/<FMWK-ID>/BUILDER_HANDOFF.md`
- `.holdouts/<FMWK-ID>/D9_HOLDOUT_SCENARIOS.md`
- `staging/<FMWK-ID>/*`
- `sawmill/<FMWK-ID>/13Q_ANSWERS.md`
- `sawmill/<FMWK-ID>/RESULTS.md`
- `sawmill/<FMWK-ID>/EVALUATION_REPORT.md`
- `sawmill/<FMWK-ID>/EVALUATION_ERRORS.md`

### Governing sources read during a run

- `.claude/agents/*`
- `Templates/TDD_AND_DEBUGGING.md`
- `Templates/AGENT_BUILD_PROCESS.yaml`
- `Templates/BUILDER_PROMPT_CONTRACT.md`
- `sawmill/COLD_START.md`
- `sawmill/run.sh`

## Execution Roadmap

### Phase 0: Seed The Canary

Create:

- `sawmill/FMWK-900-sawmill-smoke/SOURCE_MATERIAL.md`

### Phase 1: Turn A

```bash
./sawmill/run.sh FMWK-900-sawmill-smoke --from-turn A
```

Then:

1. verify Turn A artifacts
2. run `portal-steward`
3. run canary audit
4. continue only on pass

### Phase 2: Turns B and C

```bash
./sawmill/run.sh FMWK-900-sawmill-smoke --from-turn B
```

Then:

1. verify Turn B and C artifacts
2. verify holdout isolation
3. run `portal-steward`
4. run canary audit
5. continue only on pass

### Phase 3: Turn D

```bash
./sawmill/run.sh FMWK-900-sawmill-smoke --from-turn D
```

Then:

1. verify builder outputs
2. run `portal-steward`
3. run canary audit
4. continue only on pass

### Phase 4: Turn E

```bash
./sawmill/run.sh FMWK-900-sawmill-smoke --from-turn E
```

Then:

1. verify evaluator outputs
2. run `portal-steward`
3. run canary audit
4. stop with final pass/fail

### Phase 5: Real Framework

Only after canary pass:

```bash
./sawmill/run.sh FMWK-001-ledger --from-turn D
```

## Stage Completion Contract

A stage is complete only if all of these are true:

1. expected source artifacts exist
2. portal/Backstage reflects the same stage
3. hooks, runner behavior, and role contracts do not contradict that stage
4. current canary audit passes

## Required Audit Artifact

Canary audit output must be framework-local:

- `sawmill/FMWK-900-sawmill-smoke/CANARY_AUDIT.md`

## Human Interaction Model

The human only:

1. starts the flow
2. approves explicit gates
3. resolves source conflicts
4. reviews final verdict

## ASCII Flow

```text
END GOAL
  Trusted governed Sawmill
  -> then run FMWK-001-ledger

READ-ONLY GOVERNING SOURCES
  .claude/agents/*
  Templates/*
  sawmill/COLD_START.md
  sawmill/run.sh
  hooks
          |
          v
+----------------------------------------------+
|      FMWK-900-sawmill-smoke (CANARY)         |
+----------------------------------------------+

Phase 0
  seed:
    sawmill/FMWK-900-sawmill-smoke/SOURCE_MATERIAL.md
          |
          v

Phase 1
  run.sh -> spec-agent (Turn A)
    creates D1-D6
          |
          v
  verify expected artifacts
          |
          v
  portal-steward
          |
          v
  canary audit
          |
       pass only
          |
          v

Phase 2
  run.sh -> spec-agent (Turn B)
  run.sh -> holdout-agent (Turn C)
          |
          v
  verify expected artifacts + holdout isolation
          |
          v
  portal-steward
          |
          v
  canary audit
          |
       pass only
          |
          v

Phase 3
  run.sh -> builder (Turn D)
          |
          v
  verify expected artifacts
          |
          v
  portal-steward
          |
          v
  canary audit
          |
       pass only
          |
          v

Phase 4
  run.sh -> evaluator (Turn E)
          |
          v
  verify expected artifacts
          |
          v
  portal-steward
          |
          v
  canary audit
          |
          v

CANARY PASS ONLY IF
  source artifacts exist
  portal reflects them
  runtime constraints match them
  canary audit passes

THEN
  ./sawmill/run.sh FMWK-001-ledger --from-turn D
```
