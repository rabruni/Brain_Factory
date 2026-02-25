# D8: Tasks — [Component Name]

**Component:** [Component Name]
**Plan Version:** D7 [version]
**Status:** [Draft | Review | Final]
**Total Tasks:** [N]
**Parallel Opportunities:** [N pairs/groups]

---

## MVP Scope

<!-- Which D2 scenarios are in scope for this build? Which are deferred?
     Reference priority levels from D2. -->

[Scope description — which scenarios are included and why]

---

## Phase 0: Foundation

<!-- Tasks that everything else depends on. Usually parsing, core data structures, or base infrastructure. -->

#### T-001: [Task Name]

**Phase:** 0 — Foundation
**Parallel/Serial:** [Serial | Parallel with T-NNN]
**Dependency:** [None | T-NNN (reason)]
**Scope:** [S (small) | M (medium) | L (large)]
**Scenarios Satisfied:** [D2 scenario IDs — e.g., SC-001, SC-002]
**Contracts Implemented:** [D4 contract IDs — e.g., IN-001, OUT-001]

**Acceptance Criteria:**
<!-- Numbered, specific, testable criteria. Include file names, function signatures,
     entity references, and minimum test counts. -->
- [Criterion 1 — what the code must do]
- [Criterion 2 — what shape the output takes]
- [Criterion 3 — error handling requirements]
- Unit tests: [N]+ ([description of test coverage])

#### T-002: [Task Name]

**Phase:** 0 — Foundation
**Parallel/Serial:** [Serial | Parallel]
**Dependency:** [T-001 (reason)]
**Scope:** [S | M | L]
**Scenarios Satisfied:** [D2 scenario IDs]
**Contracts Implemented:** [D4 contract IDs]

**Acceptance Criteria:**
- [Criterion 1]
- [Criterion 2]
- Unit tests: [N]+

---

## Phase 1: [Phase Name]

<!-- Next layer of tasks. Often generation, transformation, or core business logic. -->

#### T-003: [Task Name]

**Phase:** 1 — [Phase Name]
**Parallel/Serial:** [Parallel with T-004]
**Dependency:** [T-002]
**Scope:** [S | M | L]
**Scenarios Satisfied:** [D2 scenario IDs]
**Contracts Implemented:** [D4 contract IDs]

**Acceptance Criteria:**
- [Criterion 1]
- [Criterion 2]
- Unit tests: [N]+

<!-- Add more phases and tasks as needed.
     Common phase structure:
     Phase 0: Foundation (parsing, core data)
     Phase 1: Generation/Transformation (core logic)
     Phase 2: Execution/Integration (external interactions)
     Phase 3: Validation/Reporting (verification, output assembly) -->

---

## Task Dependency Graph

<!-- ASCII diagram showing task dependencies and parallel opportunities. -->

```
T-001 ([Name])
  │
  ▼
T-002 ([Name])
  │
  ├──────────────┐
  ▼              ▼
T-003 ([Name]) T-004 ([Name])  ◄── parallel
  │              │
  └──────┬───────┘
         ▼
T-005 ([Name])
```

---

## Summary

| Task | Phase | Scope | Serial/Parallel | Scenarios |
|------|-------|-------|-----------------|-----------|
| T-001 | 0 | [S/M/L] | [Serial/Parallel] | [IDs] |
| T-002 | 0 | [S/M/L] | [Serial/Parallel] | [IDs] |
| T-003 | 1 | [S/M/L] | [Parallel w/ T-004] | [IDs] |

**Total: [N] tasks across [N] phases. [N] parallelizable pairs. Estimated [N] serial handoff waves.**

**MVP Tasks:** [List which tasks are required for MVP]
