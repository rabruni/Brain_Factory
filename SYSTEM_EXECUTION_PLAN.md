# System Execution Plan

This plan defines how Brain Factory, Sawmill, Backstage/TechDocs, and runtime constraints must operate as one governed system.

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

## What A Canary Pass Must Prove

The canary only passes if all of these are true for the current stage:

1. expected framework artifacts were created
2. portal/Backstage reflects those artifacts immediately
3. runtime constraints still match that stage
4. stage audit passes

This is not "run first, clean docs later." The step is incomplete until the whole system agrees.

## Artifact Model

### Framework artifacts created during a run

These are the outputs that become framework state:

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

These constrain behavior but do not become per-framework artifacts:

- `.claude/agents/*`
- `Templates/TDD_AND_DEBUGGING.md`
- `Templates/AGENT_BUILD_PROCESS.yaml`
- `Templates/BUILDER_PROMPT_CONTRACT.md`
- `sawmill/COLD_START.md`
- `sawmill/run.sh`

## Template To Artifact Map

### Turn A

Instantiates:

- `Templates/D1_CONSTITUTION.md`
- `Templates/D2_SPECIFICATION.md`
- `Templates/D3_DATA_MODEL.md`
- `Templates/D4_CONTRACTS.md`
- `Templates/D5_RESEARCH.md`
- `Templates/D6_GAP_ANALYSIS.md`

Outputs:

- `sawmill/<FMWK-ID>/D1_CONSTITUTION.md`
- `sawmill/<FMWK-ID>/D2_SPECIFICATION.md`
- `sawmill/<FMWK-ID>/D3_DATA_MODEL.md`
- `sawmill/<FMWK-ID>/D4_CONTRACTS.md`
- `sawmill/<FMWK-ID>/D5_RESEARCH.md`
- `sawmill/<FMWK-ID>/D6_GAP_ANALYSIS.md`

### Turn B

Instantiates:

- `Templates/D7_PLAN.md`
- `Templates/D8_TASKS.md`
- `Templates/D10_AGENT_CONTEXT.md`
- `Templates/BUILDER_HANDOFF_STANDARD.md`

Outputs:

- `sawmill/<FMWK-ID>/D7_PLAN.md`
- `sawmill/<FMWK-ID>/D8_TASKS.md`
- `sawmill/<FMWK-ID>/D10_AGENT_CONTEXT.md`
- `sawmill/<FMWK-ID>/BUILDER_HANDOFF.md`

### Turn C

Instantiates:

- `Templates/D9_HOLDOUT_SCENARIOS.md`

Outputs:

- `.holdouts/<FMWK-ID>/D9_HOLDOUT_SCENARIOS.md`

### Turn D

Reads governing sources:

- `Templates/TDD_AND_DEBUGGING.md`
- `Templates/AGENT_BUILD_PROCESS.yaml`
- `Templates/BUILDER_PROMPT_CONTRACT.md`
- `sawmill/<FMWK-ID>/D10_AGENT_CONTEXT.md`
- `sawmill/<FMWK-ID>/BUILDER_HANDOFF.md`

Outputs:

- `staging/<FMWK-ID>/*`
- `sawmill/<FMWK-ID>/13Q_ANSWERS.md`
- `sawmill/<FMWK-ID>/RESULTS.md`

### Turn E

Reads:

- `.holdouts/<FMWK-ID>/D9_HOLDOUT_SCENARIOS.md`
- built code from `staging/<FMWK-ID>/`

Outputs:

- `sawmill/<FMWK-ID>/EVALUATION_REPORT.md`
- `sawmill/<FMWK-ID>/EVALUATION_ERRORS.md`

## Agents Used

- `run.sh` orchestrates Turns A-E
- `spec-agent` handles Turns A and B
- `holdout-agent` handles Turn C
- `builder` handles Turn D
- `evaluator` handles Turn E
- `portal-steward` syncs portal/Backstage after stage changes
- `auditor` verifies the current canary stage

## Execution Roadmap

### Phase 0: Seed The Canary

Create:

- `sawmill/FMWK-900-sawmill-smoke/SOURCE_MATERIAL.md`

This must define a tiny, low-risk framework target. It is a system smoke test, not product work.

### Phase 1: Turn A

Run:

```bash
./sawmill/run.sh FMWK-900-sawmill-smoke --from-turn A
```

Then the system must:

1. verify Turn A artifacts exist
2. run `portal-steward`
3. run canary audit
4. continue only on pass

### Phase 2: Turns B and C

Run:

```bash
./sawmill/run.sh FMWK-900-sawmill-smoke --from-turn B
```

Then the system must:

1. verify Turn B and C artifacts exist
2. verify holdout isolation
3. run `portal-steward`
4. run canary audit
5. continue only on pass

### Phase 3: Turn D

Run:

```bash
./sawmill/run.sh FMWK-900-sawmill-smoke --from-turn D
```

Then the system must:

1. verify builder outputs exist
2. verify 13Q gate and results behavior
3. run `portal-steward`
4. run canary audit
5. continue only on pass

### Phase 4: Turn E

Run:

```bash
./sawmill/run.sh FMWK-900-sawmill-smoke --from-turn E
```

Then the system must:

1. verify evaluator outputs exist
2. run `portal-steward`
3. run canary audit
4. stop with final pass/fail

### Phase 5: Real Framework

Only after the canary passes:

```bash
./sawmill/run.sh FMWK-001-ledger --from-turn D
```

## Stage Completion Contract

A stage is complete only if all of these are true:

1. expected source artifacts exist
2. portal/Backstage reflects the same stage
3. hooks, runner behavior, and role contracts do not contradict that stage
4. current canary audit passes

If any check fails:

- stop
- report failure
- consult the human only for the failure or a source conflict

## Required Audit Artifact

Canary audit output must be framework-local:

- `sawmill/FMWK-900-sawmill-smoke/CANARY_AUDIT.md`

It must check:

1. expected artifacts for the current canary stage
2. portal/status reflection of those artifacts
3. source truth, runner behavior, role contracts, and hooks for contradiction

## Human Interaction Model

The human should not coordinate phases manually.

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
    creates D7 D8 D10 BUILDER_HANDOFF

  run.sh -> holdout-agent (Turn C)
    creates .holdouts/<FMWK>/D9
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
    reads D10 + handoff + process templates
    creates staging/* + 13Q_ANSWERS.md + RESULTS.md
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
    reads D9 + built code
    creates EVALUATION_REPORT.md / EVALUATION_ERRORS.md
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
