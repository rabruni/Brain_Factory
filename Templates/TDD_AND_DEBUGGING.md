# TDD and Debugging Discipline

## Purpose

Turn D builders read this alongside the handoff. It governs HOW code gets written — not what to build (that's the handoff), but the discipline required during building. Every gap this addresses was discovered by comparing sawmill against production-tested coding skills and finding that sawmill defines WHAT but not HOW.

---

## 1. TDD Iron Law

**NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.**

Wrote code before the test? Delete it. Not "comment out" — delete. Not "keep as reference" — delete. Start over with the test.

### The Cycle

1. **RED**: Write a test for ONE behavior. Run it. Watch it fail. Confirm the failure message matches expected behavior. If the test passes without implementation — your test is wrong.
2. **GREEN**: Write the MINIMUM code to make the test pass. Run it. Watch it pass.
3. **REFACTOR**: Clean up. Tests stay green. No new behavior during refactor.
4. **COMMIT**: Commit after every green cycle. Message format: `feat|fix|test(scope): what changed`

Move to the next behavior. Repeat.

### Rationalizations (You Will Try Every One)

| What you'll say | What you'll do instead |
|-----------------|----------------------|
| "I know this works" | Write the test anyway. |
| "Testing this is hard" | Hard to test = hard to use. Fix the design. |
| "I'll write tests after" | You won't. And if you do, they'll test your implementation, not the behavior. |
| "This is just a helper" | Helpers have bugs too. |
| "The interface is obvious" | Obvious to you now. Write the test. |
| "I'll refactor first" | RED-GREEN-REFACTOR. Not REFACTOR-RED-GREEN. |
| "I need to prototype" | Prototype in a test. Delete after. |
| "This is boilerplate" | Boilerplate breaks too. |

### Anti-Patterns

- **Testing mocks instead of behavior**: If your test only verifies that a mock was called, it tests nothing. Test the observable output.
- **Testing implementation details**: If renaming a private method breaks your test, the test is coupled to implementation. Test the public interface.
- **Tests that can't fail**: If the test passes before you write the code, the test is meaningless. Delete it and write one that exercises real behavior.
- **Testing in batches**: Writing 10 tests then implementing everything defeats TDD. One behavior at a time.

---

## 2. Systematic Debugging Protocol

When a test fails unexpectedly, a build breaks, or behavior deviates from spec — follow these four phases in order. No skipping.

### Phase 1: Root Cause Investigation

1. **Read the actual error.** The full stack trace, not just the last line.
2. **Reproduce it.** Run the exact command again. If it doesn't reproduce, you don't understand the problem.
3. **Check recent changes.** What did you change since the last green? Start there.
4. **Trace data flow.** Follow input through the code path to where it diverges from expected behavior.

### Phase 2: Pattern Analysis

1. **Find working examples.** Is there similar code in the codebase that works? What's different?
2. **Check the platform_sdk.** Does the existing SDK handle this case? How?
3. **Read the spec.** Does D2/D4 specify behavior for this scenario? Is your implementation matching it?

### Phase 3: Hypothesis and Testing

1. **Form ONE hypothesis.** Not "maybe it's X or Y" — pick one.
2. **Test it minimally.** Change ONE variable. Run the test. Did the behavior change?
3. **If wrong, discard and form another.** Don't layer fixes.

### Phase 4: Implementation

1. **Write a failing test** that reproduces the bug.
2. **Fix the code.** Minimum change.
3. **Verify GREEN.** The bug-reproducing test passes. All other tests still pass.
4. **Commit.** `fix(scope): what the bug was and why it happened`

### Iron Law

**NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.**

Do not guess. Do not try random changes. Do not copy-paste from Stack Overflow without understanding why it works.

### The 3-Fix Rule

If 3 attempted fixes fail, **question the architecture**. The problem may not be where you think it is. This ties directly to sawmill's 3-attempt limit (`AGENT_CONSTRAINTS.md`). Use your attempts wisely — systematic investigation, not shotgun debugging.

### Multi-Component Evidence Gathering

DoPeJarMo runs Docker + immudb + platform_sdk. When debugging:
- Check Docker container status and logs
- Check immudb connection and state
- Check platform_sdk configuration
- Gather evidence from ALL layers before forming a hypothesis

---

## 3. Commit Discipline

- **Commit after every GREEN cycle.** Not after every file. Not at the end. After every behavior passes.
- **Message format**: `feat|fix|test(scope): what changed`
- **Never batch** multiple behaviors into one commit. One behavior = one commit.
- **Never commit RED.** If tests are failing, you're not done.

---

## 4. Code Review Reception

When Turn E evaluation fails:

1. **Read each failure.** One at a time. Understand what the evaluator observed.
2. **Verify against the codebase.** Does the failure match what the code actually does? Check before assuming the evaluator is right.
3. **Fix one at a time.** One failure, one fix, one test run. Do not batch fixes.
4. **Test each fix.** Run the full suite after every fix. Confirm the specific failure is resolved AND no regressions.

### When to Push Back

If an evaluation result seems wrong:
- Reference the specific test output that contradicts the evaluation
- Reference the specific spec text (D2/D4) that supports your implementation
- State what you believe is correct and why, with evidence

### What Not to Do

- No performative responses: "I'll fix everything immediately!" — State what you'll change and why.
- No bulk rewrites: Fixing one failure should not involve rewriting unrelated code.
- No defensive deletions: Don't remove code to make a failure "go away." Fix the root cause.
