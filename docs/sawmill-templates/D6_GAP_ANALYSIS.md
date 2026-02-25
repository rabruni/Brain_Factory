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

**Gate verdict: [PASS — zero open items. D7 Plan may proceed. | FAIL — [N] open items remain.]**
