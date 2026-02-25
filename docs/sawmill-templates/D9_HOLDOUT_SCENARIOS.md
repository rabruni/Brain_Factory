# D9: Holdout Scenarios — [Component Name]

**Component:** [Component Name]
**Spec Version:** [X.Y.Z]
**Contracts:** D4 [version]
**Status:** [Draft | Review | Final]
**Author:** [Name — spec author, NOT the builder agent]
**Last Run:** [Date or "Not yet executed"]
**CRITICAL: This document is stored separately from the builder. The builder agent MUST NOT see these scenarios before completing their work.**

---

## Scenarios

<!-- Holdout scenarios are acceptance tests written by the spec author, stored separately
     from the build, and evaluated AFTER the builder delivers. The builder never sees them.
     This prevents "teaching to the test."

     Each scenario needs: metadata (YAML), what it validates, setup/execute/verify steps,
     and cleanup. Verify steps should be executable (bash commands with exit codes). -->

### HS-001: [Scenario title — descriptive name]

```yaml
component: [component-id]
scenario: [scenario-slug]
priority: [P0 | P1 | P2]
```

**Validates:** [D2 scenario IDs this holdout tests — e.g., SC-001, SC-006]
**Contracts:** [D4 contract IDs being verified — e.g., IN-001, OUT-001]
**Type:** [Happy path | Error path | Side-effect verification | Integration]

**Setup:**
```bash
# Prepare the test environment
# [Setup commands — create temp dirs, copy files, configure test data]
```

**Execute:**
```bash
# Run the component
# [Execution commands — invoke the component, capture output]
```

**Verify:**

| Check | What to Examine | PASS Condition | FAIL Condition |
|-------|----------------|----------------|----------------|
| 1 | [What to check] | [Concrete pass condition] | [Concrete fail condition] |
| 2 | [What to check] | [Pass condition] | [Fail condition] |

```bash
# Executable verification commands (exit code 0 = PASS, non-zero = FAIL)
# [Verification commands]
```

**Cleanup:**
```bash
# Remove temp files and restore environment
# [Cleanup commands]
```

### HS-002: [Scenario title]

```yaml
component: [component-id]
scenario: [scenario-slug]
priority: [P0 | P1 | P2]
```

**Validates:** [D2 scenario IDs]
**Contracts:** [D4 contract IDs]
**Type:** [Type]

**Setup:**
```bash
# [Setup commands]
```

**Execute:**
```bash
# [Execution commands]
```

**Verify:**

| Check | What to Examine | PASS Condition | FAIL Condition |
|-------|----------------|----------------|----------------|
| 1 | [What to check] | [Pass condition] | [Fail condition] |

```bash
# [Verification commands]
```

**Cleanup:**
```bash
# [Cleanup commands]
```

<!-- Add more holdout scenarios as needed (HS-003, HS-004, etc.)
     Minimum: 3 scenarios covering happy path, error path, and cross-boundary integration. -->

---

## Scenario Coverage Matrix

<!-- Map D2 scenarios to holdout coverage. Identify any scenarios not covered. -->

| D2 Scenario | Priority | Holdout Coverage | Notes |
|-------------|----------|-----------------|-------|
| SC-001 | [P1] | [HS-001] | [Notes] |
| SC-002 | [P1] | [HS-002, HS-003] | [Notes] |
| SC-003 | [P1] | [—] | [Why not covered / covered by unit tests] |

---

## Run Protocol

**When to run:** [After builder delivers and all handoff-level tests pass]
**Run environment:** [Required runtime environment — language version, dependencies, config]
**Run order:** [P0 scenarios first. If any P0 fails, stop. Then P1. Then P2.]
**Pass threshold:** [All P0 pass (N/N). All P1 pass (N/N). No partial credit.]
**On failure:** [File against the D8 task responsible. Include: which D2 scenario failed, which D4 contract was violated, actual vs. expected output.]
