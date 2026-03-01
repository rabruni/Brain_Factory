# Builder Handoff Standard

## File Organization
```
[handoffs_dir]/<handoff_id>/
  <handoff_id>_BUILDER_HANDOFF.md  (spec)
  <handoff_id>_RESULTS.md          (results, written by builder)
  <handoff_id>_AGENT_PROMPT.md     (dispatched prompt, optional audit)
```
IDs: H-<N> (new) | H-<N><letter> (follow-up) | CLEANUP-<N> (cleanup)

## Required Sections (all 10, in order)
1. **Mission** — one paragraph: what + why + package ID(s)
2. **Critical Constraints** — numbered non-negotiable rules. Always includes: staging-only, DTT, package everything, E2E verify, no hardcoding, no file replacement, deterministic archives, results file, full regression, baseline snapshot.
3. **Architecture/Design** — diagrams, data flows, interfaces, boundaries
4. **Implementation Steps** — numbered, ordered, with file paths + signatures
5. **Package Plan** — per package: ID, layer, assets, dependencies, manifest
6. **Test Plan** — every test method: name, description, expected behavior. Minimums: small(1-2 files)=10+, medium(3-5)=25+, large(6+)=40+
7. **Existing Code to Reference** — | What | Where | Why |
8. **E2E Verification** — exact copy-paste commands + expected output
9. **Files Summary** — | File | Location | Action (CREATE/MODIFY) |
10. **Design Principles** — 4-6 non-negotiable design rules

## Results File (MANDATORY, written by builder when finished)
Required sections: Status (PASS|FAIL|PARTIAL) | Files Created (path + SHA256) | Files Modified (SHA256 before/after) | Archives Built (SHA256) | Test Results THIS PACKAGE (total/passed/failed/skipped/command) | Full Regression ALL PACKAGES (same + new_failures) | Baseline Snapshot (packages installed, total tests) | Clean-Room Verification (packages, install order, all pass) | Issues Encountered | Notes for Reviewer | Session Log (key decisions, blockers, architectural choices, retry context)

## Reviewer Checklist
ALL must pass before VALIDATED: results file exists + correct location, all required sections, clean-room complete, baseline present, full regression run, no new failures, correct hash format, correct naming.

## Multi-Package (Parallel Waves)
Each package gets own RESULTS. Reviewer validates each. Clean-room per wave.
After final wave: Integration Handoff (MANDATORY) — wire into entrypoint, resolve lifecycle, E2E smoke, RESULTS with full system baseline.
