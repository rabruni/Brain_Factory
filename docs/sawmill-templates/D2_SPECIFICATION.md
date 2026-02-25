# D2: Specification — [Component Name]

**Component:** [Component Name]
**Package ID:** [PKG-XXXX-NNN or TBD]
**Spec Version:** [X.Y.Z]
**Status:** [Draft | Review | Final]
**Author:** [Name(s)]
**Design Sources:** [List of design documents, standards, and prior art used to extract this spec]
**Constitution:** [Reference to D1 version — e.g., D1 v1.0.0]

---

## Component Purpose

<!-- One paragraph: what this component does, stated without implementation details.
     The test: could a new team member read this and correctly explain the component's job? -->

[Component purpose paragraph]

## What This Component Is NOT

<!-- Explicit negative boundaries to prevent scope creep. At least 3 items.
     Format: "This component is NOT a [thing]. It does not [capability]." -->

- [Component] is NOT [thing]. It does not [capability].
- [Component] is NOT [thing]. It does not [capability].
- [Component] is NOT [thing]. It does not [capability].

## User Scenarios

### Primary Scenarios (happy path)

<!-- 3-7 concrete scenarios in GIVEN/WHEN/THEN format. Each describes one interaction path
     from the caller's perspective. Include priority, source tracing, and testing approach. -->

#### SC-001: [Scenario title]

**Priority:** [P1 (must-have) | P2 (important) | P3 (nice-to-have)]
**Source:** [Design doc section this was extracted from, or "NEW — justification"]

**GIVEN** [precondition — state of the system before this scenario]
**WHEN** [trigger — what the caller does]
**THEN** [outcome — what the component produces, including side effects]
**AND** [additional outcomes if needed]

**Testing Approach:** [How to verify this scenario works]

#### SC-002: [Scenario title]

**Priority:** [P1 | P2 | P3]
**Source:** [Reference]

**GIVEN** [precondition]
**WHEN** [trigger]
**THEN** [outcome]

**Testing Approach:** [Verification method]

<!-- Add more primary scenarios as needed (SC-003, SC-004, etc.) -->

### Edge Cases and Failure Modes

<!-- 2-4 scenarios covering failure paths, boundary conditions, and degradation. -->

#### SC-[N]: [Edge case title]

**Priority:** [P1 | P2 | P3]
**Source:** [Reference — e.g., D1 Article N, design doc section]

**GIVEN** [failure or boundary precondition]
**WHEN** [trigger]
**THEN** [expected failure behavior — explicit error, graceful degradation, etc.]

**Testing Approach:** [Verification method]

<!-- Add more edge case scenarios as needed -->

## Deferred Capabilities

<!-- Things this component might do eventually but are NOT in this build.
     Each deferral must explain WHY and WHAT would trigger adding it. -->

#### DEF-001: [Capability name]

**What:** [Description of the deferred capability]
**Why Deferred:** [Reason it's not in scope now]
**Trigger:** [What condition would cause this to be added]
**Impact if Never Added:** [What happens if this is permanently skipped]

<!-- Add more deferrals as needed (DEF-002, DEF-003, etc.) -->

## Success Criteria

<!-- Checklist of measurable criteria. When all are met, the component works. -->

- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]
- [ ] [Criterion 4]

## Clarification Markers

<!-- Flag anything that needs resolution before building. These feed into D6 (Gap Analysis).
     Use [NEEDS CLARIFICATION] prefix for items that block design decisions. -->

[NEEDS CLARIFICATION]: [Question that must be resolved — e.g., which backend to use, which protocol, etc.]

<!-- Remove this section if no clarifications are needed. -->
