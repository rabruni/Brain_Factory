# D9: Holdout Scenarios — FMWK-001-ledger
Meta: v:1.0.0 | contracts: D4 1.0.0 | status:Final | author:Codex holdout-agent | last run:Not yet executed
CRITICAL: Builder agent MUST NOT see these scenarios before completing their work.

## Scenarios (HS-### IDs, minimum 3: happy path + error path + integration)
Evaluator note: all bash below assumes the evaluator exports contract adapters as shell commands. Required adapters are `LEDGER_RESET_CMD`, `LEDGER_APPEND_CMD`, `LEDGER_READ_CMD`, `LEDGER_READ_RANGE_CMD`, `LEDGER_READ_SINCE_CMD`, `LEDGER_VERIFY_CMD`, `LEDGER_TIP_CMD`, `LEDGER_EXPORT_CMD`, `LEDGER_CORRUPT_CMD`, and `LEDGER_FAULT_CMD`.

### HS-001
```yaml
component: FMWK-001-ledger
scenario: genesis-and-monotonic-append
priority: P0
validates: [SC-001, SC-002, SC-005]
contracts: [IN-001, IN-006, OUT-001, OUT-005, SIDE-001, SIDE-002]
type: Happy path
```

Setup:
```bash
set -euo pipefail
: "${LEDGER_RESET_CMD:?}"
: "${LEDGER_APPEND_CMD:?}"
: "${LEDGER_TIP_CMD:?}"
export HOLDOUT_TMP="$(mktemp -d)"
sh -lc "$LEDGER_RESET_CMD"
cat > "$HOLDOUT_TMP/event-1.json" <<'EOF'
{
  "event_id": "0195b7fc-c29c-7c2f-a4da-8f6d2eb6d1a1",
  "event_type": "node_creation",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-19T23:50:00Z",
  "provenance": {
    "framework_id": "FMWK-002",
    "pack_id": "PC-001-fold-engine",
    "actor": "system"
  },
  "payload": {
    "node_id": "node-intent-dining-recall",
    "node_type": "intent",
    "lifecycle_state": "LIVE",
    "metadata": {
      "title": "Find Sarah's restaurant recommendation"
    }
  }
}
EOF
cat > "$HOLDOUT_TMP/event-2.json" <<'EOF'
{
  "event_id": "0195b7fd-c29c-7c2f-a4da-8f6d2eb6d1a2",
  "event_type": "signal_delta",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-19T23:51:00Z",
  "provenance": {
    "framework_id": "FMWK-004",
    "pack_id": "PC-002-signal-logging",
    "actor": "agent"
  },
  "payload": {
    "node_id": "node-intent-dining-recall",
    "delta": "1",
    "reason": "active_intent_hit",
    "intent_id": "intent-dining-recall"
  }
}
EOF
```

Execute:
```bash
set -euo pipefail
cat "$HOLDOUT_TMP/event-1.json" | sh -lc "$LEDGER_APPEND_CMD" > "$HOLDOUT_TMP/append-1.json"
cat "$HOLDOUT_TMP/event-2.json" | sh -lc "$LEDGER_APPEND_CMD" > "$HOLDOUT_TMP/append-2.json"
printf '{}' | sh -lc "$LEDGER_TIP_CMD" > "$HOLDOUT_TMP/tip.json"
```

Verify:

| Check | What to Examine | PASS Condition | FAIL Condition |
| --- | --- | --- | --- |
| Genesis append shape | `append-1.json` | `sequence_number=0`, `event.sequence=0`, `event.previous_hash` is the all-zero genesis hash, and `event.hash` matches `sha256:<64 hex>` | Any field missing, wrong value, or generic success shape |
| Monotonic next append | `append-2.json` vs `append-1.json` | `sequence_number=1`, `event.sequence=1`, and `event.previous_hash` equals the first event hash | Gap, fork, or incorrect linkage |
| Self-describing envelope | both append results | `event_id`, `event_type`, `schema_version`, `timestamp`, `provenance`, `payload`, `sequence`, `previous_hash`, and `hash` all exist | Envelope omits required stored fields |
| Tip visibility | `tip.json` | `sequence_number=1` and `hash` equals the second event hash after synchronous append | Tip lags the second append or shape is wrong |

```bash
set -euo pipefail
jq -e '
  .sequence_number == 0 and
  .event.sequence == 0 and
  .event.previous_hash == "sha256:0000000000000000000000000000000000000000000000000000000000000000" and
  (.event.hash | test("^sha256:[0-9a-f]{64}$")) and
  (.event | has("event_id")) and
  (.event | has("event_type")) and
  (.event | has("schema_version")) and
  (.event | has("timestamp")) and
  (.event | has("provenance")) and
  (.event | has("payload"))
' "$HOLDOUT_TMP/append-1.json" >/dev/null

jq -e --slurp '
  .[1].sequence_number == 1 and
  .[1].event.sequence == 1 and
  .[1].event.previous_hash == .[0].event.hash and
  (.[1].event.hash | test("^sha256:[0-9a-f]{64}$")) and
  (.[1].event | has("event_id")) and
  (.[1].event | has("event_type")) and
  (.[1].event | has("schema_version")) and
  (.[1].event | has("timestamp")) and
  (.[1].event | has("provenance")) and
  (.[1].event | has("payload"))
' "$HOLDOUT_TMP/append-1.json" "$HOLDOUT_TMP/append-2.json" >/dev/null

jq -e --slurp '
  .[1].sequence_number == 1 and
  .[1].hash == .[0].event.hash
' "$HOLDOUT_TMP/append-2.json" "$HOLDOUT_TMP/tip.json" >/dev/null
```

Cleanup:
```bash
rm -rf "$HOLDOUT_TMP"
```

### HS-002
```yaml
component: FMWK-001-ledger
scenario: ordered-replay-across-snapshot-boundary
priority: P1
validates: [SC-003, SC-006]
contracts: [IN-001, IN-002, IN-003, IN-004, OUT-001, OUT-002, OUT-003]
type: Integration
```

Setup:
```bash
set -euo pipefail
: "${LEDGER_RESET_CMD:?}"
: "${LEDGER_APPEND_CMD:?}"
: "${LEDGER_READ_CMD:?}"
: "${LEDGER_READ_RANGE_CMD:?}"
: "${LEDGER_READ_SINCE_CMD:?}"
export HOLDOUT_TMP="$(mktemp -d)"
sh -lc "$LEDGER_RESET_CMD"
cat > "$HOLDOUT_TMP/events.jsonl" <<'EOF'
{"event_id":"0195b7f0-1111-7c2f-a4da-8f6d2eb6d100","event_type":"session_start","schema_version":"1.0.0","timestamp":"2026-03-19T23:00:00Z","provenance":{"framework_id":"FMWK-002","pack_id":"PC-003-session-events","actor":"system"},"payload":{"session_id":"sess-operator-0001","actor_id":"operator-ray","channel":"operator","started_at":"2026-03-19T23:00:00Z"}}
{"event_id":"0195b7f1-1111-7c2f-a4da-8f6d2eb6d101","event_type":"node_creation","schema_version":"1.0.0","timestamp":"2026-03-19T23:01:00Z","provenance":{"framework_id":"FMWK-002","pack_id":"PC-001-fold-engine","actor":"system"},"payload":{"node_id":"node-sarah-french","node_type":"memory","lifecycle_state":"LIVE","metadata":{"title":"Sarah restaurant note"}}}
{"event_id":"0195b7f2-1111-7c2f-a4da-8f6d2eb6d102","event_type":"snapshot_created","schema_version":"1.0.0","timestamp":"2026-03-19T23:02:00Z","provenance":{"framework_id":"FMWK-002","pack_id":"PC-004-snapshot","actor":"system"},"payload":{"snapshot_sequence":2,"snapshot_path":"/snapshots/2.snapshot","snapshot_hash":"sha256:1111111111111111111111111111111111111111111111111111111111111111","created_at":"2026-03-19T23:02:00Z"}}
{"event_id":"0195b7f3-1111-7c2f-a4da-8f6d2eb6d103","event_type":"signal_delta","schema_version":"1.0.0","timestamp":"2026-03-19T23:03:00Z","provenance":{"framework_id":"FMWK-004","pack_id":"PC-002-signal-logging","actor":"agent"},"payload":{"node_id":"node-sarah-french","delta":"1","reason":"active_intent_hit","intent_id":"intent-dining-recall"}}
EOF
while IFS= read -r line; do
  printf '%s\n' "$line" | sh -lc "$LEDGER_APPEND_CMD" >/dev/null
done < "$HOLDOUT_TMP/events.jsonl"
```

Execute:
```bash
set -euo pipefail
printf '{"sequence_number":2}' | sh -lc "$LEDGER_READ_CMD" > "$HOLDOUT_TMP/read-one.json"
printf '{"start":0,"end":3}' | sh -lc "$LEDGER_READ_RANGE_CMD" > "$HOLDOUT_TMP/read-range.json"
printf '{"sequence_number":2}' | sh -lc "$LEDGER_READ_SINCE_CMD" > "$HOLDOUT_TMP/read-since.json"
```

Verify:

| Check | What to Examine | PASS Condition | FAIL Condition |
| --- | --- | --- | --- |
| Read one stored event | `read-one.json` | Returns a `LedgerEvent` whose `sequence=2` and `event_type=snapshot_created` | Wrong event, missing event wrapper, or reordered data |
| Ordered bounded replay | `read-range.json` | Returns four events with ascending sequences `[0,1,2,3]` and unchanged stored event types | Missing events, reordered results, or mutated envelopes |
| Replay after snapshot boundary | `read-since.json` | Returns only events with `sequence > 2`; for this fixture the sole event is sequence `3` | Includes boundary event `2`, skips sequence `3`, or reorders data |
| Snapshot boundary presence | `read-one.json` | Snapshot event exposes non-empty `payload` object for replay boundary metadata | Snapshot stored without payload metadata |

```bash
set -euo pipefail
jq -e '
  (.event.sequence == 2) and
  (.event.event_type == "snapshot_created") and
  (.event.payload | type == "object") and
  ((.event.payload | keys | length) > 0)
' "$HOLDOUT_TMP/read-one.json" >/dev/null

jq -e '
  (.events | length == 4) and
  ([.events[].sequence] == [0,1,2,3]) and
  ([.events[].event_type] == ["session_start","node_creation","snapshot_created","signal_delta"])
' "$HOLDOUT_TMP/read-range.json" >/dev/null

jq -e '
  (.events | length == 1) and
  (.events[0].sequence == 3) and
  (.events[0].event_type == "signal_delta")
' "$HOLDOUT_TMP/read-since.json" >/dev/null
```

Cleanup:
```bash
rm -rf "$HOLDOUT_TMP"
```

### HS-003
```yaml
component: FMWK-001-ledger
scenario: verify-parity-and-corruption-detection
priority: P0
validates: [SC-004, SC-010]
contracts: [IN-001, IN-005, OUT-004, SIDE-002, ERR-004]
type: Integration
```

Setup:
```bash
set -euo pipefail
: "${LEDGER_RESET_CMD:?}"
: "${LEDGER_APPEND_CMD:?}"
: "${LEDGER_VERIFY_CMD:?}"
: "${LEDGER_EXPORT_CMD:?}"
: "${LEDGER_CORRUPT_CMD:?}"
export HOLDOUT_TMP="$(mktemp -d)"
sh -lc "$LEDGER_RESET_CMD"
cat > "$HOLDOUT_TMP/events.jsonl" <<'EOF'
{"event_id":"0195b800-1111-7c2f-a4da-8f6d2eb6d110","event_type":"session_start","schema_version":"1.0.0","timestamp":"2026-03-19T23:10:00Z","provenance":{"framework_id":"FMWK-002","pack_id":"PC-003-session-events","actor":"system"},"payload":{"session_id":"sess-operator-0002","actor_id":"operator-ray","channel":"operator","started_at":"2026-03-19T23:10:00Z"}}
{"event_id":"0195b801-1111-7c2f-a4da-8f6d2eb6d111","event_type":"node_creation","schema_version":"1.0.0","timestamp":"2026-03-19T23:11:00Z","provenance":{"framework_id":"FMWK-002","pack_id":"PC-001-fold-engine","actor":"system"},"payload":{"node_id":"node-a","node_type":"memory","lifecycle_state":"LIVE","metadata":{"title":"A"}}}
{"event_id":"0195b802-1111-7c2f-a4da-8f6d2eb6d112","event_type":"signal_delta","schema_version":"1.0.0","timestamp":"2026-03-19T23:12:00Z","provenance":{"framework_id":"FMWK-004","pack_id":"PC-002-signal-logging","actor":"agent"},"payload":{"node_id":"node-a","delta":"1","reason":"active_intent_hit","intent_id":"intent-a"}} 
{"event_id":"0195b803-1111-7c2f-a4da-8f6d2eb6d113","event_type":"snapshot_created","schema_version":"1.0.0","timestamp":"2026-03-19T23:13:00Z","provenance":{"framework_id":"FMWK-002","pack_id":"PC-004-snapshot","actor":"system"},"payload":{"snapshot_sequence":3,"snapshot_path":"/snapshots/3.snapshot","snapshot_hash":"sha256:2222222222222222222222222222222222222222222222222222222222222222","created_at":"2026-03-19T23:13:00Z"}}
EOF
while IFS= read -r line; do
  printf '%s\n' "$line" | sh -lc "$LEDGER_APPEND_CMD" >/dev/null
done < "$HOLDOUT_TMP/events.jsonl"
printf '{"start":0,"end":3,"output_path":"%s"}\n' "$HOLDOUT_TMP/export.jsonl" | sh -lc "$LEDGER_EXPORT_CMD"
```

Execute:
```bash
set -euo pipefail
printf '{"start":0,"end":3,"source_mode":"online"}' | sh -lc "$LEDGER_VERIFY_CMD" > "$HOLDOUT_TMP/verify-online.json"
printf '{"start":0,"end":3,"source_mode":"offline_export","input_path":"'"$HOLDOUT_TMP"'/export.jsonl"}' | sh -lc "$LEDGER_VERIFY_CMD" > "$HOLDOUT_TMP/verify-offline.json"
printf '{"sequence_number":2}' | sh -lc "$LEDGER_CORRUPT_CMD" >/dev/null
printf '{"start":0,"end":3,"source_mode":"online"}' | sh -lc "$LEDGER_VERIFY_CMD" > "$HOLDOUT_TMP/verify-corrupt.json"
```

Verify:

| Check | What to Examine | PASS Condition | FAIL Condition |
| --- | --- | --- | --- |
| Online/offline parity | `verify-online.json` and `verify-offline.json` | Both return the same success verdict `{valid:true,start:0,end:3}` | Modes disagree or omit contract fields |
| Corruption result shape | `verify-corrupt.json` | Returns `valid=false`, `break_at=2`, `start=0`, `end=3` | Generic failure, wrong break point, or missing fields |
| Deterministic first break | `verify-corrupt.json` | First failing sequence is the corrupted sequence, not a later one | Corruption reported late or without `break_at` |

```bash
set -euo pipefail
jq -e '.valid == true and .start == 0 and .end == 3 and (has("break_at") | not)' "$HOLDOUT_TMP/verify-online.json" >/dev/null
jq -e '.valid == true and .start == 0 and .end == 3 and (has("break_at") | not)' "$HOLDOUT_TMP/verify-offline.json" >/dev/null

jq -e '
  .valid == false and
  .break_at == 2 and
  .start == 0 and
  .end == 3
' "$HOLDOUT_TMP/verify-corrupt.json" >/dev/null
```

Cleanup:
```bash
rm -rf "$HOLDOUT_TMP"
```

### HS-004
```yaml
component: FMWK-001-ledger
scenario: serialization-rejection-preserves-tip
priority: P1
validates: [SC-008]
contracts: [IN-001, IN-006, OUT-001, OUT-005, SIDE-002, ERR-002]
type: Error path
```

Setup:
```bash
set -euo pipefail
: "${LEDGER_RESET_CMD:?}"
: "${LEDGER_APPEND_CMD:?}"
: "${LEDGER_TIP_CMD:?}"
: "${LEDGER_FAULT_CMD:?}"
export HOLDOUT_TMP="$(mktemp -d)"
sh -lc "$LEDGER_RESET_CMD"
cat > "$HOLDOUT_TMP/good-event.json" <<'EOF'
{
  "event_id": "0195b810-c29c-7c2f-a4da-8f6d2eb6d120",
  "event_type": "node_creation",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-19T23:20:00Z",
  "provenance": {
    "framework_id": "FMWK-002",
    "pack_id": "PC-001-fold-engine",
    "actor": "system"
  },
  "payload": {
    "node_id": "node-b",
    "node_type": "memory",
    "lifecycle_state": "LIVE",
    "metadata": {
      "title": "B"
    }
  }
}
EOF
cat "$HOLDOUT_TMP/good-event.json" | sh -lc "$LEDGER_APPEND_CMD" >/dev/null
printf '{}' | sh -lc "$LEDGER_TIP_CMD" > "$HOLDOUT_TMP/tip-before.json"
printf '{"mode":"serialization-error-next-append"}' | sh -lc "$LEDGER_FAULT_CMD" >/dev/null
```

Execute:
```bash
set -euo pipefail
cat "$HOLDOUT_TMP/good-event.json" | sh -lc "$LEDGER_APPEND_CMD" > "$HOLDOUT_TMP/serialization-error.json" || true
printf '{}' | sh -lc "$LEDGER_TIP_CMD" > "$HOLDOUT_TMP/tip-after.json"
```

Verify:

| Check | What to Examine | PASS Condition | FAIL Condition |
| --- | --- | --- | --- |
| Error response shape | `serialization-error.json` | Response contains `error_code=LEDGER_SERIALIZATION_ERROR` and non-empty `message` | Generic exception text or wrong code |
| No success payload on error | `serialization-error.json` | Response omits success keys such as `sequence_number` and `event` | Partial success leaked on failure |
| Tip unchanged | `tip-before.json` vs `tip-after.json` | Sequence/hash are identical before and after the rejected append | Failed append advanced or mutated the tip |

```bash
set -euo pipefail
jq -e '
  .error_code == "LEDGER_SERIALIZATION_ERROR" and
  (.message | type == "string") and
  (.message | length > 0) and
  (has("sequence_number") | not) and
  (has("event") | not)
' "$HOLDOUT_TMP/serialization-error.json" >/dev/null

jq -e --slurp '
  .[0].sequence_number == .[1].sequence_number and
  .[0].hash == .[1].hash
' "$HOLDOUT_TMP/tip-before.json" "$HOLDOUT_TMP/tip-after.json" >/dev/null
```

Cleanup:
```bash
rm -rf "$HOLDOUT_TMP"
```

### HS-005
```yaml
component: FMWK-001-ledger
scenario: connection-failure-and-sequence-conflict-are-explicit
priority: P1
validates: [SC-007, SC-009]
contracts: [IN-001, IN-003, IN-006, OUT-001, OUT-003, OUT-005, SIDE-003, ERR-001, ERR-003]
type: Error path
```

Setup:
```bash
set -euo pipefail
: "${LEDGER_RESET_CMD:?}"
: "${LEDGER_APPEND_CMD:?}"
: "${LEDGER_READ_RANGE_CMD:?}"
: "${LEDGER_TIP_CMD:?}"
: "${LEDGER_FAULT_CMD:?}"
export HOLDOUT_TMP="$(mktemp -d)"
sh -lc "$LEDGER_RESET_CMD"
cat > "$HOLDOUT_TMP/base-event.json" <<'EOF'
{
  "event_id": "0195b820-c29c-7c2f-a4da-8f6d2eb6d130",
  "event_type": "session_start",
  "schema_version": "1.0.0",
  "timestamp": "2026-03-19T23:30:00Z",
  "provenance": {
    "framework_id": "FMWK-002",
    "pack_id": "PC-003-session-events",
    "actor": "system"
  },
  "payload": {
    "session_id": "sess-operator-0003",
    "actor_id": "operator-ray",
    "channel": "operator",
    "started_at": "2026-03-19T23:30:00Z"
  }
}
EOF
cat "$HOLDOUT_TMP/base-event.json" | sh -lc "$LEDGER_APPEND_CMD" >/dev/null
printf '{}' | sh -lc "$LEDGER_TIP_CMD" > "$HOLDOUT_TMP/tip-before-errors.json"
printf '{"mode":"connection-error-next-read-range"}' | sh -lc "$LEDGER_FAULT_CMD" >/dev/null
```

Execute:
```bash
set -euo pipefail
printf '{"start":0,"end":0}' | sh -lc "$LEDGER_READ_RANGE_CMD" > "$HOLDOUT_TMP/connection-error.json" || true
printf '{"mode":"sequence-conflict-next-append"}' | sh -lc "$LEDGER_FAULT_CMD" >/dev/null
cat "$HOLDOUT_TMP/base-event.json" | sh -lc "$LEDGER_APPEND_CMD" > "$HOLDOUT_TMP/sequence-error.json" || true
printf '{}' | sh -lc "$LEDGER_TIP_CMD" > "$HOLDOUT_TMP/tip-after-errors.json"
```

Verify:

| Check | What to Examine | PASS Condition | FAIL Condition |
| --- | --- | --- | --- |
| Connection error shape | `connection-error.json` | Response contains `error_code=LEDGER_CONNECTION_ERROR`, non-empty `message`, and no success `events` payload | Generic read failure or wrong error code |
| Sequence error shape | `sequence-error.json` | Response contains `error_code=LEDGER_SEQUENCE_ERROR`, non-empty `message`, and no success `sequence_number` or `event` fields | Generic append failure or partial event returned |
| No fork/no hidden write | `tip-before-errors.json` vs `tip-after-errors.json` | Tip sequence/hash remain unchanged across both failures | Retry path or conflict path mutates chain state |

```bash
set -euo pipefail
jq -e '
  .error_code == "LEDGER_CONNECTION_ERROR" and
  (.message | type == "string") and
  (.message | length > 0) and
  (has("events") | not)
' "$HOLDOUT_TMP/connection-error.json" >/dev/null

jq -e '
  .error_code == "LEDGER_SEQUENCE_ERROR" and
  (.message | type == "string") and
  (.message | length > 0) and
  (has("sequence_number") | not) and
  (has("event") | not)
' "$HOLDOUT_TMP/sequence-error.json" >/dev/null

jq -e --slurp '
  .[0].sequence_number == .[1].sequence_number and
  .[0].hash == .[1].hash
' "$HOLDOUT_TMP/tip-before-errors.json" "$HOLDOUT_TMP/tip-after-errors.json" >/dev/null
```

Cleanup:
```bash
rm -rf "$HOLDOUT_TMP"
```

## Coverage Matrix
COVERAGE GATE: All D2 P0 and P1 scenarios MUST have holdout coverage. Zero gaps allowed. P2/P3 may defer to unit tests.

| D2 Scenario | Priority | Holdout Coverage | Notes |
| --- | --- | --- | --- |
| SC-001 | P0 | HS-001 | Verifies genesis sequence `0`, all-zero `previous_hash`, and hash shape |
| SC-002 | P0 | HS-001 | Verifies contiguous next sequence, exact prior-hash linkage, synchronous tip visibility |
| SC-003 | P1 | HS-002 | Verifies `read`, `read_range`, and `read_since` ordering and stored-form replay |
| SC-004 | P0 | HS-003 | Verifies `verify_chain` parity across `online` and `offline_export` modes |
| SC-005 | P1 | HS-001 | Verifies stored event envelope fields are self-describing |
| SC-006 | P1 | HS-002 | Verifies `snapshot_created` replay boundary behavior and stored payload presence |
| SC-007 | P1 | HS-005 | Verifies explicit `LEDGER_SEQUENCE_ERROR` and no fork/no hidden write |
| SC-008 | P1 | HS-004 | Verifies `LEDGER_SERIALIZATION_ERROR` contract shape and unchanged tip |
| SC-009 | P1 | HS-005 | Verifies `LEDGER_CONNECTION_ERROR` contract shape and unchanged chain state |
| SC-010 | P0 | HS-003 | Verifies corruption returns `valid=false` with deterministic `break_at` |

## Run Protocol
When: after builder delivers + handoff tests pass.
Order: P0 first (any fail = stop), then P1, then P2.
Threshold: all P0 pass, all P1 pass, no partial credit.
On failure: file against responsible D8 task. Include: failed SC-###, violated contract, actual vs expected.
