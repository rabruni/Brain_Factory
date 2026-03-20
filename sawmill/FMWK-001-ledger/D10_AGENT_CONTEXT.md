# D10: Agent Context — FMWK-001-ledger
Meta: pkg:FMWK-001-ledger | updated:2026-03-19

## What This Project Does
This framework provides the Ledger primitive for DoPeJarMo: a synchronous, append-only, hash-chained event store that assigns global sequence numbers internally, persists self-describing events durably, replays them in order, and verifies integrity both online and from exported Ledger data without any runtime cognitive services.

## Architecture Overview
```text
append/read/verify caller
        |
        v
  ledger.service.Ledger
        |
        +--> ledger.models        # canonical event and result types
        +--> ledger.serialization # canonical bytes + SHA-256 formatting
        |
        v
   ledger.backend                # Ledger-owned storage boundary
        |
        +--> platform_sdk config/secrets/logging
        +--> immudb gRPC storage

framework-root/
  ledger/                        # production package
  tests/                         # scenario-mapped pytest suite
```

## Key Patterns (4-6)
- Append-only truth: all public operations preserve immutability and refuse any delete/rewrite surface. Reference: D1 Article 4.
- Canonical bytes first: hash computation and verification both flow through one byte-generation contract so append and verify cannot drift. Reference: D1 Article 5, D5 RQ-001 lessons.
- Storage isolation: only the Ledger package touches the storage adapter; callers consume typed contracts, not datastore details. Reference: D1 Article 6.
- Cold-storage parity: offline verification must produce the same verdict structure as online verification for the same events. Reference: D1 Article 7, D2 SC-004.
- Fail closed: connection, serialization, sequence, and corruption faults stop the operation explicitly with no silent repair. Reference: D1 Article 8.

## Commands
```bash
# From the resolved framework root
python -m compileall ledger tests
python -m pytest -q
python -m pytest -q tests/test_append_and_read.py
python -m pytest -q tests/test_integration_immudb.py -m integration
FRAMEWORK_ROOT="$PWD" python -m pytest -q "$FRAMEWORK_ROOT/tests" /Users/raymondbruni/Cowork/Brain_Factory/staging/FMWK-900-sawmill-smoke
```

## Tool Rules
| USE THIS | NOT THIS | WHY |
| Ledger interface with internal sequence assignment and canonical hash computation | Caller-supplied sequence or direct immudb `Set` from another framework | Matches D1 append-path tooling constraints exactly. |
| `platform_sdk` config/secrets access for host, port, database, and credentials | Hardcoded credentials or scattered env reads | Matches D1 configuration tooling constraints exactly. |
| Ledger-owned immudb wrapper boundary | Direct immudb imports by write-path, graph, or package-lifecycle callers | Matches D1 storage-access tooling constraints exactly. |
| SHA-256 over canonical UTF-8 JSON with sorted keys and excluded `hash` field | Language-default JSON serialization, alternate encodings, or noncanonical whitespace | Matches D1 hashing tooling constraints exactly. |
| Online and offline chain verification against exact stored hash strings | Semantic hash comparison or runtime-only verification | Matches D1 verification tooling constraints exactly. |
| Deterministic pytest scenarios plus corruption and disconnect fault injection | Ad hoc manual validation as sole evidence | Matches D1 testing tooling constraints exactly. |

## Coding Conventions
Python 3.11+ only. Prefer stdlib dataclasses, typing, and small pure functions over framework-heavy abstractions. Keep public interfaces typed. Raise the declared Ledger error classes instead of raw exceptions. Use pytest function tests with explicit scenario names. Integration tests must be opt-in and skip cleanly when immudb is unavailable. Exit non-zero on any failed test or verification command.

## Submission Protocol
1. Start by creating `13Q_ANSWERS.md` with exactly one line: `Builder Prompt Contract Version: 1.0.0`.
2. Read the handoff and this context, answer the 13Q review, and STOP until reviewer PASS.
3. Build only through DTT: write a failing test first, implement the minimum code to pass, then refactor.
4. Keep all work inside the resolved framework root; do not replace whole files when targeted edits suffice.
5. Write `RESULTS.md` in the framework sawmill directory with file hashes, full command output, baseline snapshot, package regression, and clean-room verification notes.
6. Run the full framework suite, then the full staged-package regression command from this document.
7. Use branch naming and commit format per `feat|fix|test(scope): what` if commits are requested.

## Active Components
| Component | Where | Interface (signature) |
| Ledger models | `ledger/models.py` | `LedgerEvent`, `EventProvenance`, payload dataclasses, `LedgerTip`, `ChainVerificationResult` |
| Canonical serialization | `ledger/serialization.py` | `canonical_event_bytes(event) -> bytes`, `compute_event_hash(event) -> str`, `event_key(sequence: int) -> str` |
| Storage adapter | `ledger/backend.py` | `connect()`, `append_bytes(key: str, value: bytes) -> None`, `read_bytes(sequence: int) -> bytes`, `read_range_bytes(start: int, end: int) -> list[bytes]`, `read_since_bytes(sequence_number: int) -> list[bytes]`, `get_tip_bytes() -> tuple[int, bytes] | None` |
| Public ledger service | `ledger/service.py` | `append(request) -> tuple[int, LedgerEvent]`, `read(sequence_number: int) -> LedgerEvent`, `read_range(start: int, end: int) -> list[LedgerEvent]`, `read_since(sequence_number: int) -> list[LedgerEvent]`, `verify_chain(...) -> ChainVerificationResult`, `get_tip() -> LedgerTip | None` |

## Links to Deeper Docs
- D1: constitutional boundaries, ownership, and tooling constraints.
- D2: scenario inventory and exact success criteria.
- D3: shared entities and field-level invariants.
- D4: inbound/outbound contracts, side effects, and error enums.
- D5: approved assumptions for atomic append, snapshot scope, and event naming.
- D6: resolved clarifications and the closed gate rationale.
- D7: architecture plan, file order, and testing strategy.
- D8: implementation task graph and acceptance criteria.
- D9: holdouts are intentionally withheld from builders during active build.
