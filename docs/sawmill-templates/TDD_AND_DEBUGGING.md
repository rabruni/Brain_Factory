# TDD and Debugging Discipline

Turn D builders: governs HOW code gets written. Read alongside handoff.

## 1. TDD Iron Law
**NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.** Wrote code before the test? DELETE it. Not comment out — DELETE.

Cycle: RED (write test, run, watch FAIL, confirm failure message) → GREEN (MINIMUM code to pass) → REFACTOR (tests stay green) → COMMIT (`feat|fix|test(scope): what`)

Rationalizations (you WILL try these):
- "I know this works" → Write the test anyway
- "Testing this is hard" → Hard to test = hard to use. Fix the design
- "I'll write tests after" → You won't. They'll test implementation, not behavior
- "This is just a helper" → Helpers have bugs too
- "The interface is obvious" → Write the test
- "I'll refactor first" → RED-GREEN-REFACTOR, not REFACTOR-RED-GREEN
- "I need to prototype" → Prototype in a test. Delete after
- "This is boilerplate" → Boilerplate breaks too

Anti-patterns: testing mocks instead of behavior, testing implementation details (private method rename breaks test = coupled), tests that pass before code exists (meaningless), batch-writing tests then implementing (defeats TDD).

## 2. Systematic Debugging Protocol
When tests fail unexpectedly — 4 phases, in order, NO SKIPPING:

**Phase 1 — Root Cause Investigation**: Read FULL stack trace. Reproduce exactly. Check recent changes since last green. Trace data flow to divergence point.

**Phase 2 — Pattern Analysis**: Find working examples of similar code. Check platform_sdk. Read D2/D4 spec for this scenario.

**Phase 3 — Hypothesis and Testing**: Form ONE hypothesis. Change ONE variable. Run test. If wrong, discard — don't layer fixes.

**Phase 4 — Implementation**: Write failing test reproducing bug → fix (minimum change) → verify GREEN → commit `fix(scope): root cause`.

**NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.** No guessing. No random changes.

**3-Fix Rule**: 3 failed fixes → question the architecture. Ties to sawmill 3-attempt limit (`AGENT_CONSTRAINTS.md`). Use attempts wisely.

**Multi-component**: Docker + immudb + platform_sdk — gather evidence from ALL layers before hypothesizing.

## 3. Commit Discipline
Commit after EVERY green cycle. Format: `feat|fix|test(scope): what`. NEVER batch multiple behaviors. NEVER commit RED.

## 4. Code Review Reception
Turn E failure: read each failure → verify against codebase → fix ONE at a time → test each fix (full suite, confirm no regressions).
Push back WITH EVIDENCE: specific test output, specific spec text (D2/D4). No performative responses ("I'll fix everything!") — state what changes and why. No bulk rewrites. No defensive deletions.
