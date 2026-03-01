# D1: Constitution — [Component Name]

**Version:** [X.Y.Z]
**Ratified:** [YYYY-MM-DD]
**Last Amended:** [YYYY-MM-DD]
**Design Authority:** [List governing documents — e.g., PRODUCT_SPEC_FRAMEWORK.md, BUILDER_HANDOFF_STANDARD.md, etc.]

---

## Articles

<!--
  Define the immutable rules this component must follow. Each article is a non-negotiable principle.
  Articles should cover: source of truth, isolation boundaries, separation of concerns,
  traceability, validation gates, failure handling, and determinism.

  REQUIRED: Every D1 MUST include articles verifying the Framework Decomposition Standard
  (FWK-0-DRAFT Section 3.0). The three decomposition tests are constitutional:

  1. SPLITTING TEST — This framework is independently authorable. A builder with only its
     spec pack and FWK-0 can produce it without co-authoring another framework.
  2. MERGING TEST — This framework does not contain what should be a separate framework.
     If multiple spec packs represent different capabilities (not modes of the same capability),
     the framework must be split.
  3. OWNERSHIP TEST — This framework has exclusive data ownership. No shared schemas, event
     types, or graph node types with other frameworks. Consumed data comes through declared
     interfaces.

  These three articles should appear first, before component-specific articles.

  Typical article count: 5-10 (including the 3 decomposition articles). Each needs all four subsections.
-->

### Article 1: [Principle Name]

**Rule:** [One sentence stating the immutable rule. Use MUST/MUST NOT language.]

**Why:** [One paragraph explaining why this rule exists. What goes wrong if it's violated?]

**Test:** [How to verify this rule is being followed. Concrete, executable check.]

**Violations:** [Exception policy — typically "No exceptions." If exceptions exist, state the approval process.]

### Article 2: [Principle Name]

**Rule:** [MUST/MUST NOT statement]

**Why:** [Rationale]

**Test:** [Verification method]

**Violations:** [Exception policy]

<!-- Add additional articles as needed. Number sequentially. -->

---

## Boundary Definitions

### ALWAYS (component does this without asking)

<!-- Actions the component performs autonomously, every time, with no human approval needed. -->

- [Action 1]
- [Action 2]
- [Action 3]

### ASK FIRST (component must get human approval)

<!-- Actions that require human decision before proceeding. These are judgment calls. -->

- [Action 1]
- [Action 2]

### NEVER (component refuses even if instructed)

<!-- Hard prohibitions. The component will not do these under any circumstances. -->

- [Action 1]
- [Action 2]

---

## Development Workflow Constraints

<!-- Rules about how this component is developed, tested, and released. -->

- [Constraint 1 — e.g., code lives in its own package]
- [Constraint 2 — e.g., TDD/DTT per-behavior cycles]
- [Constraint 3 — e.g., results file with hashes after every handoff]
- [Constraint 4 — e.g., full regression before release]

## Tooling Constraints

<!-- Prescribe which tools/patterns to use and which to avoid. -->

| Operation | USE THIS | NOT THIS |
|-----------|----------|----------|
| [Operation 1] | [Preferred approach] | [Anti-pattern to avoid] |
| [Operation 2] | [Preferred approach] | [Anti-pattern to avoid] |
| [Operation 3] | [Preferred approach] | [Anti-pattern to avoid] |
