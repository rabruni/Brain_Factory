# D10: Agent Context — [Component Name]

**Component:** [Component Name]
**Package:** [PKG-XXXX-NNN]
**Updated:** [YYYY-MM-DD]

---

## What This Project Does

<!-- One paragraph: what the component does, end-to-end, in plain language.
     A builder agent reads this first to understand the big picture. -->

[Project description paragraph]

## Architecture Overview

<!-- Two views: (1) ASCII diagram showing command flow, and (2) directory structure. -->

```
[Command flow diagram — show how CLI commands route through components]
```

```
[directory]/              — [Description of source modules]
tests/                    — [Test framework and location]
[other dirs]/             — [Supporting files]
```

## Key Patterns

<!-- The 4-6 most important architectural patterns the builder must understand.
     Each pattern should be one sentence with a reference to the D1 article or design decision. -->

- **[Pattern Name]:** [Description and D1/D5 reference]
- **[Pattern Name]:** [Description and reference]
- **[Pattern Name]:** [Description and reference]
- **[Pattern Name]:** [Description and reference]

## Commands

<!-- Every command the builder needs. Copy-pasteable. Include: build, test, run, verify. -->

```bash
# [Command category 1 — e.g., Run the component]
[command 1]

# [Command category 2 — e.g., Run tests]
[command 2]

# [Command category 3 — e.g., Run a single test file]
[command 3]

# [Command category 4 — e.g., Full regression]
[command 4]
```

## Tool Rules

<!-- Prescribe which tools/patterns builders should use and which to avoid.
     Format: USE THIS / NOT THIS / WHY -->

| USE THIS | NOT THIS | WHY |
|----------|----------|-----|
| [Preferred tool/pattern] | [Anti-pattern] | [Reason] |
| [Preferred tool/pattern] | [Anti-pattern] | [Reason] |

## Coding Conventions

<!-- Language-specific rules that apply to all code in this component. -->

- [Convention 1 — e.g., language version, stdlib-only policy]
- [Convention 2 — e.g., type hints on all public functions]
- [Convention 3 — e.g., dataclasses for all entities]
- [Convention 4 — e.g., explicit result objects, no exceptions for expected failures]
- [Convention 5 — e.g., exit codes]
- [Convention 6 — e.g., test framework and fixtures]

## Submission Protocol

<!-- Step-by-step: what the builder does when they're done building. -->

1. [Step 1 — e.g., answer 13 questions, STOP, wait for approval]
2. [Step 2 — e.g., build via DTT per-behavior cycles]
3. [Step 3 — e.g., write RESULTS file with hashes and test counts]
4. [Step 4 — e.g., run full regression, report new failures]

```
Branch:  [branch naming convention]
Commit:  [commit message format]
Results: [results file path convention]
```

## Active Components (what you'll interact with)

<!-- Reference table of all components the builder may need to call or modify. -->

| Component | Where | Interface |
|-----------|-------|-----------|
| [Component 1] | [file path] | [function signature] |
| [Component 2] | [file path] | [function signature] |

## Links to Deeper Docs

<!-- Pointers to other D-documents for more detail. Keep brief — just doc name and what to find there. -->

- D1 Constitution: [What to find there]
- D2 Specification: [What to find there]
- D3 Data Model: [What to find there]
- D4 Contracts: [What to find there]
- D5 Research: [What to find there]
- D6 Gap Analysis: [What to find there]
- D7 Plan: [What to find there]
- D8 Tasks: [What to find there]
- D9 Holdout Scenarios: [What to find there — note: kept separate from builders during active build]
