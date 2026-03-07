# Superpowers vs Sawmill — Gap Analysis

**Date**: 2026-03-06
**Purpose**: Compare [obra/superpowers](https://github.com/obra/superpowers) skills against the Sawmill pipeline and DoPeJarMo architecture to identify design completeness gaps.
**Method**: Full text comparison of all 14 superpowers SKILL.md files against sawmill turns, architecture docs, agent constraints, templates, and FMWK-001 outputs.

---

## Summary

Sawmill is stronger on **governance, isolation, and specification rigor**. Superpowers is stronger on **runtime discipline during building** — what happens when an agent is actually writing code, debugging, and verifying. The critical gaps are all in Turn D (Builder), where sawmill defines WHAT to build but not HOW to build well.

| Area | Sawmill | Superpowers | Verdict |
|------|---------|-------------|---------|
| Spec authoring | Turn A: D1-D6 formal docs | brainstorming: interactive Q&A | Sawmill stronger (architecture-driven) |
| Planning | Turn B: D7/D8/D10 with constitution check | writing-plans: bite-sized 2-5 min tasks | **GAP**: Sawmill tasks lack granularity |
| Builder isolation | Holdout separation (Turn C/E) | None | Sawmill stronger |
| TDD discipline | DTT mentioned in constraints | Iron law + delete-before-test + rationalizations | **GAP**: Sawmill lacks enforcement depth |
| Debugging | None | 4-phase systematic process | **CRITICAL GAP** |
| Verification | 13Q gate (pre-build) | Evidence-before-claims (during build) | **CRITICAL GAP** |
| Per-task review | None during Turn D | Two-stage review per task | **GAP** |
| Self-reflection | None | Implementer reviews own work before handoff | **GAP** |
| Code review reception | None | Technical evaluation protocol | **GAP** |
| Parallel agents | Turn B/C parallel | Domain-scoped dispatch pattern | Equivalent |
| Branch management | Staging directories | Git worktrees | Different by design (both valid) |
| Skill activation | COLD_START.md + AGENT_BOOTSTRAP.md | using-superpowers meta-skill | Equivalent |

---

## Per-Skill Comparison

### 1. brainstorming

**Superpowers says**: Before any creative work, explore user intent through one-question-at-a-time dialogue. Propose 2-3 approaches. Present design in digestible sections. Get approval. Save design doc. HARD GATE: no code until design approved.

**Sawmill equivalent**: Turn A (Spec Agent) produces D1-D6 from architecture authority docs. D6 gate requires zero OPEN items. Builder reads D10 + Handoff.

**Does sawmill cover this?** Yes, and more rigorously. Turn A doesn't discover requirements through conversation — it extracts them from authority documents (NORTH_STAR, BUILDER_SPEC, OPERATIONAL_SPEC). This is correct for DoPeJarMo because requirements are architecture-driven, not user-discovered.

**Does superpowers do something sawmill doesn't?** The interactive refinement flow is useful for ad-hoc work outside the sawmill (e.g., quick fixes, tooling, scripts). Sawmill doesn't cover how agents should handle unplanned work.

**Recommendation**: No change to sawmill. The brainstorming skill fills a different niche (ad-hoc feature discovery) that sawmill intentionally doesn't address.

---

### 2. writing-plans

**Superpowers says**: Break work into 2-5 minute bite-sized tasks. Each task has exact file paths, complete code, exact verification commands with expected output. Every step is one action: write test → run test → implement → run test → commit.

**Sawmill equivalent**: Turn B produces D7 (architecture), D8 (task list), D10 (agent context). D8 maps tasks to D2 scenarios and D4 contracts. BUILDER_HANDOFF.md provides implementation steps.

**Does sawmill cover this?** Partially. The BUILDER_HANDOFF for FMWK-001 (Section 4) has 18 numbered implementation steps, each with exact file paths, WHY explanations, and test counts. But the granularity is coarser — "Implement Ledger.append()" is a single step, not broken into "write failing test → verify it fails → write code → verify it passes → commit."

**Does superpowers do something sawmill doesn't?**
- **Task granularity**: Superpowers' 2-5 minute task atoms are smaller than sawmill's steps.
- **Complete code in plan**: Superpowers includes the actual code to write. Sawmill's handoff includes data flow diagrams and interface contracts but leaves code to the builder.
- **Explicit commit points**: Superpowers says commit after every green. Sawmill says "frequent commits" but doesn't specify when.

**Recommendation**: **ABSORB** the commit-after-every-green discipline into the BUILDER_HANDOFF_STANDARD template. The granularity difference is deliberate — sawmill builders are working from formal specs, not needing code dictated to them. But explicit commit points would help.

---

### 3. test-driven-development

**Superpowers says**: Iron Law: NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST. Wrote code before the test? Delete it. Start over. No exceptions. Verify RED (watch it fail). Verify GREEN (watch it pass). REFACTOR only after green. Extensive anti-rationalization table. Delete means delete — don't keep as "reference."

**Sawmill equivalent**: AGENT_CONSTRAINTS.md says "MUST follow DTT (Design-Test-Then-implement) per behavior." BUILDER_HANDOFF Section 2 says "DTT per behavior. For every acceptance criterion in D8: write the failing test first, implement the behavior, confirm the test passes."

**Does sawmill cover this?** The RULE exists but lacks ENFORCEMENT DEPTH. Sawmill says "write the failing test first" but doesn't say:
- Delete code written before tests (the iron law)
- Must WATCH the test fail (verify RED step)
- Common rationalizations agents use to skip TDD
- What to do when stuck (hard to test = hard to use)
- Anti-patterns (testing mocks instead of real code)

**Quoted gap**: Sawmill's entire TDD guidance is one sentence in AGENT_CONSTRAINTS: *"MUST follow DTT (Design-Test-Then-implement) per behavior."* Superpowers dedicates 370 lines to enforcement including rationalization prevention, red flags, and stuck protocols.

**Recommendation**: **CRITICAL — ABSORB**. Add a `TDD_DISCIPLINE.md` to `Templates/` that Turn D builders must read. Include:
1. The iron law (delete code written before tests)
2. Verify RED before implementing
3. The rationalizations table (agents will try every one)
4. Anti-patterns reference (mock-interface drift from superpowers' feedback doc)

---

### 4. systematic-debugging

**Superpowers says**: 4-phase process: (1) Root Cause Investigation — read errors, reproduce, check changes, trace data flow; (2) Pattern Analysis — find working examples, compare; (3) Hypothesis and Testing — form single hypothesis, test minimally, one variable at a time; (4) Implementation — create failing test, single fix, verify. Iron Law: NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST. If 3+ fixes fail, question the architecture.

**Sawmill equivalent**: **None.** Zero debugging guidance anywhere in sawmill, architecture docs, or agent constraints.

**Does sawmill cover this?** No. The sawmill pipeline assumes builders follow DTT and succeed. There is no protocol for what happens when:
- Tests fail unexpectedly during Turn D
- Integration tests hit environmental issues
- The builder encounters a bug in the existing platform_sdk
- The builder's 3rd attempt fails (AGENT_CONSTRAINTS says "max 3 attempts" but doesn't say how to debug between attempts)

**Quoted gap**: AGENT_CONSTRAINTS.md line 120: *"Gets maximum 3 attempts. After 3 failures, handoff returns to spec author."* But there is no guidance on how the builder should use those 3 attempts effectively. Without a debugging protocol, each attempt is likely to be "try something different" rather than systematic root cause analysis.

**Recommendation**: **CRITICAL — ABSORB**. Add `DEBUGGING_PROTOCOL.md` to `Templates/` as a Turn D reference. Include:
1. The 4-phase process (root cause → pattern → hypothesis → fix)
2. The iron law (no fixes without investigation)
3. The 3-fix architectural question (directly ties to sawmill's 3-attempt limit)
4. Multi-component evidence gathering (relevant for Docker + immudb + platform_sdk stack)
5. Supporting techniques: root-cause-tracing, condition-based-waiting

---

### 5. verification-before-completion

**Superpowers says**: Iron Law: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE. Gate function: IDENTIFY what proves the claim → RUN the command → READ the output → VERIFY it confirms the claim → ONLY THEN claim it. Red flags: "should work now," "I'm confident," expressing satisfaction before verification.

**Sawmill equivalent**: The 13Q gate requires the builder to prove comprehension BEFORE building. Turn E evaluates AFTER building. But during building (Turn D), there is no verification discipline.

**Does sawmill cover this?** Pre-build (13Q) and post-build (Turn E) verification exist, but **mid-build verification does not**. The builder could claim "45 tests pass" without running them. The BUILDER_HANDOFF says "Run `python3 -m pytest tests/unit/ -v`. Expected: 45 passed" but there's no enforcement that the builder actually reads the output and doesn't just claim success.

**Quoted gap**: This directly maps to the memory file entry: *"Ray does NOT want agents to hand back verification work — run it and fix it."* The verification-before-completion skill is the exact mechanism to enforce this.

**Recommendation**: **CRITICAL — ABSORB**. Add verification-before-completion rules to the BUILDER_HANDOFF_STANDARD template (Turn D). Specifically:
1. Every test run claim must include the actual output line ("45 passed in 2.3s")
2. Every "tests pass" must be from THIS session (not cached/assumed)
3. Builder RESULTS.md must include paste of final test output
4. Red flags list for the evaluator to check in Turn E

---

### 6. subagent-driven-development

**Superpowers says**: Fresh subagent per task. Two-stage review after each: (1) spec compliance reviewer checks code matches spec, (2) code quality reviewer checks implementation quality. Self-reflection step before handoff. Review loops: if reviewer finds issues, implementer fixes, reviewer re-reviews.

**Sawmill equivalent**: Turn D is a single builder agent. Turn E (Evaluator) reviews AFTER all building is complete. No per-task review during building.

**Does sawmill cover this?**
- **Spec compliance**: Superpowers reviews per task. Sawmill reviews everything at Turn E (batch). GAP: a bug in task 2 compounds through tasks 3-18 before being caught.
- **Self-reflection**: Superpowers asks "look at your work with fresh eyes" before reporting. Sawmill has no equivalent.
- **Two-stage review**: Superpowers separates "does it match spec" from "is the code good." Sawmill's Turn E combines both.

**Does superpowers do something sawmill doesn't?**
- Per-task spec compliance check prevents cascading errors
- Self-reflection catches bugs the implementer can find themselves
- Two-stage review separates concerns (spec vs quality)

**Recommendation**: **ABSORB partially**. Don't change the turn structure (holdout isolation is too valuable to compromise). Instead:
1. Add self-reflection prompt to BUILDER_HANDOFF_STANDARD: "Before reporting each implementation step complete, review your work with fresh eyes."
2. Consider adding a mid-build checkpoint: after unit tests pass (step 14 in FMWK-001), builder reports status before proceeding to integration tests. Human can catch issues early.

---

### 7. executing-plans

**Superpowers says**: Load plan → review critically → execute in batches of 3 tasks → report for human review → apply feedback → next batch → finish with branch completion skill.

**Sawmill equivalent**: Turn D builder reads D10 + Handoff, answers 13Q, gets greenlight, executes all steps, writes RESULTS.md.

**Does sawmill cover this?** Yes, but without batch checkpoints. The builder executes all 18 steps and reports at the end. Superpowers pauses every 3 tasks for human review.

**Recommendation**: **ABSORB** batch checkpoint concept. Add to BUILDER_HANDOFF_STANDARD: "Report status after completing the unit test phase (all unit tests green) before proceeding to integration tests. Human reviews and greenlights integration phase." This is a natural checkpoint that doesn't add overhead.

---

### 8. requesting-code-review / receiving-code-review

**Superpowers says**:
- **Requesting**: Get git SHAs, dispatch code-reviewer subagent with structured template. Act on feedback by severity (Critical → fix immediately, Important → fix before proceeding, Minor → note for later).
- **Receiving**: Verify before implementing. Push back with technical reasoning if wrong. No performative agreement ("You're absolutely right!"). YAGNI check on "professional" features. One fix at a time, test each.

**Sawmill equivalent**: Turn E (Evaluator) runs holdout scenarios. On failure: one-line description of WHAT failed, not HOW to fix it. Builder gets max 3 attempts. No guidance on how to receive and act on evaluation feedback.

**Does sawmill cover this?** Turn E covers the REQUESTING side (structured evaluation with pass criteria). But sawmill has NO guidance on:
- How the builder should receive Turn E feedback
- How to prioritize fixes (critical vs minor)
- When to push back on evaluation results
- How to avoid performative agreement with evaluation feedback

**Recommendation**: **ABSORB** receiving-code-review patterns. Add to AGENT_CONSTRAINTS or BUILDER_HANDOFF_STANDARD:
1. When Turn E fails: read each failure, verify against codebase, fix one at a time, test each
2. If evaluation seems wrong: push back with evidence (reference test output, spec text)
3. No performative response to evaluation ("I'll fix everything!") — state what you'll change and why

---

### 9. using-git-worktrees

**Superpowers says**: Create isolated git worktrees for feature work. Auto-detect project setup. Verify clean test baseline. Safety verification (ensure worktree dir is gitignored).

**Sawmill equivalent**: Staging directories (`staging/FMWK-ID/`). All work stays in staging. Never touches governed filesystem.

**Does sawmill cover this?** Different mechanism, same goal. Staging directories provide isolation without git branches. This is appropriate for DoPeJarMo because:
- KERNEL frameworks are hand-verified, not merged via PR
- The governed filesystem has its own install lifecycle
- Staging directories are simpler than worktrees for the sawmill model

**Recommendation**: No change. Different by design. Worktrees are useful for ad-hoc work outside sawmill (and the skill is installed for that).

---

### 10. dispatching-parallel-agents

**Superpowers says**: When facing 2+ independent problems, dispatch one agent per domain. Focused prompts, clear constraints, specific output expectations. Review and integrate results.

**Sawmill equivalent**: Turn B and Turn C run in parallel (Plan Agent and Holdout Agent). Within a turn, no parallel dispatch guidance.

**Does sawmill cover this?** Parallel turns exist but within-turn parallelism isn't addressed. For Turn D, a builder working on 18 steps doesn't parallelize them (they're sequential by design — each depends on the previous).

**Recommendation**: No change for sawmill turns. The skill is useful for ad-hoc debugging sessions outside the pipeline.

---

### 11. finishing-a-development-branch

**Superpowers says**: Verify tests → present 4 options (merge/PR/keep/discard) → execute choice → cleanup worktree.

**Sawmill equivalent**: Builder writes RESULTS.md. Turn E evaluates. If passing, human decides on installation path (KERNEL is hand-verified).

**Recommendation**: No change. Different lifecycle model.

---

### 12. using-superpowers (meta-skill)

**Superpowers says**: Check for relevant skills BEFORE any action. Even 1% chance = invoke it. Skills are mandatory, not suggestions.

**Sawmill equivalent**: COLD_START.md defines reading order. AGENT_BOOTSTRAP.md is the entry point. Agent definitions in `.claude/agents/` scope each turn's behavior.

**Recommendation**: No change. Sawmill's agent definitions serve the same purpose (prescribing behavior per turn).

---

### 13. writing-skills (meta-skill)

**Superpowers says**: How to create new skills with evaluation-driven development, progressive disclosure, and iterative testing.

**Sawmill equivalent**: Templates/ and Templates/compressed/ define document standards. No skill-authoring guidance.

**Recommendation**: No change for sawmill. The writing-skills skill is installed for creating custom skills outside the pipeline.

---

## Critical Gaps Summary

| # | Gap | Severity | What to build | Where it goes |
|---|-----|----------|---------------|---------------|
| 1 | No debugging protocol | CRITICAL | `TDD_AND_DEBUGGING.md` | `Templates/` — Turn D reference |
| 2 | No mid-build verification discipline | CRITICAL | Add to `BUILDER_HANDOFF_STANDARD.md` | `Templates/` |
| 3 | TDD enforcement lacks depth | CRITICAL | `TDD_AND_DEBUGGING.md` | `Templates/` |
| 4 | No per-task self-reflection | HIGH | Add to `BUILDER_HANDOFF_STANDARD.md` | `Templates/` |
| 5 | No mid-build checkpoint | HIGH | Add to `BUILDER_HANDOFF_STANDARD.md` | `Templates/` |
| 6 | No code review reception protocol | MODERATE | Add to `AGENT_CONSTRAINTS.md` | `architecture/` |
| 7 | No commit-after-green discipline | MODERATE | Add to `BUILDER_HANDOFF_STANDARD.md` | `Templates/` |

## What Sawmill Has That Superpowers Doesn't

For completeness — areas where sawmill's design is stronger and should NOT be weakened:

1. **Holdout isolation** (Turn C/E): Builder never sees acceptance tests. Evaluator never sees builder reasoning. Superpowers has no equivalent — all reviews happen in-context.

2. **13Q comprehension gate**: Builder must prove understanding before writing code. Superpowers has no pre-build comprehension check.

3. **Constitutional rules** (D1 ALWAYS/ASK/NEVER): Formal boundaries that agents cannot cross even if instructed. Superpowers has "iron laws" per skill but no cross-cutting constitutional framework.

4. **Authority chain**: Ambiguity resolves by walking UP documents, never by inventing. Superpowers relies on skill instructions without a formal authority hierarchy.

5. **Cryptographic provenance**: SHA-256 hashes on all deliverables. Superpowers doesn't track artifact integrity.

6. **Formal specification depth**: D1-D10 documents capture requirements at a level superpowers doesn't attempt (event schemas, error codes, interface contracts, side-effect specifications).

---

## Recommended Action Plan

**Phase 1 — Immediate (before next Turn D)**:
1. Create `Templates/TDD_AND_DEBUGGING.md` combining:
   - TDD iron law + verify RED/GREEN + rationalizations table
   - 4-phase systematic debugging protocol
   - 3-fix architectural question (ties to sawmill's 3-attempt limit)
2. Add verification-before-completion rules to `Templates/BUILDER_HANDOFF_STANDARD.md`:
   - Every claim requires fresh command output
   - RESULTS.md must include pasted test output
   - Red flags for evaluator

**Phase 2 — Before FMWK-002 Turn D**:
3. Add self-reflection prompt to BUILDER_HANDOFF_STANDARD
4. Add mid-build checkpoint (unit tests green → report → greenlight integration)
5. Add commit-after-green discipline to handoff standard
6. Add code review reception protocol to AGENT_CONSTRAINTS.md

**Phase 3 — Validate**:
7. Run FMWK-002 through sawmill with these additions
8. Compare builder behavior with vs without
9. Iterate based on results
