# 13Q Answers — FMWK-001-ledger (Turn D, H-1)

## Q1 — What am I building?
I am building exactly these 16 files from the handoff Files Summary:

1. `staging/FMWK-001-ledger/ledger/__init__.py` (CREATE)
2. `staging/FMWK-001-ledger/ledger/errors.py` (CREATE)
3. `staging/FMWK-001-ledger/ledger/schemas.py` (CREATE)
4. `staging/FMWK-001-ledger/ledger/serializer.py` (CREATE)
5. `staging/FMWK-001-ledger/ledger/ledger.py` (CREATE)
6. `staging/FMWK-001-ledger/platform_sdk/tier0_core/data/__init__.py` (CREATE)
7. `staging/FMWK-001-ledger/platform_sdk/tier0_core/data/immudb_adapter.py` (CREATE)
8. `staging/FMWK-001-ledger/tests/__init__.py` (CREATE)
9. `staging/FMWK-001-ledger/tests/unit/__init__.py` (CREATE)
10. `staging/FMWK-001-ledger/tests/unit/test_serializer.py` (CREATE)
11. `staging/FMWK-001-ledger/tests/unit/test_ledger_unit.py` (CREATE)
12. `staging/FMWK-001-ledger/tests/integration/__init__.py` (CREATE)
13. `staging/FMWK-001-ledger/tests/integration/test_ledger_integration.py` (CREATE)
14. `staging/FMWK-001-ledger/tests/integration/test_cold_storage.py` (CREATE)
15. `staging/FMWK-001-ledger/scripts/static_analysis.sh` (CREATE)
16. `sawmill/FMWK-001-ledger/RESULTS.md` (CREATE at finalize step)

## Q2 — What am I explicitly NOT building?
I am explicitly NOT building:

1. D2 Deferred + D8 Deferred scope:
   - `DEF-001` payload schema validation for deferred event types (owned by other frameworks).
   - `DEF-002` paginated range read (`read_range(..., page_size, page_token)`).
2. Any query-engine behavior (filtering/sorting/full-text/semantic retrieval).
3. Any message-queue behavior (pub/sub, consumer groups, push delivery semantics).
4. Any Graph fold/reconstruction logic (owned by FMWK-002/FMWK-005).
5. Snapshot file-format ownership (Ledger only records snapshot events).
6. Any governed filesystem install activity (staging-only authoring).
7. Any immudb admin/provisioning operations in Ledger path (`CreateDatabaseV2`, delete/compact/truncate ops).

[CRITICAL_REVIEW_REQUIRED]: D2 says deferred payload validation covers 11 of 15 event types, while D8 says 10 event types; I am treating the intent as "defer cross-framework payload schema validation entirely" despite the count mismatch.

## Q3 — First test to write (from T-003)
`test_canonical_json_excludes_hash_field` in `tests/unit/test_serializer.py`.
It verifies `canonical_bytes()` removes the `hash` field before serialization so hash computation input never self-includes `hash`.

[CRITICAL_REVIEW_REQUIRED]: T-003 defines a set of 12 tests but does not enforce strict internal ordering; I am assuming the first listed serializer test is acceptable as the first authored test.

## Q4 — Exact canonical JSON call
`json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`

## Q5 — Genesis sentinel exact value
`sha256:0000000000000000000000000000000000000000000000000000000000000000`

## Q6 — immudb key format for sequence 7
`000000000007`

## Q7 — platform_sdk files modified vs newly created
- Existing `platform_sdk` files modified: **none**.
- New files created alongside staging SDK shim:
  - `staging/FMWK-001-ledger/platform_sdk/tier0_core/data/__init__.py`
  - `staging/FMWK-001-ledger/platform_sdk/tier0_core/data/immudb_adapter.py`

## Q8 — Env var selecting mock vs real adapter
`PLATFORM_DATA_BACKEND`
- `mock` => `MockImmudbAdapter`
- `immudb` => `RealImmudbAdapter`

## Q9 — Total tests and breakdown
Total: **53**
- `tests/unit/test_serializer.py`: 12
- `tests/unit/test_ledger_unit.py`: 33
- `tests/integration/test_ledger_integration.py`: 6
- `tests/integration/test_cold_storage.py`: 2

Unit total: 45. Integration total: 8.

## Q10 — How FMWK-002 consumes appended events
FMWK-002 consumes Ledger events via `read_since(sequence_number)` for replay/reconstruction after snapshots, implementing D4 `IN-004` (read_since contract).  
FMWK-002 also writes mutations through `append(event)` under D4 `IN-001`.

[CRITICAL_REVIEW_REQUIRED]: The question wording ("after a caller appends") could be interpreted as either write invocation (`append` / IN-001) or downstream replay consumption (`read_since` / IN-004); I interpreted "consume" as replay/read path.

## Q11 — Dependency trap
The Real immudb path depends on runtime infrastructure not authored inside this Brain_Factory staging packet: running immudb service + pre-created `ledger` database from GENESIS/FMWK-000, and live SDK availability at `/Users/raymondbruni/dopejar/platform_sdk/`.

Handling:
1. Unit tests use `MockImmudbAdapter` only (`PLATFORM_DATA_BACKEND=mock`).
2. Integration tests bind to Docker immudb from `/Users/raymondbruni/dopejar/docker-compose.yml`.
3. `connect()` fails fast with `LedgerConnectionError` if `ledger` DB is missing (no create/provision fallback).

[CRITICAL_REVIEW_REQUIRED]: Assumes GENESIS has already provisioned the `ledger` database expected by D1 Article 9 and SC-EC-004; if GENESIS has not run, integration behavior is fail-fast by design.

## Q12 — Closest scope-creep item that is prohibited
Auto-provisioning the immudb database in `connect()` (e.g., `CreateDatabaseV2`) is closest to scope but explicitly prohibited.

Why out of scope:
1. D1 Article 9 infrastructure separation (GENESIS provisions, Ledger connects).
2. D8 + constraints require zero admin ops in FMWK-001 code.
3. Connect must raise `LedgerConnectionError` immediately if DB is absent.

## Q13 — Meaning of “atomic” in mutex vs gRPC write
`Atomic` in mutex context: process-local critical section around "read tip -> assign sequence/hash -> kv_set", preventing interleaving between concurrent threads in the same process.

`Atomic` in immudb gRPC context: a single write call is all-or-nothing at storage operation level (no partial persisted event on failed call).

They are not the same guarantee:
1. Mutex atomicity is concurrency ordering/serialization in the client process.
2. gRPC/immudb atomicity is storage commit integrity per operation.
3. Both are required; neither replaces the other.

[CRITICAL_REVIEW_REQUIRED]: This answer assumes single-writer process semantics from CLR-001; a distributed multi-writer deployment would need additional cross-process coordination not in current scope.
