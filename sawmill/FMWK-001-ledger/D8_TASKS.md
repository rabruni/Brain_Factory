# D8: Tasks — FMWK-001-ledger
Meta: plan: D7 1.0.0 | status:Final | total tasks:8 | parallel opportunities:2

## MVP Scope
In scope: all D2 Primary and Edge Case scenarios SC-001 through SC-011. No D2 deferred capability is included beyond the approved minimum payload schemas and the ledger-owned `snapshot_created` reference event. Deferred items remain DEF-001 and DEF-002.

## Tasks (T-### IDs, phased)
### T-001
- Phase + name: 0 Foundation | Create package skeleton and typed ledger models
- Parallel/Serial: Serial
- Dependency: None
- Scope: S
- Scenarios Satisfied: D2 SC-003, SC-006, SC-007
- Contracts Implemented: D4 OUT-001, OUT-004, OUT-005
- Acceptance Criteria:
  1. Create `ledger/__init__.py`, `ledger/errors.py`, and `ledger/models.py`.
  2. `models.py` defines structures matching D3 E-001 through E-009, including full `FMWK-NNN-name` provenance storage and `sha256:` hash-string constraints.
  3. `errors.py` defines explicit framework errors for `LEDGER_CONNECTION_ERROR`, `LEDGER_CORRUPTION_ERROR`, `LEDGER_SEQUENCE_ERROR`, and `LEDGER_SERIALIZATION_ERROR`.
  4. Add at least 4 unit tests proving model construction and error-code mapping.

### T-002
- Phase + name: 0 Foundation | Implement payload catalog and append request validation
- Parallel/Serial: Parallel with T-003 after T-001
- Dependency: T-001 (typed models must exist before validation logic)
- Scope: M
- Scenarios Satisfied: D2 SC-003, SC-007, SC-011
- Contracts Implemented: D4 IN-001, ERR-004
- Acceptance Criteria:
  1. Create `ledger/schemas.py` with validation for approved event types only: `node_creation`, `signal_delta`, `package_install`, `session_start`, `snapshot_created`.
  2. Validation rejects caller-supplied `sequence`, `previous_hash`, and `hash`.
  3. Validation preserves D6 assumptions by refusing unsupported future payload schemas rather than inferring them.
  4. Add at least 6 tests covering valid append requests, snapshot marker payload shape, and serialization-relevant rejection cases.

### T-003
- Phase + name: 0 Foundation | Implement canonical serialization and hash helpers
- Parallel/Serial: Parallel with T-002 after T-001
- Dependency: T-001 (model shapes and errors are required first)
- Scope: M
- Scenarios Satisfied: D2 SC-001, SC-002, SC-005, SC-008, SC-011
- Contracts Implemented: D4 SIDE-002, IN-005, ERR-004
- Acceptance Criteria:
  1. Create `ledger/serialization.py` with `canonical_event_bytes(...)` and `compute_event_hash(...)`.
  2. Serialization uses sorted keys, separators `,` and `:`, UTF-8, `ensure_ascii=False`, includes nulls, excludes the `hash` field, and forbids base-envelope floats.
  3. Define the exact zero-hash genesis constant and `sha256:<64 lowercase hex>` formatting helper.
  4. Add at least 8 fixture tests proving byte-for-byte canonical output and exact hash equality.

### T-004
- Phase + name: 1 Core Logic | Build append/read/tip storage boundary
- Parallel/Serial: Serial
- Dependency: T-002 and T-003 (validated requests and canonical hashing must exist)
- Scope: L
- Scenarios Satisfied: D2 SC-001, SC-002, SC-004, SC-006, SC-009, SC-010, SC-011
- Contracts Implemented: D4 IN-001, IN-002, IN-003, IN-004, IN-006, OUT-001, OUT-002, OUT-003, OUT-005, SIDE-001, SIDE-003, ERR-001, ERR-003, ERR-004
- Acceptance Criteria:
  1. Create `ledger/store.py` with methods `append_event(...)`, `read(...)`, `read_range(...)`, `read_since(...)`, and `get_tip(...)`.
  2. Append logic assigns `sequence=0` and zero `previous_hash` for genesis, then strictly increments from tip thereafter.
  3. The append critical section uses the D5-selected in-process mutex so tip-read plus write remains atomic within the single-writer model.
  4. Storage code reads config/secrets/logging through `platform_sdk` surfaces and does not expose direct immudb access to callers.
  5. Connection handling retries once after a 1-second reconnect delay and surfaces `LEDGER_CONNECTION_ERROR` on final failure.
  6. Add at least 10 tests covering first append, next append, ordered reads, read-since behavior, get-tip accuracy, connection failure, and sequence-race rejection.

### T-005
- Phase + name: 1 Core Logic | Build online and offline verification path
- Parallel/Serial: Serial
- Dependency: T-003 and T-004 (canonical hashing and ordered reads are required)
- Scope: M
- Scenarios Satisfied: D2 SC-005, SC-008, SC-011
- Contracts Implemented: D4 IN-005, OUT-004, SIDE-004, ERR-002, ERR-004
- Acceptance Criteria:
  1. Create `ledger/verify.py` with `verify_chain(...)` and a shared `verify_events(...)` helper for online/offline parity.
  2. Verification recomputes hashes in order, compares `previous_hash` linkage, and returns the first failing sequence as `break_at`.
  3. Offline verification accepts exported event data only and does not depend on Graph, HO1, HO2, or kernel services.
  4. Add at least 6 tests covering intact chain verification, corruption at an interior sequence, and online/offline result equivalence.

### T-006
- Phase + name: 2 Integration | Wire the public Ledger facade
- Parallel/Serial: Serial
- Dependency: T-004 and T-005 (all internals must exist first)
- Scope: M
- Scenarios Satisfied: D2 SC-001 through SC-011
- Contracts Implemented: D4 IN-001 through IN-006, OUT-001 through OUT-005, ERR-001 through ERR-004
- Acceptance Criteria:
  1. Create `ledger/api.py` exposing `class Ledger` with methods `append`, `read`, `read_range`, `read_since`, `verify_chain`, and `get_tip`.
  2. The facade remains orchestration-free and delegates validation, persistence, and verification to the underlying modules without introducing business logic.
  3. Add at least 5 API-level tests covering approved event append flows and failure propagation.

### T-007
- Phase + name: 2 Integration | Add staged package documentation and operator commands
- Parallel/Serial: Parallel with T-008 after T-006
- Dependency: T-006 (commands must reflect the implemented surface)
- Scope: S
- Scenarios Satisfied: D2 SC-004, SC-005, SC-006
- Contracts Implemented: D4 IN-002, IN-003, IN-004, IN-005, IN-006
- Acceptance Criteria:
  1. Create `README.md` in the framework staging root with package purpose, public methods, and exact local `pytest` commands.
  2. Document that runtime database creation is out of scope and connection failure is fail-fast.
  3. Include the offline verification command shape used in tests.

### T-008
- Phase + name: 3 Validation | Run full ledger regression and record evidence
- Parallel/Serial: Parallel with T-007 after T-006
- Dependency: T-006 (full implementation must exist)
- Scope: M
- Scenarios Satisfied: D2 SC-001 through SC-011
- Contracts Implemented: all D4 contracts via regression evidence
- Acceptance Criteria:
  1. Execute the full staged framework test suite with `PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests`.
  2. Capture command output in `sawmill/FMWK-001-ledger/RESULTS.md` with per-file SHA256s and regression totals as required by the handoff standard.
  3. Verify every P1 scenario SC-003, SC-004, SC-005, SC-006, SC-007, SC-010, and SC-011 is explicitly covered by at least one passing test reference in the results artifact.

## Task Dependency Graph
```text
T-001
  ├── T-002 ──┐
  └── T-003 ──┴── T-004 ─── T-005 ─── T-006 ─── T-007
                                              └── T-008
```

## Summary
| Task | Phase | Scope | Serial/Parallel | Scenarios |
| T-001 | 0 Foundation | S | Serial | SC-003, SC-006, SC-007 |
| T-002 | 0 Foundation | M | Parallel | SC-003, SC-007, SC-011 |
| T-003 | 0 Foundation | M | Parallel | SC-001, SC-002, SC-005, SC-008, SC-011 |
| T-004 | 1 Core Logic | L | Serial | SC-001, SC-002, SC-004, SC-006, SC-009, SC-010, SC-011 |
| T-005 | 1 Core Logic | M | Serial | SC-005, SC-008, SC-011 |
| T-006 | 2 Integration | M | Serial | SC-001 through SC-011 |
| T-007 | 2 Integration | S | Parallel | SC-004, SC-005, SC-006 |
| T-008 | 3 Validation | M | Parallel | SC-001 through SC-011 |

Total: 8 tasks, 4 phases, 2 parallelizable pairs, 6 serial waves.
MVP Tasks: T-001, T-002, T-003, T-004, T-005, T-006, T-008.
