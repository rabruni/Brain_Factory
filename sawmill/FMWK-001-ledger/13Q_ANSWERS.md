Builder Prompt Contract Version: 1.0.0

# 13Q Answers — FMWK-001-ledger

## 1. Scope — what am I building?
I am building only FMWK-001-ledger: a mechanical, append-only, hash-chained event store that validates approved append requests, assigns the next global sequence inside the ledger boundary, computes canonical event hashes, persists exactly one event synchronously, supports ordered reads/replay, reports the current tip, and verifies chain integrity online or from exported offline event data.

## 2. Scope — what am I NOT building?
I am not building write-path fold logic, HO3 graph state, HO2 orchestration, package-lifecycle gates, runtime database provisioning, business logic semantics, snapshot file contents, authorization policy, or any payload catalog beyond `node_creation`, `signal_delta`, `package_install`, `session_start`, and `snapshot_created`.

## 3. Scope — what are the D1 boundaries?
ALWAYS: own the canonical event envelope, minimum approved payload validation, internal sequence assignment, canonical UTF-8 JSON hashing, synchronous single-event append, ordered reads/replay, offline/online verification, and `platform_sdk`-backed external concerns.
ASK FIRST: expand event types, change envelope fields, change hash algorithm or hash format, change the genesis previous-hash constant, reassign payload ownership, define snapshot contents, or alter cold-storage validation assumptions.
NEVER: delete/rewrite/compact/truncate events, expose direct immudb access or admin operations, accept caller-supplied sequence fields, acknowledge before persistence, emit non-`sha256:<64 lowercase hex>` hashes, or put graph/gate/work-order/LLM logic in ledger code.

## 4. Technical — what public APIs must exist?
`class Ledger` in `staging/FMWK-001-ledger/ledger/api.py` must expose:
`append(self, request) -> LedgerEvent`
`read(self, sequence_number: int) -> LedgerEvent`
`read_range(self, start: int, end: int) -> list[LedgerEvent]`
`read_since(self, sequence_number: int) -> list[LedgerEvent]`
`verify_chain(self, start: int | None = None, end: int | None = None, source_mode: str = "online") -> VerificationResult`
`get_tip(self, include_hash: bool = True) -> LedgerTip`

Internal boundaries:
`schemas.py` validates request and payload shapes only.
`serialization.py` owns canonical bytes and hash helpers only.
`store.py` owns persistence, sequencing, tip reads, and reconnect-once only.
`verify.py` owns online/offline verification only.

## 5. Technical — what file locations and package boundary apply?
Implementation belongs under `staging/FMWK-001-ledger/`.
Source package: `staging/FMWK-001-ledger/ledger/`
Tests: `staging/FMWK-001-ledger/tests/`
Local package docs: `staging/FMWK-001-ledger/README.md`
Gate/results/evidence artifacts belong under `sawmill/FMWK-001-ledger/`.

[CRITICAL_REVIEW_REQUIRED]: `BUILDER_HANDOFF.md` Section 4 and Section 9 mention `staging/FMWK-001-ledger/13Q_ANSWERS.md`, but the builder prompt’s declared output artifact and direct instruction require `/Users/raymondbruni/Cowork/Brain_Factory/sawmill/FMWK-001-ledger/13Q_ANSWERS.md`. I am following the prompt-level declared output path because it is the more specific task instruction for this turn.

## 6. Technical — what exact data formats and error contracts govern the build?
Ledger Event fields are `event_id`, `sequence`, `event_type`, `schema_version`, `timestamp`, `provenance`, `previous_hash`, `payload`, `hash`.
`event_id` is UUIDv7 string.
`schema_version` is `1.0.0`.
`timestamp` is ISO-8601 UTC with `Z`.
`provenance.framework_id` stores full `FMWK-NNN-name`.
Genesis `previous_hash` is `sha256:` plus 64 zeroes.
Hash strings are exactly `sha256:<64 lowercase hex>`.
Canonical serialization rules are sorted keys at every level, separators `,` and `:`, UTF-8 encoding, `ensure_ascii=False`, nulls preserved, `hash` excluded from hash input, and floats forbidden in the base envelope.
Explicit error codes are `LEDGER_CONNECTION_ERROR`, `LEDGER_CORRUPTION_ERROR`, `LEDGER_SEQUENCE_ERROR`, and `LEDGER_SERIALIZATION_ERROR`.

## 7. Packaging — what package/manifests/hashes are required?
The package is `PC-001-ledger-core`. Required staged assets are:
`ledger/__init__.py`, `ledger/errors.py`, `ledger/models.py`, `ledger/schemas.py`, `ledger/serialization.py`, `ledger/store.py`, `ledger/verify.py`, `ledger/api.py`, `tests/test_serialization.py`, `tests/test_store.py`, `tests/test_verify.py`, `tests/test_api.py`, and `README.md`.
No separate manifest format is introduced here; the builder must record file inventory and SHA256 evidence in `sawmill/FMWK-001-ledger/RESULTS.md`.

## 8. Packaging — what dependencies and dependency limits apply?
Allowed implementation scope is Python 3.x stdlib plus `platform_sdk` surfaces for config, secrets, logging, and errors, with immudb reachable only through the ledger abstraction boundary. No direct caller exposure of immudb, no forbidden immudb admin operations, no runtime database provisioning, and no new primitives or extra frameworks.

## 9. Testing — how many tests and what verification threshold apply?
The minimum target is 25+ tests, aligned to SC-001 through SC-011 and the handoff’s named test methods. Required regression commands are the four targeted pytest commands for `test_serialization.py`, `test_store.py`, `test_verify.py`, and `test_api.py`, plus the full package command `PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests`. Completion requires the full staged regression to exit `0`, with no skipped failures against SC-001 through SC-011 coverage.

## 10. Integration — how does this connect to existing components?
The ledger is called by FMWK-002 write-path and approved mechanical producers through the ledger abstraction. It is the sole source of truth for acknowledged mutations, while FMWK-005 graph, FMWK-003 orchestration, FMWK-006 package-lifecycle, and cold-storage tools consume the resulting event stream, tip data, or verification results. Integration is mechanical only: the ledger stores and replays events, but does not fold state, evaluate gates, or interpret higher-level behavior.

## 11. Adversarial — what assumption could cause scope drift if I implement loosely?
The highest scope-drift risk is smuggling non-ledger semantics into validation or the public facade. If I start interpreting event meaning, defining payload schemas beyond the approved minimum catalog, or adding snapshot content semantics, I would violate D1 Articles 2 and 6.

## 12. Adversarial — what failure mode must never be softened into best effort?
I must not soften connection, sequence, serialization, or corruption failures into retries beyond the single allowed reconnect-once path or into partial success. Acknowledged must mean durable, and verification must fail closed with explicit ledger errors or `valid=false` plus exact `break_at`.

## 13. Adversarial — where is my understanding still least certain?
The least certain area is not ledger behavior itself but prompt-contract detail around the reviewer’s exact adversarial question selection and the conflicting 13Q file path references between handoff and prompt artifacts. My implementation understanding is that the framework behavior remains fixed by D1-D8, but the gate artifact path had to be resolved from the direct task instruction.

[CRITICAL_REVIEW_REQUIRED]: I was not given the selected adversarial prompts from `BUILDER_PROMPT_CONTRACT.md` in the required reading set, so Q11-Q13 are answered against the strongest adversarial risks surfaced by D1-D8 and the builder role instead of a quoted contract list. If the reviewer expects different adversarial phrasings, the mismatch is in prompt visibility rather than framework scope understanding.
