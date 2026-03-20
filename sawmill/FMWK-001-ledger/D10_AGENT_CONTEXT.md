# D10: Agent Context — FMWK-001-ledger
Meta: pkg:FMWK-001-ledger | updated:2026-03-20

## What This Project Does
FMWK-001-ledger is the append-only, hash-chained event store for DoPeJarMo. It accepts approved event append requests without caller-supplied sequencing fields, assigns the next global sequence inside the ledger boundary, persists exactly one event synchronously, returns ordered reads and replay, and verifies the stored chain online or from exported event data offline. It is a storage primitive only: no graph fold logic, no gate evaluation, no work-order management, and no LLM behavior.

## Architecture Overview
```text
write-path / mechanical caller
        |
        v
   Ledger facade (api.py)
        |
        +--> schemas.py         request + payload validation
        +--> serialization.py   canonical UTF-8 JSON + SHA-256 hash formatting
        +--> store.py           sync append/read/tip over immudb boundary
        +--> verify.py          online/offline chain verification
        |
        v
   ledger event stream / verification result

staging/FMWK-001-ledger/
├── ledger/    source package for the framework
├── tests/     staged pytest suite for SC-001..SC-011
└── README.md  local commands and package notes
```

## Key Patterns (4-6)
- Ledger-only ownership: own the event envelope, sequence assignment, and replay order only; do not absorb write-path, graph, orchestration, or package-lifecycle behavior. Reference: D1 Articles 2, 3, 6.
- Canonical bytes first: treat JSON serialization and hash formatting as byte-level contracts shared by append and verify paths. Reference: D1 Article 7, D5 RQ-003.
- Single-writer atomic append: keep tip-read plus write inside a mutex-protected critical section because D5 selected the in-process mutex assumption. Reference: D5 RQ-001, D6 CLR-001.
- Fail closed: connection, sequence, serialization, and corruption failures must return explicit ledger errors and never partial success. Reference: D1 Article 8, D4 ERR-001..ERR-004.
- Snapshot marker only: ledger stores only the `snapshot_created` reference event and never defines snapshot file contents. Reference: D2 SC-007, D5 RQ-002.

## Commands
```bash
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_serialization.py
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_store.py
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_verify.py
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_api.py
```

## Tool Rules
| USE THIS | NOT THIS | WHY |
| `platform_sdk` configuration, secrets, logging, and error surfaces with a ledger abstraction over immudb | direct caller access to immudb clients or ad hoc environment handling | D1 tooling constraint; the ledger owns the abstraction boundary, not direct client leakage. |
| canonical UTF-8 JSON with sorted keys, no whitespace, `ensure_ascii=False`, and explicit exclusion of `hash` from hash input | language-default JSON formatting, escaped unicode, omitted nulls, or floating-point hash inputs | D1 tooling constraint; byte-level hash determinism is constitutional. |
| ledger-owned atomic tip-plus-write sequencing | caller-supplied sequence numbers or non-atomic read-then-write windows | D1 tooling constraint; append-only safety depends on single linear sequencing. |
| synchronous single-event appends confirmed by immudb | buffered writes, batch buffering, or early acknowledgement | D1 tooling constraint; acknowledged means durable. |
| mechanical hash recomputation and ordered replay from stored data | semantic inspection, graph-dependent checks, or LLM-assisted validation | D1 tooling constraint; cold verification must stay runtime-independent. |
| bootstrap-time database creation outside ledger runtime and runtime fail-fast if database is absent | runtime database provisioning, delete/truncate operations, or hidden admin wrappers | D1 tooling constraint; provisioning is outside this framework and append-only must remain intact. |

## Coding Conventions
Python 3.x with stdlib-first implementation. Use type hints on public functions and dataclasses or equivalent typed models for D3 entities. Keep modules small and mechanical. Raise explicit ledger errors instead of raw exceptions. No silent fallback behaviors beyond the single reconnect retry defined in D4 SIDE-003. Use `pytest` for all tests. Return exact hash strings and exact error codes; do not soften contracts into best-effort behavior.

## Submission Protocol
1. Create `13Q_ANSWERS.md` with exactly one line: `Builder Prompt Contract Version: 1.0.0`.
2. STOP and wait for reviewer PASS before implementation.
3. After PASS, build in DTT order: write failing test, implement the smallest change, rerun the targeted test, then continue.
4. Keep all code inside `staging/FMWK-001-ledger`.
5. Run the full staged regression command before reporting completion.
6. Write `sawmill/FMWK-001-ledger/RESULTS.md` with file hashes, full test commands, full output, and regression status from this session.
7. Use branch naming and commit format only if the orchestrator asks for git actions; otherwise focus on staged filesystem outputs only.

## Active Components
| Component | Where | Interface (signature) |
| Ledger facade | `staging/FMWK-001-ledger/ledger/api.py` | `class Ledger: append(self, request) -> LedgerEvent`; `read(self, sequence_number: int) -> LedgerEvent`; `read_range(self, start: int, end: int) -> list[LedgerEvent]`; `read_since(self, sequence_number: int) -> list[LedgerEvent]`; `verify_chain(self, start: int | None = None, end: int | None = None, source_mode: str = "online") -> VerificationResult`; `get_tip(self, include_hash: bool = True) -> LedgerTip` |
| Validation catalog | `staging/FMWK-001-ledger/ledger/schemas.py` | `validate_append_request(request) -> None`; `validate_payload(event_type: str, payload) -> None` |
| Canonical serialization | `staging/FMWK-001-ledger/ledger/serialization.py` | `canonical_event_bytes(event) -> bytes`; `compute_event_hash(event) -> str` |
| Persistence boundary | `staging/FMWK-001-ledger/ledger/store.py` | `append_event(request) -> LedgerEvent`; `read(sequence_number: int) -> LedgerEvent`; `read_range(start: int, end: int) -> list[LedgerEvent]`; `read_since(sequence_number: int) -> list[LedgerEvent]`; `get_tip() -> LedgerTip` |
| Verification path | `staging/FMWK-001-ledger/ledger/verify.py` | `verify_chain(source, start: int | None, end: int | None) -> VerificationResult`; `verify_events(events) -> VerificationResult` |

## Links to Deeper Docs
- D1_CONSTITUTION.md: constitutional boundaries, tooling constraints, and decomposition tests.
- D2_SPECIFICATION.md: scenarios in scope and deferred capabilities.
- D3_DATA_MODEL.md: exact entity shapes and invariants for events, tips, and verification.
- D4_CONTRACTS.md: inbound/outbound contracts, side effects, and error codes.
- D5_RESEARCH.md: resolved implementation choices, especially mutex-based atomic append and canonical serialization.
- D6_GAP_ANALYSIS.md: assumptions closed for Turn B, including snapshot ownership and external authz ownership.
- D7_PLAN.md: planned architecture, file creation order, and testing strategy.
- D8_TASKS.md: execution order, scenario-to-contract traceability, and regression expectations.
- D9: holdouts remain separate from builders during active build.
