# D9: Holdout Scenarios — FMWK-001-ledger
Meta: v:1.0.0 | contracts:D4 v1.0.0 | status:Final | author:Holdout Agent | last run:Not yet executed
CRITICAL: Builder agent MUST NOT see these scenarios before completing their work.

---

## Environment Variables

Set before running any scenario:

```
LEDGER_MODULE         # default: ledger   — importable Python module path
IMMUDB_HOST           # default: localhost
IMMUDB_TEST_USER      # default: immudb
IMMUDB_TEST_PASS      # default: immudb
```

---

## HS-001: Append Assigns Chain Fields; Caller Receives Integer Sequence

```yaml
component: FMWK-001-ledger
scenario: hs-001-append-chain-linkage
priority: P0
validates: SC-001, SC-002, SC-006, SC-007
contracts: IN-001, OUT-001, SIDE-001, SIDE-002
type: Happy path
```

**Setup**

```bash
docker pull codenotary/immudb:latest
docker run -d --name hs001-immudb -p 13322:3322 codenotary/immudb:latest
sleep 5
# Create test database using immudb SDK directly (NOT via Ledger module — test infrastructure only)
python3 - <<'PYEOF'
from immudb import ImmudbClient
c = ImmudbClient("localhost:13322")
c.login(b"immudb", b"immudb")
c.createDatabase(b"ledger_hs001")
c.logout()
print("Setup OK: ledger_hs001 database created")
PYEOF
```

**Execute**

```bash
python3 - <<'PYEOF'
import os, sys, json, importlib, hashlib

mod = importlib.import_module(os.environ.get('LEDGER_MODULE', 'ledger'))
Ledger = mod.Ledger

l = Ledger()
l.connect({
    "host": os.environ.get('IMMUDB_HOST', 'localhost'),
    "port": 13322,
    "database": "ledger_hs001",
    "username": os.environ.get('IMMUDB_TEST_USER', 'immudb'),
    "password": os.environ.get('IMMUDB_TEST_PASS', 'immudb'),
})

ev0 = {
    "event_id": "01950000-0000-7000-8000-000000000000",
    "event_type": "session_start",
    "schema_version": "1.0.0",
    "timestamp": "2026-03-01T00:00:00Z",
    "provenance": {"framework_id": "FMWK-001", "pack_id": "PC-001-ledger", "actor": "system"},
    "payload": {"session_id": "s0"},
}
ev1 = {
    "event_id": "01950000-0000-7000-8000-000000000001",
    "event_type": "session_start",
    "schema_version": "1.0.0",
    "timestamp": "2026-03-01T00:00:01Z",
    "provenance": {"framework_id": "FMWK-001", "pack_id": "PC-001-ledger", "actor": "system"},
    "payload": {"session_id": "s1"},
}

seq0 = l.append(ev0)
seq1 = l.append(ev1)

r0 = l.read(seq0)
r1 = l.read(seq1)

with open('/tmp/hs001_results.json', 'w') as f:
    json.dump({
        "seq0": seq0,
        "seq1": seq1,
        "seq0_type": type(seq0).__name__,
        "r0": r0,
        "r1": r1,
    }, f)
print("Execute OK")
PYEOF
```

**Verify**

| Check | What to Examine | PASS Condition | FAIL Condition |
|-------|----------------|----------------|----------------|
| V1 | Type of seq0 | `isinstance(seq0, int)` | None, dict, str, or any non-int |
| V2 | seq0 value | `seq0 == 0` | Any other value |
| V3 | seq1 value | `seq1 == 1` | Any other value |
| V4 | Genesis sentinel — exact string | `r0['previous_hash'] == "sha256:" + "0"*64` | Wrong prefix, wrong length, uppercase, any deviation |
| V5 | Hash format r0 | matches `^sha256:[0-9a-f]{64}$` | Wrong case, wrong prefix, wrong length |
| V6 | Chain linkage r1→r0 | `r1['previous_hash'] == r0['hash']` | Any mismatch |
| V7 | Independent hash recompute r0 | recomputed hash (per SIDE-002) equals `r0['hash']` | Stored hash does not match content |

```bash
python3 - <<'PYEOF'
import json, hashlib, re, sys

with open('/tmp/hs001_results.json') as f:
    d = json.load(f)

seq0 = d['seq0']
seq1 = d['seq1']
r0 = d['r0']
r1 = d['r1']
GENESIS_SENTINEL = "sha256:" + "0" * 64
HASH_RE = re.compile(r'^sha256:[0-9a-f]{64}$')

def recompute_hash(event_dict):
    """Recompute expected hash per SIDE-002 exactly — independent of builder code."""
    ev = {k: v for k, v in event_dict.items() if k != 'hash'}
    canon = json.dumps(ev, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canon.encode('utf-8')).hexdigest()

failures = []

if d['seq0_type'] != 'int':
    failures.append(f"V1: seq0 type={d['seq0_type']!r}, expected int")
if seq0 != 0:
    failures.append(f"V2: seq0={seq0!r}, expected 0")
if seq1 != 1:
    failures.append(f"V3: seq1={seq1!r}, expected 1")
if r0.get('previous_hash') != GENESIS_SENTINEL:
    failures.append(f"V4: genesis sentinel mismatch: {r0.get('previous_hash')!r} (must be exactly 'sha256:' + 64 zeros)")
if not HASH_RE.match(r0.get('hash', '')):
    failures.append(f"V5: r0 hash format invalid: {r0.get('hash')!r}")
if r1.get('previous_hash') != r0.get('hash'):
    failures.append(f"V6: chain broken — r1.previous_hash={r1.get('previous_hash')!r} != r0.hash={r0.get('hash')!r}")

expected_hash = recompute_hash(r0)
if r0.get('hash') != expected_hash:
    failures.append(f"V7: independent hash mismatch — stored={r0.get('hash')!r}, recomputed={expected_hash!r}")

if failures:
    print("FAIL:\n" + "\n".join(failures))
    sys.exit(1)
print("PASS: HS-001")
sys.exit(0)
PYEOF
```

**Cleanup**

```bash
docker rm -f hs001-immudb
rm -f /tmp/hs001_results.json
```

---

## HS-002: read_since Returns Ordered Gapless Slice; Empty at Tip; Snapshot Event Written Correctly

```yaml
component: FMWK-001-ledger
scenario: hs-002-read-since-tip-snapshot
priority: P0
validates: SC-003, SC-008, SC-009
contracts: IN-004, IN-006, OUT-002, OUT-004
type: Happy path + Integration
```

**Setup**

```bash
docker run -d --name hs002-immudb -p 13323:3322 codenotary/immudb:latest
sleep 5
python3 - <<'PYEOF'
from immudb import ImmudbClient
c = ImmudbClient("localhost:13323")
c.login(b"immudb", b"immudb")
c.createDatabase(b"ledger_hs002")
c.logout()
print("Setup OK")
PYEOF
```

**Execute**

```bash
python3 - <<'PYEOF'
import os, json, importlib

mod = importlib.import_module(os.environ.get('LEDGER_MODULE', 'ledger'))
Ledger = mod.Ledger

l = Ledger()
l.connect({
    "host": os.environ.get('IMMUDB_HOST', 'localhost'),
    "port": 13323,
    "database": "ledger_hs002",
    "username": os.environ.get('IMMUDB_TEST_USER', 'immudb'),
    "password": os.environ.get('IMMUDB_TEST_PASS', 'immudb'),
})

# SC-009: check empty ledger tip BEFORE any writes
tip_empty = l.get_tip()

# Write 20 events (sequences 0-19)
for i in range(20):
    ev = {
        "event_id": f"01950001-0000-7000-8000-{i:012x}",
        "event_type": "session_start",
        "schema_version": "1.0.0",
        "timestamp": "2026-03-01T00:00:00Z",
        "provenance": {"framework_id": "FMWK-001", "pack_id": "PC-001-ledger", "actor": "system"},
        "payload": {"index": i},
    }
    l.append(ev)

tip_after = l.get_tip()

# SC-003: read events after sequence 9 (expect events 10-19)
events_since_9 = l.read_since(9)

# SC-003 edge: at tip — must return empty list, not error
events_at_tip = l.read_since(19)

# SC-003 edge: read_since(-1) should return all 20 events (sequences > -1)
events_since_neg1 = l.read_since(-1)

# SC-008: append a snapshot_created event and read it back
snap_ev = {
    "event_id": "01950001-0000-7001-8000-000000000000",
    "event_type": "snapshot_created",
    "schema_version": "1.0.0",
    "timestamp": "2026-03-01T01:00:00Z",
    "provenance": {"framework_id": "FMWK-001", "pack_id": "PC-001-ledger", "actor": "system"},
    "payload": {
        "snapshot_path": "/snapshots/19.snapshot",
        "snapshot_hash": "sha256:" + "a" * 64,
        "snapshot_sequence": 19,
    },
}
snap_seq = l.append(snap_ev)
snap_event = l.read(snap_seq)

with open('/tmp/hs002_results.json', 'w') as f:
    json.dump({
        "tip_empty": tip_empty,
        "tip_after": tip_after,
        "events_since_9": events_since_9,
        "events_at_tip": events_at_tip,
        "events_since_neg1_count": len(events_since_neg1),
        "snap_seq": snap_seq,
        "snap_event": snap_event,
    }, f)
print("Execute OK")
PYEOF
```

**Verify**

| Check | What to Examine | PASS Condition | FAIL Condition |
|-------|----------------|----------------|----------------|
| V1 | Empty ledger tip — sequence_number | `== -1` | Any other value |
| V2 | Empty ledger tip — hash | `== ""` | Non-empty string |
| V3 | tip_after.sequence_number | `== 19` | Not 19 |
| V4 | tip_after.hash format | matches `^sha256:[0-9a-f]{64}$` | Wrong format |
| V5 | events_since_9 count | `len == 10` | != 10 (gap, dup, or missing) |
| V6 | events_since_9 first sequence | `== 10` | != 10 |
| V7 | events_since_9 last sequence | `== 19` | != 19 |
| V8 | Strict ascending — no gaps | every `seq[i+1] == seq[i] + 1` | Any gap or inversion |
| V9 | read_since(tip) returns empty | `events_at_tip == []` | Non-empty list |
| V10 | read_since(-1) returns all 20 | `count == 20` | != 20 |
| V11 | snap_event.sequence | `== 20` | != 20 |
| V12 | snap_event payload — snapshot_path | present | Missing key |
| V13 | snap_event payload — snapshot_hash | present | Missing key |
| V14 | snap_event payload — snapshot_sequence | present and `== 19` | Missing or wrong value |

```bash
python3 - <<'PYEOF'
import json, re, sys

with open('/tmp/hs002_results.json') as f:
    d = json.load(f)

tip_e = d['tip_empty']
tip_a = d['tip_after']
ev9 = d['events_since_9']
at_tip = d['events_at_tip']
snap = d['snap_event']
HASH_RE = re.compile(r'^sha256:[0-9a-f]{64}$')
failures = []

# V1, V2: empty ledger tip shape (D4 OUT-004 explicit contract)
if tip_e.get('sequence_number') != -1:
    failures.append(f"V1: empty tip sequence_number={tip_e.get('sequence_number')!r}, expected -1")
if tip_e.get('hash') != "":
    failures.append(f"V2: empty tip hash={tip_e.get('hash')!r}, expected empty string")

# V3, V4: tip after 20 writes
if tip_a.get('sequence_number') != 19:
    failures.append(f"V3: tip.sequence_number={tip_a.get('sequence_number')!r}, expected 19")
if not HASH_RE.match(tip_a.get('hash', '')):
    failures.append(f"V4: tip hash format invalid: {tip_a.get('hash')!r}")

# V5-V8: read_since(9) ordering and completeness
if len(ev9) != 10:
    failures.append(f"V5: events_since_9 count={len(ev9)}, expected 10")
elif ev9[0].get('sequence') != 10:
    failures.append(f"V6: first event sequence={ev9[0].get('sequence')!r}, expected 10")
elif ev9[-1].get('sequence') != 19:
    failures.append(f"V7: last event sequence={ev9[-1].get('sequence')!r}, expected 19")
else:
    for i in range(len(ev9) - 1):
        if ev9[i + 1]['sequence'] != ev9[i]['sequence'] + 1:
            failures.append(f"V8: gap/inversion at index {i}: {ev9[i]['sequence']} -> {ev9[i+1]['sequence']}")
            break

# V9: at-tip returns empty list (not error)
if at_tip != []:
    failures.append(f"V9: at-tip not empty: {at_tip!r} — must be [] per D4 IN-004")

# V10: read_since(-1) returns all 20
if d['events_since_neg1_count'] != 20:
    failures.append(f"V10: read_since(-1) count={d['events_since_neg1_count']}, expected 20")

# V11-V14: snapshot event
if snap.get('sequence') != 20:
    failures.append(f"V11: snap sequence={snap.get('sequence')!r}, expected 20")
payload = snap.get('payload', {})
for field in ('snapshot_path', 'snapshot_hash', 'snapshot_sequence'):
    if field not in payload:
        failures.append(f"V12/V13/V14: snap payload missing field {field!r}")
if payload.get('snapshot_sequence') != 19:
    failures.append(f"V14: snap payload.snapshot_sequence={payload.get('snapshot_sequence')!r}, expected 19")

if failures:
    print("FAIL:\n" + "\n".join(failures))
    sys.exit(1)
print("PASS: HS-002")
sys.exit(0)
PYEOF
```

**Cleanup**

```bash
docker rm -f hs002-immudb
rm -f /tmp/hs002_results.json
```

---

## HS-003: verify_chain Returns Exact VerifyChainResult Shape on Corruption; Functions Without Kernel

```yaml
component: FMWK-001-ledger
scenario: hs-003-chain-verify-corruption-shape
priority: P0
validates: SC-004, SC-005, SC-EC-001
contracts: IN-005, OUT-003, ERR-002
type: Error path + Side-effect verification
```

**SC-005 isolation note**: This test imports ONLY the Ledger module and immudb SDK — no FMWK-002, FMWK-003, FMWK-004, FMWK-005, HO1, HO2, or Graph services are imported or started. The subprocess environment mimics cold-storage CLI verification.

**Setup**

```bash
docker run -d --name hs003-immudb -p 13324:3322 codenotary/immudb:latest
sleep 5
python3 - <<'PYEOF'
from immudb import ImmudbClient
c = ImmudbClient("localhost:13324")
c.login(b"immudb", b"immudb")
c.createDatabase(b"ledger_hs003")
c.logout()
print("Setup OK")
PYEOF
```

**Execute**

```bash
python3 - <<'PYEOF'
# ISOLATION: import ONLY ledger module and immudb SDK.
# No other FMWK modules. Simulates cold-storage CLI context (SC-005).
import os, json, importlib

mod = importlib.import_module(os.environ.get('LEDGER_MODULE', 'ledger'))
Ledger = mod.Ledger

l = Ledger()
l.connect({
    "host": os.environ.get('IMMUDB_HOST', 'localhost'),
    "port": 13324,
    "database": "ledger_hs003",
    "username": os.environ.get('IMMUDB_TEST_USER', 'immudb'),
    "password": os.environ.get('IMMUDB_TEST_PASS', 'immudb'),
})

# Write 6 events (sequences 0-5)
for i in range(6):
    ev = {
        "event_id": f"01950002-0000-7000-8000-{i:012x}",
        "event_type": "session_start",
        "schema_version": "1.0.0",
        "timestamp": "2026-03-01T00:00:00Z",
        "provenance": {"framework_id": "FMWK-001", "pack_id": "PC-001-ledger", "actor": "system"},
        "payload": {"idx": i},
    }
    l.append(ev)

# Verify intact chain before corruption (must be valid)
result_intact = l.verify_chain(start=0, end=5)

# Corrupt event 3: overwrite its key in immudb with a wrong hash.
# immudb is append-only per-key (versioned); the latest version is returned on GET.
# Writing a new version of key "000000000003" with a tampered hash field
# causes verify_chain() to see a hash that does not match recomputed content.
# This uses immudb SDK directly — test infrastructure, NOT Ledger module.
from immudb import ImmudbClient
ci = ImmudbClient("localhost:13324")
ci.login(b"immudb", b"immudb")
ci.useDatabase(b"ledger_hs003")

key = b"000000000003"
raw = ci.get(key)
event3 = json.loads(raw.value.decode('utf-8'))
# Tamper: replace stored hash with a wrong value (preserves all other fields)
event3["hash"] = "sha256:" + "d" * 63 + "0"   # invalid — will not match content
corrupted_bytes = json.dumps(
    event3, sort_keys=True, separators=(',', ':'), ensure_ascii=False
).encode('utf-8')
ci.set(key, corrupted_bytes)
ci.logout()

# verify_chain on full range — must detect corruption at event 3
result_corrupted = l.verify_chain(start=0, end=5)

# verify_chain on clean sub-range (events 0-2) — must still pass
result_clean_range = l.verify_chain(start=0, end=2)

with open('/tmp/hs003_results.json', 'w') as f:
    json.dump({
        "result_intact": result_intact,
        "result_corrupted": result_corrupted,
        "result_clean_range": result_clean_range,
    }, f)
print("Execute OK")
PYEOF
```

**Verify**

| Check | What to Examine | PASS Condition | FAIL Condition |
|-------|----------------|----------------|----------------|
| V1 | Intact chain — valid | `result_intact['valid'] == True` | False or missing |
| V2 | Corrupted result — 'valid' key present | `'valid' in result_corrupted` | Missing key |
| V3 | Corrupted result — valid == False | `result_corrupted['valid'] == False` | True (corruption undetected) |
| V4 | Corrupted result — 'break_at' key present | `'break_at' in result_corrupted` | **Missing — D4 shape violation. Code throwing a generic exception satisfies a weak test but violates OUT-003.** |
| V5 | Corrupted result — break_at == 3 | `result_corrupted['break_at'] == 3` | Any other integer |
| V6 | Clean sub-range passes | `result_clean_range['valid'] == True` | False (overcorrection past the corruption point) |
| V7 | verify_chain does not raise | result returned as dict, no exception | Exception propagated to caller instead of returned result |

```bash
python3 - <<'PYEOF'
import json, sys

with open('/tmp/hs003_results.json') as f:
    d = json.load(f)

intact = d['result_intact']
corrupted = d['result_corrupted']
clean_r = d['result_clean_range']
failures = []

# V1
if intact.get('valid') is not True:
    failures.append(f"V1: intact chain not valid: {intact!r}")

# V2, V3, V4, V5 — these are the mandatory D4 contract shape checks
if 'valid' not in corrupted:
    failures.append(f"V2: 'valid' key missing from result: {corrupted!r}")
elif corrupted['valid'] is not False:
    failures.append(f"V3: valid={corrupted['valid']!r}, expected False — corruption undetected")

if 'break_at' not in corrupted:
    failures.append(
        f"V4: 'break_at' key MISSING from result — D4 OUT-003 shape violation. "
        f"A generic exception or bare False satisfies a weak test but not the D4 contract. "
        f"Result was: {corrupted!r}"
    )
elif corrupted['break_at'] != 3:
    failures.append(f"V5: break_at={corrupted['break_at']!r}, expected 3")

# V6
if clean_r.get('valid') is not True:
    failures.append(f"V6: clean sub-range (0-2) failed: {clean_r!r}")

if failures:
    print("FAIL:\n" + "\n".join(failures))
    sys.exit(1)
print("PASS: HS-003")
sys.exit(0)
PYEOF
```

**Cleanup**

```bash
docker rm -f hs003-immudb
rm -f /tmp/hs003_results.json
```

---

## HS-004: Float Payload Raises LedgerSerializationError with Correct Code; No immudb Write

```yaml
component: FMWK-001-ledger
scenario: hs-004-serialization-error-shape
priority: P0
validates: SC-001 (failure path)
contracts: IN-001, SIDE-002, ERR-004
type: Error path
```

**Setup**

```bash
docker run -d --name hs004-immudb -p 13325:3322 codenotary/immudb:latest
sleep 5
python3 - <<'PYEOF'
from immudb import ImmudbClient
c = ImmudbClient("localhost:13325")
c.login(b"immudb", b"immudb")
c.createDatabase(b"ledger_hs004")
c.logout()
print("Setup OK")
PYEOF
```

**Execute**

```bash
python3 - <<'PYEOF'
import os, json, importlib

mod = importlib.import_module(os.environ.get('LEDGER_MODULE', 'ledger'))
Ledger = mod.Ledger
LedgerSerializationError = mod.LedgerSerializationError

l = Ledger()
l.connect({
    "host": os.environ.get('IMMUDB_HOST', 'localhost'),
    "port": 13325,
    "database": "ledger_hs004",
    "username": os.environ.get('IMMUDB_TEST_USER', 'immudb'),
    "password": os.environ.get('IMMUDB_TEST_PASS', 'immudb'),
})

# Append one valid event to establish a non-zero state to detect any unintended write
ev_valid = {
    "event_id": "01950003-0000-7000-8000-000000000000",
    "event_type": "session_start",
    "schema_version": "1.0.0",
    "timestamp": "2026-03-01T00:00:00Z",
    "provenance": {"framework_id": "FMWK-001", "pack_id": "PC-001-ledger", "actor": "system"},
    "payload": {"valid": True},
}
l.append(ev_valid)
tip_before = l.get_tip()

# Attempt to append event with a float value in payload (forbidden per IN-001 and SIDE-002)
ev_bad = {
    "event_id": "01950003-0000-7000-8000-000000000001",
    "event_type": "session_start",
    "schema_version": "1.0.0",
    "timestamp": "2026-03-01T00:00:01Z",
    "provenance": {"framework_id": "FMWK-001", "pack_id": "PC-001-ledger", "actor": "system"},
    "payload": {"signal_value": 0.75},   # 0.75 is float — PROHIBITED
}

raised_type = None
raised_code = None
try:
    l.append(ev_bad)
except LedgerSerializationError as e:
    raised_type = "LedgerSerializationError"
    raised_code = getattr(e, 'code', None)
except Exception as e:
    raised_type = type(e).__name__
    raised_code = None

tip_after = l.get_tip()

with open('/tmp/hs004_results.json', 'w') as f:
    json.dump({
        "tip_before": tip_before,
        "raised_type": raised_type,
        "raised_code": raised_code,
        "tip_after": tip_after,
    }, f)
print("Execute OK")
PYEOF
```

**Verify**

| Check | What to Examine | PASS Condition | FAIL Condition |
|-------|----------------|----------------|----------------|
| V1 | Exception type raised | `raised_type == "LedgerSerializationError"` | Generic Exception, ValueError, TypeError, or no exception at all |
| V2 | error.code attribute | `raised_code == "LEDGER_SERIALIZATION_ERROR"` | None, missing attribute, wrong string — D4 ERR-004 shape violation |
| V3 | tip sequence unchanged | `tip_after.sequence_number == tip_before.sequence_number` | Incremented — partial write occurred before serialization check |
| V4 | tip hash unchanged | `tip_after.hash == tip_before.hash` | Changed — write occurred despite error |

```bash
python3 - <<'PYEOF'
import json, sys

with open('/tmp/hs004_results.json') as f:
    d = json.load(f)

failures = []

if d['raised_type'] != 'LedgerSerializationError':
    failures.append(
        f"V1: expected LedgerSerializationError, got {d['raised_type']!r} — "
        f"D4 ERR-004 requires the exact LedgerSerializationError class, not a generic exception"
    )
if d['raised_code'] != 'LEDGER_SERIALIZATION_ERROR':
    failures.append(
        f"V2: error.code={d['raised_code']!r}, expected 'LEDGER_SERIALIZATION_ERROR' — "
        f"D4 ERR-004 shape violation (code attribute must be present and exact)"
    )

tb = d['tip_before']
ta = d['tip_after']
if tb.get('sequence_number') != ta.get('sequence_number'):
    failures.append(
        f"V3: tip sequence changed {tb.get('sequence_number')} -> {ta.get('sequence_number')} — "
        f"partial write to immudb before serialization check"
    )
if tb.get('hash') != ta.get('hash'):
    failures.append(f"V4: tip hash changed — a write occurred despite the serialization error")

if failures:
    print("FAIL:\n" + "\n".join(failures))
    sys.exit(1)
print("PASS: HS-004")
sys.exit(0)
PYEOF
```

**Cleanup**

```bash
docker rm -f hs004-immudb
rm -f /tmp/hs004_results.json
```

---

## HS-005: connect() to Missing Database Raises LedgerConnectionError Immediately; Zero Admin Operations

```yaml
component: FMWK-001-ledger
scenario: hs-005-connect-missing-database-zero-admin
priority: P0
validates: SC-EC-004
contracts: IN-007, ERR-001
type: Error path + Integration
```

**Setup**

```bash
docker run -d --name hs005-immudb -p 13326:3322 codenotary/immudb:latest
sleep 5
# DO NOT create a "ledger" database. Verify it is absent.
python3 - <<'PYEOF'
from immudb import ImmudbClient
c = ImmudbClient("localhost:13326")
c.login(b"immudb", b"immudb")
dbs = [d.decode('utf-8') if isinstance(d, bytes) else d for d in c.databaseList()]
if "ledger" in dbs:
    print(f"SETUP ERROR: 'ledger' database already exists: {dbs}")
    import sys; sys.exit(1)
c.logout()
print(f"Setup OK: ledger absent. Existing databases: {dbs}")
PYEOF
```

**Execute**

```bash
python3 - <<'PYEOF'
import os, json, importlib

mod = importlib.import_module(os.environ.get('LEDGER_MODULE', 'ledger'))
Ledger = mod.Ledger
LedgerConnectionError = mod.LedgerConnectionError

l = Ledger()
cfg = {
    "host": os.environ.get('IMMUDB_HOST', 'localhost'),
    "port": 13326,
    "database": "ledger",   # Does NOT exist — GENESIS not run
    "username": os.environ.get('IMMUDB_TEST_USER', 'immudb'),
    "password": os.environ.get('IMMUDB_TEST_PASS', 'immudb'),
}

raised_at = None  # "connect" or "first_operation" or None
raised_type = None
raised_code = None

try:
    l.connect(cfg)
    raised_at = None  # connect() did not raise
    # If connect() silently succeeded, try a first operation
    try:
        l.get_tip()
    except LedgerConnectionError as e:
        raised_at = "first_operation"
        raised_type = "LedgerConnectionError"
        raised_code = getattr(e, 'code', None)
    except Exception as e:
        raised_at = "first_operation"
        raised_type = type(e).__name__
        raised_code = None
except LedgerConnectionError as e:
    raised_at = "connect"
    raised_type = "LedgerConnectionError"
    raised_code = getattr(e, 'code', None)
except Exception as e:
    raised_at = "connect"
    raised_type = type(e).__name__
    raised_code = None

# Check whether the "ledger" database was created during the attempt
from immudb import ImmudbClient
ci = ImmudbClient("localhost:13326")
ci.login(b"immudb", b"immudb")
dbs_after = [d.decode('utf-8') if isinstance(d, bytes) else d for d in ci.databaseList()]
ledger_db_created = "ledger" in dbs_after
ci.logout()

with open('/tmp/hs005_results.json', 'w') as f:
    json.dump({
        "raised_at": raised_at,
        "raised_type": raised_type,
        "raised_code": raised_code,
        "ledger_db_created": ledger_db_created,
        "dbs_after": dbs_after,
    }, f)
print("Execute OK")
PYEOF
```

**Verify**

| Check | What to Examine | PASS Condition | FAIL Condition |
|-------|----------------|----------------|----------------|
| V1 | Exception type raised | `raised_type == "LedgerConnectionError"` | Generic exception, or no exception at all |
| V2 | error.code attribute | `raised_code == "LEDGER_CONNECTION_ERROR"` | None, missing, or wrong string — D4 ERR-001 shape violation |
| V3 | Error raised at connect() not deferred | `raised_at == "connect"` | "first_operation" — D4 IN-007 says "fail immediately" |
| V4 | Zero admin operations — database not created | `ledger_db_created == False` | True — Ledger called CreateDatabaseV2 or equivalent admin op |

```bash
python3 - <<'PYEOF'
import json, sys

with open('/tmp/hs005_results.json') as f:
    d = json.load(f)

failures = []

if d['raised_type'] != 'LedgerConnectionError':
    failures.append(
        f"V1: expected LedgerConnectionError, got {d['raised_type']!r} — "
        f"D4 IN-007 requires LedgerConnectionError when database does not exist"
    )
if d['raised_code'] != 'LEDGER_CONNECTION_ERROR':
    failures.append(
        f"V2: error.code={d['raised_code']!r}, expected 'LEDGER_CONNECTION_ERROR' — "
        f"D4 ERR-001 shape violation (code attribute must be present and exact)"
    )
if d['raised_at'] != 'connect':
    failures.append(
        f"V3: error raised at {d['raised_at']!r}, expected 'connect' — "
        f"D4 IN-007 says 'MUST fail immediately' at connect(), not deferred to first operation"
    )
if d['ledger_db_created']:
    failures.append(
        f"V4: 'ledger' database WAS CREATED — Ledger called an admin operation (CreateDatabaseV2 or equivalent). "
        f"D4 IN-007 prohibits any admin gRPC call. Databases after attempt: {d['dbs_after']}"
    )

if failures:
    print("FAIL:\n" + "\n".join(failures))
    sys.exit(1)
print("PASS: HS-005")
sys.exit(0)
PYEOF
```

**Cleanup**

```bash
docker rm -f hs005-immudb
rm -f /tmp/hs005_results.json
```

---

## Coverage Matrix

| D2 Scenario | Priority | Holdout Coverage | Notes |
|-------------|----------|-----------------|-------|
| SC-001 | P0 | HS-001 (happy path), HS-004 (failure path) | Full |
| SC-002 | P0 | HS-001 (V — read back by sequence) | Full |
| SC-003 | P0 | HS-002 (V5-V10) | Full — includes at-tip empty list |
| SC-004 | P0 | HS-003 (V1, intact chain) | Full |
| SC-005 | P0 | HS-003 (import isolation note) | Verified by process-level import constraint |
| SC-006 | P0 | HS-001 (V4: exact sentinel, exact string comparison) | Full |
| SC-007 | P0 | HS-001 (V6: r1.previous_hash == r0.hash) | Full |
| SC-008 | P1 | HS-002 (V11-V14) | Full |
| SC-009 | P1 | HS-002 (V1-V4, including empty ledger shape) | Full |
| SC-EC-001 | P0 | HS-003 (V2-V5, shape-verified) | Full — D4 break_at shape required |
| SC-EC-002 | P1 | None | Deferred to builder unit tests. D2 testing approach: "Use mock to simulate atomicity failure." Requires implementation-specific mock injection into atomicity mechanism. LedgerSequenceError code shape verified via builder unit test. |
| SC-EC-003 | P1 | None | Deferred to builder unit tests. D2 testing approach: "Mock immudb to fail after connection established." Requires precise timing control during gRPC call. LedgerConnectionError code shape covered by HS-005 proxy. |
| SC-EC-004 | P0 | HS-005 (V1-V4) | Full — admin prohibition verified via post-connect immudb database list |

### Coverage Gate Status

- All P0 scenarios: **COVERED** (SC-001 through SC-EC-001, SC-EC-004)
- All P1 scenarios: **COVERED or JUSTIFIED DEFERRAL**
  - SC-EC-002, SC-EC-003: Deferred with documented justification — D2 explicitly specifies mock-based unit test approach for both

---

## Run Protocol

**When**: After builder delivers code and builder's handoff tests pass.

**Pre-requisites**:
- Docker available and `codenotary/immudb:latest` image pulled
- `immudb-py` Python package installed (`pip install immudb-py`)
- `LEDGER_MODULE` env var set to the builder's importable module path (default: `ledger`)
- Run from project root with the FMWK-001-ledger package installed or on `PYTHONPATH`

**Order**:
1. Run HS-001 through HS-005 in sequence. Any P0 failure stops execution.
2. Each scenario is independent — Docker containers use separate ports (13322-13326).

**Threshold**: All 5 scenarios must exit 0. No partial credit.

**On failure**: File against responsible D8 task. Include:
- Scenario ID (HS-NNN)
- Failed check (V#)
- Violated D4 contract (ERR-NNN, IN-NNN, or OUT-NNN)
- Actual value vs expected value (exact strings)
