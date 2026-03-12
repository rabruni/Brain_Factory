# D4: Contracts — sawmill-smoke
Meta: v:1.0.0 (matches D2) | data model: D3 1.0.0 | status:Final

IDs: IN-NNN (inbound), OUT-NNN (outbound), SIDE-NNN (side-effect), ERR-NNN (error).

## Inbound (IN-###)
### IN-001
- Caller: Local Python caller or unit test
- Trigger: Invoke `ping()`
- Scenarios (D2 SC-###): SC-001, SC-002

| Field | Type | Required | Description | Constraints |
| args | Type:none | Req:yes | Desc:`ping()` accepts no arguments | Constraint:must be empty |

Constraints: Function signature is zero-argument and returns synchronously.

Example
```python
result = ping()
```

## Outbound (OUT-###)
### OUT-001
- Consumer: `test_ping`
- Scenarios: SC-001, SC-002, SC-003
- Response Shape (D3 entity ref): E-001 PingReturn

Example success
```python
"pong"
```

Example failure
```text
ImportError, SyntaxError, or assertion failure if the module/test is broken.
```

## Side-Effects (SIDE-###)
No side effects. This framework performs no writes, network calls, or service interactions.

## Errors (ERR-###)
### ERR-001
- Condition: `smoke.py` cannot be imported or `ping()` does not return `"pong"`.
- Scenarios: SC-002, SC-004
- Caller Action: Fail the unit test and stop the smoke validation.

### ERR-002
- Condition: A dependency or external service is introduced into the canary implementation.
- Scenarios: SC-003, SC-004
- Caller Action: Treat as spec violation and reject the framework output.

## Error Code Enum
| Code | Meaning | Retryable |
| IMPORT_OR_ASSERT_FAILURE | The trivial module/test contract is broken | no |
| SCOPE_VIOLATION | The canary exceeds task constraints | no |
