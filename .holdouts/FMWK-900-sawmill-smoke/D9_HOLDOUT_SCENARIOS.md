# D9: Holdout Scenarios — sawmill smoke canary
Meta: v:1.0.0 | contracts: D4 1.0.0 | status:Final | author:holdout-agent | last run:Not yet executed
CRITICAL: Builder agent MUST NOT see these scenarios before completing their work.

## Scenarios

```yaml
component: sawmill-smoke-canary
scenario: ping-returns-pong-from-staged-module
priority: P0
```
Validates: D2 SC-001
Contracts: D4 IN-001, OUT-001
Type: Happy path
Setup:
```bash
set -euo pipefail
ROOT="${ROOT:-$(pwd)}"
STAGE_DIR="$ROOT/staging/FMWK-900-sawmill-smoke"
test -f "$STAGE_DIR/smoke.py"
```
Execute:
```bash
set -euo pipefail
ROOT="${ROOT:-$(pwd)}"
STAGE_DIR="$ROOT/staging/FMWK-900-sawmill-smoke"
OUTPUT="$(PYTHONPATH="$STAGE_DIR" python3 - <<'PY'
from smoke import ping
import json
print(json.dumps({"function_name": "ping", "arguments": [], "result": ping()}))
PY
)"
printf '%s\n' "$OUTPUT" > /tmp/fmwk900_hs001.json
```
Verify:
| Check | What to Examine | PASS Condition | FAIL Condition |
| --- | --- | --- | --- |
| Inbound call shape | `/tmp/fmwk900_hs001.json` | `function_name` is `ping` and `arguments` is `[]` | Missing field or wrong call shape |
| Success response shape | `/tmp/fmwk900_hs001.json` | `result` exists and equals `pong` | Missing `result` or any other value |
```bash
set -euo pipefail
python3 - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("/tmp/fmwk900_hs001.json").read_text())
assert data["function_name"] == "ping"
assert data["arguments"] == []
assert data["result"] == "pong"
PY
```
Cleanup:
```bash
rm -f /tmp/fmwk900_hs001.json
```

```yaml
component: sawmill-smoke-canary
scenario: unit-test-passes-against-staged-output
priority: P1
```
Validates: D2 SC-002
Contracts: D4 IN-001, OUT-001
Type: Integration
Setup:
```bash
set -euo pipefail
ROOT="${ROOT:-$(pwd)}"
STAGE_DIR="$ROOT/staging/FMWK-900-sawmill-smoke"
test -f "$STAGE_DIR/test_smoke.py"
```
Execute:
```bash
set -euo pipefail
ROOT="${ROOT:-$(pwd)}"
STAGE_DIR="$ROOT/staging/FMWK-900-sawmill-smoke"
PYTHONPATH="$STAGE_DIR" python3 -m pytest "$STAGE_DIR/test_smoke.py" -q > /tmp/fmwk900_hs002.out 2>&1
```
Verify:
| Check | What to Examine | PASS Condition | FAIL Condition |
| --- | --- | --- | --- |
| Caller-observed success | `/tmp/fmwk900_hs002.out` | Pytest exits 0 and reports one passing test | Non-zero exit or no passing test reported |
```bash
set -euo pipefail
grep -Eq '^\.([[:space:]].*)?$|1 passed' /tmp/fmwk900_hs002.out
```
Cleanup:
```bash
rm -f /tmp/fmwk900_hs002.out
```

```yaml
component: sawmill-smoke-canary
scenario: import-failure-surfaces-import-failure-shape
priority: P1
```
Validates: D2 SC-002, D2 SC-003
Contracts: D4 IN-001, ERR-001
Type: Error path
Setup:
```bash
set -euo pipefail
ROOT="${ROOT:-$(pwd)}"
STAGE_DIR="$ROOT/staging/FMWK-900-sawmill-smoke"
TMP_DIR="$(mktemp -d /tmp/fmwk900_hs003.XXXXXX)"
cp "$STAGE_DIR/test_smoke.py" "$TMP_DIR/test_smoke.py"
printf '%s\n' 'raise ImportError("synthetic import failure")' > "$TMP_DIR/smoke.py"
```
Execute:
```bash
set -euo pipefail
TMP_DIR="$(ls -dt /tmp/fmwk900_hs003.* | head -n 1)"
set +e
PYTHONPATH="$TMP_DIR" python3 -m pytest "$TMP_DIR/test_smoke.py" -q > /tmp/fmwk900_hs003.out 2>&1
STATUS=$?
set -e
STATUS="$STATUS" python3 - <<'PY'
import json
import os
from pathlib import Path
text = Path("/tmp/fmwk900_hs003.out").read_text()
payload = {
    "code": "IMPORT_FAILURE",
    "caller_action": "Fail the test run immediately",
    "error": "ImportError" if "ImportError" in text else None,
    "details": text,
}
Path("/tmp/fmwk900_hs003.json").write_text(json.dumps(payload))
raise SystemExit(0 if int(os.environ["STATUS"]) != 0 else 1)
PY
```
Verify:
| Check | What to Examine | PASS Condition | FAIL Condition |
| --- | --- | --- | --- |
| Error code shape | `/tmp/fmwk900_hs003.json` | `code` equals `IMPORT_FAILURE` | Missing code or wrong code |
| Contract metadata | `/tmp/fmwk900_hs003.json` | `caller_action` matches D4 and `error` is `ImportError` | Missing metadata or generic error shape |
| Immediate failure | `/tmp/fmwk900_hs003.out` | Pytest output shows collection/import failure and no passing test | Test run appears successful |
```bash
set -euo pipefail
python3 - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("/tmp/fmwk900_hs003.json").read_text())
assert data["code"] == "IMPORT_FAILURE"
assert data["caller_action"] == "Fail the test run immediately"
assert data["error"] == "ImportError"
text = Path("/tmp/fmwk900_hs003.out").read_text()
assert "ImportError" in text
assert "1 passed" not in text
PY
```
Cleanup:
```bash
rm -rf /tmp/fmwk900_hs003.*
rm -f /tmp/fmwk900_hs003.out /tmp/fmwk900_hs003.json
```

```yaml
component: sawmill-smoke-canary
scenario: wrong-return-surfaces-wrong-return-shape
priority: P1
```
Validates: D2 SC-001, D2 SC-002
Contracts: D4 OUT-001, ERR-002
Type: Error path
Setup:
```bash
set -euo pipefail
ROOT="${ROOT:-$(pwd)}"
STAGE_DIR="$ROOT/staging/FMWK-900-sawmill-smoke"
TMP_DIR="$(mktemp -d /tmp/fmwk900_hs004.XXXXXX)"
cp "$STAGE_DIR/test_smoke.py" "$TMP_DIR/test_smoke.py"
cat > "$TMP_DIR/smoke.py" <<'PY'
def ping():
    return "nope"
PY
```
Execute:
```bash
set -euo pipefail
TMP_DIR="$(ls -dt /tmp/fmwk900_hs004.* | head -n 1)"
set +e
PYTHONPATH="$TMP_DIR" python3 -m pytest "$TMP_DIR/test_smoke.py" -q > /tmp/fmwk900_hs004.out 2>&1
STATUS=$?
set -e
python3 - <<PY
import json
from pathlib import Path
text = Path("/tmp/fmwk900_hs004.out").read_text()
payload = {
    "code": "WRONG_RETURN",
    "caller_action": "Fail the assertion immediately",
    "result": "nope",
    "error": "returned value did not equal pong" if "pong" in text else None,
    "status": $STATUS,
}
Path("/tmp/fmwk900_hs004.json").write_text(json.dumps(payload))
raise SystemExit(0 if $STATUS != 0 else 1)
PY
```
Verify:
| Check | What to Examine | PASS Condition | FAIL Condition |
| --- | --- | --- | --- |
| Error response shape | `/tmp/fmwk900_hs004.json` | `code` is `WRONG_RETURN`, `result` captures non-`pong` value, and `error` matches D4 failure shape | Generic failure with missing metadata |
| Caller action | `/tmp/fmwk900_hs004.json` | `caller_action` is `Fail the assertion immediately` | Wrong caller action |
| Assertion failure visible | `/tmp/fmwk900_hs004.out` | Pytest output shows assertion failure mentioning `pong` | Run passes or failure does not identify wrong return |
```bash
set -euo pipefail
python3 - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("/tmp/fmwk900_hs004.json").read_text())
assert data["code"] == "WRONG_RETURN"
assert data["caller_action"] == "Fail the assertion immediately"
assert data["result"] != "pong"
assert data["error"] == "returned value did not equal pong"
assert data["status"] != 0
text = Path("/tmp/fmwk900_hs004.out").read_text()
assert "AssertionError" in text
assert "pong" in text
PY
```
Cleanup:
```bash
rm -rf /tmp/fmwk900_hs004.*
rm -f /tmp/fmwk900_hs004.out /tmp/fmwk900_hs004.json
```

```yaml
component: sawmill-smoke-canary
scenario: staged-output-stays-within-canary-scope
priority: P1
```
Validates: D2 SC-003, D2 SC-004
Contracts: D4 SIDE-001, ERR-003
Type: Side-effect verification
Setup:
```bash
set -euo pipefail
ROOT="${ROOT:-$(pwd)}"
STAGE_DIR="$ROOT/staging/FMWK-900-sawmill-smoke"
test -d "$STAGE_DIR"
```
Execute:
```bash
set -euo pipefail
ROOT="${ROOT:-$(pwd)}"
STAGE_DIR="$ROOT/staging/FMWK-900-sawmill-smoke"
find "$STAGE_DIR" -maxdepth 1 -type f | sed "s|$STAGE_DIR/||" | sort > /tmp/fmwk900_hs005.files
python3 - <<'PY' > /tmp/fmwk900_hs005.imports
from pathlib import Path
import ast
stage = Path("staging/FMWK-900-sawmill-smoke")
imports = []
for path in sorted(stage.glob("*.py")):
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
print("\n".join(sorted(imports)))
PY
```
Verify:
| Check | What to Examine | PASS Condition | FAIL Condition |
| --- | --- | --- | --- |
| Scope boundary | `/tmp/fmwk900_hs005.files` | Only `smoke.py` and `test_smoke.py` exist at stage root | Any extra staged file appears |
| No dependency setup | `/tmp/fmwk900_hs005.imports` | Imports are limited to local module `smoke` and Python stdlib/pytest references; no platform/service modules | Any platform/service dependency appears |
| No side effects | Runtime behavior | Importing and testing require no external service bootstrap | Any command needs service startup or external system |
```bash
set -euo pipefail
python3 - <<'PY'
from pathlib import Path
files = Path("/tmp/fmwk900_hs005.files").read_text().splitlines()
assert files == ["smoke.py", "test_smoke.py"], files
imports = [line.strip() for line in Path("/tmp/fmwk900_hs005.imports").read_text().splitlines() if line.strip()]
for name in imports:
    banned_prefixes = ("platform_sdk", "docker", "requests", "sqlalchemy", "fastapi", "dopejar")
    assert not name.startswith(banned_prefixes), name
PY
```
Cleanup:
```bash
rm -f /tmp/fmwk900_hs005.files /tmp/fmwk900_hs005.imports
```

## Coverage Matrix
COVERAGE GATE: All D2 P0 and P1 scenarios MUST have holdout coverage. Zero gaps allowed. P2/P3 may defer to unit tests.
| D2 Scenario | Priority | Holdout Coverage | Notes |
| --- | --- | --- | --- |
| SC-001 | P0 | HS-001, HS-004 | Direct success contract and wrong-return contract |
| SC-002 | P1 | HS-002, HS-003, HS-004 | End-to-end unit test pass plus import/return failure handling |
| SC-003 | P1 | HS-003, HS-005 | Import requires no setup; no dependency or service bootstrap allowed |
| SC-004 | P1 | HS-005 | Stage must remain limited to the two canary-owned files |

## Run Protocol
When: after builder delivers + handoff tests pass.
Order: P0 first (any fail = stop), then P1, then P2.
Threshold: all P0 pass, all P1 pass, no partial credit.
On failure: file against responsible D8 task. Include: failed SC-###, violated contract, actual vs expected.
