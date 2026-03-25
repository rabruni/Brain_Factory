# FMWK-002 Write Path

`write_path` is DoPeJarMo's synchronous consistency layer. It accepts mutation
requests, appends them durably through the Ledger contract, folds the appended
event into Graph state, and returns success only after both steps complete.

## Public Surface

- `WritePathService.submit_mutation()` for synchronous append-and-fold
- `WritePathService.create_snapshot()` for artifact-first snapshot creation
- `WritePathService.recover()` for snapshot-aware replay on startup
- `WritePathService.refold_from_genesis()` for governed full refold

## Package Layout

- `write_path/models.py`: request, receipt, snapshot, and recovery entities
- `write_path/errors.py`: typed write-path failures
- `write_path/ports.py`: Ledger and Graph dependency protocols
- `write_path/system_events.py`: system-authored request builders
- `write_path/folds.py`: mechanical fold helpers and bounded arithmetic
- `write_path/recovery.py`: snapshot orchestration and replay/refold flows
- `write_path/service.py`: primary synchronous service

## Test Surface

Unit tests live under `tests/` and use the declared doubles in
`tests/conftest.py` for append failures, fold failures, snapshot failures, and
deterministic replay control.
