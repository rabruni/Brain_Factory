# FMWK-001-ledger — Ledger Primitive

Append-only, hash-chained event store for DoPeJarMo. KERNEL phase.

## Overview

The `ledger` package implements the Ledger primitive: every state mutation
in DoPeJarMo (node creation, signal delta, session boundary, package install)
enters the system as a `LedgerClient.append()` call from the Write Path
(FMWK-002). The Ledger assigns monotonic sequence numbers, computes SHA-256
hash chains using deterministic canonical JSON, and persists to immudb via
`ImmudbStore`.

## Usage

```python
from ledger import LedgerClient, EventType
from platform_sdk.tier0_core.config import get_config

client = LedgerClient(config=get_config())
client.connect()

seq = client.append({
    "event_type": "session_start",
    "schema_version": "1.0.0",
    "timestamp": "2026-03-21T03:21:00Z",
    "provenance": {"framework_id": "FMWK-002", "pack_id": None, "actor": "system"},
    "payload": {},
})

event = client.read(seq)
tip = client.get_tip()
result = client.verify_chain()
```

## Commands

```bash
# Run unit tests (no live immudb required)
cd staging/FMWK-001-ledger && PLATFORM_ENVIRONMENT=test pytest tests/ -v

# Cold-storage CLI verification (requires: docker-compose up ledger)
cd staging/FMWK-001-ledger && python -m ledger --verify
```

## Structure

```
ledger/
  __init__.py       Public exports
  api.py            LedgerClient (6-method public interface)
  errors.py         4 typed error classes
  models.py         4 dataclasses + EventType enum (15 values)
  schemas.py        validate_event_data()
  serialization.py  canonical_json() + canonical_hash()
  store.py          ImmudbStore (threading.Lock, retry, immudb-py)
  verify.py         walk_chain() (pure function)
  __main__.py       CLI: python -m ledger --verify
tests/
  conftest.py         MockImmudbStore + fixtures
  test_api.py         LedgerClient tests (46)
  test_serialization.py  Canonical hash tests (12)
  test_store.py       ImmudbStore mock tests (13)
  test_verify.py      walk_chain tests (9)
```

## Key Design Decisions

- **Single-writer mutex**: `append()` acquires `store._lock` non-blockingly.
  Concurrent `append()` calls raise `LedgerSequenceError` immediately.
  Single kernel process assumption (D5 RQ-001).

- **Canonical JSON**: `json.dumps(d, sort_keys=True, separators=(',',':'), ensure_ascii=False)`
  — deterministic byte-level format across Python versions. Any change
  requires human approval (D1 ASK FIRST boundary).

- **Float fields as strings**: `"0.1"` not `0.1` in payloads (D5 RQ-003).
  Cross-language IEEE 754 divergence breaks hash matching.

- **Empty Ledger sentinel**: `TipRecord(sequence_number=-1, hash="sha256:"+"0"*64)`.
  Eliminates special case in Write Path genesis handling (D6 CLR-002).

- **Fail closed**: `LedgerConnectionError` always raised on immudb failure.
  No buffering, no silent fallback (D1 Article 9).
