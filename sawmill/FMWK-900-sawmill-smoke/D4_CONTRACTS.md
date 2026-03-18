# D4: Contracts — sawmill smoke canary
Meta: v:1.0.0 (matches D2) | data model: D3 1.0.0 | status:Final

IDs: IN-NNN (inbound), OUT-NNN (outbound), SIDE-NNN (side-effect), ERR-NNN (error).

## Inbound
### IN-001
- Caller: `test_smoke.py`
- Trigger: Unit test imports and calls `ping()`
- Scenarios: D2 SC-001, SC-002

| Field | Type | Required | Description | Constraints |
| --- | --- | --- | --- | --- |
| function_name | Type:string | Req:yes | Invoked symbol | Constraint:must equal `ping` |
| arguments | Type:list | Req:yes | Call arguments | Constraint:must be empty |

Constraints: No arguments, no setup, no dependencies.

Example:
```json
{
  "function_name": "ping",
  "arguments": []
}
```

## Outbound
### OUT-001
- Consumer: `test_smoke.py`
- Scenarios: D2 SC-001, SC-002
- Response Shape: D3 E-001 return value
- Example success:
```json
{
  "result": "pong"
}
```
- Example failure:
```json
{
  "error": "returned value did not equal pong"
}
```

## Side-Effects
### SIDE-001
- Target System: None
- Trigger: `ping()` execution
- Scenarios: D2 SC-003, SC-004
- Write Shape: none
- Ordering Guarantee: no side effects occur
- Failure Behavior: not applicable

## Errors
### ERR-001
- Condition: `smoke.py` cannot be imported
- Scenarios: D2 SC-002, SC-003
- Caller Action: Fail the test run immediately

### ERR-002
- Condition: `ping()` returns any value other than `"pong"`
- Scenarios: D2 SC-001, SC-002
- Caller Action: Fail the assertion immediately

### ERR-003
- Condition: Extra dependencies or extra files are introduced
- Scenarios: D2 SC-003, SC-004
- Caller Action: Reject the staged canary as out of scope

## Error Code Enum
| Code | Meaning | Retryable |
| --- | --- | --- |
| IMPORT_FAILURE | Python could not import `smoke.py` or `ping` | no |
| WRONG_RETURN | `ping()` returned a value other than `"pong"` | no |
| SCOPE_VIOLATION | The canary contains forbidden dependencies or artifacts | no |
