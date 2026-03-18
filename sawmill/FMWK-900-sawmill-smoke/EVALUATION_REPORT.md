# Evaluation Report — FMWK-900-sawmill-smoke

Run ID: 20260318T041151Z-03ee32956103
Attempt: 1
Date: 2026-03-17

## P0 Scenarios

### HS-001: ping-returns-pong-from-staged-module (P0)

| Run | Setup | Execute | Verify | Result |
|-----|-------|---------|--------|--------|
| 1   | OK    | OK      | OK     | PASS   |
| 2   | OK    | OK      | OK     | PASS   |
| 3   | OK    | OK      | OK     | PASS   |

Aggregate: **PASS** (3/3)

## P1 Scenarios

### HS-002: unit-test-passes-against-staged-output (P1)

| Run | Setup | Execute | Verify | Result |
|-----|-------|---------|--------|--------|
| 1   | OK    | OK      | OK     | PASS   |
| 2   | OK    | OK      | OK     | PASS   |
| 3   | OK    | OK      | OK     | PASS   |

Aggregate: **PASS** (3/3)

### HS-003: import-failure-surfaces-import-failure-shape (P1)

| Run | Setup | Execute | Verify | Result |
|-----|-------|---------|--------|--------|
| 1   | OK    | OK      | OK     | PASS   |
| 2   | OK    | OK      | OK     | PASS   |
| 3   | OK    | OK      | OK     | PASS   |

Aggregate: **PASS** (3/3)

### HS-004: wrong-return-surfaces-wrong-return-shape (P1)

| Run | Setup | Execute | Verify | Result |
|-----|-------|---------|--------|--------|
| 1   | OK    | OK      | OK     | PASS   |
| 2   | OK    | OK      | OK     | PASS   |
| 3   | OK    | OK      | OK     | PASS   |

Aggregate: **PASS** (3/3)

### HS-005: staged-output-stays-within-canary-scope (P1)

| Run | Setup | Execute | Verify | Result |
|-----|-------|---------|--------|--------|
| 1   | OK    | OK      | OK     | PASS   |
| 2   | OK    | OK      | OK     | PASS   |
| 3   | OK    | OK      | OK     | PASS   |

Aggregate: **PASS** (3/3)

## Summary

| Priority | Scenarios | Passed | Failed |
|----------|-----------|--------|--------|
| P0       | 1         | 1      | 0      |
| P1       | 4         | 4      | 0      |
| Total    | 5         | 5      | 0      |

Pass rate: 100% (5/5)

All P0 passed. All P1 passed. Overall >= 90%.

Final verdict: PASS
