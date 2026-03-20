# FMWK-001-ledger

Append-only, hash-chained event storage for DoPeJarMo. This staged package owns event validation, canonical hashing, linear append/read behavior, and online or offline chain verification. It does not provision databases, fold graph state, evaluate gates, or interpret event meaning beyond the approved payload catalog.

## Public Surface

- `Ledger.append(request) -> LedgerEvent`
- `Ledger.read(sequence_number) -> LedgerEvent`
- `Ledger.read_range(start, end) -> list[LedgerEvent]`
- `Ledger.read_since(sequence_number) -> list[LedgerEvent]`
- `Ledger.verify_chain(start=None, end=None, source_mode="online") -> VerificationResult`
- `Ledger.get_tip(include_hash=True) -> LedgerTip`

## Local Commands

```bash
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_serialization.py
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_store.py
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_verify.py
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_api.py
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests
```

Offline verification uses exported event bytes only. The test suite exercises this shape through `verify_chain(exported_bytes, source_mode="offline")`.

Runtime database creation is intentionally out of scope. If the configured ledger database is absent or the connection fails after one reconnect attempt, the framework fails closed with `LEDGER_CONNECTION_ERROR`.
