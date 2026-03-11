# Harness Invariants

The Sawmill harness truth model is frozen as of `SAWMILL_RUNTIME_SPEC_v0.1`.

The following invariants MUST NOT change without a spec revision:

- `events.jsonl` is the canonical causal ledger
- `status.json` is a deterministic projection of `events.jsonl`
- `run.sh` remains the canonical runtime entry path
- `manual_intervention_recorded` invalidates governed PASS unless explicitly allowed by `operator_mode`
- evidence artifacts gate stage completion
- convergence gate determines final run validity

The harness has been validated by both governed failures and a governed end-to-end PASS canary.
