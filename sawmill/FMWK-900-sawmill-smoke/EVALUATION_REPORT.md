# Evaluation Report — FMWK-900-sawmill-smoke

- **Run ID**: 20260322T000705Z-2cc56e4f0789
- **Attempt**: 2
- **Holdout hash**: sha256:41514c354b6ae1f3c4a14b381bd21646fda57cdcb4e112e8a16943c30581f67b
- **Staging hash**: sha256:c3675554cb0b29e2aa138adc1c7709c802d3987b86f72ed10e2c9dce3de7bb86
- **Date**: 2026-03-22

## Summary

| Metric | Value |
|--------|-------|
| Total scenarios | 4 |
| P0 scenarios | 0 |
| P1 scenarios | 4 |
| P2 scenarios | 0 |
| Scenarios passed | 4 |
| Scenarios failed | 0 |
| Overall pass rate | 100% |

All scenarios classified as **PUBLIC_API_ONLY**. No synthesized helpers. No escalations.

## Per-Scenario Results

### HS-001: Declared zero-argument callable returns the exact canary value
- **Priority**: P1
- **Category**: happy-path
- **Classification**: PUBLIC_API_ONLY
- **Generated test**: `runs/20260322T000705Z-2cc56e4f0789/eval_tests/attempt2/HS-001.py`
- **Mapping**: `runs/20260322T000705Z-2cc56e4f0789/eval_tests/attempt2/HS-001.mapping.md`
- **Runs**: 3/3 PASSED
  - Run 1: PASS (5/5 assertions, 0.151s)
  - Run 2: PASS (5/5 assertions, 0.148s)
  - Run 3: PASS (5/5 assertions, 0.141s)
- **Aggregate**: PASS (3/3, threshold 2/3)

### HS-002: Imported caller path succeeds through the test-facing boundary
- **Priority**: P1
- **Category**: lifecycle
- **Classification**: PUBLIC_API_ONLY
- **Generated test**: `runs/20260322T000705Z-2cc56e4f0789/eval_tests/attempt2/HS-002.py`
- **Mapping**: `runs/20260322T000705Z-2cc56e4f0789/eval_tests/attempt2/HS-002.mapping.md`
- **Runs**: 3/3 PASSED
  - Run 1: PASS (5/5 assertions, 0.145s)
  - Run 2: PASS (5/5 assertions, 0.147s)
  - Run 3: PASS (5/5 assertions, 0.145s)
- **Aggregate**: PASS (3/3, threshold 2/3)

### HS-003: Noncompliant return values are rejected as contract failures
- **Priority**: P1
- **Category**: failure-injection
- **Classification**: PUBLIC_API_ONLY
- **Generated test**: `runs/20260322T000705Z-2cc56e4f0789/eval_tests/attempt2/HS-003.py`
- **Mapping**: `runs/20260322T000705Z-2cc56e4f0789/eval_tests/attempt2/HS-003.mapping.md`
- **Runs**: 3/3 PASSED
  - Run 1: PASS (4/4 assertions, 0.160s)
  - Run 2: PASS (4/4 assertions, 0.158s)
  - Run 3: PASS (4/4 assertions, 0.143s)
- **Aggregate**: PASS (3/3, threshold 2/3)

### HS-004: Scope drift is rejected when extra files, dependencies, or framework behaviors appear
- **Priority**: P1
- **Category**: integrity
- **Classification**: PUBLIC_API_ONLY
- **Generated test**: `runs/20260322T000705Z-2cc56e4f0789/eval_tests/attempt2/HS-004.py`
- **Mapping**: `runs/20260322T000705Z-2cc56e4f0789/eval_tests/attempt2/HS-004.mapping.md`
- **Runs**: 3/3 PASSED
  - Run 1: PASS (5/5 assertions, 0.151s)
  - Run 2: PASS (5/5 assertions, 0.153s)
  - Run 3: PASS (5/5 assertions, 0.142s)
- **Aggregate**: PASS (3/3, threshold 2/3)

## Verdict Logic

1. All P0 scenarios passed: N/A (none declared)
2. All P1 scenarios passed: YES (4/4)
3. Overall pass rate >= 90%: YES (100%)

All three conditions satisfied.

## Failed Scenarios

None.

Final verdict: PASS
