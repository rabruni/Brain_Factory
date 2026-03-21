# Evaluation Report — FMWK-001-ledger

| Field | Value |
|-------|-------|
| Run ID | 20260321T054057Z-6d3169742c02 |
| Attempt | 1 |
| Framework | FMWK-001-ledger |
| Holdout Hash | sha256:4059d9b33f303c7f304123c36b217e287ce0c6aa2bbe1ae7d474c105432c0447 |
| Staging Hash | sha256:5a1655eb54b35d61f6da555ccf0ae8ecfb64968fa9dc383799278bc85b23dffd |
| Date | 2026-03-21 |

## Results Summary

| Metric | Value |
|--------|-------|
| Total scenarios | 11 |
| P0 scenarios | 7 (all passed) |
| P1 scenarios | 4 (all passed) |
| Overall pass rate | 100% (11/11) |

## Per-Scenario Results

### P0 Scenarios

| Scenario | Title | Run 1 | Run 2 | Run 3 | Aggregate |
|----------|-------|-------|-------|-------|-----------|
| HS-001 | Genesis append assigns sequence 0 with zero previous_hash | PASS | PASS | PASS | **PASS** (3/3) |
| HS-002 | Sequential appends form an unbroken hash chain | PASS | PASS | PASS | **PASS** (3/3) |
| HS-003 | Read operations return complete events in correct order | PASS | PASS | PASS | **PASS** (3/3) |
| HS-004 | Tip reflects empty-ledger sentinel and advances after each append | PASS | PASS | PASS | **PASS** (3/3) |
| HS-005 | Hash chain verification detects intact chain and locates corruption | PASS | PASS | PASS | **PASS** (3/3) |
| HS-008 | Cold-storage offline verification produces identical results | PASS | PASS | PASS | **PASS** (3/3) |
| HS-011 | Multi-type append sequence with bulk read and chain verification | PASS | PASS | PASS | **PASS** (3/3) |

### P1 Scenarios

| Scenario | Title | Run 1 | Run 2 | Run 3 | Aggregate |
|----------|-------|-------|-------|-------|-----------|
| HS-006 | immudb unreachable on append raises LedgerConnectionError | PASS | PASS | PASS | **PASS** (3/3) |
| HS-007 | Concurrent append raises LedgerSequenceError and creates no fork | PASS | PASS | PASS | **PASS** (3/3) |
| HS-009 | Non-serializable payload raises LedgerSerializationError | PASS | PASS | PASS | **PASS** (3/3) |
| HS-010 | Out-of-range and negative sequence reads raise LedgerSequenceError | PASS | PASS | PASS | **PASS** (3/3) |

## Generated Test Paths

| Scenario | Test File | Mapping File |
|----------|-----------|-------------|
| HS-001 | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/test_hs_001.py` | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/HS-001.mapping.md` |
| HS-002 | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/test_hs_002.py` | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/HS-002.mapping.md` |
| HS-003 | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/test_hs_003.py` | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/HS-003.mapping.md` |
| HS-004 | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/test_hs_004.py` | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/HS-004.mapping.md` |
| HS-005 | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/test_hs_005.py` | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/HS-005.mapping.md` |
| HS-006 | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/test_hs_006.py` | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/HS-006.mapping.md` |
| HS-007 | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/test_hs_007.py` | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/HS-007.mapping.md` |
| HS-008 | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/test_hs_008.py` | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/HS-008.mapping.md` |
| HS-009 | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/test_hs_009.py` | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/HS-009.mapping.md` |
| HS-010 | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/test_hs_010.py` | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/HS-010.mapping.md` |
| HS-011 | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/test_hs_011.py` | `runs/20260321T054057Z-6d3169742c02/eval_tests/attempt1/HS-011.mapping.md` |

## Verdict Logic

1. All P0 scenarios passed (7/7): **SATISFIED**
2. All P1 scenarios passed (4/4): **SATISFIED**
3. Overall pass rate 100% >= 90%: **SATISFIED**

Final verdict: PASS
