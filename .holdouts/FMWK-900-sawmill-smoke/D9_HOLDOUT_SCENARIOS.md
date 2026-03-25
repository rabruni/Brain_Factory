# D9: Holdout Scenarios — FMWK-900-sawmill-smoke
Meta: v:1.0.0 | contracts:D4 1.0.0 | status:Final | author:Codex holdout-agent | last run:Not yet executed
CRITICAL: Builder MUST NOT see these scenarios before completing work.

## Purpose
Behavioral holdout scenarios only. No executable code. Evaluator later discovers API surface from staged code and writes tests.

## Scenarios
```yaml
scenario_id: "HS-001"
title: "Declared zero-argument callable returns the exact canary value"
priority: P1
authority:
  d2_scenarios: [SC-001]
  d4_contracts: [IN-001, OUT-001, SIDE-001]
category: happy-path
setup:
  description: "Prepare the staged framework so a caller can access the single declared callable surface."
  preconditions:
    - "The staged framework is available for caller-side inspection and invocation."
    - "The evaluator has identified the declared zero-argument callable surface from the staged framework."
action:
  description: "Invoke the declared callable with the empty caller-visible request shape."
  steps:
    - "Access the single declared zero-argument callable surface."
    - "Invoke it without positional input and without keyword input."
expected_outcome:
  description: "The caller observes the exact canary response and no side-effects."
  assertions:
    - subject: "Callable invocation"
      condition: "when executed with the empty request shape"
      observable: "returns the exact lowercase literal \"pong\""
    - subject: "Caller-visible response"
      condition: "after the invocation completes"
      observable: "matches the declared success payload value \"pong\""
    - subject: "Observable system state"
      condition: "throughout and after invocation"
      observable: "shows no caller-visible writes or side-effects"
  negative_assertions:
    - "The invocation does not require any caller-visible request fields."
    - "The invocation does not produce any caller-visible write target."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "Observed callable surface used for the invocation"
  - "Observed return value from each run"
  - "Observed absence of caller-visible side-effects"
```
Authority Basis:
- D2 SC-001: "GIVEN a Python caller invokes `ping()` with no arguments WHEN the function executes THEN it returns the exact string `\"pong\"`"
- D4 IN-001: "Empty caller-visible request payload for `ping()` | Must be `{}` with no fields"
- D4 IN-001 Constraints: "The callable surface is zero-argument only. No positional or keyword arguments are part of the contract."
- D4 OUT-001 Example success: `{ "value": "pong" }`
- D4 SIDE-001: "Write Shape: No writes"
- D4 SIDE-001: "Failure Behavior: Not applicable; the function has no side-effects"
Notes for Evaluator:
- Treat the staged callable that satisfies the D4 zero-argument contract as the target. The required observable is only the exact caller-visible value and absence of side-effects.

```yaml
scenario_id: "HS-002"
title: "Imported caller path succeeds when the declared callable is exercised through the test-facing boundary"
priority: P1
authority:
  d2_scenarios: [SC-002]
  d4_contracts: [IN-001, OUT-001, ERR-001]
category: lifecycle
setup:
  description: "Prepare the framework in the same caller-visible state used by the test-facing boundary."
  preconditions:
    - "The staged framework is available for caller-side import discovery."
    - "The evaluator has identified the test-facing boundary that imports the declared callable from the framework."
action:
  description: "Exercise the imported callable through the test-facing boundary."
  steps:
    - "Resolve the test-facing import path used by the framework."
    - "Run the caller-visible assertion path that exercises the declared zero-argument callable."
expected_outcome:
  description: "The imported boundary succeeds because the declared callable is present and returns the contract value."
  assertions:
    - subject: "Test-facing import boundary"
      condition: "when it resolves the declared callable from the framework"
      observable: "successfully reaches the callable without contract failure"
    - subject: "Assertion path"
      condition: "when the callable is exercised through that boundary"
      observable: "passes because the observed value is the exact literal \"pong\""
  negative_assertions:
    - "The boundary does not encounter a missing callable condition."
    - "The boundary does not encounter a renamed callable condition."
    - "The boundary does not encounter a non-zero-argument callable condition."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "Observed import boundary used by the framework"
  - "Observed result of the caller-visible assertion path for each run"
  - "Any caller-visible contract failure surfaced during import or invocation"
```
Authority Basis:
- D2 SC-002: "GIVEN the test runner imports `ping` from `smoke` WHEN `test_ping()` runs THEN the assertion passes"
- D4 IN-001 Constraints: "The callable surface is zero-argument only. No positional or keyword arguments are part of the contract."
- D4 OUT-001: "Scenarios: SC-001, SC-002, SC-004"
- D4 ERR-001: "Condition: `ping()` is missing, renamed, or has a non-zero-argument signature"
- D4 ERR-001: "Caller Action: Treat as contract failure and fix the module/test to match the declared callable surface"
Notes for Evaluator:
- This scenario is about the caller-visible import and assertion behavior, not the implementation details of the module layout beyond what the staged framework exposes.

```yaml
scenario_id: "HS-003"
title: "Noncompliant return values are rejected as contract failures"
priority: P1
authority:
  d2_scenarios: [SC-004]
  d4_contracts: [OUT-001, ERR-002]
category: failure-injection
setup:
  description: "Prepare a caller-visible execution path that can detect whether the staged callable complies with the declared return contract."
  preconditions:
    - "The staged framework is available for caller-side invocation."
    - "The evaluator has a caller-visible assertion path that compares the observed return value to the declared exact literal."
action:
  description: "Exercise the staged callable and evaluate the observed return value against the declared exact literal contract."
  steps:
    - "Invoke the declared zero-argument callable through the caller-visible assertion path."
    - "Compare the observed return value to the exact lowercase literal required by the contract."
expected_outcome:
  description: "Any value other than the exact literal is treated as a contract failure."
  assertions:
    - subject: "Return-value validation"
      condition: "if the observed value is anything other than the exact lowercase literal \"pong\""
      observable: "the caller-visible assertion path fails validation"
    - subject: "Failure classification"
      condition: "when the observed value differs from the declared exact literal"
      observable: "the outcome is treated as a contract failure rather than a success"
  negative_assertions:
    - "A non-matching return value is not accepted as equivalent."
    - "A non-matching return value does not produce a framework-level success result."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "Observed return value from each run"
  - "Observed caller-visible validation result for each run"
  - "Observed contract-failure classification when the value is noncompliant"
```
Authority Basis:
- D2 SC-004: "GIVEN `ping()` returns any value other than the exact lowercase literal `\"pong\"` WHEN `test_ping()` runs THEN the framework fails validation"
- D4 OUT-001: "Example failure: No framework-level failure payload exists; noncompliance appears as a test failure or Python call-site exception."
- D4 ERR-002: "Condition: `ping()` returns any value other than `\"pong\"`"
- D4 ERR-002: "Caller Action: Treat as contract failure and restore the exact literal return value"
Notes for Evaluator:
- Use the staged code only to find the callable and the assertion boundary. The expected outcome is limited to the caller-visible validation failure semantics stated above.

```yaml
scenario_id: "HS-004"
title: "Scope drift is rejected when extra files, dependencies, or framework behaviors appear"
priority: P1
authority:
  d2_scenarios: [SC-003, SC-005]
  d4_contracts: [SIDE-001, ERR-003]
category: integrity
setup:
  description: "Prepare the staged framework for caller-visible scope inspection."
  preconditions:
    - "The staged framework contents are available for evaluator inspection."
    - "The evaluator can identify the framework files that are in scope for the canary."
action:
  description: "Inspect the staged framework for out-of-scope surface."
  steps:
    - "Inspect the staged framework contents."
    - "Determine whether the framework exposes only the declared in-scope files and no declared dependencies."
    - "Determine whether any additional files, dependencies, or framework behaviors appear."
expected_outcome:
  description: "The canary remains in scope only when no extra surface appears; any extra surface is rejected."
  assertions:
    - subject: "Framework scope inspection"
      condition: "when the staged framework contains only the declared in-scope files and no dependencies"
      observable: "the framework remains within the declared canary scope"
    - subject: "Framework scope inspection"
      condition: "when additional files, dependencies, or framework behaviors appear"
      observable: "the build is rejected as out of scope"
  negative_assertions:
    - "Extra files are not accepted as part of the canary."
    - "Extra dependencies are not accepted as part of the canary."
    - "Extra framework behaviors are not accepted as part of the canary."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "Observed staged file inventory"
  - "Observed dependency declarations or absence of declarations"
  - "Observed caller-visible rationale for accepting or rejecting scope"
```
Authority Basis:
- D2 SC-003: "GIVEN the framework is prepared for build/review WHEN its contents are inspected THEN only `smoke.py` and `test_smoke.py` are in scope and no dependencies are declared"
- D2 SC-005: "GIVEN additional files, services, or framework patterns are introduced WHEN the framework is reviewed THEN the build is treated as out of scope and rejected"
- D4 SIDE-001: "Target System: None"
- D4 SIDE-001: "Write Shape: No writes"
- D4 ERR-003: "Condition: Additional files, dependencies, or framework behaviors appear"
- D4 ERR-003: "Caller Action: Reject the build as out of scope and remove the extra surface"
Notes for Evaluator:
- This scenario covers both the happy in-scope inspection outcome and the cross-boundary rejection path when the staged package surface drifts beyond the declared canary.

## Coverage Matrix
All D2 P0 and P1 scenarios MUST have holdout coverage. Zero gaps allowed.

| D2 Scenario | Priority | Holdout Coverage | Notes |
|-------------|----------|------------------|-------|
| SC-001 | P1 | HS-001 | Happy-path invocation and exact return literal |
| SC-002 | P1 | HS-002 | Test-facing import and assertion boundary |
| SC-003 | P1 | HS-004 | In-scope file/dependency inspection |
| SC-004 | P1 | HS-003 | Invalid return value rejection |
| SC-005 | P1 | HS-004 | Scope-drift rejection for extra surface |

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
