# Review Report — Ledger (FMWK-001)

Run ID: 20260321T054057Z-6d3169742c02
Attempt: 1
Date: 2026-03-21

Builder Prompt Contract Version Reviewed: 1.0.0
Reviewer Prompt Contract Version: 1.0.0

---

## Summary

The builder's 13Q answers are concrete, specific, and aligned with the
handoff, D2, D3, D4, D6, and D10. All file paths, API signatures, data
formats, error contracts, test obligations, and integration details have been
cross-referenced against the source-of-truth documents and the live
platform_sdk code. The builder is ready to implement without spec drift.

---

## Findings

### Q1 — What am I building? — PASS
Correctly identifies the `ledger` package, all 6 LedgerClient methods, hash
chaining mechanics, threading.Lock single-writer model, and complete
deliverable list (9 source + 5 test + README + RESULTS.md +
builder_evidence.json). All paths match the handoff.

### Q2 — What am I NOT building? — PASS
Correctly excludes FMWK-002 (Write Path), FMWK-005 (Graph), FMWK-006
(Package Lifecycle), DEF-001 (snapshot format), DEF-002 (deferred payload
schemas), multi-process deployment, async interface, and kernel services.
Scope boundaries are precise.

### Q3 — D1 constitutional boundaries — PASS
ALWAYS, ASK FIRST, and NEVER boundaries all correctly stated and traceable to
D1 articles and D10 key patterns. The reference to Q5's CRITICAL_REVIEW_REQUIRED
flag under the ALWAYS section is transparent.

### Q4 — APIs from D4 — PASS
All 6 inbound contract signatures match D4 exactly. Error contracts verified:
- `read(N > tip)` → LedgerSequenceError (D4 IN-002 postcondition 2) ✓
- `read(N < 0)` → LedgerSequenceError (D4 IN-002 postcondition 3) ✓
- `read_range(end > tip)` → LedgerSequenceError (D4 IN-003 postcondition 2) ✓
- `read_since(N > tip)` → LedgerSequenceError (D4 IN-004 postcondition 3) ✓
- `read_since(tip)` → `[]` (D4 IN-004 postcondition 2) ✓
- `verify_chain()` immudb down → LedgerConnectionError NOT {valid:false} (D4 IN-005 postcondition 6) ✓
- Concurrent append → LedgerSequenceError (D4 IN-001 Constraints) ✓
- Invalid event_type → LedgerSerializationError before lock (D4 ERR-004) ✓

ImmudbStore internal interface (connect, set, get, scan, get_count) matches
the handoff architecture diagram.

### Q5 — File locations — PASS (with CRITICAL_REVIEW_REQUIRED resolved)

**CRITICAL_REVIEW_REQUIRED resolution:**

The builder correctly identified that `platform_sdk.tier0_core.data` is
SQLAlchemy 2.x async (verified: `data.py` imports `create_async_engine`,
`AsyncSession`, exposes `get_session()`, `get_engine()` — zero immudb or gRPC
capability). The D10 statement "ALL immudb access goes through
`platform_sdk.tier0_core.data`" is inaccurate for immudb access.

The existing SDK module for immudb is `platform_sdk.tier0_core.ledger`, which
uses `from immudb import ImmudbClient` directly (ledger.py line 179). However,
the BUILDER_HANDOFF Section 7 explicitly states this build **supersedes** the
existing LedgerProvider.

**The builder's proposed resolution is ACCEPTED:**
1. `store.py` wraps `immudb-py` directly as the `ImmudbStore` class — this is
   the abstraction boundary. The BUILDER_HANDOFF architecture diagram
   explicitly shows `ImmudbStore (store.py)` as a designed component.
2. `MockImmudbStore` (in-memory dict) provides the test mock via dependency
   injection.
3. `import immudb` is permitted ONLY in `store.py` — all other modules access
   immudb through `ImmudbStore`. This is consistent with the existing SDK
   pattern where `ImmudbProvider` in `ledger.py` also imports immudb directly.
4. The "No direct `import immudb`" rule applies to all modules EXCEPT
   `store.py`, which IS the abstraction layer.

All 9 source file paths and 5 test file paths match the handoff. Sawmill
output paths (RESULTS.md, builder_evidence.json, README.md) are correct.

### Q6 — Data formats from D3 — PASS
All 4 entities verified against D3:
- LedgerEvent (E-001): 9 fields, all types and constraints correct
- Provenance (E-002): 3 fields correct
- TipRecord (E-003): 2 fields correct, empty sentinel format correct
- ChainVerificationResult (E-004): 2 fields correct

EventType enum: all 15 values match D3/D4 exactly. Float-as-string rule,
null field inclusion, key format (20-char zero-padded), hash format
("sha256:" + 64 hex) — all correct.

### Q7 — Manifest fields — PASS
Package metadata (package_id, framework_id, version, manifest_hash) correct.
RESULTS.md required sections all listed. builder_evidence.json fields listed
with note about computing hashes at write time — reasonable.

### Q8 — Dependencies — PASS
- Stdlib: hashlib, json, threading, dataclasses, typing, time, sys, argparse ✓
- Platform SDK: config (PlatformConfig), ids (new_id), secrets, logging, metrics ✓
- `new_id(kind="uuid7")` API verified: exists in `platform_sdk/tier0_core/ids.py:54`
- `PlatformConfig` immudb fields verified: immudb_host, immudb_port,
  immudb_database, immudb_username, immudb_password all present in
  `platform_sdk/tier0_core/config.py:46-50`
- immudb-py scoped to store.py only (per Q5 resolution) ✓

### Q9 — Testing — PASS
- Mandatory minimum: 40 tests ✓
- Target: ≥55 tests ✓
- Distribution matches handoff test plan exactly
- 60 explicitly named tests exceeds target
- TDD discipline correctly articulated
- Verification criteria (pytest commands, grep checks) correct
- `import immudb` grep exception for store.py is transparent and aligned
  with Q5 resolution

### Q10 — Integration — PASS
- Upstream (Write Path FMWK-002) and downstream (Graph FMWK-005, Package
  Lifecycle FMWK-006) correctly identified
- PlatformConfig wiring verified against live config.py
- CLI integration (python -m ledger --verify) correctly described with
  output format and exit codes
- immudb wiring correct: port 3322, database "ledger", key format
  `f"{sequence:020d}"`, value as canonical JSON bytes

### Q11 — Adversarial: Most Likely Misinterpretation — PASS
Correctly identifies SC-011 mutex scope as highest risk. Accurately describes
the failure mode (lock only around set vs. around entire read-tip → compute →
write path) and the consequence (silent sequence fork). Commits to acquiring
lock before get_tip(), referencing D10 Key Pattern 1 and D5 RQ-001.

### Q12 — Adversarial: Most Likely Postcondition Misimplementation — PASS
Correctly identifies verify_chain() + connection error as highest risk.
Quotes D4 IN-005 postcondition 6 exactly. Correctly explains why returning
ChainVerificationResult(valid=False) for connection errors conflates
infrastructure failure with data corruption. Secondary risk (read_since
exclusive boundary) also correctly identified with commitment to first
returned event at sequence N+1.

### Q13 — Evaluator Probes — PASS
Eight plausible probes, all well-reasoned and traceable to D2/D4/D6:
1. Empty Ledger sentinel exact format — traceable to D6 CLR-002
2. Null field canonical hash — traceable to D3 Canonical JSON Constraint
3. Float string vs float number — traceable to D5 RQ-003
4. read_since(tip) → [] — traceable to D4 IN-004 postcondition 2
5. Chain corruption vs connection failure — traceable to D4 IN-005 postcondition 6
6. Atomicity on failure — traceable to D4 IN-001 postcondition 8
7. Inclusive bounds on read_range — traceable to D6 CLR-004
8. CLI exit codes — traceable to D1 Article 8

---

## Next Action

Builder may proceed to implementation following DTT discipline and D8 task
order (T-001 through T-012).

Review verdict: PASS
