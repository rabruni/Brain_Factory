# Sawmill Analysis — A Temporary Dark Factory

**Status**: WORKING DRAFT
**Date**: 2026-02-25
**Purpose**: Design a product-agnostic build process ("the sawmill") that takes design documents and produces built, tested, verified code through Claude Code and Codex CLI agents operating on a shared repository.

**Scope boundary**: This document defines THE FACTORY — the turns, the templates, the agent roles, the quality gates. It does NOT define what gets built. Products, primitives, schemas, and build order are inputs to the sawmill, not part of it.

---

## Part 1: What the Industry Is Doing

### 1.1 The Dark Factory Maturity Levels

| Level | Description | Human Role |
|-------|-------------|------------|
| **L1** | AI completes code fragments | Developer does everything else |
| **L2** | AI generates functions/files, humans review all changes | Review bottleneck (2-8 hrs) |
| **L3** | AI generates from specs, holdout scenarios gate quality, humans approve final merge | Spec author + merge approver |
| **L3.5** | L3 with selective auto-merge on stable components | Same, reduced merge friction |
| **L4** | Full dark factory — specs in, tested merged code out | Spec author only |

**The sawmill is an L3 factory.** Human provides design docs and approves gates. Agents spec, build, and evaluate. Holdouts gate quality. Human approves merges.

### 1.2 The Three Pillars (Industry Consensus)

**Pillar 1: Spec-Driven Development.** Specs are source of truth; code is derived. Every ambiguity in the spec is a degree of freedom for the agent. Degrees of freedom produce hallucination.

**Pillar 2: Holdout Scenario Separation.** Coding agents MUST NOT see acceptance tests. A separate evaluator with cleared context judges code against scenarios the builder never saw. Each scenario runs 3 times; 2/3 must pass; 90% overall gate.

**Pillar 3: Isolation Between Generation and Validation.** The code generation layer and the validation layer must be completely isolated. Separate agent contexts, no shared state between builder and evaluator.

### 1.3 Multi-Agent Coordination (What Works, What Fails)

**What fails:** Equal-status agents with locking (20 agents degraded to 2-3 throughput). Optimistic concurrency (agents became risk-averse). Unsupervised autonomy without holdout gates. "Vibe coding" at scale (72% of developers reject it — UC San Diego/Cornell, Dec 2025).

**What works:** Hierarchical role-based architecture (Planner → Worker → Judge). Git worktrees for isolation. Writer/Reviewer separation (prevents confirmation bias). Plan/Execute model stratification (powerful models plan, faster models execute).

**Hard limits:** Files >500KB often excluded from indexing. Multi-file refactors achieve only 42% capability in enterprise. Context compaction in long sessions loses architectural decisions.

### 1.4 Claude Code + Codex CLI Specific Patterns

**Claude Code:** Deep reasoning, subagent orchestration, persistent specialist agents via `.claude/agents/`, Agent Teams for multi-session work.

**Codex CLI:** Background/async execution, phone-accessible (Codex Cloud), strong at well-scoped implementation, headless workers.

**Same-repo best practices:** Git worktrees for isolation. CLAUDE.md as institutional context ("quality difference obvious within 24 hours"). Limit 3-4 specialist agents. Opus for planning, Sonnet for execution. Persistent agents in `.claude/agents/`.

---

## Part 2: The D1-D10 Template System

### 2.1 Keep the Full System

The D1-D10 templates are kept as 10 separate documents. The apparent "duplication" across documents is not duplication — it is **multi-point verification through controlled redundancy**. Each document restates certain key information in its own context and at its own altitude. When those restatements are consistent, the specification is coherent. When they diverge, drift has been caught before it reaches code.

This is the same pattern as double-entry bookkeeping, redundant safety systems in engineering, and (notably) DoPeJar's own Ledger/Graph architecture — one is source of truth, the other is a derived view, and discrepancies surface errors.

### 2.2 The Controlled Redundancy Map

Each row below shows information that appears in multiple D-documents and WHY.

| Information | Where It Appears | Verification Purpose |
|-------------|-----------------|---------------------|
| **Component boundaries** | D1 NEVER list, D2 "What it is NOT", D6 boundary analysis | D1 states the rule (constitutional). D2 states the scope (behavioral). D6 verifies the boundary was walked (analytical). Divergence = drift between principle, scope, and analysis. |
| **Testing approach** | D2 per-scenario testing, D7 testing strategy, D8 acceptance criteria | D2 says HOW to verify (caller's view). D7 says HOW architecture supports it (mocking, integration). D8 says WHAT tests must pass (task-level). Divergence = testing conflation across altitudes. |
| **Tooling rules** | D1 Tooling Constraints (USE/NOT), D10 Tool Rules (USE/NOT/WHY) | D1 is the constitutional rule. D10 is the builder's executable guide. D10 must faithfully translate D1. Divergence = builder will use forbidden tools. |
| **Component purpose** | D2 Component Purpose, D7 Summary, D10 "What This Project Does" | Written at three stages (extraction, planning, builder briefing). Divergence = the component means different things to spec writer, planner, and builder. |
| **Error handling** | D4 Error Contracts, D6 Error Propagation | D4 defines the contract. D6 verifies boundary coverage. D6 is a gap check ON D4. Divergence = unwalked error boundary. |
| **Architecture** | D7 Architecture Overview, D10 Architecture Overview | D7 is the full plan. D10 is the builder's condensed view. Divergence = builder has incomplete picture. |

### 2.3 Within-Turn Deduplication

One genuine redundancy to clean up: **D2 "Clarification Markers"** and **D6 "Clarification Log"** capture the same items. D2 markers should be pointers (`See D6 CLR-001`), not full entries. The authoritative clarification lives in D6 only.

### 2.4 What to Add to the Template System

| Gap | Why It Matters | Solution |
|-----|---------------|---------|
| **No CLAUDE.md** | Every agent session starts cold | CLAUDE.md at repo root with institutional context, Lexicon of Precision, routing rules |
| **No specialist agent definitions** | Ad-hoc agent invocations guess at roles | `.claude/agents/` with defined roles |
| **No isolation strategy** | Two agents on same files = merge conflicts | Git worktrees: one per active handoff |
| **No holdout isolation mechanism** | D9 says "stored separately" but not HOW | `.holdouts/` directory excluded from builder context |
| **No retry protocol** | Single-attempt system | Max 3 retries, error context appended |
| **No session boundary protocol** | Context compaction loses decisions | "Land the plane" pattern at session end |

---

## Part 3: Turns

### 3.1 What Is a Turn

A **turn** is one complete agent session focused on one phase of the sawmill pipeline. Each turn has:

- **Role**: Which agent performs this turn
- **Inputs**: What the agent reads (and ONLY what it reads)
- **Outputs**: What documents are produced
- **Gates**: What must be true before the next turn can start
- **Human role**: What the human does during this turn
- **Self-checks**: How the controlled redundancy is used within this turn

Turns are sequential. A turn's gate must pass before the next turn begins. Within a turn, the agent works interactively with the human — surfacing gaps, asking questions, refusing to proceed past gates until issues are resolved.

### 3.2 Turn A — Specification (D1 through D6)

**Role**: Spec Agent (Claude Code, Opus)
**Inputs**: Design documents (architecture docs, prior specs, standards)
**Outputs**: D1, D2, D3, D4, D5, D6 — all filled, per component
**Gate**: D6 has zero OPEN items
**Human role**: Answer questions when agent encounters gaps. Approve D6 gate.

**How the agent works:**

The spec agent reads the design documents and extracts into D1 through D6 in order. It does not invent — it extracts what's there and surfaces what isn't. When it encounters something the design docs don't answer, it MUST stop and ask the human. It does not guess, assume, or paper over gaps.

The agent is compelled to reduce risk and manage scope proactively. This means:

- When a boundary is unclear, the agent flags it in D6 rather than choosing an interpretation
- When scope could expand, the agent adds to D1 NEVER and D2 "What it is NOT" rather than accommodating
- When a design decision has multiple valid options, the agent logs it in D5 Research with options table and asks the human to decide
- When a D4 error contract doesn't cover a D6 boundary, the agent flags the gap rather than inventing coverage

**Self-checks during this turn** (using controlled redundancy):

| After writing... | Check against... | If they diverge... |
|-----------------|-----------------|-------------------|
| D2 "What it is NOT" | D1 NEVER boundaries | Scope definition drifted from constitutional rules. Reconcile before proceeding. |
| D4 Error Contracts | D2 edge case scenarios | An error path in D2 has no contract in D4, or a contract exists for an undocumented scenario. Flag in D6. |
| D6 boundary analysis | D4 contracts | A boundary was walked that has no contract, or a contract exists for an unwalked boundary. Reconcile. |

**D-documents produced in this turn, in order:**

| Order | Document | What the agent does | Key constraint |
|-------|----------|-------------------|----------------|
| 1 | **D1 Constitution** | Extract immutable rules from design docs. Define ALWAYS/ASK/NEVER boundaries. Tooling constraints. | Every article needs Rule, Why, Test, Violations. At least 5 articles. |
| 2 | **D2 Specification** | Extract GIVEN/WHEN/THEN scenarios. Define negative boundaries. Flag clarifications as `See D6 CLR-NNN`. | 3-7 primary scenarios, 2-4 edge cases. Every scenario traceable to a design doc. |
| 3 | **D3 Data Model** | Extract entity schemas. Field tables with types, required flags, constraints. Entity relationship map. | Every field has type + required/optional. Every entity has at least one example. Invariants for each. |
| 4 | **D4 Contracts** | Define inbound, outbound, side-effect, and error contracts. Concrete examples for each. | Every contract traces to D2 scenarios. Error codes with retryable flag. |
| 5 | **D5 Research** | Document design decisions. Options considered with pros/cons. Prior art review. | Every Blocking question resolved before D6. Each decision has rationale. |
| 6 | **D6 Gap Analysis** | Walk every boundary (all 9 categories). Log all clarifications from D1-D5. | **GATE: Zero OPEN items. Every gap RESOLVED or ASSUMED with justification. Human approves.** |

### 3.3 Turn B — Build Planning (D7, D8, D10)

**Role**: Plan Agent (Claude Code, Opus — can be same session as Turn A if context allows)
**Inputs**: D1 through D6 from Turn A
**Outputs**: D7, D8, D10
**Gate**: D7 Constitution Check passes all D1 articles. D8 tasks trace to D2 scenarios and D4 contracts. D10 tooling rules match D1 tooling constraints.
**Human role**: Review architecture approach. Approve plan.

**How the agent works:**

The plan agent translates the spec (what to build) into a build plan (how to build it). It produces architecture, task decomposition, and builder context. The controlled redundancy between Turn A and Turn B outputs is intentional — it forces the plan to be verified against the spec.

**Self-checks during this turn:**

| After writing... | Check against... | If they diverge... |
|-----------------|-----------------|-------------------|
| D7 Summary | D2 Component Purpose | Component description drifted during planning. Reconcile. |
| D7 Constitution Check | D1 articles (every one) | Architecture violates a constitutional rule. Fix architecture or escalate to human. |
| D7 Testing Strategy | D2 per-scenario Testing Approach | Planning changed how something gets tested without updating the scenario. Flag. |
| D8 task acceptance criteria | D2 scenarios + D4 contracts | A task doesn't trace to a scenario, or a scenario has no task. Gap in decomposition. |
| D10 Tool Rules | D1 Tooling Constraints | Builder guidance diverges from constitution. Reconcile. |
| D10 Architecture Overview | D7 Architecture Overview | Builder's condensed view lost critical detail. Fix D10. |

**D-documents produced in this turn, in order:**

| Order | Document | What the agent does | Key constraint |
|-------|----------|-------------------|----------------|
| 1 | **D7 Plan** | Architecture overview, component responsibilities (mapping to D2 scenarios), file structure, testing strategy, complexity tracking. Constitution Check table verifying every D1 article. | Every component maps to D2 scenarios. Constitution Check covers all articles. |
| 2 | **D8 Tasks** | Phased task decomposition. Each task has: phase, dependencies, scope, D2 scenarios satisfied, D4 contracts implemented, acceptance criteria with test counts. Dependency graph. | Every D2 P1 scenario has at least one task. Every D4 contract has at least one task. Minimum test counts enforced. |
| 3 | **D10 Agent Context** | Builder handbook: project description, architecture overview (condensed from D7), key patterns (from D1+D5), commands (copy-pasteable), tool rules (from D1), coding conventions, submission protocol, active components table. | Must be self-contained enough that a builder reads D10 FIRST and can orient before reading the handoff. |

### 3.4 Turn C — Holdout Authoring (D9)

**Role**: Holdout Agent (Claude Code, Opus — **different agent session, cleared context**)
**Inputs**: D2 Specification + D4 Contracts ONLY. No other D-documents. No design docs. No builder handoff.
**Outputs**: D9 Holdout Scenarios
**Gate**: Coverage matrix covers all P0 and P1 scenarios from D2. At least 3 scenarios. Human reviews for strength.
**Human role**: Review holdouts. Verify they test behavior, not implementation. Store in `.holdouts/`.

**How the agent works:**

The holdout agent sees ONLY what the component should do (D2 scenarios) and what shape its interfaces take (D4 contracts). It does NOT know how the component will be built (D7), what tasks exist (D8), or what tools will be used (D10). This isolation is critical — holdouts test behavioral expectations, not architectural decisions.

The agent writes 3-5 executable acceptance scenarios. Each has setup, execute, verify (with bash commands and exit codes), and cleanup. The verify steps must be concrete enough that a different agent can run them mechanically.

**Why D2+D4 only:**

If the holdout agent saw D7 (architecture), it might write scenarios that test file structure rather than behavior. If it saw D8 (tasks), it might write scenarios that map 1:1 to tasks rather than testing cross-cutting behavior. If it saw D10 (agent context), it might write scenarios using the same tools the builder will use, reducing independence. D2+D4 keeps holdouts at the behavioral altitude — what callers observe, not what builders implement.

### 3.5 Turn D — Build (Handoff + 13Q + DTT)

**Role**: Builder Agent (Claude Code or Codex CLI, Sonnet)
**Inputs**: D10 (read first), Builder Handoff (generated from D7+D8), referenced code per handoff Section 7
**Outputs**: Built code, test suite, Results file
**Gate**: All tests pass. Results file complete with SHA256 hashes. PR opened.
**Human role**: Review 13Q answers. Greenlight build. Monitor progress.

**How the builder works:**

**Step 1: Orient.** Read D10 Agent Context first. This gives the builder the project's big picture, commands, conventions, and tool rules before it sees any specific task.

**Step 2: Read handoff.** Read the Builder Handoff for this specific task. The handoff follows BUILDER_HANDOFF_STANDARD.md format: Mission, Critical Constraints, Architecture/Design, Implementation Steps, Package Plan, Test Plan, Existing Code to Reference, E2E Verification, Files Summary, Design Principles.

**Step 3: 13Q Gate.** Answer all 13 questions (10 verification + 3 adversarial). **STOP. Do not write any code, create any directories, or make any plans.** Wait for human review and explicit greenlight.

The 13Q gate structure:

| Questions | Category | What they verify |
|-----------|----------|-----------------|
| 1-3 | Scope | What am I building? What am I NOT building? What are the boundaries from D1? |
| 4-6 | Technical | What APIs, file locations, data formats from D3/D4? |
| 7-8 | Packaging | What manifests, hashes, dependencies? |
| 9 | Testing | How many tests? What verification criteria from D8? |
| 10 | Integration | How does this connect to existing components? |
| 11-13 | Adversarial | Selected per system maturity (see below) |

*Genesis adversarial set* (use when infrastructure doesn't exist yet):
- 11 — The Dependency Trap: "What does your deliverable depend on that doesn't exist yet? How do you handle that absence without inventing infrastructure?"
- 12 — The Scope Creep Check: "What is the closest thing to 'building infrastructure' in your plan, and why is it actually in scope?"
- 13 — The Semantic Audit: "Identify one word in your current plan that is ambiguous and redefine it precisely."

*Infrastructure adversarial set* (use when governance pipeline is operational):
- 11 — The Failure Mode: "Which specific file/hash in your scope is the most likely culprit if a gate check fails?"
- 12 — The Shortcut Check: "Is there an established tool you are tempted to skip in favor of a manual approach? If yes, explain why you will NOT do that."
- 13 — The Semantic Audit: "Identify one word in your current plan that is ambiguous and redefine it precisely."

**Step 4: DTT — Design, Test, Then implement.**

DTT is a per-behavior TDD cycle. It is NOT "design everything, test everything, then implement everything." It is a tight loop repeated for each behavior:

```
For each behavior in the handoff's Test Plan:

  1. DESIGN: Read the behavior description and acceptance criteria.
     Decide: what function/method, what signature, what it returns,
     what errors it raises. Write this down as a comment or docstring.
     Do NOT write implementation code yet.

  2. TEST: Write a test (or tests) for this one behavior.
     The test MUST call the function/method.
     The test MUST assert the expected outcome.
     Run the test. It MUST FAIL (red). If it passes, the test
     is not testing anything — rewrite it.

  3. IMPLEMENT: Write the MINIMUM code to make the failing test pass.
     Not elegant. Not complete. Just enough to go green.
     Run the test. It MUST PASS (green).

  4. REFACTOR: Clean up the code. Tests stay green.
     Run all tests for this component after every change.

  Move to the next behavior. Repeat.
```

**After all behaviors are built:**

5. Run the FULL test suite (all components, not just this one).
6. Write the Results file per BUILDER_HANDOFF_STANDARD.md template.
7. Open a PR.

**Step 5: Results file.** Contains: Status (PASS/FAIL/PARTIAL), Files created/modified with SHA256 hashes, test results (this package), full regression results (all packages), issues encountered, session log (decisions made, context for next session).

### 3.6 Turn E — Evaluation (D9 Executed)

**Role**: Evaluator Agent (Claude Code, Opus — **different agent session, cleared context**)
**Inputs**: D9 Holdout Scenarios (from `.holdouts/`) + built code (from PR branch). **Nothing else.** No handoff, no spec, no builder reasoning, no results file.
**Outputs**: Evaluation report
**Gate**: 2/3 pass per scenario. 90% overall. Human reviews report.
**Human role**: Review evaluation report. Merge PR or send back to builder.

**How the evaluator works:**

The evaluator checks out the PR branch in a clean worktree. It reads the holdout scenarios from `.holdouts/`. For each scenario, it runs the setup, execute, and verify steps exactly as written. It runs each scenario 3 times. A scenario passes if 2 of 3 runs pass. The overall build passes if 90% of scenarios pass.

**On failure:** The evaluator produces a one-line failure message per failed scenario. This message describes WHAT failed (which check, actual vs. expected), not WHY or HOW to fix it. The one-line message is appended to the builder's error context for retry. The builder gets up to 3 total attempts.

**After 3 failures:** The handoff returns to the spec author. Three build failures on the same handoff indicates the spec has a gap — either the spec is underspecified (builder can't figure out what to build), or the holdouts are testing something the spec doesn't describe.

### 3.7 Turn Summary

```
TURN A: SPECIFICATION                    TURN C: HOLDOUT AUTHORING
─────────────────────                    ─────────────────────────
Role:  Spec Agent (Opus)                 Role:  Holdout Agent (Opus, cleared)
Input: Design docs                       Input: D2 + D4 ONLY
Output: D1, D2, D3, D4, D5, D6          Output: D9
Gate:  D6 zero OPEN items               Gate:  Coverage matrix complete
Human: Answers gaps, approves D6         Human: Reviews holdout strength
                │                                       │
                ▼                                       │
TURN B: BUILD PLANNING                                  │
──────────────────────                                  │
Role:  Plan Agent (Opus)                                │
Input: D1-D6                                            │
Output: D7, D8, D10                                     │
Gate:  Constitution check passes                        │
Human: Reviews plan, approves                           │
                │                                       │
                ▼                                       │
TURN D: BUILD                                           │
─────────                                               │
Role:  Builder Agent (Sonnet)                           │
Input: D10 + Handoff + ref code                         │
Process: 13Q → approval → DTT → results → PR            │
Gate:  All tests pass, results complete                 │
Human: Reviews 13Q, greenlights                         │
                │                                       │
                ▼                                       ▼
TURN E: EVALUATION
──────────────────
Role:  Evaluator Agent (Opus, cleared)
Input: D9 + PR branch code ONLY
Process: Run scenarios 3x each
Gate:  2/3 per scenario, 90% overall
Human: Reviews report, merges or sends back
                │
                ▼
        MERGE or RETRY (max 3)
```

**Turn A and Turn C can run in parallel** — they have no dependencies on each other. Turn C needs only D2+D4, which are produced in Turn A, so Turn C can start as soon as D2 and D4 are complete (before D5-D6 finish). However, holdouts should be reviewed by the human after D6 gate passes, to ensure the spec the holdouts are testing is the final spec.

**Turns A and B can potentially be one session** — if context window allows, the same agent session that wrote D1-D6 can continue into D7-D8-D10. The cross-document verification between turns A and B (D7 Constitution Check vs D1, D8 task tracing vs D2+D4, D10 tools vs D1) serves as a drift check even within one session.

---

## Part 4: Operating Principles

These are product-agnostic. They govern how the sawmill processes ANY spec.

1. **Specs are source of truth, code is derived.** If the spec is complete, the build is deterministic. If the build fails, the failure traces to a spec gap.

2. **Every ambiguity is a degree of freedom.** Degrees of freedom produce hallucination. Specs must eliminate them before they reach a builder.

3. **Generation and validation are isolated.** The builder never sees holdout scenarios. The evaluator has cleared context. No shared state.

4. **Agents assemble, they do not architect.** If a builder agent needs to make a design decision, the spec failed — not the agent.

5. **Start from spec, ask if there's a gap.** The spec agent extracts what's in the design docs and surfaces what isn't. It does not invent. It asks.

6. **Reduce risk, manage scope.** The spec agent is biased toward narrowing scope (add to NEVER, add to "What it is NOT") and surfacing risk (add to D6), not toward accommodating ambiguity.

7. **Controlled redundancy is verification.** Information restated across documents at different altitudes is not duplication — it is a coherence check. Divergence = drift detected.

8. **Block rather than guess.** When in doubt, stop and ask. Determinism over cleverness.

9. **Three retries, then human.** After 3 build failures, the handoff returns to the spec author. The spec has a gap.

10. **Land the plane.** Every agent session ends with a written summary and next-session prompt. No orphaned context.

11. **Trust is earned.** No auto-merge until 20+ handoffs show holdout gate and human judgment agree consistently.

---

## Part 5: Agent Roles and Isolation

| Role | Turn | Tool | Model | What It Reads | What It NEVER Reads | Isolation |
|------|------|------|-------|--------------|-------------------|-----------|
| **Spec Agent** | A | Claude Code | Opus | Design docs, prior specs | `.holdouts/`, builder results | Main worktree |
| **Plan Agent** | B | Claude Code | Opus | D1-D6 | `.holdouts/`, builder results | Main worktree (can be same session as Turn A) |
| **Holdout Agent** | C | Claude Code (fresh) | Opus | D2 + D4 ONLY | D1, D3, D5, D6, D7, D8, D10, design docs, builder results | Cleared context |
| **Builder** | D | Claude Code or Codex CLI | Sonnet | D10 + handoff + referenced code | `.holdouts/`, D9, evaluator reports | Dedicated git worktree |
| **Evaluator** | E | Claude Code (fresh) | Opus | D9 + PR branch code | Handoff, D1-D8, D10, builder reasoning, results file | Separate worktree, cleared context |

**Critical isolation rules:**

- Builder NEVER sees `.holdouts/` or D9.
- Evaluator NEVER sees the builder's handoff, spec, reasoning, or results file.
- Holdout Agent NEVER sees D1, D3, D5, D6, D7, D8, D10, or design docs.
- Reviewer and Builder are ALWAYS different agent sessions.
- "Cleared context" means a fresh agent session with no memory of prior turns.

---

## Part 6: Repository Structure

This is what the sawmill adds to ANY repo.

```
[repo]/
├── CLAUDE.md                          ← Institutional context for all agents
├── .claude/
│   └── agents/                        ← Persistent specialist agent definitions
│       ├── spec-agent.md              ← Turn A+B behavior
│       ├── holdout-agent.md           ← Turn C behavior
│       ├── builder.md                 ← Turn D behavior
│       └── evaluator.md              ← Turn E behavior
│
├── sawmill/
│   ├── PROCESS.md                     ← The turn workflow, formalized
│   └── templates/                     ← The D1-D10 templates (full, not compressed)
│       ├── D1_CONSTITUTION.md
│       ├── D2_SPECIFICATION.md
│       ├── D3_DATA_MODEL.md
│       ├── D4_CONTRACTS.md
│       ├── D5_RESEARCH.md
│       ├── D6_GAP_ANALYSIS.md
│       ├── D7_PLAN.md
│       ├── D8_TASKS.md
│       ├── D9_HOLDOUT_SCENARIOS.md
│       ├── D10_AGENT_CONTEXT.md
│       ├── BUILDER_HANDOFF_STANDARD.md
│       ├── BUILDER_PROMPT_CONTRACT.md
│       └── RESULTS.md
│
├── .holdouts/                         ← Holdout scenarios (isolated from builders)
│   └── [component].scenarios.md
│
└── _staging/                          ← Build work area
```

Product-specific directories (specs per component, source, architecture docs) live wherever the product defines. The sawmill dictates process structure, not product structure.

---

## Part 7: Sawmill Design Decisions

### 7.1 Confirmed by Research

| Decision | Evidence |
|----------|----------|
| Git worktrees for agent isolation | Industry consensus across all sources |
| Holdout scenarios physically separated from builder context | #1 recommendation from every dark factory implementation |
| 13Q gate before building | Aligns with "Explore → Plan → Code" pattern |
| DTT (test-first) per-behavior cycles | Industry consensus; prevents tests matching buggy code |
| Spec quality as primary bottleneck | Universal finding across all implementations |
| CLAUDE.md as institutional context | Unanimous recommendation |
| D2+D4 only for holdout agent | Cleaner independence test; behavior, not architecture |
| Spec agent starts from design docs, asks on gaps | Extraction over invention |

### 7.2 Decisions Needing Input

| Decision | Options | Lean | Reasoning |
|----------|---------|------|-----------|
| **Holdout isolation** | (A) `.holdouts/` dir excluded from builder context, (B) separate branch, (C) encrypted | A | Simplest; `.gitignore` + CLAUDE.md rules enforce |
| **Agent routing** | (A) Claude Code only, (B) Codex CLI only, (C) Claude Code orchestrates, Codex CLI for parallel builds | C | Claude Code for reasoning; Codex CLI for well-scoped parallel work |
| **Worktree strategy** | (A) One worktree per active handoff, (B) Separate checkouts, (C) Sequential | A | Lighter than checkouts; branch-per-handoff gives clean PR flow |
| **Session continuity** | (A) "Land the plane" summaries, (B) JSONL state files, (C) Git commits | A + C | Summaries + frequent commits = recoverable |

---

## Part 8: Risks (Sawmill-Specific)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Spec quality insufficient** | HIGH | HIGH | D6 gap gate. After first 5 handoffs, trace deviations to spec gaps. |
| **Holdout scenarios too weak** | MEDIUM | HIGH | Review holdout quality after first 5 handoffs. Must test behavior, not implementation. |
| **Context compaction loses decisions** | HIGH | MEDIUM | "Land the plane" protocol. Frequent commits. Session logs in Results file. |
| **Builder/evaluator isolation breaks** | LOW | HIGH | CLAUDE.md rules + fresh sessions. Verify in first 3 runs. |
| **Token costs escalate** | MEDIUM | MEDIUM | Budget per handoff. Hard cap: 3 retries. |
| **Controlled redundancy catches nothing** | LOW | MEDIUM | If cross-document checks never diverge, either specs are perfect or checks aren't being done. Audit after 10 handoffs. |

---

## Part 9: What to Build (The Sawmill Itself)

The sawmill needs these artifacts before it can process any spec:

1. **CLAUDE.md** — Institutional context. Lexicon of Precision. Agent routing rules. Highest ROI single action.
2. **D1-D10 templates** — Move existing templates from `Templates/` to `sawmill/templates/`. Add minor fixes (D2 clarification markers become pointers to D6).
3. **Supporting standards** — Move BUILDER_HANDOFF_STANDARD.md, BUILDER_PROMPT_CONTRACT.md, RESULTS template to `sawmill/templates/`.
4. **`.claude/agents/`** — Define 4 specialist agents: spec-agent, holdout-agent, builder, evaluator. Each definition specifies the agent's turn, inputs, outputs, gates, and isolation rules.
5. **`.holdouts/` directory** — Set up with isolation rules (excluded from builder context via CLAUDE.md and `.gitignore`).
6. **PROCESS.md** — The turn workflow from Part 3, formalized as the canonical reference for all agents.

Six deliverables. Then the sawmill is operational and can accept its first design document.

---

## Sources

- [HackerNoon: The Dark Factory Pattern](https://hackernoon.com/the-dark-factory-pattern-moving-from-ai-assisted-to-fully-autonomous-coding)
- [Thoughtworks: Spec-Driven Development](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices)
- [Simon Willison: Parallel Coding Agents](https://simonwillison.net/2025/Oct/5/parallel-coding-agents/)
- [Simon Willison: StrongDM Software Factory](https://simonwillison.net/2026/Feb/7/software-factory/)
- [Mike Mason: AI Coding Agents Jan 2026](https://mikemason.ca/writing/ai-coding-agents-jan-2026/)
- [Addy Osmani: Future of Agentic Coding](https://addyosmani.com/blog/future-agentic-coding/)
- [GitHub Blog: Spec Kit](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)
- [VS Code Multi-Agent Development (Feb 2026)](https://code.visualstudio.com/blogs/2026/02/05/multi-agent-development)
- [GitHub Agent HQ (Feb 2026)](https://github.blog/news-insights/company-news/pick-your-agent-use-claude-and-codex-on-agent-hq/)
- [Claude Code Subagent Best Practices](https://claudefa.st/blog/guide/agents/sub-agent-best-practices)
- [Claude Code Agent Teams Guide](https://claudefa.st/blog/guide/agents/agent-teams)
