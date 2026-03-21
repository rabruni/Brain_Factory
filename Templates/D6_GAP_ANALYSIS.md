# D6: Gap Analysis — [Component Name]

**Component:** [Component Name]
**Spec Version:** [X.Y.Z] (matches D2/D3/D4)
**Status:** [In Progress | Complete]
**Shared Gaps:** [Count]
**Private Gaps:** [Count]
**Unresolved:** [Count — MUST be 0 before D7 can proceed]

---

## Boundary Analysis

<!-- Walk every boundary this component touches. For each category, identify whether
     existing contracts cover the need, or whether a gap exists that must be resolved. -->

### Isolation Boundary Completeness Check

<!-- Before closing D6, walk every Sawmill isolation boundary that will consume this spec pack.
     For each consumer, verify that every field definition, payload schema, enum, error code, format
     convention, response shape, behavioral postcondition, temporal invariant, and failure-routing instruction needed to produce correct output is fully
     defined in documents that consumer is allowed to read.
     Minimum check:
       - Turn C / Holdout reads D2 + D4 only
       - Turn D / Builder reads D10 + handoff + D3 + D4
       - Turn E / Evaluator reads D9 + staging only
     If any consumer would need to read a forbidden document to produce correct output, record a gap as OPEN.
     OPEN isolation-boundary completeness gaps block D7.

     D4-D3 RESTATEMENT CHECK: For every payload schema inlined in D4, verify it matches D3 exactly —
     same field names, same types, same required/optional status. D4 restates D3 for consumer
     self-containment; it does not define its own fields. If D4 has a field D3 doesn't, or vice versa,
     or required/optional differs, record as OPEN.

     HOLDOUT BEHAVIOR CHECK: For each D2 scenario that Turn C will encode, verify that D2+D4 define the
     observable pass/fail behavior tightly enough that Holdout does not need to invent temporal assertions
     or stronger semantics. If a D9 assertion would require unstated behavior, record as OPEN. -->

| Consumer Boundary | Allowed Inputs | Completeness Status | Notes |
|-------------------|----------------|---------------------|-------|
| Turn C / Holdout | D2 + D4 only | [RESOLVED/OPEN] | [Can Holdout derive all valid requests, verdict checks, and temporal postconditions from allowed docs alone?] |
| Turn D / Builder | D10 + handoff + D3 + D4 | [RESOLVED/OPEN] | [Can Builder implement and retry correctly without forbidden docs?] |
| Turn E / Evaluator | D9 + staging only | [RESOLVED/OPEN] | [Can Evaluator execute and route failures without forbidden docs?] |

**Isolation gaps found:** [None / list gaps]

### Testable Surface Completeness (BLOCKING — if OPEN, Turn C/D/E results are not trusted)

- Every D9 scenario that requires setup beyond production API calls: does D4 declare the required test double?
- Every declared test double: does it specify failure modes matching D4 error contracts?
- Every declared test double: is its location in package code (NOT `tests/`)?
- If a scenario requires concurrent/timing behavior: does D4 declare how to deterministically reproduce it?
- Status: CLEAR / OPEN (with gap description)
- If OPEN: this gap BLOCKS Turn C holdout authoring, Turn D build, and Turn E evaluation. Resolve before proceeding.

### 1. Data In

[Brief description of how data enters this component.]

| Boundary | Classification | Status |
|----------|---------------|--------|
| [Input source 1] | [PRIVATE/SHARED] | [RESOLVED — explanation / OPEN — what's missing] |
| [Input source 2] | [PRIVATE/SHARED] | [RESOLVED/OPEN] |

**Gaps found:** [None / list gaps]

### 2. Data Out

| Boundary | Classification | Status |
|----------|---------------|--------|
| [Output 1] | [PRIVATE/SHARED] | [RESOLVED/OPEN] |
| [Output 2] | [PRIVATE/SHARED] | [RESOLVED/OPEN] |

**Gaps found:** [None / list gaps]

### 3. Persistence

| What | Where | Owned By | Status |
|------|-------|----------|--------|
| [Persisted data 1] | [Storage location] | [Owner] | [RESOLVED/OPEN] |

**Gaps found:** [None / list gaps]

### 4. Auth / Authz

| Boundary | Status |
|----------|--------|
| [Auth boundary 1] | [RESOLVED/OPEN] |

**Gaps found:** [None / list gaps]

### 5. External Services

| Service | Interface | Status |
|---------|-----------|--------|
| [Service 1] | [How it's called] | [RESOLVED/OPEN] |

<!-- If gaps exist, document them in detail: -->

#### GAP-[N]: [Gap Title] ([RESOLVED | OPEN])

**Category:** [Boundary category from above]
**What Is Needed:** [What the component requires at this boundary]
**Existing Contract:** [Reference to existing spec, or "NONE"]
**Gap Description:** [What must be defined]
**Shared?:** [YES/NO — do other components depend on this?]

**Recommendation:**
- [ ] [Define as shared contract / Define inline / Stub with assumptions]

**Resolution:** [How it was resolved, if RESOLVED]

**Impact If Unresolved:** [What breaks if this stays OPEN]

### 6. Configuration

| Config Item | Source | Status |
|-------------|--------|--------|
| [Config 1] | [Where it comes from] | [RESOLVED/OPEN] |

**Gaps found:** [None / list gaps]

### 7. Error Propagation

| Error Source | Propagation Path | Status |
|--------------|-----------------|--------|
| [Error 1] | [How it propagates] | [RESOLVED/OPEN] |

**Gaps found:** [None / list gaps]

### 8. Observability

| What | How | Status |
|------|-----|--------|
| [Observable 1] | [Observation method] | [RESOLVED/OPEN] |

**Gaps found:** [None / list gaps]

### 9. Resource Accounting

| Resource | Accounting Method | Status |
|----------|-------------------|--------|
| [Resource 1] | [How it's tracked] | [RESOLVED/OPEN] |

**Gaps found:** [None / list gaps]

---

## Clarification Log

<!-- Clarifications found during D1-D5 extraction. Each one is a question the design docs
     didn't answer. All must be RESOLVED before D7 can proceed. -->

#### CLR-001: [Clarification title]

**Found During:** [Which deliverable — D1, D2, D3, D4, or D5]
**Question:** [The specific question that needs an answer]
**Options:** [Reference to D5 research question if applicable, or list options here]
**Status:** [OPEN | RESOLVED(answer) | ASSUMED(assumption)]
**Blocks:** [What deliverables or handoffs are blocked by this]

<!-- Add more clarifications as needed (CLR-002, etc.) -->

---

## Summary

| Category | Gaps Found | Shared | Resolved | Remaining |
|----------|-----------|--------|----------|-----------|
| Data In | [N] | [N] | [N] | [N] |
| Data Out | [N] | [N] | [N] | [N] |
| Persistence | [N] | [N] | [N] | [N] |
| Auth/Authz | [N] | [N] | [N] | [N] |
| External Services | [N] | [N] | [N] | [N] |
| Configuration | [N] | [N] | [N] | [N] |
| Error Propagation | [N] | [N] | [N] | [N] |
| Observability | [N] | [N] | [N] | [N] |
| Resource Accounting | [N] | [N] | [N] | [N] |
| **TOTAL** | **[N]** | **[N]** | **[N]** | **[N]** |

**Gate verdict: [PASS — zero open items, including zero OPEN isolation-boundary completeness gaps. D7 Plan may proceed. | FAIL — [N] open items remain, including any OPEN isolation-boundary completeness gap.]**
