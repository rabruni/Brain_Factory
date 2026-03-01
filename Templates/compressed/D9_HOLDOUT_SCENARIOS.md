# D9: Holdout Scenarios — {name}
Meta: v:{ver} | contracts: D4 {ver} | status:{Draft|Review|Final} | author:{spec author, NOT builder} | last run:{date or "Not yet executed"}
CRITICAL: Builder agent MUST NOT see these scenarios before completing their work.

## Scenarios (HS-### IDs, minimum 3: happy path + error path + integration)
Per scenario:
- YAML header: component, scenario slug, priority (P0|P1|P2)
- Validates: D2 SC-### IDs
- Contracts: D4 contract IDs being verified
- Type: Happy path | Error path | Side-effect verification | Integration
- Setup: bash commands to prepare environment
- Execute: bash commands to run component
- Verify: | Check | What to Examine | PASS Condition | FAIL Condition | + executable bash (exit 0=PASS)
- Cleanup: bash commands

## Coverage Matrix
COVERAGE GATE: All D2 P0 and P1 scenarios MUST have holdout coverage. Zero gaps allowed. P2/P3 may defer to unit tests.
| D2 Scenario | Priority | Holdout Coverage | Notes |

## Run Protocol
When: after builder delivers + handoff tests pass.
Order: P0 first (any fail = stop), then P1, then P2.
Threshold: all P0 pass, all P1 pass, no partial credit.
On failure: file against responsible D8 task. Include: failed SC-###, violated contract, actual vs expected.
