# Evaluation Report — FMWK-001-ledger

Run ID: `20260320T202813Z-6935d147c49b`
Attempt: 1
Date: 2026-03-20

## Holdout Hashes

- holdout_hash: `sha256:b1f1c423dbcf4cd9987632c7b4ca825934a1f6bafc58918c51d7eb8fcb7cc33c`
- staging_hash: `sha256:f10f26900f3a0bc7c21e2bc29fe4884e0e29bb861ca59e1de859729399c9f9ee`

## P0 Scenarios

### HS-001 — genesis-and-monotonic-append (P0)

| Run | Result |
|-----|--------|
| 1   | PASS   |
| 2   | PASS   |
| 3   | PASS   |

**Aggregate: PASS (3/3)**

Checks verified:
- Genesis append: sequence_number=0, sequence=0, previous_hash is all-zero genesis hash, hash matches sha256 format
- Monotonic next append: sequence_number=1, sequence=1, previous_hash equals first event hash
- Self-describing envelope: all required fields present (event_id, event_type, schema_version, timestamp, provenance, payload)
- Tip visibility: sequence_number=1, hash equals second event hash

### HS-003 — verify-parity-and-corruption-detection (P0)

| Run | Result |
|-----|--------|
| 1   | PASS   |
| 2   | PASS   |
| 3   | PASS   |

**Aggregate: PASS (3/3)**

Checks verified:
- Online verification: valid=true, start=0, end=3, no break_at
- Offline verification: valid=true, start=0, end=3, no break_at (parity with online)
- Corruption detection: valid=false, break_at=2, start=0, end=3 (deterministic first break at corrupted sequence)

## P1 Scenarios

### HS-002 — ordered-replay-across-snapshot-boundary (P1)

| Run | Result |
|-----|--------|
| 1   | PASS   |
| 2   | PASS   |
| 3   | PASS   |

**Aggregate: PASS (3/3)**

Checks verified:
- Read one: sequence=2, event_type=snapshot_created, non-empty payload object
- Ordered bounded replay: 4 events with ascending sequences [0,1,2,3] and correct event types
- Replay after snapshot boundary: only sequence 3 (signal_delta) returned for read_since(2)

### HS-004 — serialization-rejection-preserves-tip (P1)

| Run | Result |
|-----|--------|
| 1   | PASS   |
| 2   | PASS   |
| 3   | PASS   |

**Aggregate: PASS (3/3)**

Checks verified:
- Error response: error_code=LEDGER_SERIALIZATION_ERROR, non-empty message, no success fields
- Tip unchanged: sequence_number and hash identical before and after rejected append

### HS-005 — connection-failure-and-sequence-conflict-are-explicit (P1)

| Run | Result |
|-----|--------|
| 1   | PASS   |
| 2   | PASS   |
| 3   | PASS   |

**Aggregate: PASS (3/3)**

Checks verified:
- Connection error: error_code=LEDGER_CONNECTION_ERROR, non-empty message, no events payload
- Sequence error: error_code=LEDGER_SEQUENCE_ERROR, non-empty message, no success fields
- No fork/no hidden write: tip sequence_number and hash unchanged across both failures

## Summary

| Scenario | Priority | Aggregate | Runs |
|----------|----------|-----------|------|
| HS-001   | P0       | PASS      | 3/3  |
| HS-003   | P0       | PASS      | 3/3  |
| HS-002   | P1       | PASS      | 3/3  |
| HS-004   | P1       | PASS      | 3/3  |
| HS-005   | P1       | PASS      | 3/3  |

- P0 gate: PASS (2/2 scenarios)
- P1 gate: PASS (3/3 scenarios)
- Overall pass rate: 5/5 (100%)

Final verdict: PASS
