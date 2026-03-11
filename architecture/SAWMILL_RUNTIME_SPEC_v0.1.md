---
Authority: DRAFT
Requires: Ray Approval
Implements: Sawmill Convergence v0.1
File: architecture/SAWMILL_RUNTIME_SPEC_v0.1.md
---

# SAWMILL_RUNTIME_SPEC_v0.1

## 1. Authority Model

This document is the normative runtime specification for Sawmill Convergence v0.1.

The Sawmill runtime SHALL operate under a single truth model.

The single truth model consists of these artifacts:

- `events.jsonl` — canonical causal history
- `status.json` — canonical current-state projection
- `run.json` — canonical run contract snapshot

The following authority rules are REQUIRED:

- `run.sh` SHALL remain the canonical entry path for a Sawmill run.
- `events.jsonl` SHALL be append-only and SHALL be the canonical causal ledger for the run.
- `status.json` SHALL be a derived projection of `events.jsonl` and SHALL NOT contain independent history.
- `run.json` SHALL be the static contract snapshot for the run and SHALL NOT be rewritten after run start except for explicitly allowed completion timestamps if adopted by implementation.
- Human-readable docs SHALL be treated as governed required outputs, but SHALL be projections of runtime truth and SHALL NOT become independent authorities.
- Verification SHALL consume harness artifacts and evidence artifacts. Verification SHALL NOT consume human prose as authority.
- LangGraph MAY control transition logic inside Turn D/E only.
- LangGraph MUST NOT own truth storage.
- Promptfoo and DeepEval, if later integrated, MUST act as verification components only and MUST NOT become competing runtime authorities.

A run SHALL be considered governed only if runtime, governed record, and verification artifacts are mechanically convergent.

## 2. Run Artifact Schemas

Every run MUST create a run directory at:

```text
sawmill/<FMWK-ID>/runs/<run-id>/
```

The run directory MUST contain:

```text
run.json
status.json
events.jsonl
logs/
  <step>.stdout.log
  <step>.stderr.log
```

### 2.1 `run.json`

`run.json` is REQUIRED and MUST contain these fields:

- `run_id`
- `framework_id`
- `started_at`
- `requested_entry_path`
- `from_turn`
- `retry_budget`
- `role_backend_resolution`
- `model_policies`
- `prompt_contract_versions`
- `role_file_hashes`
- `prompt_file_hashes`
- `artifact_registry_version_hash`
- `graph_version`
- `operator_mode`

`operator_mode` MUST be one of:

- `governed`
- `interactive`
- `manual_intervention_allowed`

`run.json` SHALL represent the run contract snapshot. It SHALL record the exact runtime contract under which the run executed.

### 2.2 `status.json`

`status.json` is REQUIRED and MUST contain at least:

- `run_id`
- `framework_id`
- `current_turn`
- `current_step`
- `current_role`
- `current_backend`
- `current_attempt`
- `state`
- `governed_path_intact`
- `last_successful_event_id`
- `latest_failure_code`

Allowed `state` values are:

- `running`
- `retrying`
- `escalated`
- `failed`
- `passed`
- `invalidated`

`operator_assisted` MUST NOT appear as a state.

`status.json` SHALL be fully derivable from `events.jsonl`. If derivation fails, the run SHALL be treated as invalid.

### 2.3 `events.jsonl`

`events.jsonl` is REQUIRED and SHALL be append-only.

Every event record in `events.jsonl` MUST contain these fields:

- `event_id`
- `run_id`
- `timestamp`
- `turn`
- `step`
- `role`
- `backend`
- `attempt`
- `event_type`
- `outcome`
- `failure_code`
- `causal_parent_event_id`
- `evidence_refs`
- `contract_refs`
- `summary`

`failure_code` MAY be null for non-failure events, but the field MUST exist.

`evidence_refs` and `contract_refs` MAY be empty lists, but the fields MUST exist.

Per-step logs in `logs/` SHALL be referenced from `events.jsonl` through `evidence_refs` when applicable.

## 3. Event Taxonomy

The runtime MUST emit only event types defined by this specification unless this document is revised.

The required event types are:

- `run_started`
- `preflight_passed`
- `turn_started`
- `prompt_rendered`
- `agent_invoked`
- `agent_exited`
- `output_verified`
- `review_verdict_recorded`
- `evaluation_verdict_recorded`
- `retry_started`
- `escalation_triggered`
- `timeout_triggered`
- `manual_intervention_recorded`
- `turn_completed`
- `run_completed`
- `run_failed`

### 3.1 Event causal rules

The runtime MUST enforce the following minimum parent rules:

- `run_started`
  - parent: none

- `preflight_passed`
  - parent: `run_started`

- `turn_started`
  - parent: `run_started` OR previous `turn_completed`

- `prompt_rendered`
  - parent: `turn_started`

- `agent_invoked`
  - parent: `prompt_rendered`

- `agent_exited`
  - parent: `agent_invoked`

- `output_verified`
  - parent: `agent_exited`

- `review_verdict_recorded`
  - parent: reviewer `agent_exited`

- `evaluation_verdict_recorded`
  - parent: evaluator `agent_exited`

- `retry_started`
  - parent: `review_verdict_recorded` OR `evaluation_verdict_recorded`

- `escalation_triggered`
  - parent: `review_verdict_recorded` OR `evaluation_verdict_recorded`

- `timeout_triggered`
  - parent: `agent_invoked`

- `manual_intervention_recorded`
  - parent: `timeout_triggered` OR failure event

- `turn_completed`
  - parent: `review_verdict_recorded` OR `evaluation_verdict_recorded`

- `run_completed`
  - parent: final `turn_completed`

- `run_failed`
  - parent: failure event

The runtime MUST reject illegal causal parentage during projection or validation.

### 3.2 Event semantics

The following semantic rules are REQUIRED:

- `prompt_rendered` SHALL mean prompt rendering succeeded for the step.
- `agent_invoked` SHALL mean the runtime attempted to launch the selected backend/role.
- `agent_exited` SHALL record the backend process exit outcome.
- `output_verified` SHALL mean required stage outputs were validated immediately after production.
- `review_verdict_recorded` SHALL record a reviewer verdict after reviewer execution.
- `evaluation_verdict_recorded` SHALL record an evaluator verdict after evaluator execution.
- `retry_started` SHALL indicate a new attempt in the shared Turn D/E retry loop.
- `manual_intervention_recorded` SHALL indicate that a human or operator performed work outside the governed automatic path.
- `run_completed` SHALL only appear for terminal success.
- `run_failed` SHALL only appear for terminal non-success.

## 4. Evidence Artifact Schemas

The runtime MUST validate evidence artifacts twice:

- stage validation: immediately when each evidence artifact is produced
- final convergence validation: when the run attempts to reach a terminal state

Missing, malformed, or contradictory evidence MUST invalidate the run.

### 4.1 `builder_evidence.json`

`builder_evidence.json` is REQUIRED for Turn D build completion.

It MUST contain:

- `run_id`
- `attempt`
- `handoff_hash`
- `q13_answers_hash`
- `behaviors`
- `full_test_command`
- `full_test_result`
- `files_changed`
- `results_hash`

`behaviors` MUST be a non-empty array.

Each `behaviors[]` entry MUST contain:

- `behavior_id`
- `failing_test_command`
- `failing_observation`
- `passing_test_command`
- `passing_observation`
- `files_touched`

`files_changed` MUST identify changed files for the attempt.

`results_hash` MUST refer to the governed `RESULTS.md` artifact for the same run.

### 4.2 `reviewer_evidence.json`

`reviewer_evidence.json` is REQUIRED for Turn D review completion.

It MUST contain:

- `run_id`
- `attempt`
- `q13_answers_hash`
- `builder_prompt_contract_version_reviewed`
- `reviewer_prompt_contract_version`
- `findings`
- `verdict`
- `failure_code`

`verdict` MUST be one of:

- `PASS`
- `RETRY`
- `ESCALATE`

`findings` MAY be empty only if `verdict=PASS`.

### 4.3 `evaluator_evidence.json`

`evaluator_evidence.json` is REQUIRED for Turn E completion.

It MUST contain:

- `run_id`
- `attempt`
- `holdout_hash`
- `staging_hash`
- `scenarios`
- `verdict`
- `pass_rate`

`verdict` MUST be one of:

- `PASS`
- `FAIL`

`scenarios` MUST be a non-empty array.

Each `scenarios[]` entry MUST identify the scenario and its per-run execution results.

### 4.4 Evidence consistency requirements

The runtime MUST reject evidence when any of the following occur:

- `run_id` does not match the active run
- `attempt` does not match the active attempt
- required fields are missing
- required field types are malformed
- hashes refer to artifacts from a different run
- verdict values are outside the allowed set
- evidence contradicts causal events or final reports

## 5. Turn D/E Supervisory Boundary

LangGraph MAY control only the Turn D/E supervisory loop:

```text
builder → reviewer → builder → evaluator
```

LangGraph integration SHALL obey these rules:

- LangGraph MAY decide transitions inside Turn D/E.
- LangGraph MUST emit events into the same `events.jsonl` stream used by the rest of the runtime.
- LangGraph MUST NOT create an independent truth store.
- LangGraph MUST NOT redefine `status.json`.
- LangGraph MUST NOT redefine run authority outside Turn D/E.
- `run.sh` SHALL remain the canonical entry path and outer runtime authority.

The Turn D/E supervisor MUST operate under the same retry budget and evidence-validation rules as the rest of the runtime.

The shared attempt budget for Turn D/E SHALL be three attempts unless `run.json` explicitly defines a different approved retry budget in a future revision of this spec.

## 6. Status Projection Rules

The runtime MUST implement deterministic projection:

```text
events.jsonl → status.json
```

### 6.1 Projection rules

The projection algorithm SHALL obey all of the following:

1. `status.json` is rebuilt by folding events in timestamp order.
2. `run_id` must match the run directory.
3. duplicate `event_id` causes projection failure.
4. illegal state transitions cause projection failure.
5. `governed_path_intact` initializes as `true`.
6. `manual_intervention_recorded` sets `governed_path_intact=false`.
7. `governed_path_intact` can never revert to `true`.
8. terminal states are:
   - `passed`
   - `failed`
   - `escalated`
   - `invalidated`
9. if terminal PASS occurs while `governed_path_intact=false` and `operator_mode ≠ manual_intervention_allowed`, projection MUST set final state to `invalidated`.

manual_intervention_recorded sets governed_path_intact=false.

If a run would otherwise terminate with PASS while governed_path_intact=false and operator_mode ≠ manual_intervention_allowed,
the runtime MUST set final state = invalidated.

### 6.2 Projection behavior by event

The projection MUST update state deterministically:

- `run_started` -> `running`
- `retry_started` -> `retrying`
- `escalation_triggered` -> `escalated`
- `run_failed` -> `failed`
- `run_completed` -> `passed`, unless invalidation coercion applies
- any terminal contradiction -> `invalidated`

If a terminal state has been reached, additional non-terminal transitions MUST cause projection failure.

### 6.3 Projection failure conditions

Projection MUST fail if any of the following occur:

- duplicate `event_id`
- missing required parent event
- illegal parent-child event relation
- illegal terminal transition
- inconsistent `run_id`
- state cannot be deterministically derived
- `status.json` fields contradict the folded event stream

When projection fails, the run SHALL be treated as invalid and SHALL NOT be considered passed.

## 7. Governed Record Projection

Docs are first-class governed outputs, but they are projections only.

The governed record projection MUST satisfy all of the following:

- docs MUST render runtime truth from harness artifacts
- docs MUST NOT independently assert state
- docs MUST NOT claim stage completion, PASS, or failure cause absent support in harness events and evidence artifacts
- docs MUST surface manual intervention when it occurred
- docs MUST surface invalidation when it occurred
- docs MUST remain consistent with `status.json`

The governed record projection MAY include human-readable summaries, but those summaries SHALL be derived from:

- `run.json`
- `status.json`
- `events.jsonl`
- validated evidence artifacts

If docs and harness disagree, the docs SHALL be considered stale and the convergence gate SHALL fail.

## 8. Convergence Gate

A run is valid only if ALL of the following hold:

- `status.json` is derivable from `events.jsonl`
- all evidence artifacts validate
- docs match harness state
- no stage marked complete without causal events
- no manual intervention unless allowed by `operator_mode`

If intervention occurred:

- final state MUST be invalidated
- unless `manual_intervention_allowed`

Additional convergence failure conditions are REQUIRED:

- `status.json` cannot be derived from `events.jsonl` without contradiction
- docs claim PASS while harness state is `failed`, `escalated`, or `invalidated`
- a stage is marked complete without corresponding events and evidence
- evidence artifacts exist without matching invocation/completion events
- stale artifacts from a prior run are interpreted as current without matching `run_id`

A run that fails the convergence gate SHALL NOT be considered a governed PASS.

## 9. Implementation Contract

An implementation of this specification MUST satisfy all of the following:

- create the required run directory structure
- produce `run.json`, `status.json`, and `events.jsonl`
- emit per-step logs
- emit the required event taxonomy
- enforce the causal parent rules
- enforce deterministic projection from `events.jsonl` to `status.json`
- validate evidence artifacts at stage time and final convergence time
- mark manual intervention explicitly through `manual_intervention_recorded`
- coerce final PASS to `invalidated` when governed path integrity is broken and operator mode does not allow intervention
- keep LangGraph bounded to Turn D/E supervision only if LangGraph is present
- keep docs as governed projections, not independent authorities

### Required test classes

The implementation MUST include the following test classes:

#### Harness tests
- run start and preflight success
- prompt render failure
- reviewer timeout
- evaluator FAIL
- interruption during Turn D/E
- manual intervention recording
- duplicate event id rejection
- illegal transition rejection

#### Evidence tests
- missing `builder_evidence.json`
- malformed `reviewer_evidence.json`
- contradictory `evaluator_evidence.json`
- wrong `run_id`
- wrong `attempt`
- stale evidence from prior run

#### Convergence tests
- docs claim PASS while harness does not
- stage marked complete without causal events
- `status.json` not derivable from `events.jsonl`
- manual intervention followed by apparent PASS results in `invalidated`

#### Canary acceptance test
The FMWK-900 failure case where:

- `run.sh` fails
- operator intervenes manually
- artifacts later appear successful

MUST terminate as:

- `invalidated`

and MUST NEVER terminate as:

- `PASS`
