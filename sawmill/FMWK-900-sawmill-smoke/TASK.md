# Task: FMWK-900-sawmill-smoke

## Framework
- ID: FMWK-900
- Name: sawmill-smoke
- Layer: SYSTEM-TEST

## What to Spec

This is a **system test canary**, not a product framework. It exists solely to exercise the Sawmill pipeline end-to-end. The spec should be as minimal as possible — just enough to produce valid D1-D6 artifacts.

### Build Target

One Python module with one function:

```python
# staging/FMWK-900-sawmill-smoke/smoke.py
def ping() -> str:
    """System test canary function."""
    return "pong"
```

One test:

```python
# staging/FMWK-900-sawmill-smoke/test_smoke.py
from smoke import ping

def test_ping():
    assert ping() == "pong"
```

That is the entire scope. Nothing else.

## Owns
- `smoke.py` — one function
- `test_smoke.py` — one test

## Dependencies
- None. No platform_sdk, no immudb, no Docker, no external services.

## Constraints
- This is NOT a product framework. Do NOT apply KERNEL framework patterns.
- Do NOT create error classes, schemas, adapters, or data models.
- Do NOT reference the nine primitives — this framework is outside that scope.
- The D1-D6 artifacts should each be extremely short (a few lines per section).
- D5 (Research) should state "No research needed — trivial system test."
- D6 (Gap Analysis) should have zero open items.
