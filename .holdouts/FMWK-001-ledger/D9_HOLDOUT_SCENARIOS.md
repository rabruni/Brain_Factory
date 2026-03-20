# D9: Holdout Scenarios — FMWK-001-ledger
Meta: v:1.0.0 | contracts: D4 1.0.0 | status:Final | author:holdout-agent, NOT builder | last run:Not yet executed
CRITICAL: Builder agent MUST NOT see these scenarios before completing their work.

## Harness Assumptions
These holdouts stay black-box by driving only caller-visible ledger operations. The evaluator should bind the following environment variables to runnable shell snippets:

- `LEDGER_RESET_CMD` resets the ledger fixture to an empty state.
- `LEDGER_APPEND_CMD` reads an IN-001 JSON request from stdin and writes the response JSON to stdout.
- `LEDGER_READ_CMD` reads an IN-002 JSON request from stdin and writes the response JSON to stdout.
- `LEDGER_READ_RANGE_CMD` reads an IN-003 JSON request from stdin and writes the response JSON array to stdout.
- `LEDGER_READ_SINCE_CMD` reads an IN-004 JSON request from stdin and writes the response JSON array to stdout.
- `LEDGER_VERIFY_CMD` reads an IN-005 JSON request from stdin and writes the response JSON to stdout.
- `LEDGER_TIP_CMD` reads an IN-006 JSON request from stdin and writes the response JSON to stdout.
- `LEDGER_EXPORT_CMD` writes an offline export to `$EXPORT_PATH`.
- `LEDGER_TAMPER_CMD` mutates either the live or offline ledger fixture using `TAMPER_MODE`, `TAMPER_SEQUENCE`, and `EXPORT_PATH` as needed.
- `LEDGER_RACE_APPEND_CMD` attempts an append under an induced tip-race using `REQUEST_JSON`.
- `LEDGER_BACKEND_DOWN_CMD` makes the backing immudb unavailable without deleting prior committed data.
- `LEDGER_BACKEND_UP_CMD` restores the backing immudb after `LEDGER_BACKEND_DOWN_CMD`.

All commands are executed with `bash -lc "<snippet>"`.

## Scenarios

### HS-001
```yaml
component: FMWK-001-ledger
scenario_slug: genesis-append-populates-ledger-owned-fields
priority: P0
```
Validates: D2 SC-001, SC-003
Contracts: D4 IN-001, OUT-001, SIDE-001, SIDE-002
Type: Happy path

Setup:
```bash
set -euo pipefail
for v in LEDGER_RESET_CMD LEDGER_APPEND_CMD; do
  [ -n "${!v:-}" ] || { echo "missing $v" >&2; exit 2; }
done
TEST_ROOT="$(mktemp -d)"
export TEST_ROOT
bash -lc "$LEDGER_RESET_CMD"
cat > "$TEST_ROOT/append_req.json" <<'JSON'
{
  "event_type": "session_start",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:20:00Z",
  "provenance": {
    "framework_id": "FMWK-001-ledger",
    "pack_id": "PC-001-ledger-core",
    "actor": "system"
  },
  "payload": {
    "session_id": "session-0195b8d1",
    "session_kind": "operator",
    "subject_id": "ray",
    "started_by": "operator"
  }
}
JSON
```

Execute:
```bash
set -euo pipefail
bash -lc "$LEDGER_APPEND_CMD" < "$TEST_ROOT/append_req.json" > "$TEST_ROOT/append_resp.json"
```

Verify:

| Check | What to Examine | PASS Condition | FAIL Condition |
| --- | --- | --- | --- |
| Genesis sequencing | `sequence`, `previous_hash` | `sequence == 0` and `previous_hash` is the all-zero genesis hash | Any other sequence or prior hash |
| Envelope completion | response object | Includes `event_id`, `event_type`, `schema_version`, `timestamp`, `provenance`, `payload`, `hash` | Missing any required field |
| Caller immutability | request vs response | Caller did not provide ledger-owned fields, but response did | Ledger accepts caller-owned sequencing fields or omits assigned fields |
| Hash format | `hash` | `sha256:` followed by 64 lowercase hex chars | Wrong prefix, length, or casing |

```bash
set -euo pipefail
jq -e '
  .sequence == 0 and
  .previous_hash == "sha256:0000000000000000000000000000000000000000000000000000000000000000" and
  (.event_id | type == "string" and length > 0) and
  .event_type == "session_start" and
  .schema_version == "1.0.0" and
  .timestamp == "2026-03-20T20:20:00Z" and
  .provenance.framework_id == "FMWK-001-ledger" and
  .provenance.pack_id == "PC-001-ledger-core" and
  .provenance.actor == "system" and
  .payload.session_id == "session-0195b8d1" and
  (.hash | test("^sha256:[0-9a-f]{64}$"))
' "$TEST_ROOT/append_resp.json" >/dev/null
```

Cleanup:
```bash
set -euo pipefail
rm -rf "$TEST_ROOT"
```

### HS-002
```yaml
component: FMWK-001-ledger
scenario_slug: sequential-append-read-replay-and-tip-remain-linear
priority: P0
```
Validates: D2 SC-002, SC-004, SC-006, SC-007
Contracts: D4 IN-001, IN-002, IN-003, IN-004, IN-006, OUT-001, OUT-002, OUT-003, OUT-005, SIDE-001
Type: Integration

Setup:
```bash
set -euo pipefail
for v in LEDGER_RESET_CMD LEDGER_APPEND_CMD LEDGER_READ_CMD LEDGER_READ_RANGE_CMD LEDGER_READ_SINCE_CMD LEDGER_TIP_CMD; do
  [ -n "${!v:-}" ] || { echo "missing $v" >&2; exit 2; }
done
TEST_ROOT="$(mktemp -d)"
export TEST_ROOT
bash -lc "$LEDGER_RESET_CMD"

cat > "$TEST_ROOT/event_0.json" <<'JSON'
{
  "event_type": "node_creation",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:21:00Z",
  "provenance": {
    "framework_id": "FMWK-002",
    "pack_id": "PC-002-write-path",
    "actor": "system"
  },
  "payload": {
    "node_id": "memory-001",
    "node_type": "memory",
    "subject_id": "ray"
  }
}
JSON

cat > "$TEST_ROOT/event_1.json" <<'JSON'
{
  "event_type": "signal_delta",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:22:00Z",
  "provenance": {
    "framework_id": "FMWK-002",
    "pack_id": "PC-002-write-path",
    "actor": "system"
  },
  "payload": {
    "node_id": "memory-001",
    "signal_name": "operator_reinforcement",
    "delta": 1,
    "reason": "operator confirmed importance"
  }
}
JSON

cat > "$TEST_ROOT/event_2.json" <<'JSON'
{
  "event_type": "snapshot_created",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:23:00Z",
  "provenance": {
    "framework_id": "FMWK-002",
    "pack_id": "PC-002-write-path",
    "actor": "system"
  },
  "payload": {
    "snapshot_sequence": 2,
    "snapshot_path": "/snapshots/2.snapshot",
    "snapshot_hash": "sha256:5c1f3ed4c95346f1dc3ddca6ca9ea6240cfa0b8455174a8c4363130f0f2387cc"
  }
}
JSON
```

Execute:
```bash
set -euo pipefail
bash -lc "$LEDGER_APPEND_CMD" < "$TEST_ROOT/event_0.json" > "$TEST_ROOT/resp_0.json"
bash -lc "$LEDGER_APPEND_CMD" < "$TEST_ROOT/event_1.json" > "$TEST_ROOT/resp_1.json"
bash -lc "$LEDGER_APPEND_CMD" < "$TEST_ROOT/event_2.json" > "$TEST_ROOT/resp_2.json"

printf '%s\n' '{"sequence_number":1}' > "$TEST_ROOT/read_req.json"
bash -lc "$LEDGER_READ_CMD" < "$TEST_ROOT/read_req.json" > "$TEST_ROOT/read_resp.json"

printf '%s\n' '{"start":0,"end":2}' > "$TEST_ROOT/range_req.json"
bash -lc "$LEDGER_READ_RANGE_CMD" < "$TEST_ROOT/range_req.json" > "$TEST_ROOT/range_resp.json"

printf '%s\n' '{"sequence_number":1}' > "$TEST_ROOT/since_req.json"
bash -lc "$LEDGER_READ_SINCE_CMD" < "$TEST_ROOT/since_req.json" > "$TEST_ROOT/since_resp.json"

printf '%s\n' '{"include_hash":true}' > "$TEST_ROOT/tip_req.json"
bash -lc "$LEDGER_TIP_CMD" < "$TEST_ROOT/tip_req.json" > "$TEST_ROOT/tip_resp.json"
```

Verify:

| Check | What to Examine | PASS Condition | FAIL Condition |
| --- | --- | --- | --- |
| Linear append | append responses | Sequences are `0,1,2` and each `previous_hash` equals the prior event `hash` | Gaps, duplicates, or broken linkage |
| Single read | `read_resp.json` | Returns sequence `1` event unchanged | Wrong sequence or altered payload |
| Range read ordering | `range_resp.json` | Returns 3 events in ascending sequence order | Missing, reordered, or mutated events |
| Replay boundary | `since_resp.json` | Returns only sequence `2` snapshot event | Includes boundary event or omits snapshot event |
| Tip contract | `tip_resp.json` | Reports `sequence_number == 2` and `hash == resp_2.hash` | Wrong latest sequence/hash |

```bash
set -euo pipefail
prev0="$(jq -r '.hash' "$TEST_ROOT/resp_0.json")"
prev1="$(jq -r '.hash' "$TEST_ROOT/resp_1.json")"

jq -e --arg prev0 "$prev0" --arg prev1 "$prev1" '
  .sequence == 1 and .previous_hash == $prev0
' "$TEST_ROOT/resp_1.json" >/dev/null

jq -e --arg prev1 "$prev1" '
  .sequence == 2 and .previous_hash == $prev1 and
  .event_type == "snapshot_created" and
  .payload.snapshot_sequence == 2 and
  (.payload.snapshot_hash | test("^sha256:[0-9a-f]{64}$"))
' "$TEST_ROOT/resp_2.json" >/dev/null

jq -e '
  .sequence == 1 and
  .event_type == "signal_delta" and
  .payload.reason == "operator confirmed importance"
' "$TEST_ROOT/read_resp.json" >/dev/null

jq -e '
  length == 3 and
  .[0].sequence == 0 and
  .[1].sequence == 1 and
  .[2].sequence == 2 and
  .[2].event_type == "snapshot_created"
' "$TEST_ROOT/range_resp.json" >/dev/null

jq -e '
  length == 1 and
  .[0].sequence == 2 and
  .[0].event_type == "snapshot_created"
' "$TEST_ROOT/since_resp.json" >/dev/null

jq -e --arg hash2 "$(jq -r '.hash' "$TEST_ROOT/resp_2.json")" '
  .sequence_number == 2 and .hash == $hash2
' "$TEST_ROOT/tip_resp.json" >/dev/null
```

Cleanup:
```bash
set -euo pipefail
rm -rf "$TEST_ROOT"
```

### HS-003
```yaml
component: FMWK-001-ledger
scenario_slug: online-and-offline-verification-agree-on-intact-ledger
priority: P1
```
Validates: D2 SC-005
Contracts: D4 IN-005, OUT-004, SIDE-002, SIDE-004
Type: Side-effect verification

Setup:
```bash
set -euo pipefail
for v in LEDGER_RESET_CMD LEDGER_APPEND_CMD LEDGER_VERIFY_CMD LEDGER_EXPORT_CMD; do
  [ -n "${!v:-}" ] || { echo "missing $v" >&2; exit 2; }
done
TEST_ROOT="$(mktemp -d)"
export TEST_ROOT
bash -lc "$LEDGER_RESET_CMD"

cat > "$TEST_ROOT/session_start.json" <<'JSON'
{
  "event_type": "session_start",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:20:00Z",
  "provenance": {
    "framework_id": "FMWK-001-ledger",
    "pack_id": "PC-001-ledger-core",
    "actor": "system"
  },
  "payload": {
    "session_id": "session-0195b8d1",
    "session_kind": "operator",
    "subject_id": "ray",
    "started_by": "operator"
  }
}
JSON

cat > "$TEST_ROOT/package_install.json" <<'JSON'
{
  "event_type": "package_install",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:21:00Z",
  "provenance": {
    "framework_id": "FMWK-006",
    "pack_id": "PC-006-package-lifecycle",
    "actor": "system"
  },
  "payload": {
    "package_id": "pkg-ledger",
    "version": "1.0.0",
    "action": "install"
  }
}
JSON
```

Execute:
```bash
set -euo pipefail
bash -lc "$LEDGER_APPEND_CMD" < "$TEST_ROOT/session_start.json" > "$TEST_ROOT/resp_0.json"
bash -lc "$LEDGER_APPEND_CMD" < "$TEST_ROOT/package_install.json" > "$TEST_ROOT/resp_1.json"

printf '%s\n' '{"source_mode":"online"}' > "$TEST_ROOT/verify_online_req.json"
bash -lc "$LEDGER_VERIFY_CMD" < "$TEST_ROOT/verify_online_req.json" > "$TEST_ROOT/verify_online_resp.json"

export EXPORT_PATH="$TEST_ROOT/ledger_export.jsonl"
bash -lc "$LEDGER_EXPORT_CMD"

printf '%s\n' '{"start":0,"end":1,"source_mode":"offline"}' > "$TEST_ROOT/verify_offline_req.json"
bash -lc "$LEDGER_VERIFY_CMD" < "$TEST_ROOT/verify_offline_req.json" > "$TEST_ROOT/verify_offline_resp.json"
```

Verify:

| Check | What to Examine | PASS Condition | FAIL Condition |
| --- | --- | --- | --- |
| Online verify | `verify_online_resp.json` | `valid == true` and reported range spans committed events | Returns invalid or wrong bounds |
| Offline verify | `verify_offline_resp.json` | `valid == true` with the same covered range as online verify | Returns invalid or mismatched bounds |
| Cross-path determinism | online vs offline result | Both paths agree on start and end sequence | Any disagreement between online and offline verdicts |

```bash
set -euo pipefail
jq -e '
  .valid == true and
  .start_sequence == 0 and
  .end_sequence == 1
' "$TEST_ROOT/verify_online_resp.json" >/dev/null

jq -e '
  .valid == true and
  .start_sequence == 0 and
  .end_sequence == 1
' "$TEST_ROOT/verify_offline_resp.json" >/dev/null
```

Cleanup:
```bash
set -euo pipefail
rm -rf "$TEST_ROOT"
```

### HS-004
```yaml
component: FMWK-001-ledger
scenario_slug: verify-chain-reports-first-corruption-boundary
priority: P0
```
Validates: D2 SC-008
Contracts: D4 IN-005, OUT-004, SIDE-002, SIDE-004, ERR-002
Type: Error path

Setup:
```bash
set -euo pipefail
for v in LEDGER_RESET_CMD LEDGER_APPEND_CMD LEDGER_VERIFY_CMD LEDGER_EXPORT_CMD LEDGER_TAMPER_CMD; do
  [ -n "${!v:-}" ] || { echo "missing $v" >&2; exit 2; }
done
TEST_ROOT="$(mktemp -d)"
export TEST_ROOT
bash -lc "$LEDGER_RESET_CMD"

cat > "$TEST_ROOT/e0.json" <<'JSON'
{
  "event_type": "session_start",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:20:00Z",
  "provenance": {
    "framework_id": "FMWK-001-ledger",
    "pack_id": "PC-001-ledger-core",
    "actor": "system"
  },
  "payload": {
    "session_id": "session-0195b8d1",
    "session_kind": "operator",
    "subject_id": "ray",
    "started_by": "operator"
  }
}
JSON

cat > "$TEST_ROOT/e1.json" <<'JSON'
{
  "event_type": "signal_delta",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:21:00Z",
  "provenance": {
    "framework_id": "FMWK-002",
    "pack_id": "PC-002-write-path",
    "actor": "system"
  },
  "payload": {
    "node_id": "memory-001",
    "signal_name": "operator_reinforcement",
    "delta": 1,
    "reason": "operator confirmed importance"
  }
}
JSON

cat > "$TEST_ROOT/e2.json" <<'JSON'
{
  "event_type": "package_install",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:22:00Z",
  "provenance": {
    "framework_id": "FMWK-006",
    "pack_id": "PC-006-package-lifecycle",
    "actor": "system"
  },
  "payload": {
    "package_id": "pkg-ledger",
    "version": "1.0.0",
    "action": "install"
  }
}
JSON
```

Execute:
```bash
set -euo pipefail
bash -lc "$LEDGER_APPEND_CMD" < "$TEST_ROOT/e0.json" > /dev/null
bash -lc "$LEDGER_APPEND_CMD" < "$TEST_ROOT/e1.json" > /dev/null
bash -lc "$LEDGER_APPEND_CMD" < "$TEST_ROOT/e2.json" > /dev/null

export EXPORT_PATH="$TEST_ROOT/ledger_export.jsonl"
bash -lc "$LEDGER_EXPORT_CMD"

export TAMPER_MODE="offline"
export TAMPER_SEQUENCE="1"
bash -lc "$LEDGER_TAMPER_CMD"

printf '%s\n' '{"start":0,"end":2,"source_mode":"offline"}' > "$TEST_ROOT/verify_req.json"
bash -lc "$LEDGER_VERIFY_CMD" < "$TEST_ROOT/verify_req.json" > "$TEST_ROOT/verify_resp.json"
```

Verify:

| Check | What to Examine | PASS Condition | FAIL Condition |
| --- | --- | --- | --- |
| Failure shape | `verify_resp.json` | Includes `valid`, `start_sequence`, `end_sequence`, and `break_at` | Missing any required failure field |
| Corruption verdict | `valid` | `valid == false` | Returns success |
| First break boundary | `break_at` | `break_at == 1` for the first tampered sequence | Any other break position |
| Verified range | `start_sequence`, `end_sequence` | Preserves the requested bounds `0..2` | Wrong range in failure response |

```bash
set -euo pipefail
jq -e '
  (.valid == false) and
  (.start_sequence == 0) and
  (.end_sequence == 2) and
  (.break_at == 1)
' "$TEST_ROOT/verify_resp.json" >/dev/null
```

Cleanup:
```bash
set -euo pipefail
rm -rf "$TEST_ROOT"
```

### HS-005
```yaml
component: FMWK-001-ledger
scenario_slug: append-and-tip-fail-with-contract-shaped-errors
priority: P0
```
Validates: D2 SC-009, SC-010, SC-011
Contracts: D4 IN-001, IN-006, OUT-001, OUT-005, SIDE-001, SIDE-002, SIDE-003, ERR-001, ERR-003, ERR-004
Type: Error path

Setup:
```bash
set -euo pipefail
for v in LEDGER_RESET_CMD LEDGER_APPEND_CMD LEDGER_TIP_CMD LEDGER_RACE_APPEND_CMD LEDGER_BACKEND_DOWN_CMD LEDGER_BACKEND_UP_CMD; do
  [ -n "${!v:-}" ] || { echo "missing $v" >&2; exit 2; }
done
TEST_ROOT="$(mktemp -d)"
export TEST_ROOT
bash -lc "$LEDGER_RESET_CMD"

cat > "$TEST_ROOT/baseline.json" <<'JSON'
{
  "event_type": "session_start",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:20:00Z",
  "provenance": {
    "framework_id": "FMWK-001-ledger",
    "pack_id": "PC-001-ledger-core",
    "actor": "system"
  },
  "payload": {
    "session_id": "session-0195b8d1",
    "session_kind": "operator",
    "subject_id": "ray",
    "started_by": "operator"
  }
}
JSON

cat > "$TEST_ROOT/race_req.json" <<'JSON'
{
  "event_type": "signal_delta",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:21:00Z",
  "provenance": {
    "framework_id": "FMWK-002",
    "pack_id": "PC-002-write-path",
    "actor": "system"
  },
  "payload": {
    "node_id": "memory-001",
    "signal_name": "operator_reinforcement",
    "delta": 1,
    "reason": "operator confirmed importance"
  }
}
JSON

cat > "$TEST_ROOT/bad_serialization.json" <<'JSON'
{
  "event_type": "signal_delta",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-20T20:22:00Z",
  "provenance": {
    "framework_id": "FMWK-002",
    "pack_id": "PC-002-write-path",
    "actor": "system"
  },
  "payload": {
    "node_id": "memory-001",
    "signal_name": "operator_reinforcement",
    "delta": 1.5,
    "reason": "float should violate canonical envelope contract"
  }
}
JSON

printf '%s\n' '{"include_hash":true}' > "$TEST_ROOT/tip_req.json"
```

Execute:
```bash
set -euo pipefail
bash -lc "$LEDGER_APPEND_CMD" < "$TEST_ROOT/baseline.json" > "$TEST_ROOT/baseline_resp.json"
bash -lc "$LEDGER_TIP_CMD" < "$TEST_ROOT/tip_req.json" > "$TEST_ROOT/tip_before.json"

export REQUEST_JSON="$TEST_ROOT/race_req.json"
bash -lc "$LEDGER_RACE_APPEND_CMD" > "$TEST_ROOT/race_resp.json" || true

bash -lc "$LEDGER_BACKEND_DOWN_CMD"
bash -lc "$LEDGER_TIP_CMD" < "$TEST_ROOT/tip_req.json" > "$TEST_ROOT/conn_resp.json" || true
bash -lc "$LEDGER_BACKEND_UP_CMD"
bash -lc "$LEDGER_TIP_CMD" < "$TEST_ROOT/tip_req.json" > "$TEST_ROOT/tip_after_conn.json"

bash -lc "$LEDGER_APPEND_CMD" < "$TEST_ROOT/bad_serialization.json" > "$TEST_ROOT/ser_resp.json" || true
bash -lc "$LEDGER_TIP_CMD" < "$TEST_ROOT/tip_req.json" > "$TEST_ROOT/tip_after_ser.json"
```

Verify:

| Check | What to Examine | PASS Condition | FAIL Condition |
| --- | --- | --- | --- |
| Sequence error shape | `race_resp.json` | JSON object with `code == "LEDGER_SEQUENCE_ERROR"` and a non-empty `message` | Generic crash, wrong code, or missing message |
| Connection error shape | `conn_resp.json` | JSON object with `code == "LEDGER_CONNECTION_ERROR"` and a non-empty `message` | Wrong code or missing message |
| Serialization error shape | `ser_resp.json` | JSON object with `code == "LEDGER_SERIALIZATION_ERROR"` and a non-empty `message` | Wrong code or missing message |
| No partial writes on error | tip snapshots | `tip_before`, `tip_after_conn`, and `tip_after_ser` all report the same sequence/hash | Any failed operation advances tip |

```bash
set -euo pipefail
jq -e '
  .code == "LEDGER_SEQUENCE_ERROR" and
  (.message | type == "string" and length > 0)
' "$TEST_ROOT/race_resp.json" >/dev/null

jq -e '
  .code == "LEDGER_CONNECTION_ERROR" and
  (.message | type == "string" and length > 0)
' "$TEST_ROOT/conn_resp.json" >/dev/null

jq -e '
  .code == "LEDGER_SERIALIZATION_ERROR" and
  (.message | type == "string" and length > 0)
' "$TEST_ROOT/ser_resp.json" >/dev/null

before_seq="$(jq -r '.sequence_number' "$TEST_ROOT/tip_before.json")"
before_hash="$(jq -r '.hash' "$TEST_ROOT/tip_before.json")"

jq -e --arg seq "$before_seq" --arg hash "$before_hash" '
  (.sequence_number | tostring) == $seq and .hash == $hash
' "$TEST_ROOT/tip_after_conn.json" >/dev/null

jq -e --arg seq "$before_seq" --arg hash "$before_hash" '
  (.sequence_number | tostring) == $seq and .hash == $hash
' "$TEST_ROOT/tip_after_ser.json" >/dev/null
```

Cleanup:
```bash
set -euo pipefail
rm -rf "$TEST_ROOT"
```

## Coverage Matrix
COVERAGE GATE: All D2 P0 and P1 scenarios MUST have holdout coverage. Zero gaps allowed. P2/P3 may defer to unit tests.

| D2 Scenario | Priority | Holdout Coverage | Notes |
| --- | --- | --- | --- |
| SC-001 | P0 | HS-001 | Genesis append assigns sequence 0 and zero previous hash |
| SC-002 | P0 | HS-002 | Sequential append preserves single linear tip |
| SC-003 | P1 | HS-001 | Ledger-owned fields are filled into a self-describing stored event |
| SC-004 | P1 | HS-002 | Read, range read, and read_since preserve order and payload bytes |
| SC-005 | P1 | HS-003 | Online and offline verification agree on intact chain |
| SC-006 | P1 | HS-002 | `get_tip` returns latest committed sequence/hash |
| SC-007 | P1 | HS-002 | Snapshot reference event is replayable after boundary |
| SC-008 | P0 | HS-004 | Corruption yields `valid=false` with exact `break_at` |
| SC-009 | P0 | HS-005 | Tip race rejects append with `LEDGER_SEQUENCE_ERROR` |
| SC-010 | P1 | HS-005 | Backend failure yields `LEDGER_CONNECTION_ERROR` with no new commit |
| SC-011 | P1 | HS-005 | Serialization failure yields `LEDGER_SERIALIZATION_ERROR` with no partial write |

## Run Protocol
When: after builder delivers + handoff tests pass.
Order: HS-001, HS-002, HS-004, HS-005, HS-003.
Threshold: all P0 pass, all P1 pass, no partial credit.
On failure: file against responsible D8 task. Include: failed SC-###, violated contract, actual vs expected.
