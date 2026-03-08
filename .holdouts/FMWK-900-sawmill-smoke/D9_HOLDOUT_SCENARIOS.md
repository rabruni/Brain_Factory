# D9: Holdout Scenarios — FMWK-900-sawmill-smoke
Meta: v:1.0.0 | contracts: D4 1.0.0 | status:Review | author:Holdout Agent | last run:Not yet executed
CRITICAL: Builder agent MUST NOT see these scenarios before completing their work.

## Scenarios

### HS-001
```yaml
component: smoke-canary
scenario_slug: direct-ping-returns-pong
priority: P1
```
Validates: D2 SC-001, SC-002
Contracts: D4 IN-001, OUT-001
Type: Happy path

Setup:
```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
ARTIFACT_DIR="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-001"

rm -rf "$ARTIFACT_DIR"
mkdir -p "$ARTIFACT_DIR"
test -f "$REPO_ROOT/staging/FMWK-900-sawmill-smoke/smoke.py"
```

Execute:
```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
ARTIFACT_DIR="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-001"

PYTHONPATH="$REPO_ROOT/staging/FMWK-900-sawmill-smoke${PYTHONPATH:+:$PYTHONPATH}" \
python3 - <<'PY' > "$ARTIFACT_DIR/result.json"
import inspect
import json

from smoke import ping

print(json.dumps({
    "argcount": len(inspect.signature(ping).parameters),
    "callable": callable(ping),
    "result": ping(),
}, sort_keys=True))
PY
```

Verify:

| Check | What to Examine | PASS Condition | FAIL Condition |
|-------|------------------|----------------|----------------|
| Import and callable shape | `artifacts/hs-001/result.json` | JSON contains `callable: true` and `argcount: 0` | import fails, symbol is not callable, or function requires arguments |
| Return literal | `artifacts/hs-001/result.json` | JSON contains `result: "pong"` exactly | any other return value or response shape |

```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
RESULT_FILE="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-001/result.json"

RESULT_FILE="$RESULT_FILE" python3 - <<'PY'
import json
import os
import pathlib
import sys

data = json.loads(pathlib.Path(os.environ["RESULT_FILE"]).read_text())
expected = {"argcount": 0, "callable": True, "result": "pong"}
if data != expected:
    print(data)
    sys.exit(1)
PY
```

Cleanup:
```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
rm -rf "$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-001"
```

### HS-002
```yaml
component: smoke-canary
scenario_slug: pytest-canary-passes
priority: P1
```
Validates: D2 SC-003
Contracts: D4 IN-002, OUT-002, SIDE-001
Type: Integration

Setup:
```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
ARTIFACT_DIR="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-002"

rm -rf "$ARTIFACT_DIR"
mkdir -p "$ARTIFACT_DIR"
test -f "$REPO_ROOT/staging/FMWK-900-sawmill-smoke/test_smoke.py"
```

Execute:
```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
ARTIFACT_DIR="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-002"

cd "$REPO_ROOT"
status=0
python3 -m pytest -q staging/FMWK-900-sawmill-smoke/test_smoke.py \
  > "$ARTIFACT_DIR/pytest.log" 2>&1 || status=$?
printf '%s\n' "$status" > "$ARTIFACT_DIR/exit_code"
```

Verify:

| Check | What to Examine | PASS Condition | FAIL Condition |
|-------|------------------|----------------|----------------|
| Runner outcome | `artifacts/hs-002/exit_code` | exit code is `0` | non-zero exit code |
| Pytest contract shape | `artifacts/hs-002/pytest.log` | log contains `1 passed` and no `FAILED`/`ERROR` markers | missing pass summary, collection error, or test failure |

```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
EXIT_FILE="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-002/exit_code"
LOG_FILE="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-002/pytest.log"

EXIT_FILE="$EXIT_FILE" LOG_FILE="$LOG_FILE" python3 - <<'PY'
import os
import pathlib
import sys

code = int(pathlib.Path(os.environ["EXIT_FILE"]).read_text().strip())
log = pathlib.Path(os.environ["LOG_FILE"]).read_text()
checks = [
    code == 0,
    "1 passed" in log,
    "FAILED" not in log,
    "ERROR" not in log,
]
if not all(checks):
    print(log)
    sys.exit(1)
PY
```

Cleanup:
```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
rm -rf "$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-002"
```

### HS-003
```yaml
component: smoke-canary
scenario_slug: missing-ping-fails-fast-with-import-shape
priority: P1
```
Validates: D2 SC-004
Contracts: D4 IN-002, OUT-002, SIDE-001, ERR-001
Type: Error path

Setup:
```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
ARTIFACT_DIR="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-003"
SMOKE_FILE="$REPO_ROOT/staging/FMWK-900-sawmill-smoke/smoke.py"

rm -rf "$ARTIFACT_DIR"
mkdir -p "$ARTIFACT_DIR"
cp "$SMOKE_FILE" "$ARTIFACT_DIR/smoke.py.bak"

cat <<'PY' > "$SMOKE_FILE"
def not_ping():
    return "pong"
PY
```

Execute:
```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
ARTIFACT_DIR="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-003"

cd "$REPO_ROOT"
status=0
python3 -m pytest -q staging/FMWK-900-sawmill-smoke/test_smoke.py \
  > "$ARTIFACT_DIR/pytest.log" 2>&1 || status=$?
printf '%s\n' "$status" > "$ARTIFACT_DIR/exit_code"
```

Verify:

| Check | What to Examine | PASS Condition | FAIL Condition |
|-------|------------------|----------------|----------------|
| Build stops on import failure | `artifacts/hs-003/exit_code` | exit code is non-zero | pytest exits `0` |
| Error contract shape | `artifacts/hs-003/pytest.log` | log shows import-time failure for `ping` from `smoke`, references `test_smoke.py`, and does not degrade into an assertion failure | any generic failure shape, missing `ping`/`smoke` details, or assertion-based failure |

```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
EXIT_FILE="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-003/exit_code"
LOG_FILE="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-003/pytest.log"

EXIT_FILE="$EXIT_FILE" LOG_FILE="$LOG_FILE" python3 - <<'PY'
import os
import pathlib
import sys

code = int(pathlib.Path(os.environ["EXIT_FILE"]).read_text().strip())
log = pathlib.Path(os.environ["LOG_FILE"]).read_text()
checks = [
    code != 0,
    "test_smoke.py" in log,
    "smoke" in log,
    "ping" in log,
    ("ImportError" in log) or ("cannot import name 'ping'" in log),
    ("ERROR collecting" in log) or ("ImportError while importing test module" in log),
    "AssertionError" not in log,
]
if not all(checks):
    print(log)
    sys.exit(1)
PY
```

Cleanup:
```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
ARTIFACT_DIR="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-003"
SMOKE_FILE="$REPO_ROOT/staging/FMWK-900-sawmill-smoke/smoke.py"

if [ -f "$ARTIFACT_DIR/smoke.py.bak" ]; then
  cp "$ARTIFACT_DIR/smoke.py.bak" "$SMOKE_FILE"
fi
rm -rf "$ARTIFACT_DIR"
```

### HS-004
```yaml
component: smoke-canary
scenario_slug: wrong-return-fails-with-assertion-shape
priority: P1
```
Validates: D2 SC-005
Contracts: D4 IN-002, OUT-002, SIDE-001, ERR-002
Type: Error path

Setup:
```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
ARTIFACT_DIR="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-004"
SMOKE_FILE="$REPO_ROOT/staging/FMWK-900-sawmill-smoke/smoke.py"

rm -rf "$ARTIFACT_DIR"
mkdir -p "$ARTIFACT_DIR"
cp "$SMOKE_FILE" "$ARTIFACT_DIR/smoke.py.bak"

cat <<'PY' > "$SMOKE_FILE"
def ping():
    return "pang"
PY
```

Execute:
```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
ARTIFACT_DIR="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-004"

cd "$REPO_ROOT"
status=0
python3 -m pytest -q staging/FMWK-900-sawmill-smoke/test_smoke.py \
  > "$ARTIFACT_DIR/pytest.log" 2>&1 || status=$?
printf '%s\n' "$status" > "$ARTIFACT_DIR/exit_code"
```

Verify:

| Check | What to Examine | PASS Condition | FAIL Condition |
|-------|------------------|----------------|----------------|
| Canary fails | `artifacts/hs-004/exit_code` | exit code is non-zero | pytest exits `0` |
| Error contract shape | `artifacts/hs-004/pytest.log` | log shows assertion failure for `ping() == "pong"` and includes the actual wrong literal | import failure, generic crash, or assertion output that does not expose expected vs actual values |

```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
EXIT_FILE="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-004/exit_code"
LOG_FILE="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-004/pytest.log"

EXIT_FILE="$EXIT_FILE" LOG_FILE="$LOG_FILE" python3 - <<'PY'
import os
import pathlib
import sys

code = int(pathlib.Path(os.environ["EXIT_FILE"]).read_text().strip())
log = pathlib.Path(os.environ["LOG_FILE"]).read_text()
checks = [
    code != 0,
    "AssertionError" in log,
    "pong" in log,
    "pang" in log,
    ("1 failed" in log) or ("FAILED" in log),
    "ImportError" not in log,
]
if not all(checks):
    print(log)
    sys.exit(1)
PY
```

Cleanup:
```bash
REPO_ROOT="/Users/raymondbruni/Cowork/Brain_Factory"
ARTIFACT_DIR="$REPO_ROOT/.holdouts/FMWK-900-sawmill-smoke/artifacts/hs-004"
SMOKE_FILE="$REPO_ROOT/staging/FMWK-900-sawmill-smoke/smoke.py"

if [ -f "$ARTIFACT_DIR/smoke.py.bak" ]; then
  cp "$ARTIFACT_DIR/smoke.py.bak" "$SMOKE_FILE"
fi
rm -rf "$ARTIFACT_DIR"
```

## Coverage Matrix
COVERAGE GATE: All D2 P0 and P1 scenarios MUST have holdout coverage. Zero gaps allowed. P2/P3 may defer to unit tests.

| D2 Scenario | Priority | Holdout Coverage | Notes |
|-------------|----------|------------------|-------|
| SC-001 - Module Exposes `ping` | P1 | HS-001 | Verifies importability, callability, and zero-argument signature |
| SC-002 - `ping()` Returns `"pong"` | P1 | HS-001 | Verifies exact return literal |
| SC-003 - Smoke Test Passes | P1 | HS-002 | Verifies pytest success path on the owned test file |
| SC-004 - Missing or Renamed Function Fails Fast | P1 | HS-003 | Verifies import failure shape, fail-fast behavior, and correct caller-visible error form |
| SC-005 - Wrong Return Literal Fails the Canary | P1 | HS-004 | Verifies assertion failure shape with expected and actual literals exposed |

## Run Protocol
When: after builder delivers and handoff tests pass.
Order: HS-003 and HS-004 are destructive and must restore `smoke.py`; run HS-001, HS-002, HS-003, HS-004 sequentially.
Threshold: all P1 scenarios pass; no partial credit.
On failure: file against responsible D8 task. Include failed SC-###, violated D4 contract ID, and actual vs expected log shape.
