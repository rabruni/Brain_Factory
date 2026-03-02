# 13Q Gate Answers — FMWK-001-ledger

Builder Agent: H-1 | Prompt Contract Version: 1.0.0 | Date: 2026-03-01

---

## Scope Questions

### Q1: What are you building?

I am building FMWK-001-ledger — the append-only, hash-chained event store for DoPeJarMo. All 16 files:

| # | File | Purpose |
|---|------|---------|
| 1 | `staging/FMWK-001-ledger/ledger/__init__.py` | Package exports: Ledger, LedgerConfig, LedgerEvent, LedgerTip, VerifyChainResult, Ledger*Error |
| 2 | `staging/FMWK-001-ledger/ledger/errors.py` | 4 error classes (ERR-001..004) inheriting platform_sdk base |
| 3 | `staging/FMWK-001-ledger/ledger/schemas.py` | Frozen dataclasses: E-001 (LedgerEvent), E-003 (LedgerTip), E-004 (VerifyChainResult), E-005 (SnapshotCreatedPayload), E-006 (NodeCreationPayload), E-007 (SessionStartPayload, SessionEndPayload), E-008 (PackageInstallPayload), E-009 (EVENT_TYPE_CATALOG frozenset of 15 types), plus `LedgerConfig.from_env()` for `IMMUDB_HOST`, `IMMUDB_PORT`, `IMMUDB_DATABASE` |
| 4 | `staging/FMWK-001-ledger/ledger/serializer.py` | `compute_hash()`, `check_no_floats()`, `canonical_bytes()`, `GENESIS_SENTINEL` constant |
| 5 | `staging/FMWK-001-ledger/ledger/ledger.py` | Ledger class — 7 public methods (connect, append, read, read_range, read_since, get_tip, verify_chain) with threading.Lock mutex |
| 6 | `staging/FMWK-001-ledger/platform_sdk/tier0_core/data/immudb_adapter.py` | ImmudbAdapter Protocol + MockImmudbAdapter + RealImmudbAdapter + get_adapter() |
| 7 | `staging/FMWK-001-ledger/platform_sdk/tier0_core/data/__init__.py` | Exports for the immudb adapter (additive only; no existing file modified) |
| 8 | `staging/FMWK-001-ledger/tests/__init__.py` | Test package marker |
| 9 | `staging/FMWK-001-ledger/tests/unit/__init__.py` | Unit test package marker |
| 10 | `staging/FMWK-001-ledger/tests/unit/test_serializer.py` | 12 tests — canonical serializer contract |
| 11 | `staging/FMWK-001-ledger/tests/unit/test_ledger_unit.py` | 33 tests — all scenarios via MockProvider |
| 12 | `staging/FMWK-001-ledger/tests/integration/__init__.py` | Integration test package marker |
| 13 | `staging/FMWK-001-ledger/tests/integration/test_ledger_integration.py` | 6 integration tests — Docker immudb on :3322 |
| 14 | `staging/FMWK-001-ledger/tests/integration/test_cold_storage.py` | 2 cold-storage tests — SC-005 offline verify |
| 15 | `staging/FMWK-001-ledger/scripts/static_analysis.sh` | 4-check static analysis gate |
| 16 | `sawmill/FMWK-001-ledger/RESULTS.md` | Builder results file with SHA-256 hashes per BUILDER_HANDOFF_STANDARD.md |

Total: 16 files. All in `staging/FMWK-001-ledger/`. Zero modifications to existing files. Zero writes to the governed filesystem.

---

### Q2: What am I explicitly NOT building?

Per D2 Deferred Capabilities and D8 deferred scope:

1. **DEF-001 — Payload schema validation for deferred event types.** I will NOT validate payloads for the 10 event types owned by other frameworks (signal_delta, methylation_delta, suppression, unsuppression, mode_change, consolidation, work_order_transition, intent_transition, package_uninstall, framework_install). The Ledger validates base schema only. Payload validation is a pluggable extension point for when those frameworks register their schemas.

2. **DEF-002 — Paginated range read.** I will NOT implement `read_range(start, end, page_size, page_token)`. The unpaginated form is sufficient for KERNEL phase.

3. **NOT building any fold logic, signal accumulation, gate validation, Graph update logic, work order management, or snapshot format.** These belong to FMWK-002 through FMWK-006 respectively (D1 Article 2 — MERGING prohibition).

4. **NOT building a query engine.** No filtering, sorting, full-text search, or semantic retrieval (D2 NOT section).

5. **NOT building pub/sub or message queue capabilities** (D2 NOT section).

6. **NOT building the GENESIS ceremony** that creates the immudb `ledger` database. `connect()` assumes the database already exists (D1 Article 9).

---

### Q3: What is the very first test I will write, and what does it test?

Per D8 T-003 (canonical serializer task), the first tests written will be in `tests/unit/test_serializer.py`. The DTT cycle dictates I write these 12 tests BEFORE implementing `serializer.py`. The very first test I will write is:

**`test_genesis_sentinel_exact_string`** — asserts `GENESIS_SENTINEL == "sha256:" + "0" * 64` using exact string comparison (not regex). This is the simplest test to start with: it tests a constant value and will fail immediately because the module doesn't exist yet. This confirms the DTT red phase works correctly (import error / NameError, not a silent pass).

All 12 serializer tests should fail in the red phase with "not found" type errors (ModuleNotFoundError or ImportError), not assertion errors, confirming the test infrastructure is correct before implementation begins.

---

## Technical Questions

### Q4: What exact Python call produces the canonical JSON for hash computation?

```python
json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
```

Where `obj` is a copy of the event dict with the `hash` key removed entirely. The result is then encoded to UTF-8 bytes (no BOM) and fed to `hashlib.sha256()`. The hexdigest is prefixed with `"sha256:"`.

Complete hash computation:
```python
import copy, json, hashlib

def canonical_bytes(event: dict) -> bytes:
    obj = {k: v for k, v in event.items() if k != "hash"}
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode("utf-8")

def compute_hash(event: dict) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(event)).hexdigest()
```

---

### Q5: What is the genesis sentinel value?

```
sha256:0000000000000000000000000000000000000000000000000000000000000000
```

That is exactly 71 characters: the 7-character prefix `sha256:` followed by 64 lowercase hex zero digits. Verified by: `"sha256:" + "0" * 64`.

---

### Q6: What is the immudb key format for sequence number 7?

```
000000000007
```

That is exactly 12 characters: a 12-digit zero-padded decimal string. Produced by: `f"{7:012d}"`.

---

## Packaging Questions

### Q7: Which existing platform_sdk files will I MODIFY? Which will I only CREATE new alongside?

**Modified: ZERO.** No existing platform_sdk file is modified or replaced. This is Critical Constraint #4 in the handoff.

**Created (additive only):**
- `staging/FMWK-001-ledger/platform_sdk/tier0_core/data/immudb_adapter.py` — NEW file
- `staging/FMWK-001-ledger/platform_sdk/tier0_core/data/__init__.py` — NEW file (staging-only package shim; does not replace any existing file in the live platform_sdk)

All new files are in the staging directory. They will be contributed to the real platform_sdk during GENESIS installation, not during this build.

---

### Q8: What environment variable selects MockImmudbAdapter vs RealImmudbAdapter?

`PLATFORM_DATA_BACKEND`

- `PLATFORM_DATA_BACKEND=mock` → `MockImmudbAdapter` (for all unit tests; no Docker needed)
- `PLATFORM_DATA_BACKEND=immudb` → `RealImmudbAdapter` (for integration tests; Docker immudb on :3322)

The `get_adapter()` function reads this env var and returns the corresponding adapter instance.

---

## Verification Question

### Q9: How many tests total? Breakdown by file?

**53 tests total.**

| File | Test Count | Docker Required |
|------|-----------|----------------|
| `tests/unit/test_serializer.py` | 12 | No |
| `tests/unit/test_ledger_unit.py` | 33 | No |
| `tests/integration/test_ledger_integration.py` | 6 | Yes |
| `tests/integration/test_cold_storage.py` | 2 | Yes |
| **Total** | **53** | |

Unit tests: 45 (12 + 33). Integration tests: 8 (6 + 2).

The packet is internally aligned on 33 tests in `test_ledger_unit.py`, 12 in `test_serializer.py`, and 53 total tests (45 unit + 8 integration).

---

## Integration Question

### Q10: After a caller appends an event, how does FMWK-002 (write-path) consume it?

FMWK-002 (write-path) is the primary consumer. The interaction is:

1. **On write:** FMWK-002 calls `Ledger.append(event)` (D4 IN-001). The Ledger returns the assigned `sequence_number` as an `int` (D4 OUT-001). FMWK-002 uses this to confirm the write position and proceed with fold logic.

2. **On replay (Graph reconstruction after snapshot):** FMWK-002 calls `Ledger.read_since(snapshot_sequence)` (D4 IN-004). The Ledger returns all events after the snapshot position as `list[LedgerEvent]` in strictly ascending order (D4 OUT-002). FMWK-002 replays these through fold logic to rebuild the Graph.

3. **On tip check (atomicity):** FMWK-002 may call `Ledger.get_tip()` (D4 IN-006) to check the current write position (D4 OUT-004), though this is primarily used internally by the Ledger's own `append()` mutex mechanism.

The key contract: FMWK-002 supplies events WITHOUT `sequence`, `previous_hash`, or `hash` (D4 IN-001 constraints). The Ledger assigns all three internally. FMWK-002 receives back the immutable, hash-chained event and folds it into the Graph — the Ledger never interprets events.

---

## Adversarial Questions (Genesis Set)

### Q11 (Dependency Trap): Which piece of your implementation depends on something that does not yet exist in the dopejar_sdk repo, and how will you handle that gap?

**The entire `platform_sdk` dependency chain does not exist in my working scope.**

The dopejar_sdk repository (where `platform_sdk` lives, per AGENT_BOOTSTRAP.md) is a separate repository from Brain_Factory. The handoff directs me to work in `staging/FMWK-001-ledger/` relative to the dopejar_sdk repo root, but my current workspace is Brain_Factory. Specific dependencies that may not exist:

1. **`platform_sdk.tier0_core.errors` base class** — My error classes must inherit from this base. If the base class doesn't exist or has a different API than I assume, my inheritance chain breaks.

2. **`platform_sdk.tier0_core.config`** — `connect()` reads config through this. If the module's `get_config()` signature differs, my connect implementation breaks.

3. **`platform_sdk.tier0_core.secrets`** — Same risk for `get_secret()`.

4. **`platform_sdk.tier0_core.logging`** — Same risk for `get_logger()`.

5. **`immudb-py` package** — `RealImmudbAdapter` wraps the immudb Python SDK. If the package API has changed or is not installed, the real adapter won't work (unit tests are unaffected since they use MockProvider).

**How I will handle this:**

- For unit tests (45 of 53): I will create local stubs/mocks of the platform_sdk modules within the staging directory. The MockImmudbAdapter is self-contained (dict-backed). Unit tests never touch real platform_sdk or immudb.
- For the immudb adapter: `MockImmudbAdapter` requires zero external dependencies. `RealImmudbAdapter` will import from the actual `immudb` package — this is tested only in integration tests with Docker.
- For error inheritance: I will follow the Platform SDK pattern (Protocol + MockProvider + RealProvider). If the actual base class isn't accessible, I'll define a minimal base in the staging scope that follows the documented pattern, and flag it for review.

`[CRITICAL_REVIEW_REQUIRED]`: The handoff says work happens in `staging/FMWK-001-ledger/` relative to `dopejar_sdk` repo root, but I am in `Brain_Factory`. I need clarification on whether (a) I should clone/access `dopejar_sdk` separately, (b) work in Brain_Factory's `staging/` directory with local platform_sdk stubs, or (c) the dopejar_sdk repo should be available somewhere on this machine. My assumption: I will work in Brain_Factory for now — creating `staging/FMWK-001-ledger/` here — and stub platform_sdk dependencies locally. The code should be portable to dopejar_sdk once that repo is available.

---

### Q12 (Scope Creep Check): What is the one thing closest to being in scope that I am explicitly prohibited from building, and why is it out of scope?

**DEF-001 — Payload schema validation for deferred event types.**

This is the closest to being in scope because:
- I AM already validating `event_type` against `EVENT_TYPE_CATALOG` (15 types) at `append()` time
- I AM already defining payload schemas for 5 event types owned by FMWK-001 (E-005 through E-008)
- It would be natural to also validate that each event's `payload` conforms to its declared schema at append time

**Why it's out of scope:** 10 of the 15 event types have payloads owned by other frameworks (FMWK-002 owns signal_delta, FMWK-003 owns work_order_transition, etc.). Those frameworks don't exist yet. If I validated payloads now, I would either:
- Need to import schemas from frameworks that haven't been built (violating D1 Article 1 — SPLITTING)
- Need to hardcode schema shapes that those frameworks should own (violating D1 Article 3 — OWNERSHIP)

The Ledger validates the envelope (base schema). Payload validation is pluggable (DEF-001) — it becomes possible only when each framework registers its payload schema. Building it now would couple FMWK-001 to frameworks that don't exist, breaking independent authorship.

---

### Q13 (Semantic Audit): What does "atomic" mean in each context?

The word "atomic" appears in two distinct contexts in the spec:

**Context 1 — Mutex atomicity (CLR-001, D5 RQ-001):**
"Atomic" means that the read-then-write sequence in `append()` — (1) read the current tip, (2) compute new sequence, (3) write the event — executes as an indivisible unit with respect to **other threads in the same Python process**. The `threading.Lock()` ensures no two threads can interleave these steps. If thread A reads tip and thread B also reads tip before A writes, both would compute the same sequence number — the mutex prevents this. This is **process-local concurrency control**. It does NOT protect against two separate OS processes calling append simultaneously.

**Context 2 — immudb gRPC call atomicity (D4 SIDE-001, D2 SC-EC-003):**
"Atomic" means that a single `kv_set` gRPC call to immudb either completes fully (the key-value pair is durably written and acknowledged) or fails entirely (no partial write exists). This is **storage-layer transactional atomicity** — it's a property of the immudb server and gRPC protocol, not of our code. If the gRPC call fails mid-flight, immudb guarantees no half-written entry exists.

**Are the two guarantees the same?** No. They are complementary but distinct:
- The mutex guarantees **sequence correctness** within a single process (no duplicate sequences from interleaved reads)
- The gRPC atomicity guarantees **write integrity** at the storage level (no partial events in immudb)

Both are necessary. Without the mutex, two threads could assign the same sequence. Without gRPC atomicity, a network failure could leave a half-written event in immudb that corrupts the chain.

The combined guarantee is: at most one thread computes a sequence at a time (mutex), and each computed sequence is either fully written or not written at all (gRPC atomicity). The `LedgerSequenceError` is the safety net if the mutex guarantee is somehow violated.

`[CRITICAL_REVIEW_REQUIRED]`: The mutex provides no cross-process protection. If two separate Python processes both instantiate Ledger and call append(), they would have independent mutexes and could race. The spec says this cannot happen because BUILDER_SPEC.md declares single-writer architecture (exactly one FMWK-002 Write Path process). I'm assuming this architectural guarantee holds — if it doesn't, the mutex is insufficient and we need Option A (immudb ExecAll). My implementation follows D5 RQ-001's decision: Option B (in-process mutex), with the understanding that multi-writer is a design violation caught by `LedgerSequenceError`.

---

## STOP

I have answered all 13 questions. I am NOT writing any code, creating any directories, or making any plans until I receive explicit human greenlight.
