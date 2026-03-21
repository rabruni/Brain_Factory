# D9: Holdout Scenarios — [Component Name]

**Component:** [Component Name]
**Spec Version:** [X.Y.Z]
**Contracts:** D4 [version]
**Status:** [Draft | Review | Final]
**Author:** [Name — holdout author, NOT the builder agent]
**Last Run:** [Date or "Not yet executed"]
**CRITICAL:** This document is stored separately from the builder. The builder agent MUST NOT see these scenarios before completing their work.

---

## Purpose

This document defines behavioral holdout scenarios, not executable scripts.

The Holdout Agent writes caller-visible scenarios from D2 + D4 only.
The Evaluator Agent later reads this document plus the staged code, discovers the
actual public API surface, writes executable tests, runs them, and records evidence.

D9 MUST NOT contain:
- import statements
- executable bash or Python
- implementation-specific class names
- method calls tied to a specific implementation
- constructor arguments inferred from staged code

D9 MUST contain:
- caller-visible setup
- caller-visible actions
- caller-visible expected outcomes
- authority basis for every assertion
- evidence requirements for evaluation

---

## Scenario Schema

Each scenario MUST be written as YAML-in-markdown using the exact required fields below.
All fields are mandatory.

### HS-001: [Scenario Title]

```yaml
scenario_id: "HS-001"
title: "[Short descriptive title]"
priority: "P0"
authority:
  d2_scenarios:
    - "SC-001"
  d4_contracts:
    - "IN-001"
    - "ERR-001"
category: "happy-path"
setup:
  description: "[Natural-language setup summary]"
  preconditions:
    - "[Required initial state]"
action:
  description: "[Natural-language action summary]"
  steps:
    - "[Ordered caller-visible action 1]"
    - "[Ordered caller-visible action 2]"
expected_outcome:
  description: "[Natural-language expected result summary]"
  assertions:
    - subject: "[What is being checked]"
      condition: "[Expected condition]"
      observable: "[Observable evidence of success/failure]"
  negative_assertions:
    - "[What must NOT be observable]"
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "[Observed value or artifact 1]"
  - "[Observed value or artifact 2]"
```

**Authority Basis:**
- [Exact D2 statement supporting the scenario]
- [Exact D4 contract/postcondition supporting assertion 1]
- [Exact D4 contract/postcondition supporting assertion 2]

**Notes for Evaluator:**
- [Optional clarification that remains behavioral, not implementation-specific]

### HS-002: [Scenario Title]

```yaml
scenario_id: "HS-002"
title: "[Short descriptive title]"
priority: "P1"
authority:
  d2_scenarios:
    - "SC-002"
  d4_contracts:
    - "IN-002"
category: "edge-case"
setup:
  description: "[Natural-language setup summary]"
  preconditions:
    - "[Required initial state]"
action:
  description: "[Natural-language action summary]"
  steps:
    - "[Ordered caller-visible action]"
expected_outcome:
  description: "[Natural-language expected result summary]"
  assertions:
    - subject: "[What is being checked]"
      condition: "[Expected condition]"
      observable: "[Observable evidence]"
  negative_assertions:
    - "[What must NOT happen]"
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "[Observed value or artifact]"
```

**Authority Basis:**
- [Exact D2 statement(s)]
- [Exact D4 statement(s)]

**Notes for Evaluator:**
- [Optional behavioral clarification]

---

## Authoring Rules

### No Contract Strengthening

Holdout may assert only behavior explicitly authorized by D2 + D4.

Do NOT invent:
- fields or response members
- API names
- constructor signatures
- setup protocols not justified by D2 + D4
- temporal semantics stronger than the authority documents
- rollback expectations not stated by D2 + D4
- hidden helper methods or test hooks

If a desired assertion cannot be traced to D2 + D4, it is a D6 OPEN gap, not a valid D9 assertion.

### Authority Basis Is Mandatory

Every assertion in `expected_outcome.assertions` and `negative_assertions` MUST be justified in the
`Authority Basis` block with exact D2 and/or D4 statements.

### Behavioral, Not Implementation-Specific

Describe:
- what state must exist
- what the caller does
- what must be observable

Do not describe:
- imports
- concrete classes
- method names
- constructor arguments
- internal storage layout
- implementation helper hooks

The evaluator discovers the API surface later from staged code. D9 defines expected behavior only.

---

## Scenario Coverage Matrix

| D2 Scenario | Priority | Holdout Coverage | Notes |
|-------------|----------|-----------------|-------|
| SC-001 | [P0/P1] | [HS-001] | [Notes] |
| SC-002 | [P0/P1] | [HS-002, HS-003] | [Notes] |

Coverage gate:
- All D2 P0 scenarios MUST have at least one holdout scenario.
- All D2 P1 scenarios MUST have at least one holdout scenario.
- Zero P0/P1 coverage gaps allowed.

---

## Evaluator Execution Contract

The evaluator reads this D9 document plus staged code and MUST:
- discover the public API surface from staged code
- write one generated test per scenario before execution
- write one mapping file per scenario explaining how the behavioral scenario mapped to the discovered API
- run each generated test 3 times
- preserve raw run outputs per scenario/run

Evaluator-generated files are expected under:
- `runs/<RUN_ID>/eval_tests/attempt<N>/<HS-ID>.py`
- `runs/<RUN_ID>/eval_tests/attempt<N>/<HS-ID>.mapping.md`
- `runs/<RUN_ID>/eval_tests/attempt<N>/<HS-ID>.run1.json`
- `runs/<RUN_ID>/eval_tests/attempt<N>/<HS-ID>.run2.json`
- `runs/<RUN_ID>/eval_tests/attempt<N>/<HS-ID>.run3.json`

The mapping file MUST cite:
- D9 fields used for the translation
- staged code paths used for API discovery

The evaluator MAY inspect staged code to learn how to call the implementation.
The evaluator MUST use D9 + D4 authority to decide what to expect.

---

## Run Protocol

**When to run:** After builder delivery is staged and evaluator is invoked.
**Run order:** P0 scenarios first. If any P0 fails, stop. Then P1. Then P2.
**Scenario pass rule:** A scenario passes if at least 2 of 3 runs pass.
**Overall pass rule:** All P0 scenarios pass, all P1 scenarios pass, and overall pass rate is >= 90%.
**On failure:** Record failed scenario IDs, violated D4 contracts, and actual vs expected observations. Do not rely on forbidden documents.
