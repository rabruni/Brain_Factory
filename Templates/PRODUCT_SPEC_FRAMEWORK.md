# Product Spec Framework

**Status:** [Draft | Final] | **Created:** [YYYY-MM-DD] | **Author:** [Name(s)]
**Purpose:** Define the complete set of deliverables required to fully specify a component before decomposing it into agent-executable handoffs.

---

## Why This Framework Exists

The gap between "we know what this component should do" and "an agent can build it without us chasing issues for days" is filled by seven deliverables. Each one answers a different question. Together they constitute a complete product spec — sufficient to decompose into handoffs and sufficient to verify the result.

The framework is extraction-first: most content already exists in design documents. The work is consolidation and gap-finding, not invention. When a deliverable cannot be completed from existing design docs, that gap IS the finding — it becomes a Forced Clarification (Deliverable 6) that must be resolved before handoff decomposition begins.

**Process flow:**

```
Design Documents                    Product Spec (D1-D10)                   Build Sequence
─────────────────                   ──────────────────────                  ──────────────
[Your design docs]     ──┐
[Architecture docs]    ──┼──▶  Extract ──▶ D1 through D10 ──▶ Resolve ──▶ Handoff decomposition
[Prior art / specs]    ──┘         ▲              │           D6 gaps         │
                                   │              ▼                           ▼
                             Repeatable      Gap Analysis               H-0: Shared contracts
                             per component   surfaces what              H-1: Thinnest working pipe
                                             design docs                H-2+: Layered capabilities
                                             don't answer
```

---

## The Seven Core Deliverables

<!-- These seven deliverables form the conceptual model. In practice, the D1-D10 template
     system expands these into 10 documents plus supporting standards. The mapping is:
     D1 = Constitution (identity + immutable rules)
     D2 = Specification (scenarios)
     D3 = Data Model (interfaces)
     D4 = Contracts (boundaries)
     D5 = Research (design decisions)
     D6 = Gap Analysis (forced clarifications)
     D7 = Plan (architecture)
     D8 = Tasks (work decomposition)
     D9 = Holdout Scenarios (acceptance proof)
     D10 = Agent Context (builder handbook)
-->

### D1: Component Identity

**Question it answers:** What is this thing, and where does it live in the system?

**What it contains:**
- Name, ID, and any aliases or prior names
- System placement (tier, classification, role)
- One-paragraph purpose statement (no implementation details)
- Explicit "What it is NOT" boundaries (at least 3)

**Acceptance criteria:**
- [ ] Purpose paragraph uses no implementation terms
- [ ] "What it is NOT" contains at least 3 explicit negative boundaries
- [ ] A reviewer can answer "What does it do? What does it NOT do?" from D1 alone

---

### D2: User Stories and Scenarios

**Question it answers:** What does this component do from the perspective of its callers?

**What it contains:**
- 3-7 primary scenarios in GIVEN/WHEN/THEN format
- 2-4 edge case scenarios covering failure modes
- Source tracing for each scenario (which design doc it came from)

**Acceptance criteria:**
- [ ] Every primary scenario traces to a design doc section
- [ ] At least 2 edge case scenarios cover failure modes
- [ ] Scenarios are from the caller's perspective, not the component's internals
- [ ] Coverage includes: normal operation, error, resource exhaustion, invalid input

---

### D3: Interface Definitions

**Question it answers:** What goes in, what comes out, and what is the exact shape of each?

**What it contains:**
- Inbound interface(s) with field-level schemas
- Outbound interface(s) with field-level schemas
- Side-effect interfaces (observable writes to external systems)
- Error interface (error codes, shapes, caller recovery actions)

**Acceptance criteria:**
- [ ] Every field has a type, required/optional flag, and description
- [ ] Every interface has at least one concrete example
- [ ] Error interface covers: invalid input, missing dependency, resource exhaustion, upstream failure

---

### D4: Dependency Surface Analysis

**Question it answers:** What does this component need from the system that may not exist yet?

**Boundary categories to examine:**

| Category | What to examine |
|----------|----------------|
| **Data In** | Is the inbound schema defined somewhere shared, or only here? |
| **Data Out** | Will other components consume this output? |
| **Persistence** | What gets written to disk/ledger? Is the format shared? |
| **Auth / Authz** | Who can call this component? How is identity established? |
| **External Services** | What APIs or providers does this call? |
| **Configuration** | What's tunable? Where does config live? |
| **Error Propagation** | Does a failure here cascade? How does the system recover? |
| **Observability** | What can an operator see? Metrics, health checks, traces? |
| **Resource Accounting** | How are consumed resources reported? |

**Acceptance criteria:**
- [ ] Every boundary category examined (no "N/A" without justification)
- [ ] Every gap classified as SHARED or component-private
- [ ] Every SHARED gap has a recommendation

---

### D5: Non-Goals

**Question it answers:** What is explicitly out of scope for this component?

**What it contains:**
- Capability non-goals (permanent architectural boundaries)
- Deferred capabilities (with WHY and TRIGGER for each)
- Adjacent component boundaries (capabilities owned by other components)

**Acceptance criteria:**
- [ ] At least 3 capability non-goals
- [ ] Every deferred capability has WHY and TRIGGER
- [ ] Adjacent boundaries reference the actual owning component

---

### D6: Forced Clarifications

**Question it answers:** What do we NOT know yet, and what must be resolved before building?

**This is the most important deliverable.** D1-D5 are extraction. D6 is where you discover what the design docs don't answer.

**What it contains:**
- Unresolved design questions (found during D1-D5 extraction)
- Decision-required items (multiple valid options, human must choose)
- Assumption log (assumptions made during extraction that need validation)

**Status values:** OPEN | RESOLVED(answer) | ASSUMED(assumption)

**Acceptance criteria:**
- [ ] Every ASSUMED entry in D1-D5 has a corresponding D6 clarification
- [ ] Every OPEN clarification states which handoffs it blocks
- [ ] RESOLVED items include the decision and who made it
- [ ] **Gate: zero OPEN items before handoff decomposition begins**

---

### D7: Holdout Scenarios

**Question it answers:** How do we prove the built component actually works, independent of the builder's own tests?

**The Dark Factory pattern:** The builder agent writes tests during DTT. But holdout scenarios are acceptance tests written by the spec author, stored separately, evaluated AFTER the builder delivers. The builder never sees them.

**What it contains:**
- 3-5 end-to-end acceptance scenarios
- Executable verification steps (commands with exit codes, not prose)
- Separation enforcement (holdouts stored separately from builder handoffs)

**Acceptance criteria:**
- [ ] At least 3 holdout scenarios (happy path, error path, integration)
- [ ] Every scenario has executable verification steps
- [ ] Scenarios are stored separately from handoff specs

---

## How the Deliverables Compose

```
D1: Identity ─────────────────────────▶ "What is it?"
D2: User Stories ─────────────────────▶ "What does it do?" (caller's view)
D3: Interface Definitions ────────────▶ "What goes in / comes out?" (exact shapes)
D4: Dependency Surface ───────────────▶ "What's missing?" (shared contracts, gaps)
D5: Non-Goals ────────────────────────▶ "What does it NOT do?" (scope boundaries)
D6: Forced Clarifications ────────────▶ "What don't we know?" (gate before building)
D7: Holdout Scenarios ────────────────▶ "How do we prove it works?" (reviewer's tests)

D1-D3: Extraction (pull from design docs)
D4:    Analysis (walk boundaries, find gaps)
D5:    Scoping (prevent creep)
D6:    Accumulated during D1-D5 (gaps found along the way)
D7:    Written after D1-D3 are stable (acceptance proof)
```

**The handoff decomposition gate:** D6 has zero OPEN items. Only then do you decompose into:

- **H-0:** Shared contracts identified by D4
- **H-1:** Thinnest working pipe (smallest subset of D2 scenarios)
- **H-2+:** Layered capabilities (remaining D2 scenarios)

Each handoff references specific D2 scenarios, D3 interfaces, and D4 contracts.

---

## Repeatable Process

This framework applies to any component. The steps:

1. **Select component.** Identify what you're speccing.
2. **Identify design doc sources.** Which documents contain information about this component.
3. **Extract D1-D3.** Pull identity, scenarios, and interfaces. Log clarifications to D6 as they arise.
4. **Analyze D4.** Walk every boundary in D3. Flag shared gaps.
5. **Scope D5.** Define what's permanently out, what's deferred, what belongs elsewhere.
6. **Resolve D6.** Review all clarifications. Resolve or accept assumptions. Gate: zero OPEN items.
7. **Write D7.** Author holdout scenarios from D2+D3. Store separately.
8. **Decompose into handoffs.** D4 shared gaps to H-0. D2 scenarios to H-1 through H-N.

Time estimate for extraction: 2-4 hours per component (with design docs already written).

---

## D-Template System (Extended)

The seven core deliverables expand into a 10-document system (D1-D10) for full agent-executable specs. The additional documents provide the architecture plan, task decomposition, and builder context needed for autonomous agent builds.

| D-Template | Core Deliverable | Purpose |
|------------|-----------------|---------|
| D1: Constitution | Component Identity | Immutable rules + identity |
| D2: Specification | User Stories | GIVEN/WHEN/THEN scenarios |
| D3: Data Model | Interface Definitions | Entity schemas + relationships |
| D4: Contracts | Dependency Surface | Inbound/outbound/side-effect/error contracts |
| D5: Research | (expanded) | Design decisions + prior art review |
| D6: Gap Analysis | Forced Clarifications | Boundary analysis + clarification log |
| D7: Plan | (expanded) | Architecture + file structure + testing strategy |
| D8: Tasks | (new) | Work decomposition + dependencies + phases |
| D9: Holdout Scenarios | Holdout Scenarios | Acceptance tests (hidden from builders) |
| D10: Agent Context | (new) | Builder handbook (commands, conventions, patterns) |

Supporting standards:
- **BUILDER_HANDOFF_STANDARD.md** — Format for generated handoff documents
- **BUILDER_PROMPT_CONTRACT.md** — Agent prompt template with verification gate
- **AGENT_BUILD_PROCESS.yaml** — Machine-readable workflow definition
