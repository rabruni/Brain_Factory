Prompt Contract Version: 1.0.0

# BUILDER HANDOFF — FMWK-001-ledger

## 1. Mission
Build the `FMWK-001-ledger` framework as the DoPeJarMo Ledger primitive: a Python package that owns canonical Ledger event schemas, append-only sequence assignment, canonical hash-chain verification, ordered replay, and a Ledger-owned storage adapter over immudb. This framework exists so every governed mutation can be durably recorded and later replayed or verified from cold storage without expanding into write-path, graph, or package-lifecycle behavior.

## 2. Critical Constraints
1. Work only in the resolved framework staging root for this framework. Do not edit runtime repos or other frameworks.
2. Follow DTT exactly: no production code before a failing test. `Templates/TDD_AND_DEBUGGING.md` is mandatory. If you wrote code before the test, delete it and restart from RED.
3. Package everything needed for this framework: source, tests, fixtures, and any minimal support files.
4. E2E verify the framework with the commands in Section 8 and paste output into `RESULTS.md`.
5. No hardcoded production credentials, ports, or environment-specific secrets. Use `platform_sdk` config/secrets boundaries.
6. No file replacement shortcuts. Make targeted edits and preserve any user-authored workspace changes outside your scope.
7. Any archive or exported fixture you create must be deterministic and hashable.
8. `RESULTS.md` is mandatory and must include file hashes, test commands, pasted output, baseline snapshot, and full regression results.
9. Run full regression on all staged packages after the framework suite passes. Record new failures or `NONE`.
10. Record a baseline snapshot before final reporting: packages under test and collected test count.
11. Do not bypass the 13Q review. Create `13Q_ANSWERS.md`, stop, and wait for reviewer PASS before implementing.
12. Honor framework boundaries: no fold logic, graph queries, gate execution, work-order logic, snapshots beyond `snapshot_created` metadata, or immudb admin surfaces.
13. Use deterministic exact-string assertions for hashes, sequences, and corruption break positions. No semantic equivalence checks.

## 3. Architecture/Design
```text
Append/Read/Verify caller
        |
        v
  Ledger service
        |
        +--> Event/request/result models
        +--> Canonical serialization + SHA-256 hashing
        |
        v
  Ledger storage adapter
        |
        +--> platform_sdk config/secrets/logging
        +--> immudb `ledger` database

Offline verification:
exported Ledger events --> same canonical serializer --> same verify_chain result shape
```

Boundaries:
- Public boundary: `Ledger.append`, `Ledger.read`, `Ledger.read_range`, `Ledger.read_since`, `Ledger.verify_chain`, `Ledger.get_tip`.
- Storage boundary: one Ledger-owned adapter file. No other file or framework touches immudb transport details.
- Data boundary: `LedgerEvent`, `LedgerTip`, `ChainVerificationResult`, and the minimum payload models from D3.
- Failure boundary: `LedgerConnectionError`, `LedgerSerializationError`, `LedgerSequenceError`, `LedgerCorruptionError`.

## 4. Implementation Steps
1. Create `13Q_ANSWERS.md` with exactly `Builder Prompt Contract Version: 1.0.0`, answer the 13Q review, and stop for reviewer PASS.
   Why: The prompt contract forbids implementation before comprehension is validated.
2. Create `ledger/errors.py`, `ledger/models.py`, `ledger/__init__.py`, and `tests/conftest.py`.
   Signatures: `class LedgerConnectionError(Exception)`, `class LedgerSerializationError(Exception)`, `class LedgerSequenceError(Exception)`, `class LedgerCorruptionError(Exception)`.
   Signatures: `@dataclass class LedgerEvent`, `@dataclass class EventProvenance`, `@dataclass class LedgerTip`, `@dataclass class ChainVerificationResult`.
   Why: The rest of the framework depends on one canonical type and error surface.
3. Write failing tests for event envelope and payload validation in `tests/test_models.py`, then implement the minimum validation logic in `ledger/models.py`.
   Why: D3 ownership of the event envelope is constitutional and must be locked before storage code exists.
4. Write failing serialization/hash tests in `tests/test_serialization.py`, then implement `ledger/serialization.py`.
   Signatures: `def canonical_event_bytes(event) -> bytes`, `def compute_event_hash(event) -> str`, `def event_key(sequence: int) -> str`.
   Why: Hash-chain determinism is the core integrity contract; append and verify must share one byte path.
5. Write failing backend tests in `tests/test_connection_failures.py`, then implement `ledger/backend.py`.
   Signatures: `def connect()`, `def append_bytes(key: str, value: bytes) -> None`, `def read_bytes(sequence: int) -> bytes`, `def read_range_bytes(start: int, end: int) -> list[bytes]`, `def read_since_bytes(sequence_number: int) -> list[bytes]`, `def get_tip_bytes() -> tuple[int, bytes] | None`.
   Why: Reconnect-once and fail-closed behavior must be proven before the public service composes them.
6. Write failing append/read tests in `tests/test_append_and_read.py`, then implement `ledger/service.py`.
   Signatures: `class Ledger`, `def append(self, request) -> tuple[int, LedgerEvent]`, `def read(self, sequence_number: int) -> LedgerEvent`, `def read_range(self, start: int, end: int) -> list[LedgerEvent]`, `def read_since(self, sequence_number: int) -> list[LedgerEvent]`, `def get_tip(self) -> LedgerTip | None`.
   Why: Sequence assignment, append-only persistence, replay, and tip queries are the public behavioral center of the framework.
7. Write failing verification tests in `tests/test_verification.py`, then finish `Ledger.verify_chain`.
   Signature: `def verify_chain(self, start: int | None = None, end: int | None = None, source_mode: str = "online", offline_events: list[LedgerEvent] | None = None) -> ChainVerificationResult`.
   Why: Cold-storage verifiability is a constitutional requirement, not a later optimization.
8. Add `tests/test_integration_immudb.py` as an opt-in suite against real immudb.
   Why: Unit tests prove determinism; integration tests prove the storage boundary behaves the same under the real backend.
9. Run framework tests, then full staged-package regression, then write `sawmill/FMWK-001-ledger/RESULTS.md`.
   Why: The handoff is incomplete without session-local evidence and regression impact accounting.

## 5. Package Plan
| Package ID | Layer | Assets | Dependencies | Manifest |
| FMWK-001-ledger | KERNEL | `ledger/__init__.py`, `ledger/errors.py`, `ledger/models.py`, `ledger/serialization.py`, `ledger/backend.py`, `ledger/service.py`, `tests/conftest.py`, `tests/test_models.py`, `tests/test_serialization.py`, `tests/test_append_and_read.py`, `tests/test_verification.py`, `tests/test_connection_failures.py`, `tests/test_integration_immudb.py` | Python 3.11+, `platform_sdk`, `pytest`, runtime immudb transport only behind the Ledger adapter if required | Framework-local package manifest or metadata only if the resolved framework root already uses one; do not invent packaging systems outside local repo convention |

## 6. Test Plan
- `test_models_rejects_caller_sequence_fields`: append request rejects caller-controlled `sequence`, `previous_hash`, and `hash`.
- `test_models_accepts_snapshot_created_payload`: snapshot metadata payload satisfies D3 E-007.
- `test_canonical_event_bytes_sorted_keys`: serialization sorts keys at every level.
- `test_canonical_event_bytes_uses_utf8_no_ascii_escape`: Unicode is stored as literal UTF-8 bytes.
- `test_canonical_event_bytes_keeps_null_fields`: null fields remain present in hash input.
- `test_compute_event_hash_exact_prefix_and_length`: hash output is exact `sha256:<64 lowercase hex>`.
- `test_genesis_append_assigns_sequence_zero`: first append gets sequence `0`.
- `test_genesis_append_uses_zero_previous_hash`: first append uses the all-zero previous hash.
- `test_append_links_previous_hash_to_prior_event`: subsequent append links to prior hash exactly.
- `test_append_rejects_sequence_conflict`: sequence conflict raises `LedgerSequenceError` and writes nothing.
- `test_append_rejects_serialization_failure`: bad input raises `LedgerSerializationError` and preserves tip.
- `test_append_records_snapshot_created_event`: snapshot metadata event stores and replays cleanly.
- `test_read_returns_exact_stored_event`: point read returns canonical stored content.
- `test_read_range_returns_ascending_sequence_order`: bounded replay stays ordered.
- `test_read_since_minus_one_replays_from_genesis`: `read_since(-1)` includes all events.
- `test_read_since_snapshot_boundary_returns_post_snapshot_events`: replay after snapshot starts after the boundary.
- `test_get_tip_returns_latest_sequence_and_hash`: tip matches the last committed event.
- `test_verify_chain_online_valid_chain`: valid chain returns `valid=true`.
- `test_verify_chain_offline_matches_online`: offline export verification matches online verdict exactly.
- `test_verify_chain_returns_first_break_at_sequence`: corruption reports the first failing sequence.
- `test_backend_reconnect_once_then_succeeds`: one reconnect attempt may recover the operation.
- `test_backend_reconnect_once_then_fails_closed`: second failure raises `LedgerConnectionError`.
- `test_backend_missing_database_fails_fast`: missing `ledger` database raises `LedgerConnectionError`.
- `test_integration_append_read_verify_round_trip`: real immudb happy path.
- `test_integration_missing_database_contract`: real backend missing-database path.
- `test_integration_reconnect_once_contract`: real backend reconnect-once path if the environment can simulate it.

Minimum expected suite size: 25+ tests total before final reporting. If you add helper behavior, add tests with it.

## 7. Existing Code to Reference
| What | Where | Why |
| Smoke framework layout | `staging/FMWK-900-sawmill-smoke/` | Shows local workspace expectation: simple Python module plus pytest tests. |
| Scenario authority | `sawmill/FMWK-001-ledger/D2_SPECIFICATION.md` | Source of exact behaviors and success criteria. |
| Contract authority | `sawmill/FMWK-001-ledger/D4_CONTRACTS.md` | Source of public methods, side effects, and error codes. |
| Clarification authority | `sawmill/FMWK-001-ledger/D6_GAP_ANALYSIS.md` | Locks the v1 mutex assumption, snapshot boundary, and offline verification assumption. |
| TDD discipline | `Templates/TDD_AND_DEBUGGING.md` | Mandatory development and debugging process. |

## 8. E2E Verification
```bash
# From the resolved framework root
python -m compileall ledger tests
python -m pytest -q
python -m pytest -q tests/test_append_and_read.py
python -m pytest -q tests/test_verification.py -k online_offline
python -m pytest -q tests/test_integration_immudb.py -m integration
FRAMEWORK_ROOT="$PWD" python -m pytest -q "$FRAMEWORK_ROOT/tests" /Users/raymondbruni/Cowork/Brain_Factory/staging/FMWK-900-sawmill-smoke
```

Expected output:
- `compileall` completes without syntax errors.
- Unit suite reports all tests passed.
- The targeted append/read and verification commands report passing tests with zero failures.
- Integration suite either passes or is explicitly skipped because the environment lacks real immudb; do not fake a pass.
- Full staged-package regression reports no new failures.

## 9. Files Summary
| File | Location | Action (CREATE/MODIFY) |
| `__init__.py` | `ledger/__init__.py` | CREATE |
| `errors.py` | `ledger/errors.py` | CREATE |
| `models.py` | `ledger/models.py` | CREATE |
| `serialization.py` | `ledger/serialization.py` | CREATE |
| `backend.py` | `ledger/backend.py` | CREATE |
| `service.py` | `ledger/service.py` | CREATE |
| `conftest.py` | `tests/conftest.py` | CREATE |
| `test_models.py` | `tests/test_models.py` | CREATE |
| `test_serialization.py` | `tests/test_serialization.py` | CREATE |
| `test_append_and_read.py` | `tests/test_append_and_read.py` | CREATE |
| `test_verification.py` | `tests/test_verification.py` | CREATE |
| `test_connection_failures.py` | `tests/test_connection_failures.py` | CREATE |
| `test_integration_immudb.py` | `tests/test_integration_immudb.py` | CREATE |
| `13Q_ANSWERS.md` | framework root | CREATE |
| `RESULTS.md` | `sawmill/FMWK-001-ledger/RESULTS.md` | MODIFY or CREATE |

## 10. Design Principles
1. The Ledger is storage truth only; no fold, graph, orchestration, or gate logic enters this framework.
2. One canonical serializer governs both append and verify so the chain cannot drift across code paths.
3. All failures are explicit and fail closed; no silent repair, no silent retries beyond reconnect-once.
4. Sequence ownership belongs to the Ledger alone; callers never choose sequence numbers.
5. Offline verification is a first-class requirement, not optional tooling.
6. The public API stays small and typed; internal complexity belongs behind the Ledger boundary.

## 11. Verification Discipline
Every claim that tests passed must include pasted command output from this session in `RESULTS.md`. Do not summarize counts without evidence. If a command cannot run, record the exact reason and the attempted command. Treat phrases like "should work," "probably passes," or "I’m confident" as failures of evidence. Use `Templates/TDD_AND_DEBUGGING.md` for the debugging protocol if anything fails unexpectedly.

## 12. Mid-Build Checkpoint
After all unit tests pass and before final integration/regression work:
- Record the passing unit-test command and pasted output.
- Record how many files were created.
- Record any deviations from D2/D4 as `NONE` or explicit blockers.
- Continue unless the orchestrator or reviewer escalates.

## 13. Self-Reflection
Before marking any step complete, confirm all of the following:
- The code still matches D2 scenarios and D4 contracts exactly.
- Edge cases from D8 are covered by tests, not only by reasoning.
- The implementation is still understandable six months from now.
- TDD was followed for every behavior. If not, delete the out-of-order code and redo it.
- No scope leaked into write-path, graph, package-lifecycle, or runtime provisioning concerns.
