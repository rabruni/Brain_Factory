# Builder Handoff Standard

## Purpose

This document defines the standard format for all builder handoff documents. Every handoff — whether a new component, a follow-up fix, or an upgrade — must follow this template.

---

## File Organization

Each handoff gets its own directory:

```
[handoffs_dir]/<handoff_id>/
├── <handoff_id>_BUILDER_HANDOFF.md    ← the spec
├── sawmill/<FMWK-ID>/RESULTS.md       ← the results (written by builder)
└── <handoff_id>_AGENT_PROMPT.md       ← the dispatched prompt (optional, for audit)
```

**Handoff ID patterns:**

| Type | ID Pattern | Example |
|------|------------|---------|
| New component | `H-<N>` | `H-32` |
| Follow-up | `H-<N><letter>` | `H-32A` |
| Cleanup | `CLEANUP-<N>` | `CLEANUP-5` |

---

## Required Sections

Every handoff document MUST contain these sections in order:

### 1. Mission
One paragraph: what the agent is building and why. Include the package ID(s).

### 2. Critical Constraints
Numbered list of non-negotiable rules. Always includes:

<!-- Customize these to your project. The items below are a starting template.
     Keep constraints that apply universally; add project-specific ones. -->

1. **All work goes in the designated staging/build directory.** Never write to production paths.
2. **DTT: Design, Test, Then implement.** Per-behavior TDD cycles: write a failing test for one behavior, write minimum code to pass, refactor, repeat.
3. **Package everything.** New code ships as packages with manifests, hashes, and proper dependencies.
4. **End-to-end verification.** After building, run the full test suite. All tests must pass.
5. **No hardcoding.** Every threshold, timeout, retry count, rate limit — all config-driven.
6. **No file replacement.** Packages must never overwrite another package's files.
7. **Deterministic archives.** Use deterministic archive creation. No non-reproducible metadata.
8. **Results file.** When finished, write a results file following the template below.
9. **Full regression test.** Run ALL package tests (not just yours) and report results.
10. **Baseline snapshot.** Include a baseline snapshot so the next agent can diff against it.

Add task-specific constraints as needed.

### 3. Architecture / Design
Explain WHAT to build. Diagrams, data flows, component relationships. Be explicit about interfaces and boundaries.

### 4. Implementation Steps
Numbered, ordered steps. Include file paths, function signatures, and enough detail that the agent can execute without interpretation. Every step that enforces a safety or architectural constraint MUST include a one-line "Why" so the builder understands the intent, not just the instruction.

### 5. Package Plan
For each package: package ID, layer, assets list, dependencies, and any framework manifest.

### 6. Test Plan
List every test method with name, one-line description, and expected behavior.

Minimum test counts:
- Small packages (1-2 source files): 10+ tests
- Medium packages (3-5 source files): 25+ tests
- Large packages (6+ source files): 40+ tests

### 7. Existing Code to Reference
Table of files the agent should read before building:

| What | Where | Why |
|------|-------|-----|
| [Example pattern] | [file path] | [What to learn from it] |

### 8. End-to-End Verification
Exact commands for clean-room verification. Copy-pasteable. Include expected output.

### 9. Files Summary
Table of every file created or modified:

| File | Location | Action |
|------|----------|--------|
| [filename] | [path] | [CREATE / MODIFY] |

### 10. Design Principles
Non-negotiable design rules for this specific component. Usually 4-6 items.

---

## Results File

**Every handoff agent MUST write a results file when finished.**

**Required content:**

```markdown
# Results: [Handoff Title]

## Status: PASS | FAIL | PARTIAL

## Files Created
- path/to/file1 (SHA256: abc123...)

## Files Modified
- path/to/existing (SHA256 before: xxx, after: yyy)

## Archives Built
- package-name.tar.gz (SHA256: ghi789...)

## Test Results — THIS PACKAGE
- Total: N tests
- Passed: N
- Failed: N
- Skipped: N
- Command: [exact test command]

## Full Regression Test — ALL PACKAGES
- Total: N tests
- Passed: N
- Failed: N
- Skipped: N
- Command: [exact test command]
- New failures introduced by this agent: [list or NONE]

## Baseline Snapshot (AFTER this agent's work)
- Packages installed: N
- Total tests (all packages): N

## Clean-Room Verification
- Packages installed: N
- Install order: [ordered list]
- All tests pass after each install: YES/NO

## Issues Encountered
- [Problems, workarounds, deviations from spec]

## Notes for Reviewer
- [Design decisions made outside spec]

## Session Log
- [Key decisions made during build]
- [Blockers encountered and how they were resolved]
- [Architectural choices not in the spec — why they were made]
- [Context for next session if this handoff retries]
```

---

## Reviewer Checklist

**Before marking any handoff as VALIDATED, the reviewer MUST verify ALL of these:**

- [ ] RESULTS file exists at correct location
- [ ] RESULTS file has ALL required sections
- [ ] Clean-Room Verification section is complete
- [ ] Baseline Snapshot section is present
- [ ] Full regression test was run (ALL packages, not just this one)
- [ ] No new test failures introduced
- [ ] Manifest hashes use correct format
- [ ] RESULTS file naming follows convention

---

## Multi-Package Builds (Parallel Waves)

### During Each Wave
1. Each package gets its own RESULTS file
2. Reviewer validates each against the checklist above
3. Clean-room verification runs for EACH wave

### After the Final Wave: Integration Handoff (MANDATORY)
When packages form a system, an Integration Handoff ties them together:
1. Wire new packages into the entrypoint
2. Resolve package lifecycle (mark superseded packages, update dependencies)
3. Run E2E smoke test (verify the integrated system works)
4. Write RESULTS file with full system baseline snapshot
