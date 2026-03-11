# D4: Contracts - sawmill-smoke
Meta: v:0.1.0 (matches D2) | data model: D3 0.1.0 | status:Final

IDs: IN-NNN (inbound), OUT-NNN (outbound), SIDE-NNN (side-effect), ERR-NNN (error).

## Inbound
IN-001
- Caller: Direct Python caller or `test_smoke.py`
- Trigger: Import `ping` and call it
- Scenarios: SC-001, SC-002
- Request Shape:

| Field | Type | Required | Description | Constraints |
|---|---|---|---|---|
| args | none | yes | No arguments accepted | Call signature is exactly `ping()` |

- Constraints: The function is zero-argument and pure.
- Example: `ping()`

## Outbound
OUT-001
- Consumer: Direct caller or `test_smoke.py`
- Scenarios: SC-001, SC-002, SC-101
- Response Shape: No D3 entity by design; scalar string result only
- Example success: `"pong"`
- Example failure: any value other than `"pong"`

## Side-Effects
SIDE-001
- Target System: None
- Trigger: `ping()` execution
- Scenarios: SC-001, SC-002
- Write Shape: None
- Ordering Guarantee: None required; function is pure
- Failure Behavior: No side effects are permitted

## Errors
ERR-001
- Condition: `ping()` returns a value other than `"pong"`
- Scenarios: SC-101
- Caller Action: Fail verification immediately

ERR-002
- Condition: Import path or callable name does not resolve to `smoke.ping`
- Scenarios: SC-002, SC-102
- Caller Action: Fail test execution immediately

ERR-003
- Condition: Extra files, dependencies, or framework concerns are introduced
- Scenarios: SC-003, SC-103
- Caller Action: Reject the package as out of scope

## Error Code Enum
| Code | Meaning | Retryable |
|---|---|---|
| RETURN_MISMATCH | Return value was not `"pong"` | no |
| IMPORT_FAILURE | `smoke.ping` could not be imported or called | no |
| SCOPE_VIOLATION | Scope exceeded one function and one test | no |
