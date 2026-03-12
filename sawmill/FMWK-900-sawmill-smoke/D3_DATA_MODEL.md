# D3: Data Model — sawmill-smoke
Meta: v:1.0.0 (matches D2) | status:Final | shared entities:0

## Entities (E-### IDs, e.g. E-001)
No persistent or shared data entities are defined for this framework. The assignment explicitly forbids creating data models beyond the trivial function and test.

### E-001 — PingReturn
- Scope: PRIVATE
- Used By: n/a
- Source: SC-001, SC-002
- Description: Ephemeral string output produced by `ping()` and consumed immediately by the unit test assertion. It is not stored, shared, serialized, or versioned.

| Field | Type | Required | Description | Constraints |
| return_value | Type:string | Req:yes | Desc:Literal returned by `ping()` | Constraint:must equal `pong` |

```json
{
  "return_value": "pong"
}
```

Invariants: `return_value` is always the literal `"pong"` when `ping()` succeeds.

## Entity Relationship Map
```text
ping() -> PingReturn("pong") -> test_ping assertion
```

## Migration Notes
No prior model — greenfield.
