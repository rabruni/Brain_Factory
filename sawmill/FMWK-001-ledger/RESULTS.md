# Results — FMWK-001-ledger

Status: PASS
Run: `20260320T205424Z-45d3202a8b43`
Attempt: `2`
Framework: `FMWK-001-ledger`
Package: `PC-001-ledger-core`

## Summary

- Regression status: PASS
- Total passing tests: 35
- Spec deviations: none
- Issues encountered during build:
  - Corrected one hash fixture after confirming it did not match the locked canonical-byte fixture.
  - Tightened the `LedgerEvent` provenance invariant after store reads exposed a typed-model mismatch.
  - Corrected one verifier test fixture that had converted typed provenance into a plain dict.

## Mid-Build Checkpoint

- Passing test count before final regression: 35
- Latest output before final reporting:

```text
...................................                                      [100%]
35 passed in 0.06s
```

- Files created:
  - `staging/FMWK-001-ledger/README.md`
  - `staging/FMWK-001-ledger/ledger/__init__.py`
  - `staging/FMWK-001-ledger/ledger/api.py`
  - `staging/FMWK-001-ledger/ledger/errors.py`
  - `staging/FMWK-001-ledger/ledger/models.py`
  - `staging/FMWK-001-ledger/ledger/schemas.py`
  - `staging/FMWK-001-ledger/ledger/serialization.py`
  - `staging/FMWK-001-ledger/ledger/store.py`
  - `staging/FMWK-001-ledger/ledger/verify.py`
  - `staging/FMWK-001-ledger/tests/test_api.py`
  - `staging/FMWK-001-ledger/tests/test_serialization.py`
  - `staging/FMWK-001-ledger/tests/test_store.py`
  - `staging/FMWK-001-ledger/tests/test_verify.py`

## Baseline Snapshot

- Staging root: `staging/FMWK-001-ledger`
- Full regression command: `PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests`
- Baseline file inventory:
  - `staging/FMWK-001-ledger/README.md`
  - `staging/FMWK-001-ledger/ledger/__init__.py`
  - `staging/FMWK-001-ledger/ledger/api.py`
  - `staging/FMWK-001-ledger/ledger/errors.py`
  - `staging/FMWK-001-ledger/ledger/models.py`
  - `staging/FMWK-001-ledger/ledger/schemas.py`
  - `staging/FMWK-001-ledger/ledger/serialization.py`
  - `staging/FMWK-001-ledger/ledger/store.py`
  - `staging/FMWK-001-ledger/ledger/verify.py`
  - `staging/FMWK-001-ledger/tests/test_api.py`
  - `staging/FMWK-001-ledger/tests/test_serialization.py`
  - `staging/FMWK-001-ledger/tests/test_store.py`
  - `staging/FMWK-001-ledger/tests/test_verify.py`

## Command Output

Command:

```bash
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_serialization.py
```

Output:

```text
.....                                                                    [100%]
5 passed in 0.02s
```

Command:

```bash
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_store.py
```

Output:

```text
....................                                                     [100%]
20 passed in 0.03s
```

Command:

```bash
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_verify.py
```

Output:

```text
.....                                                                    [100%]
5 passed in 0.02s
```

Command:

```bash
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests/test_api.py
```

Output:

```text
.....                                                                    [100%]
5 passed in 0.02s
```

Command:

```bash
PYTHONPATH=staging/FMWK-001-ledger pytest -q staging/FMWK-001-ledger/tests
```

Output:

```text
...................................                                      [100%]
35 passed in 0.06s
```

## SHA256 Inventory

- `sha256:2fe3620483210852572036978e80dcf1d3282d238fbec3f5d03f52511f5ad6ad` `staging/FMWK-001-ledger/README.md`
- `sha256:9e9830863a375b31966be54138d32e1c10674ae9fb93473aa07bbaaf4cc92840` `staging/FMWK-001-ledger/ledger/__init__.py`
- `sha256:e888dec24a86861a028c8c420951254537761e7d0b874a36fc0389c3d6b8cc24` `staging/FMWK-001-ledger/ledger/api.py`
- `sha256:ea2e67795feee4597e8cf9d01813bf6a372d86ff2c23a5719c4546f28a757776` `staging/FMWK-001-ledger/ledger/errors.py`
- `sha256:9e55721f6bd4ecb0d755b05e376bc7771ea4be7dfad3905544efefbaa9079ef7` `staging/FMWK-001-ledger/ledger/models.py`
- `sha256:d6061f3e824069ff5f272365114fcd91392da305c92b53340c07a4c19e862f17` `staging/FMWK-001-ledger/ledger/schemas.py`
- `sha256:519a0e169fb88d740054a583cfa2254844cb6f7b1428047cc7af32541e2c366c` `staging/FMWK-001-ledger/ledger/serialization.py`
- `sha256:2359b32d2734faf41228484eaf8c147c614078e6688a5bedc1dc9201786005b3` `staging/FMWK-001-ledger/ledger/store.py`
- `sha256:b1b9a45cf11af395e4bf552d7b7211efd23e8ed11079e301b80167c3d2d555da` `staging/FMWK-001-ledger/ledger/verify.py`
- `sha256:1565a319ad7ee8c1499a2ecf7742b6a6883e72b5db2ef0187dcb1e5c7eb00507` `staging/FMWK-001-ledger/tests/test_api.py`
- `sha256:02a399b0ebd70301f1a4d460e3951ff5f30eeced1f66345996468b077fcd356d` `staging/FMWK-001-ledger/tests/test_serialization.py`
- `sha256:6351bc837270443e3f44fb54d5b6d7b354df82e2a7cc597ab71b2c03df13b921` `staging/FMWK-001-ledger/tests/test_store.py`
- `sha256:f75ec366a69807e8254baaeb3d2a0c89d1f01a56a2e842cafca435af300e6c9c` `staging/FMWK-001-ledger/tests/test_verify.py`
