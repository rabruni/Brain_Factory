# D4: Contracts — FMWK-900-sawmill-smoke
Meta: v:1.0.0 (matches D2) | data model: D3 1.0.0 | status:Final

IDs: IN-NNN (inbound), OUT-NNN (outbound), SIDE-NNN (side-effect), ERR-NNN (error).

## Inbound
IN-001
- Caller: Python caller or test runner
- Trigger: Direct invocation of `ping()`
- Scenarios: SC-001, SC-002

| Field | Type | Required | Description | Constraints |
| request | object | yes | Empty caller-visible request payload for `ping()` | Must be `{}` with no fields |

- Constraints: The callable surface is zero-argument only. No positional or keyword arguments are part of the contract.
- Example: `ping()`

## Outbound
OUT-001
- Consumer: Python caller or test runner
- Scenarios: SC-001, SC-002, SC-004
- Response Shape: D3 E-002 PingResponse
- Example success:

```json
{
  "value": "pong"
}
```

- Example failure: No framework-level failure payload exists; noncompliance appears as a test failure or Python call-site exception.

## Side-Effects
SIDE-001
- Target System: None
- Trigger: `ping()` execution
- Scenarios: SC-001, SC-003
- Write Shape: No writes
- Ordering Guarantee: None required
- Failure Behavior: Not applicable; the function has no side-effects

## Errors
ERR-001
- Condition: `ping()` is missing, renamed, or has a non-zero-argument signature
- Scenarios: SC-002, SC-005
- Caller Action: Treat as contract failure and fix the module/test to match the declared callable surface

ERR-002
- Condition: `ping()` returns any value other than `"pong"`
- Scenarios: SC-004
- Caller Action: Treat as contract failure and restore the exact literal return value

ERR-003
- Condition: Additional files, dependencies, or framework behaviors appear
- Scenarios: SC-003, SC-005
- Caller Action: Reject the build as out of scope and remove the extra surface

## Error Code Enum
| Code | Meaning | Retryable |
| SMOKE_SIGNATURE_INVALID | Callable surface does not match `ping()` with zero arguments | no |
| SMOKE_RETURN_INVALID | Return value is not the exact literal `"pong"` | no |
| SMOKE_SCOPE_DRIFT | Framework contains extra scope beyond the declared canary | no |

## Testable Surface
No test doubles required.
