# D4: Contracts - FMWK-900-sawmill-smoke
Meta: v:1.0.0 (matches D2) | data model: D3 1.0.0 | status:Draft

IDs: IN-NNN (inbound), OUT-NNN (outbound), SIDE-NNN (side-effect), ERR-NNN (error).

## Inbound

### IN-001
- Caller: `test_smoke.py` or any local smoke runner
- Trigger: direct call to `ping()`
- Scenarios: D2 SC-001, SC-002

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| args | none | yes | Function input | must be omitted |

- Constraints: `ping()` is zero-argument and must be callable after import.
- Example: `ping()`

### IN-002
- Caller: `pytest`
- Trigger: execution of `test_ping`
- Scenarios: D2 SC-003, SC-004, SC-005

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| test_file | path | yes | Test target | exactly `staging/FMWK-900-sawmill-smoke/test_smoke.py` |
| imported_symbol | string | yes | Symbol under test | exactly `ping` |

- Constraints: pytest must be able to import `ping` from `smoke` before assertion runs.
- Example: `pytest staging/FMWK-900-sawmill-smoke/test_smoke.py`

## Outbound

### OUT-001
- Consumer: caller of `ping()`
- Scenarios: D2 SC-001, SC-002
- Response Shape: D3 E-001 invariant `return_literal = "pong"`
- Example success: `"pong"`
- Example failure: any non-`"pong"` value

### OUT-002
- Consumer: builder or Sawmill validation step
- Scenarios: D2 SC-003, SC-004, SC-005
- Response Shape: D3 E-002 invariant `assertion = ping() == "pong"`
- Example success: `1 passed`
- Example failure: import error or assertion failure

## Side-Effects

### SIDE-001
- Target System: local Python/pytest process
- Trigger: import and execution of the owned canary files
- Scenarios: D2 SC-001, SC-002, SC-003, SC-004, SC-005
- Write Shape: none; read/execute only
- Ordering Guarantee: `smoke.py` must be importable before `test_ping` executes
- Failure Behavior: fail fast and stop the build on the first import, syntax, or assertion error

## Errors

### ERR-001
- Condition: `ping` is missing, renamed, or not importable from `smoke`
- Scenarios: D2 SC-004
- Caller Action: stop the build, restore `ping`, and rerun pytest

### ERR-002
- Condition: `ping()` returns a value other than `"pong"`
- Scenarios: D2 SC-005
- Caller Action: fail the canary, restore the literal return, and rerun pytest

## Error Code Enum

| Code | Meaning | Retryable |
|------|---------|-----------|
| IMPORT_FAILURE | `ping` could not be imported from `smoke` | no |
| WRONG_RETURN | `ping()` returned a value other than `"pong"` | no |
