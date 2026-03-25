# Review Report — FMWK-002-write-path (Turn D)

Date: 2026-03-22
Run ID: 20260322T021641Z-00ae718794cd
Attempt: 2

Builder Prompt Contract Version Reviewed: 1.0.0
Reviewer Prompt Contract Version: 1.0.0

---

## Summary

The builder's 13Q answers are concrete, specific, and well-aligned with the handoff and D10 context. The builder demonstrates clear understanding of scope boundaries, file paths, interface contracts, test obligations, integration topology, and the two adversarial failure modes. Two `[CRITICAL_REVIEW_REQUIRED]` flags were raised and are resolved below. Neither constitutes a blocker.

---

## Findings

### Q1 — Scope and Outputs
**PASS.** Builder correctly identifies the package, staging root (`staging/FMWK-002-write-path/`), all four primary responsibilities (submit_mutation, snapshot, recovery, refold), and the full set of planned output artifacts including `builder_evidence.json`. No scope confusion.

### Q2 — Not Building
**PASS.** Correctly excludes: second event store, query layer, policy engine, background queue, direct-caller managed writes, package gates, LLM execution, multi-process writer coordination, snapshot format optimization. Explicitly calls out no writes to `/Users/raymondbruni/dopejar/`.

### Q3 — Constitutional Boundaries
**PASS.** ALWAYS/ASK/NEVER structure is accurate. Correctly states append-first-fold-second success ordering, mechanical-only fold, bounded methylation `0.0–1.0`, typed error surfaces, and SDK-governed snapshot I/O. The builder correctly identifies that widening accepted event types or moving execution into HO3 requires escalation.

### Q4 — APIs from D4
**PASS.** All four `WritePathService` methods listed with exact signatures. All `LedgerPort` and `GraphPort` methods listed with exact signatures. Supporting module APIs (`fold_live_event`, `clamp_methylation`, `create_snapshot`, `recover_graph`, `refold_from_genesis`, all three system-event builders) listed correctly. Exact match with D10 Active Components table.

### Q5 — File Locations [CRITICAL_REVIEW_REQUIRED RESOLVED]
**PASS.** All source files correctly listed under `staging/FMWK-002-write-path/write_path/`. All test files correctly listed under `staging/FMWK-002-write-path/tests/`. Sawmill artifacts correctly listed under `sawmill/FMWK-002-write-path/`.

**[CRITICAL_REVIEW_REQUIRED] Resolution — Double location conflict:**
The builder flagged a perceived conflict between D4's "package code" language and D10/handoff's explicit placement of doubles in `tests/conftest.py`. This is resolved as follows:

- D10 is explicit: "declared doubles live in `tests/conftest.py`"
- Handoff Step 1 is explicit: doubles are in `tests/conftest.py` and `write_path/ports.py`
- D6's "package code" language refers to the staging package (`staging/FMWK-002-write-path/`) as a whole, not the `write_path/` module specifically — `tests/conftest.py` is part of that package

**Directive: doubles go in `tests/conftest.py`. Do not create a separate module under `write_path/` for doubles.** The `write_path/ports.py` module declares the Protocol interfaces; the doubles implementing those protocols for test use live in `tests/conftest.py`.

### Q6 — Data Formats
**PASS.** Core entities (`MutationRequest`, `MutationReceipt`, `SnapshotDescriptor`, `RecoveryCursor`) listed with correct fields. Format constraints correct: ISO-8601 UTC with Z, decimal strings not binary floats, absolute `/snapshots/...snapshot` paths, `sha256:` + 64 hex chars hash format, correct `RecoveryCursor.mode` values, `replay_from_sequence = -1` for genesis. All five write-path-owned payload schemas listed: `methylation_delta`, `suppression`, `unsuppression`, `mode_change`, `consolidation`.

### Q7 — Manifest and Packaging [CRITICAL_REVIEW_REQUIRED RESOLVED]
**PASS.** Package ID, framework ID, version, staging root, importability requirement, and RESULTS.md hash requirement all correct.

**[CRITICAL_REVIEW_REQUIRED] Resolution — Missing hash values in 13Q turn prompt:**
The builder correctly infers that `handoff_hash` and `q13_answers_hash` are not provided at 13Q time and will be injected by the orchestrator at build time (after reviewer PASS). This assumption is correct. The `q13_answers_hash` is provided in the reviewer's prompt; the orchestrator will supply both values to the builder at build turn. This does not block the 13Q gate.

**Directive: builder should copy both hash values verbatim from the orchestrator's build-turn prompt when assembling `builder_evidence.json`.**

### Q8 — Dependencies
**PASS.** Correctly lists FMWK-001 and FMWK-005 contract dependencies, all required `platform_sdk` modules, and all stdlib dependencies. No gaps.

### Q9 — Testing Obligation
**PASS.** 40+ minimum, 45-55 target, per-file minimums, all nine required named behaviors, all six verification commands, TDD rule — all correctly stated and in exact alignment with the handoff test plan.

### Q10 — Integration Understanding
**PASS.** Correctly identifies callers (HO1, HO2/runtime, FMWK-006). Correctly describes the full data-flow for live mutation, snapshot, recovery, and full refold paths. Correctly states that the Write Path depends on FMWK-001 and FMWK-005 contracts but does not absorb their ownership.

### Q11 — Primary Failure Mode
**PASS.** Correctly identifies SC-008 (durable append + fold failure) as the critical failure. Correct expected behavior: return `WritePathFoldError`, preserve durable sequence boundary, require recovery before subsequent writes. Likely evaluator probes correctly anticipated (receipt returned anyway, write allowed after fold failure, wrong replay boundary).

### Q12 — Forbidden Shortcut
**PASS.** Correctly identifies: no bypass path for system events (`session_start`, `session_end`, `snapshot_created` must use `submit_mutation()`). Correctly identifies: no direct Graph mutation or Ledger writes outside declared ports, including in tests. Likely shortcut failures correctly anticipated.

### Q13 — Semantic Drift
**PASS.** Correct characterization of drift (Write Path becomes governance engine, query layer, policy engine, or background processor). Correct self-audit questions. Builder demonstrates understanding that success receipt means "durable append + completed fold" — no more, no less.

---

## Next Action

Both `[CRITICAL_REVIEW_REQUIRED]` flags are resolved. The builder is ready to implement.

After this PASS, the orchestrator should inject `handoff_hash` and `q13_answers_hash` into the build-turn prompt so the builder can copy them verbatim into `builder_evidence.json`.

Builder must follow D8 order exactly and apply DTT (Design, Test failing, Then implement) for every behavior before claiming completion.

Review verdict: PASS
