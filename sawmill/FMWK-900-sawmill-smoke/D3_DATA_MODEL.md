# D3: Data Model — sawmill smoke canary
Meta: v:1.0.0 (matches D2) | status:Final | shared entities:0

This canary has no runtime data model. To satisfy the artifact requirement without inventing product data, this document records only the two private file artifacts named in the task.

## Entities
### E-001 `smoke.py`
- Scope: PRIVATE
- Source: D2 SC-001, SC-003, SC-004
- Description: Python module containing the single function `ping()`.

| Field | Type | Required | Description | Constraints |
| --- | --- | --- | --- | --- |
| filename | Type:string | Req:yes | Owned module filename | Constraint:must equal `smoke.py` |
| symbol | Type:string | Req:yes | Exported function name | Constraint:must equal `ping` |
| return_type | Type:string | Req:yes | Declared return type | Constraint:must equal `str` |
| return_value | Type:string | Req:yes | Literal function result | Constraint:must equal `pong` |

```json
{
  "filename": "smoke.py",
  "symbol": "ping",
  "return_type": "str",
  "return_value": "pong"
}
```

Invariants:
- `ping()` exists exactly once in `smoke.py`.
- `ping()` always returns `"pong"`.

### E-002 `test_smoke.py`
- Scope: PRIVATE
- Source: D2 SC-002, SC-004
- Description: Python test module containing the single verification for `ping()`.

| Field | Type | Required | Description | Constraints |
| --- | --- | --- | --- | --- |
| filename | Type:string | Req:yes | Owned test filename | Constraint:must equal `test_smoke.py` |
| imported_symbol | Type:string | Req:yes | Symbol imported from module | Constraint:must equal `ping` |
| test_name | Type:string | Req:yes | Test function name | Constraint:must equal `test_ping` |
| assertion | Type:string | Req:yes | Expected check | Constraint:must equal `ping() == "pong"` |

```json
{
  "filename": "test_smoke.py",
  "imported_symbol": "ping",
  "test_name": "test_ping",
  "assertion": "ping() == \"pong\""
}
```

Invariants:
- `test_smoke.py` contains one test function named `test_ping`.
- The test asserts `ping() == "pong"`.

## Entity Relationship Map
```text
E-002 test_smoke.py --> imports --> E-001 smoke.py
```

## Migration Notes
No prior model — greenfield.
