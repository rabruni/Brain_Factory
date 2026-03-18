# D7: Plan — sawmill smoke canary
Meta: v:1.0.0 (matches D2) | status:Final | constitution: D1 1.0.0 | gap analysis: D6 PASS (0 open)

## Summary
Build a minimal system-test canary that stages one Python module exposing `ping() -> str` and one unit test proving it returns `"pong"`. The architecture stays intentionally flat because the task exists to verify the Sawmill pipeline end to end without adding product behavior, dependencies, or framework scaffolding.

## Technical Context
Language/Version | Python 3.x | Key Dependencies | none | Storage | none | Testing Framework | pytest-style unit test | Platform | local Python execution in staged framework output | Performance Goals | deterministic instant import and test execution | Scale/Scope | exactly two owned files and one behavior

## Constitution Check
| Article | Principle | Compliant (YES/NO) | Notes (how architecture satisfies) |
| --- | --- | --- | --- |
| 1. SPLITTING | exactly one module and one test | YES | Plan creates only `smoke.py` and `test_smoke.py`. |
| 2. MERGING | no hidden extra capability | YES | Only `ping() -> "pong"` is implemented and tested. |
| 3. OWNERSHIP | exclusive ownership of the two files | YES | File plan assigns both owned files only to this framework. |
| 4. SOURCE OF TRUTH | task file defines full scope | YES | Every component and test traces directly to D2 scenarios sourced from `TASK.md`. |
| 5. ISOLATION | zero runtime dependencies | YES | No `platform_sdk`, Docker, services, or external imports are allowed. |
| 6. TRACEABILITY | every artifact maps to task scope | YES | D8 tasks trace to D2 and D4; no supporting artifacts beyond required Turn B docs. |
| 7. VALIDATION | one assertion on `ping() == "pong"` | YES | Testing strategy uses one unit test with the exact required assertion. |
| 8. FAILURE HANDLING | fail fast with normal Python/test failures | YES | Import or assertion failures surface directly; no custom error machinery is added. |
| 9. DETERMINISM | literal `"pong"` on every call | YES | Single pure function returns a fixed literal with no side effects. |

## Architecture Overview
```text
test_smoke.py
  imports ping from smoke.py
  calls ping()
  asserts result == "pong"
```

### Component Responsibilities
- File: `smoke.py`
  - Responsibility | implement the single deterministic function
  - Implements | D2 SC-001, SC-003
  - Depends On | none
  - Exposes | `def ping() -> str`
- File: `test_smoke.py`
  - Responsibility | verify importability and correct literal return value
  - Implements | D2 SC-002, SC-003, SC-004
  - Depends On | `smoke.py`
  - Exposes | `def test_ping() -> None`

### File Creation Order
```text
smoke.py         # source file defining ping() -> "pong"
test_smoke.py    # unit test importing ping and asserting the literal result
```

### Testing Strategy
- Unit Tests: one direct unit test imports `ping`, calls it without arguments, and asserts the literal `"pong"` result; no mocking is required because there are no dependencies.
- Integration Tests: none; D1 and D2 explicitly prohibit external systems and broader architecture.
- Smoke Test: run the single test file and expect one passing test with no setup beyond local Python execution.

### Complexity Tracking
| Component | Est. Lines | Risk (Low/Med/High) | Notes |
| --- | --- | --- | --- |
| `smoke.py` | 3-5 | Low | One pure function with fixed output. |
| `test_smoke.py` | 4-6 | Low | One import and one assertion. |
| Total source | 3-5 | Low | Minimal canary scope. |
| Total tests | 4-6 | Low | Single verification path. |

### Migration Notes
Greenfield — no migration.
