# D3: Data Model - FMWK-900-sawmill-smoke
Meta: v:1.0.0 (matches D2) | status:Draft | shared entities:0

This framework introduces no runtime or shared data model. D3 records the two private owned artifacts required by `TASK.md` so D4 can trace contracts without inventing extra implementation scope.

## Entities

### E-001 - Smoke Module Artifact
- Scope: PRIVATE
- Source: D2 SC-001, SC-002
- Description: The owned Python source file `smoke.py` containing the single in-scope callable `ping()`.

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| path | path | yes | Source file path | exactly `staging/FMWK-900-sawmill-smoke/smoke.py` |
| symbol | string | yes | Exported function name | exactly `ping` |
| args | string | yes | Function signature summary | exactly `none` |
| return_literal | string | yes | Expected return value | exactly `pong` |

```json
{
  "path": "staging/FMWK-900-sawmill-smoke/smoke.py",
  "symbol": "ping",
  "args": "none",
  "return_literal": "pong"
}
```

Invariants:
- The file defines `ping`.
- `ping()` accepts no arguments.
- `ping()` returns the literal string `"pong"`.

### E-002 - Smoke Test Artifact
- Scope: PRIVATE
- Source: D2 SC-003, SC-004, SC-005
- Description: The owned pytest file `test_smoke.py` that imports `ping` and proves the canary behavior with one assertion.

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| path | path | yes | Test file path | exactly `staging/FMWK-900-sawmill-smoke/test_smoke.py` |
| imported_symbol | string | yes | Imported symbol under test | exactly `ping` |
| assertion | string | yes | Expected test assertion | exactly `ping() == "pong"` |

```json
{
  "path": "staging/FMWK-900-sawmill-smoke/test_smoke.py",
  "imported_symbol": "ping",
  "assertion": "ping() == \"pong\""
}
```

Invariants:
- The file imports `ping` from `smoke`.
- The test asserts the exact literal `pong`.
- The file contains one in-scope test, `test_ping`.

## Entity Relationship Map

```text
E-002 Smoke Test Artifact
  -> imports `ping` from
E-001 Smoke Module Artifact
```

## Migration Notes

No prior model - greenfield. This document tracks owned artifacts only; it does not introduce a reusable runtime data model.
