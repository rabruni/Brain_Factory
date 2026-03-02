# Builder Handoff Standard

## File Organization
```
[handoffs_dir]/<handoff_id>/
  <handoff_id>_BUILDER_HANDOFF.md  (spec)
  sawmill/<FMWK-ID>/RESULTS.md     (results, written by builder)
  <handoff_id>_AGENT_PROMPT.md     (dispatched prompt, optional audit)
```
IDs: H-<N> (new) | H-<N><letter> (follow-up) | CLEANUP-<N> (cleanup)

## Required Sections (ALL 10, in this exact order, no exceptions)
1. **Mission** — one paragraph: what + why + package ID(s)
2. **Critical Constraints** — numbered non-negotiable rules. ALWAYS includes ALL of: staging-only, DTT, package everything, E2E verify, no hardcoding, no file replacement, deterministic archives, results file, full regression of ALL packages, baseline snapshot.
3. **Architecture/Design** — diagrams, data flows, every interface and boundary
4. **Implementation Steps** — numbered, strictly ordered, with file paths + function signatures. Every step that enforces a safety or architectural constraint MUST include a one-line "Why" (e.g., "Step 4: Implement mutex around append — WHY: immudb gRPC is not thread-safe for sequence increments"). Without the Why, builders implement the letter but not the spirit.
5. **Package Plan** — per package: ID, layer, every asset, all dependencies, manifest
6. **Test Plan** — every test method: name, description, expected behavior. Mandatory minimums: small(1-2 files)=10+, medium(3-5)=25+, large(6+)=40+
7. **Existing Code to Reference** — | What | Where | Why |
8. **E2E Verification** — exact copy-paste commands + expected output, no exceptions
9. **Files Summary** — | File | Location | Action (CREATE/MODIFY) | for every file, no omissions
10. **Design Principles** — 4-6 non-negotiable design rules

## Results File (MANDATORY — every handoff agent MUST write this when finished, no exceptions)
Required sections, ALL mandatory: Status (PASS|FAIL|PARTIAL) | Files Created (path + SHA256 for every file) | Files Modified (SHA256 before + after) | Archives Built (SHA256) | Test Results THIS PACKAGE (total/passed/failed/skipped/command) | Full Regression ALL PACKAGES (same + new_failures list or NONE) | Baseline Snapshot (packages installed, total tests) | Clean-Room Verification (packages, install order, all tests pass after each install) | Issues Encountered | Notes for Reviewer | Session Log (key decisions, blockers resolved, architectural choices not in spec, retry context)
Canonical: `| Status:PASS | Files:N (SHA256 each) | Tests:N/N/N | Regression:ALL pkgs |`

## Reviewer Checklist (ALL must pass before VALIDATED, no partial credit)
Results file exists at correct location, ALL required sections present, clean-room verification complete, baseline snapshot present, full regression was run on ALL packages (not just this one), no new test failures introduced, every manifest hash uses correct format, results file naming follows convention.

## Multi-Package (Parallel Waves)
Every package gets its own RESULTS file. Reviewer validates every one against the full checklist. Clean-room verification for every wave.
After final wave: Integration Handoff (MANDATORY, no exceptions) — wire all new packages into entrypoint, resolve every package lifecycle (mark superseded, update all dependencies), E2E smoke test of integrated system, RESULTS file with full system baseline snapshot.
