# D3: Data Model — FMWK-900-sawmill-smoke
Meta: v:1.0.0 (matches D2) | status:Final | shared entities:0

## Entities
E-001 PingRequest
- Scope: PRIVATE
- Source: SC-001, SC-002
- Description: Documentation-only invocation shape for the canary function. It exists to state that `ping()` accepts no caller-provided fields and creates no persistent model.

| Field | Type | Required | Description | Constraints |
| request:object | Type:object | Req:yes | Desc:empty invocation payload for `ping()` | Constraint:must be `{}` with no fields |

```json
{}
```

Invariants: The invocation payload is always empty. No arguments are accepted.

E-002 PingResponse
- Scope: PRIVATE
- Source: SC-001, SC-002, SC-004
- Description: Documentation-only response shape for the canary function. It captures the only observable output contract: the function returns the literal `"pong"`.

| Field | Type | Required | Description | Constraints |
| value:string | Type:string | Req:yes | Desc:return value from `ping()` | Constraint:must equal `"pong"` |

```json
{
  "value": "pong"
}
```

Invariants: `value` is always the exact lowercase string `"pong"`. The response is transient and not persisted or shared.

## Entity Relationship Map
```text
PingRequest ({})
   |
   v
ping()
   |
   v
PingResponse {"value":"pong"}
```

## Migration Notes
No prior model — greenfield.
