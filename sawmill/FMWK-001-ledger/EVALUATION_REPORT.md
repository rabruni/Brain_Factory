# Evaluation Report — FMWK-001-ledger

Run ID: 20260320T205424Z-45d3202a8b43
Attempt: 2
Holdout hash: sha256:0283f98318cbfa55bfc767896c987a1f4384bcb6a83419665b36636f4578e080
Staging hash: sha256:0fb62e5bca70e8584ec9068c58c38be2861392dcd3ec9e44a1a3b76777cf635a

## Run Order

P0 first, then P1. Per D9 protocol: HS-001, HS-002, HS-004, HS-005, HS-003.

## Results

### HS-001 — genesis-append-populates-ledger-owned-fields (P0)

| Run | Result |
|-----|--------|
| 1 | PASS |
| 2 | PASS |
| 3 | PASS |

Aggregate: **PASS** (3/3)

All checks passed: genesis sequencing (sequence 0, zero previous_hash), envelope completion (all required fields present), caller immutability (ledger-owned fields populated by framework), hash format (sha256: prefix + 64 hex chars).

### HS-002 — sequential-append-read-replay-and-tip-remain-linear (P0)

| Run | Result |
|-----|--------|
| 1 | FAIL |
| 2 | FAIL |
| 3 | FAIL |

Aggregate: **FAIL** (0/3)

Execute phase aborted: first append (node_creation event) rejected by `schemas.py:validate_payload` with `LEDGER_SERIALIZATION_ERROR: initial_state must be an object`. The holdout payload contains `{node_id, node_type, subject_id}` but the builder's schema requires `initial_state` (a Mapping) as a mandatory field for `node_creation` events. No verify checks reached.

### HS-004 — verify-chain-reports-first-corruption-boundary (P0)

| Run | Result |
|-----|--------|
| 1 | FAIL |
| 2 | FAIL |
| 3 | FAIL |

Aggregate: **FAIL** (0/3)

Execute phase aborted: third append (package_install event) rejected by `schemas.py:validate_payload` with `LEDGER_SERIALIZATION_ERROR: framework_id must be a non-empty string`. The holdout payload contains `{package_id, version, action}` but the builder's schema requires `framework_id`, `install_scope`, and `manifest_hash` as mandatory fields for `package_install` events. First two appends (session_start, signal_delta) succeeded. No verify checks reached.

### HS-005 — append-and-tip-fail-with-contract-shaped-errors (P0)

| Run | Result |
|-----|--------|
| 1 | PASS |
| 2 | PASS |
| 3 | PASS |

Aggregate: **PASS** (3/3)

All checks passed: sequence error shape (LEDGER_SEQUENCE_ERROR with message), connection error shape (LEDGER_CONNECTION_ERROR with message), serialization error shape (LEDGER_SERIALIZATION_ERROR with message for float delta), no partial writes (tip unchanged after all three error types).

### HS-003 — online-and-offline-verification-agree-on-intact-ledger (P1)

| Run | Result |
|-----|--------|
| 1 | FAIL |
| 2 | FAIL |
| 3 | FAIL |

Aggregate: **FAIL** (0/3)

Execute phase aborted: second append (package_install event) rejected by `schemas.py:validate_payload` with `LEDGER_SERIALIZATION_ERROR: framework_id must be a non-empty string`. Same root cause as HS-004. No verify checks reached.

## Summary

| Scenario | Priority | Aggregate |
|----------|----------|-----------|
| HS-001 | P0 | PASS |
| HS-002 | P0 | FAIL |
| HS-004 | P0 | FAIL |
| HS-005 | P0 | PASS |
| HS-003 | P1 | FAIL |

- P0 pass: 2/4 (HS-001, HS-005)
- P1 pass: 0/1
- Overall pass rate: 2/5 = 40%

## Gate Check

- All P0 pass: NO (HS-002, HS-004 failed)
- All P1 pass: NO (HS-003 failed)
- Overall >= 90%: NO (40%)

## Root Cause Summary

Two distinct schema over-constraints in `staging/FMWK-001-ledger/ledger/schemas.py:validate_payload`:

1. **node_creation**: requires `initial_state` as a mandatory Mapping. Holdout payloads (from D4 contracts) do not include `initial_state`.
2. **package_install**: requires `framework_id`, `install_scope`, and `manifest_hash` as mandatory fields. Holdout payloads (from D4 contracts) include only `package_id`, `version`, and `action`.

These schema constraints reject valid contract-conforming payloads, causing 3 of 5 scenarios to abort during the execute phase before any verification checks run.

Final verdict: FAIL
