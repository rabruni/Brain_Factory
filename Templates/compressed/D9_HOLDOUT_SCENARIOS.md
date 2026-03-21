# D9: Holdout Scenarios — {name}
Meta: v:{ver} | contracts:D4 {ver} | status:{Draft|Review|Final} | author:{holdout author, NOT builder} | last run:{date or "Not yet executed"}
CRITICAL: Builder MUST NOT see these scenarios before completing work.

## Purpose
Behavioral holdout scenarios only. No executable code. Evaluator later discovers API surface from staged code and writes tests.

## Per-Scenario Schema (all fields required)
Each `HS-NNN` uses YAML-in-markdown:
- scenario_id: "HS-NNN"
- title: string
- priority: P0|P1|P2
- authority:
  - d2_scenarios: [SC-NNN, ...]
  - d4_contracts: [IN-NNN, ERR-NNN, ...]
- category: happy-path|edge-case|failure-injection|integrity|lifecycle
- setup:
  - description: string
  - preconditions: ordered list
- action:
  - description: string
  - steps: ordered caller-visible operations
- expected_outcome:
  - description: string
  - assertions:
    - subject / condition / observable
  - negative_assertions: list
- pass_criteria:
  - runs_required: 3
  - pass_threshold: "2 of 3"
- evidence_to_collect: list
Below each YAML block include:
- Authority Basis: exact D2 + D4 statements supporting every assertion
- Notes for Evaluator: optional behavioral clarification only

## Rules
- No imports, class names, method calls, constructor args, or executable bash/python.
- No contract strengthening or invented temporal semantics.
- If an assertion is not explicitly supported by D2+D4, it is a D6 OPEN gap.
- Describe behavior only: setup, action, observable outcome.

## Coverage Matrix
All D2 P0 and P1 scenarios MUST have holdout coverage. Zero gaps allowed.
| D2 Scenario | Priority | Holdout Coverage | Notes |

## Evaluator Contract
Evaluator writes, per scenario per attempt:
- `eval_tests/attemptN/HS-NNN.py`
- `eval_tests/attemptN/HS-NNN.mapping.md`
- `eval_tests/attemptN/HS-NNN.run{1,2,3}.json`
Mapping file MUST cite D9 fields used + staged code paths used for API discovery.
Evaluator may use code to learn HOW to call the implementation, never WHAT behavior to expect.

## Run Protocol
Order: P0 first, then P1, then P2.
Scenario pass: 2 of 3 runs.
Overall pass: all P0 pass, all P1 pass, overall >= 90%.
