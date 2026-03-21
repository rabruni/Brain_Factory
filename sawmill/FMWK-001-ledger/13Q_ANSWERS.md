Builder Prompt Contract Version: 1.0.0

# 13Q Comprehension Gate — FMWK-001-ledger (Turn D)

Date: 2026-03-20
Attempt: 1

---

## Q1 — What am I building?

The `ledger` Python package: FMWK-001-ledger, the Ledger primitive for DoPeJarMo. It is an append-only, hash-chained event store backed by immudb. It exposes one public class, `LedgerClient`, with exactly six methods: `append`, `read`, `read_range`, `read_since`, `verify_chain`, `get_tip`. Every state mutation in DoPeJarMo (node creation, signal delta, session boundary, package install) enters as a `LedgerClient.append()` call from the Write Path (FMWK-002). The Ledger assigns monotonic sequence numbers, computes SHA-256 hashes using deterministic canonical JSON (sort_keys, no whitespace, ensure_ascii=False), threads `previous_hash` from each event's predecessor, and stores canonical JSON bytes in immudb under zero-padded sequence keys. An in-process `threading.Lock` prevents sequence forks. All unit tests use MockProvider — no live immudb required.

**Deliverables:**
- `staging/FMWK-001-ledger/ledger/` — 9 source files (errors, models, schemas, serialization, store, verify, api, __init__, __main__)
- `staging/FMWK-001-ledger/tests/` — 5 test files (conftest + 4 test modules)
- `staging/FMWK-001-ledger/README.md`
- `sawmill/FMWK-001-ledger/RESULTS.md` (after build)
- `sawmill/FMWK-001-ledger/builder_evidence.json` (after build)

---

## Q2 — What am I NOT building?

- **NOT** FMWK-002 Write Path — the sole permitted caller of `append()`; routing mutations through Write Path is FMWK-002's job.
- **NOT** FMWK-005 Graph — consumer of `read()`, `read_range()`, `read_since()` for replay; Graph materialization is FMWK-005's job.
- **NOT** FMWK-006 Package Lifecycle — consumer of `verify_chain()` and `get_tip()`; gate logic is FMWK-006's job.
- **NOT** the snapshot file format (DEF-001 — explicitly deferred; `snapshot_created` event is accepted but the `.snapshot` file format is out of scope).
- **NOT** payload schemas for deferred event types (`methylation_delta`, `suppression`, `unsuppression`, `mode_change`, `consolidation`, `work_order_transition`, `intent_transition`, `package_uninstall`, `framework_install`) — the Ledger accepts these as opaque JSON objects and validates only JSON serializability.
- **NOT** further retry logic beyond the spec's one-reconnect + one-retry; the Write Path owns further retry.
- **NOT** multi-process deployment coordination — single-process assumption is documented (D5 RQ-001).
- **NOT** an async interface — the model is synchronous throughout (threading.Lock, not asyncio.Lock).
- **NOT** the kernel WebSocket server, HO2 orchestrator, or any other framework.

---

## Q3 — What are the D1 constitutional boundaries?

**ALWAYS (non-negotiable):**
- All immudb access through the abstraction layer (D1 Article 10; platform_sdk contract). See Q5 for a CRITICAL_REVIEW_REQUIRED flag on this.
- All ID generation through `platform_sdk.tier0_core.ids` (`new_id(kind="uuid7")`).
- All config reads through `platform_sdk.tier0_core.config` (`PlatformConfig`); no bare `os.getenv()`.
- Fail closed on infrastructure failure: immudb unreachable → raise `LedgerConnectionError`, never buffer or swallow.
- Canonical JSON per SIDE-002: `json.dumps(d, sort_keys=True, separators=(',',':'), ensure_ascii=False)` — exact bytes, no deviation.
- Every state mutation logged; nothing written without a hash; no event is ever modified after write.
- TDD discipline: test exists → test fails → code written → test passes. No code before tests.

**ASK FIRST boundaries (require human approval before changing):**
- Changing the canonical JSON serialization format (D10 Key Pattern 2; D1 ASK FIRST).
- Adding new EventType values.
- Changing the zero-padded key format in immudb (lexicographic order constraint).
- Changing the empty-tip sentinel format (D6 CLR-002).
- Multi-process deployment (would require replacing threading.Lock with server-side transaction, D5 RQ-001).

**NEVER:**
- Write directly to immudb without going through `ImmudbStore`.
- Create new primitives (assemble from the nine).
- Add business logic, payload interpretation, or routing to the Ledger — storage only.
- Write to `/Users/raymondbruni/dopejar/` directly — staging only.
- Read D9 (holdout scenarios).
- Use `asyncio.Lock()` — the model is synchronous.
- Use `os.getenv()` for config or secrets.
- Silence `LedgerConnectionError` or return a fallback value instead of raising.
- Return `ChainVerificationResult(valid=False)` when immudb is unreachable — that is a `LedgerConnectionError`, not a corruption result.

---

## Q4 — What are the APIs from D4?

Six inbound contracts, all confirmed from D4:

| Method | Signature | Returns | Source |
|--------|-----------|---------|--------|
| `append` | `append(event_data: dict) -> int` | sequence_number ≥ 0 | IN-001 |
| `read` | `read(sequence_number: int) -> LedgerEvent` | LedgerEvent or raises | IN-002 |
| `read_range` | `read_range(start: int, end: int) -> list[LedgerEvent]` | list (inclusive bounds) | IN-003 |
| `read_since` | `read_since(sequence_number: int) -> list[LedgerEvent]` | list (exclusive lower bound) | IN-004 |
| `verify_chain` | `verify_chain(start: int = 0, end: int | None = None) -> ChainVerificationResult` | result or raises | IN-005 |
| `get_tip` | `get_tip() -> TipRecord` | TipRecord or raises | IN-006 |

**Critical error contracts from D4:**
- `read(N)` where N > tip → `LedgerSequenceError` (IN-002 postcondition 2)
- `read(N)` where N < 0 → `LedgerSequenceError` (IN-002 postcondition 3)
- `read_range(start, end)` where end > tip → `LedgerSequenceError` (IN-003 postcondition 2)
- `read_since(N)` where N > tip → `LedgerSequenceError` (IN-004 postcondition 3)
- `read_since(tip)` → `[]` empty list (IN-004 postcondition 2)
- `verify_chain()` when immudb unreachable → **raises `LedgerConnectionError`** NOT `{valid: false}` (IN-005 postcondition 6 — this is a critical distinction)
- Concurrent `append()` → `LedgerSequenceError` (IN-001 Constraints)
- Invalid `event_type` or missing required field → `LedgerSerializationError` (raised before lock is acquired)

**ImmudbStore interface (internal):**
- `connect() -> None` — fails fast with `LedgerConnectionError` if "ledger" database doesn't exist
- `set(key: str, value: bytes) -> None` — mutex-protected write with 1-reconnect+1-retry
- `get(key: str) -> bytes` — raises `LedgerSequenceError` if key not found
- `scan(start_key: str, end_key: str) -> list[bytes]` — ascending order
- `get_count() -> int`

---

## Q5 — What are the file locations from D2/D3/D4?

**Source files (all CREATE, all new):**

| File | Path |
|------|------|
| errors.py | `staging/FMWK-001-ledger/ledger/errors.py` |
| models.py | `staging/FMWK-001-ledger/ledger/models.py` |
| schemas.py | `staging/FMWK-001-ledger/ledger/schemas.py` |
| serialization.py | `staging/FMWK-001-ledger/ledger/serialization.py` |
| store.py | `staging/FMWK-001-ledger/ledger/store.py` |
| verify.py | `staging/FMWK-001-ledger/ledger/verify.py` |
| api.py | `staging/FMWK-001-ledger/ledger/api.py` |
| __init__.py | `staging/FMWK-001-ledger/ledger/__init__.py` |
| __main__.py | `staging/FMWK-001-ledger/ledger/__main__.py` |

**Test files:**

| File | Path |
|------|------|
| conftest.py | `staging/FMWK-001-ledger/tests/conftest.py` |
| test_serialization.py | `staging/FMWK-001-ledger/tests/test_serialization.py` |
| test_store.py | `staging/FMWK-001-ledger/tests/test_store.py` |
| test_verify.py | `staging/FMWK-001-ledger/tests/test_verify.py` |
| test_api.py | `staging/FMWK-001-ledger/tests/test_api.py` |

**Sawmill outputs:**

| File | Path |
|------|------|
| RESULTS.md | `sawmill/FMWK-001-ledger/RESULTS.md` |
| builder_evidence.json | `sawmill/FMWK-001-ledger/builder_evidence.json` |
| README.md | `staging/FMWK-001-ledger/README.md` |

**[CRITICAL_REVIEW_REQUIRED]: platform_sdk.tier0_core.data is SQLAlchemy, not immudb.**

The spec (D10, BUILDER_HANDOFF.md) states: "ALL immudb access goes through `platform_sdk.tier0_core.data`" and the D10 architecture diagram labels it "gRPC abstraction + MockProvider." However, reading the actual `/Users/raymondbruni/dopejar/platform_sdk/tier0_core/data.py`, it is a SQLAlchemy 2.x async module with `get_engine()`, `get_session()`, `dispose_engine()` — zero immudb or gRPC capability. The existing `platform_sdk/tier0_core/ledger.py` (reference only, not to be copied) uses `from immudb import ImmudbClient` directly.

My assumed resolution: `store.py` will wrap `immudb-py` in a `ImmudbStore` class. Unit tests will use `MockImmudbStore` (an in-memory dict) injected via `conftest.py` fixture or dependency injection into `LedgerClient`. The constraint "NEVER import immudb in ledger/ modules" applies to all modules EXCEPT `store.py`, which is the explicit immudb abstraction boundary. The "MockProvider" referenced in test descriptions refers to `MockImmudbStore`, not `platform_sdk.tier0_core.data.MockProvider` (which does not exist for immudb).

If this interpretation is wrong, the reviewer should clarify before I proceed to implementation.

---

## Q6 — What are the data formats from D3?

**LedgerEvent (E-001) — 9 fields:**

| Field | Type | Source |
|-------|------|--------|
| event_id | str (UUID v7) | Assigned by Ledger via platform_sdk.tier0_core.ids |
| sequence | int (≥0) | Assigned by Ledger; genesis=0 |
| event_type | str (EventType enum) | Caller-supplied; validated against 15-value enum |
| schema_version | str (semver) | Caller-supplied (e.g., "1.0.0") |
| timestamp | str (ISO-8601 UTC+Z) | Caller-supplied (e.g., "2026-03-21T03:21:00Z") |
| provenance | Provenance | Caller-supplied; see E-002 |
| previous_hash | str ("sha256:"+64hex) | Assigned by Ledger from prior tip.hash |
| payload | dict (JSON-serializable) | Caller-supplied; event-type-specific |
| hash | str ("sha256:"+64hex) | Assigned by Ledger via canonical_hash() |

**Provenance (E-002) — 3 fields:**
- `framework_id: str` (required, e.g., "FMWK-002")
- `pack_id: Optional[str]` (optional, may be null)
- `actor: str` (required, enum: "system", "operator", "agent")

**TipRecord (E-003) — 2 fields:**
- `sequence_number: int` (-1 if empty Ledger sentinel)
- `hash: str` ("sha256:"+64zeros if empty Ledger sentinel)

**ChainVerificationResult (E-004) — 2 fields:**
- `valid: bool`
- `break_at: Optional[int]` (null when valid=True; lowest corrupted sequence when valid=False)

**EventType enum — 15 values (from D3/D4):**
node_creation, signal_delta, methylation_delta, suppression, unsuppression, mode_change, consolidation, work_order_transition, intent_transition, session_start, session_end, package_install, package_uninstall, framework_install, snapshot_created

**Critical data format rules:**
- Float values in payloads MUST be strings: `"0.1"`, not `0.1` (D5 RQ-003, D3 Canonical JSON Constraint)
- Null fields included in canonical JSON as `"field":null`, not omitted
- Keys in immudb: zero-padded to 20 chars (e.g., sequence 5 → `"00000000000000000005"`)
- Hash format: exactly `"sha256:"` + 64 lowercase hex chars, no uppercase, no "0x", no base64
- Empty Ledger sentinel: `TipRecord(sequence_number=-1, hash="sha256:0000000000000000000000000000000000000000000000000000000000000000")`

---

## Q7 — What are the manifest fields?

Package manifest (for RESULTS.md):
- `package_id`: `FMWK-001-ledger`
- `framework_id`: `FMWK-001`
- `version`: `1.0.0`
- `manifest_hash`: SHA-256 of the package manifest file, computed after all files are written; format "sha256:" + 64hex

RESULTS.md must include:
- Status (PASS / FAIL / PARTIAL)
- Files Created: path + SHA-256 for every file (computed via `shasum -a 256`)
- Test Results: full command + full pasted pytest stdout + counts (total/passed/failed/skipped)
- Full Regression: same format
- Baseline Snapshot: packages installed, test count at session start
- Clean-Room Verification steps
- Issues Encountered
- Notes for Reviewer
- Session Log

builder_evidence.json requires:
- `run_id` (from orchestrator)
- `attempt` (current attempt number)
- `handoff_hash` (provided by orchestrator — to be copied verbatim when available)
- `q13_answers_hash` (computed via `shasum -a 256` on 13Q_ANSWERS.md after writing)
- `results_hash` (computed via `shasum -a 256` on RESULTS.md after writing)
- Per-behavior red→green evidence
- Full test command + result
- Changed files list

**Note:** The orchestrator prompt for this turn did not inject explicit `handoff_hash` or `q13_answers_hash` values. These will be computed from the actual files at evidence-write time using `shasum -a 256`.

---

## Q8 — What are the dependencies?

**Python stdlib (permitted, no new installs):**
- `hashlib` — SHA-256 computation
- `json` — canonical JSON serialization
- `threading` — threading.Lock for single-writer mutex
- `dataclasses` — @dataclass for LedgerEvent, Provenance, TipRecord, ChainVerificationResult
- `typing` — Optional, List, etc.
- `time` — sleep in retry logic (1 second wait before reconnect)
- `sys` — CLI exit codes (0=valid, 1=invalid/error)
- `argparse` — CLI argument parsing in __main__.py

**Platform SDK (required, all covered concerns):**
- `platform_sdk.tier0_core.config` → `PlatformConfig`, `get_config()` — immudb connection params
- `platform_sdk.tier0_core.ids` → `new_id(kind="uuid7")` — UUID v7 event_id generation
- `platform_sdk.tier0_core.secrets` → `get_secret(key)` — immudb credentials (optional, PlatformConfig also carries them)
- `platform_sdk.tier0_core.logging` — structured logging
- `platform_sdk.tier0_core.metrics` — append/error/latency metrics

**External library (immudb-py — only in store.py, per Q5 CRITICAL_REVIEW_REQUIRED note):**
- `immudb-py` — immudb gRPC client for `ImmudbStore` real implementation

**Test tools:**
- `pytest` — test runner
- `PLATFORM_ENVIRONMENT=test` env var — activates MockProvider (MockImmudbStore)

---

## Q9 — Testing

**Mandatory minimum:** 40 tests (≥6 source files rule from D8 Section 6)
**Target:** ≥55 tests

**Distribution from D8 Test Plan:**
- `test_serialization.py`: ≥8 tests (canonical_json + canonical_hash test vectors)
- `test_store.py`: ≥10 tests (ImmudbStore unit tests, all using MockImmudbStore)
- `test_verify.py`: ≥8 tests (walk_chain unit tests against constructed LedgerEvent lists)
- `test_api.py`: ≥35 tests broken down as:
  - get_tip(): ≥4 tests
  - append(): ≥10 tests (including SC-001, SC-002, SC-010, SC-011)
  - read(): ≥4+1=5 tests (includes connection error case per D4)
  - read_range(): ≥4 tests
  - read_since(): ≥3 tests
  - verify_chain(): ≥8 tests

**Total confirmable from test plan:** 8 + 10 + 8 + (4 + 10 + 5 + 4 + 3 + 8) = 8 + 10 + 8 + 34 = 60 explicitly named tests (exceeds ≥55 target)

**Verification criteria:**
- `PLATFORM_ENVIRONMENT=test pytest tests/ -v` → all pass, zero failures
- `PLATFORM_ENVIRONMENT=test pytest tests/ --collect-only | tail -5` → N ≥ 55 collected
- `grep -r "import immudb" ledger/` → zero matches (except potentially store.py per Q5 flag)
- `grep -r "import uuid" ledger/` → zero matches (ids go through platform_sdk)

**TDD discipline:** For each behavior — test exists (RED) → implementation (GREEN) → refactor. Integration tests marked `@pytest.mark.integration`; not required for unit test run.

---

## Q10 — Integration

**Upstream caller (Write Path FMWK-002):**
- Calls `LedgerClient.append(event_data)` for every state mutation
- `LedgerClient` is initialized with `PlatformConfig` — the Write Path will construct one and pass it in
- `LedgerClient.connect()` must be called before any method; fails fast if immudb "ledger" DB absent

**Downstream consumers:**
- FMWK-005 Graph: calls `read()`, `read_range()`, `read_since()` for replay on startup
- FMWK-006 Package Lifecycle: calls `verify_chain()` post-install and `get_tip()` for chain walk start

**Platform SDK wiring:**
- `PlatformConfig` provides: `immudb_host`, `immudb_port`, `immudb_database`, `immudb_username`, `immudb_password`
- `new_id(kind="uuid7")` called in `append()` to generate `event_id`
- `get_secret()` available if credentials need runtime retrieval (PlatformConfig defaults cover local dev)

**CLI integration:**
- `python -m ledger --verify` connects to immudb directly via `ImmudbStore` with NO kernel process running
- Output: `{"valid": bool, "break_at": int|null, "tip": {"sequence_number": int, "hash": "sha256:..."}}` to stdout
- Exit code 0 = valid, exit code 1 = invalid or error

**immudb wiring:**
- Database: "ledger" (must exist before connect(); fail fast if absent per D6 CLR-001)
- Port: 3322 (gRPC) — from `config.immudb_port`
- Key format: `f"{sequence:020d}"` (20-char zero-padded sequence)
- Value: `canonical_json(full_event_dict).encode("utf-8")`

---

## Q11 — Adversarial: Most Likely Architectural Misinterpretation

**SC-011 concurrent append mutex scope.**

The test `test_append_concurrent_no_fork` expects: "two threads append simultaneously → exactly one succeeds, one raises `LedgerSequenceError`; `get_tip().sequence_number` incremented by exactly 1."

The critical path in BUILDER_HANDOFF Section 3 says: acquire `store._lock` at step 2 (before `get_tip()`), release at step 12 (after `store.set()` returns). The ENTIRE sequence read-tip → compute-seq → write must be atomic under the lock.

The misinterpretation risk: placing the lock only around `store.set()` (just the write) but not around the read-tip step. This allows two concurrent callers to both call `get_tip()`, both get sequence N, both compute next = N+1, and both try to write to key N+1. The second writer would succeed (no conflict at immudb level) and produce a fork — two different events at the same sequence. This breaks the chain silently.

**My implementation will:** acquire `store._lock` at the start of `append()` before calling `get_tip()`, and not release until after `store.set()` returns (or raises). This is explicitly called out in D10 Key Pattern 1: "This prevents two concurrent callers from computing the same next sequence number."

---

## Q12 — Adversarial: Most Likely Postcondition Misimplementation

**`verify_chain()` when immudb is unreachable.**

D4 IN-005 postcondition 6 (quoted exactly): "If immudb unreachable: raises LedgerConnectionError (ERR-001). Does NOT return {valid:false} — an unreachable immudb is an infrastructure failure, not a corruption."

The intuitive but wrong implementation returns `ChainVerificationResult(valid=False, break_at=None)` or `ChainVerificationResult(valid=False, break_at=0)` when immudb is down. This is incorrect — it conflates infrastructure failure with data corruption, and would mislead callers into thinking the chain is broken when it's actually just inaccessible.

**Secondary risk:** `read_since(N)` exclusive vs inclusive boundary. D4 IN-004 postcondition 1: "Returns all events with sequence > sequence_number." This is an EXCLUSIVE lower bound — `read_since(5)` returns sequences 6, 7, 8, ... not 5, 6, 7, .... The test `test_read_since_returns_events_after_sequence` explicitly verifies `read_since(5)` with tip at 10 returns sequences [6,7,8,9,10].

**My implementation will:** in `verify_chain()`, propagate `LedgerConnectionError` from `read_range()` directly — do NOT catch it and convert to a `ChainVerificationResult`. In `read_since(N)`, the first returned event has `sequence = N + 1`.

---

## Q13 — Adversarial: What Will the Evaluator Probe?

Based on the D9 isolation rules (D9 not shown to builders), the evaluator independently generated holdout scenarios from D2+D4. The most likely adversarial probes given the contract specifications:

1. **Empty Ledger sentinel exact format:** Does `get_tip()` return `TipRecord(sequence_number=-1, hash="sha256:" + "0" * 64)`? The evaluator will check: not `sequence_number=0`, not `None`, not a raised exception, and the hash is exactly 71 chars (`"sha256:"` + 64 zeros, not shorter).

2. **Null field canonical hash:** Does `canonical_hash({"event_type": "x", "payload": null})` produce a different value than `canonical_hash({"event_type": "x"})`? D3 Canonical JSON Constraint: "Null fields are included in serialization as `field:null`, not omitted." The evaluator will test that omitting a field vs setting it to null gives different hashes.

3. **Float string vs float number hash:** `canonical_hash({"val": "0.1"})` ≠ `canonical_hash({"val": 0.1})`. D5 RQ-003. The evaluator will verify these produce different digests.

4. **`read_since(tip)` returns `[]`:** Not a `LedgerSequenceError`, not a single-item list. Confirmed by D4 IN-004 postcondition 2. Evaluator will test the boundary condition explicitly.

5. **Chain corruption vs connection failure in verify_chain():** The evaluator will likely test that a mocked connection failure raises `LedgerConnectionError` rather than returning a `ChainVerificationResult`. See Q12.

6. **Atomicity on failure:** After a failed `append()` (immudb down), `get_tip()` returns the SAME value as before the failed append. The evaluator will test this by: (1) appending to create tip at seq 0, (2) forcing immudb to fail, (3) attempting another append (raises `LedgerConnectionError`), (4) verifying `get_tip()` still returns seq 0.

7. **Inclusive bounds on `read_range()`:** `read_range(3, 7)` returns exactly 5 events [seq 3, 4, 5, 6, 7], not 4. D6 CLR-004 resolved this as INCLUSIVE on both ends.

8. **CLI exit code:** `python -m ledger --verify` exits with code 0 on valid chain, code 1 on corruption or connection error. The evaluator may test both paths.
