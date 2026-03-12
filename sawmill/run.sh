#!/bin/bash
# ============================================================================
# Sawmill Orchestrator — DoPeJarMo Build Pipeline
# ============================================================================
#
# Usage:  ./sawmill/run.sh <FMWK-ID> [--from-turn A|B|C|D|E] [--interactive]
# Example: ./sawmill/run.sh FMWK-001-ledger --from-turn D
#          ./sawmill/run.sh FMWK-900-sawmill-smoke
#          ./sawmill/run.sh FMWK-900-sawmill-smoke --interactive
#
# This script orchestrates the five Sawmill turns (A-E) for a single
# framework. It dispatches worker agents, records checkpoints, and manages
# retry/review loops.
#
# Operational source of truth:
#   sawmill/EXECUTION_CONTRACT.md defines the runtime execution model.
#   This script remains the runtime authority for actual stage execution.
#
# Expected execution contract:
#   Human  -> authorizes the run and handles escalations
#   Claude -> orchestrates invocation and supervises progress
#   Workers -> resolved by sawmill/ROLE_REGISTRY.yaml
#
# Prerequisites:
#   - At least one agent CLI installed: claude, codex, or gemini
#   - Repository is the working directory
#
# Role/backend defaults come from sawmill/ROLE_REGISTRY.yaml.
# Environment overrides still win at runtime:
#   SAWMILL_SPEC_AGENT=claude|codex|gemini
#   SAWMILL_BUILD_AGENT=claude|codex|gemini
#   SAWMILL_HOLDOUT_AGENT=claude|codex|gemini
#   SAWMILL_EVAL_AGENT=claude|codex|gemini
#   SAWMILL_AUDIT_AGENT=claude|codex|gemini
#   SAWMILL_PORTAL_AGENT=claude|codex|gemini
#
# Runtime defaults to unattended, exception-driven execution. Use
# --interactive to pause at checkpoints for human review.
# ============================================================================

set -euo pipefail

# --- Configuration ---------------------------------------------------------

usage() {
    echo "Usage: ./sawmill/run.sh <FMWK-ID> [--from-turn A|B|C|D|E] [--interactive]"
    echo "       ./sawmill/run.sh --audit"
    echo "Example: ./sawmill/run.sh FMWK-001-ledger --from-turn D"
    echo "         ./sawmill/run.sh FMWK-900-sawmill-smoke"
    echo "         ./sawmill/run.sh FMWK-900-sawmill-smoke --interactive"
    echo "         ./sawmill/run.sh --audit"
}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helpers used by both audit mode and the normal pipeline.
log() { echo -e "${BLUE}[sawmill]${NC} $1"; }
checkpoint() {
    echo -e "\n${YELLOW}>>> CHECKPOINT: $1${NC}"
    if [ "${INTERACTIVE:-false}" != true ]; then
        log "Unattended mode: checkpoint recorded, continuing"
        return 0
    fi
    if [ ! -t 0 ]; then
        fail "Interactive checkpoints require a live TTY. Re-run with --interactive in a terminal or use the default unattended path."
        exit 1
    fi
    echo -e "${YELLOW}>>> Review the output, then press Enter to continue (or Ctrl+C to abort)${NC}"
    read -r
}
escalate() {
    fail "$1"
    exit 1
}
pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }

validate_agent_timeout() {
    case "$AGENT_TIMEOUT_SECONDS" in
        ''|*[!0-9]*)
            fail "SAWMILL_AGENT_TIMEOUT_SECONDS must be a non-negative integer (got '${AGENT_TIMEOUT_SECONDS}')"
            exit 1
            ;;
        *)
            ;;
    esac
}

extract_prompt_contract_version() {
    local file_path="$1"
    awk '
        {
            line = $0
            lower = tolower(line)
            if (match(lower, /\*\*version\*\*:[[:space:]]*[0-9a-z._-]+/)) {
                segment = substr(lower, RSTART, RLENGTH)
                sub(/^.*\*\*version\*\*:[[:space:]]*/, "", segment)
                print segment
                exit
            }
            if (match(lower, /(^|[|[:space:]])version:[[:space:]]*[0-9a-z._-]+([|[:space:]]|$)/)) {
                segment = substr(lower, RSTART, RLENGTH)
                sub(/^.*version:[[:space:]]*/, "", segment)
                sub(/[|[:space:]].*$/, "", segment)
                print segment
                exit
            }
        }
    ' "$file_path"
}

load_prompt_contract_versions() {
    export BUILDER_PROMPT_CONTRACT_VERSION REVIEWER_PROMPT_CONTRACT_VERSION
    BUILDER_PROMPT_CONTRACT_VERSION="$(extract_prompt_contract_version "Templates/BUILDER_PROMPT_CONTRACT.md")"
    REVIEWER_PROMPT_CONTRACT_VERSION="$(extract_prompt_contract_version "Templates/REVIEWER_PROMPT_CONTRACT.md")"

    if [ -z "$BUILDER_PROMPT_CONTRACT_VERSION" ] || [ -z "$REVIEWER_PROMPT_CONTRACT_VERSION" ]; then
        fail "Unable to determine prompt contract versions from Templates/BUILDER_PROMPT_CONTRACT.md and Templates/REVIEWER_PROMPT_CONTRACT.md"
        exit 1
    fi
}

iso_timestamp() {
    date -u +%Y-%m-%dT%H:%M:%SZ
}

new_run_id() {
    python3 - <<'PY'
import datetime
import uuid
ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
print(f"{ts}-{uuid.uuid4().hex[:12]}")
PY
}

new_event_id() {
    python3 - <<'PY'
import uuid
print(uuid.uuid4().hex)
PY
}

hash_file() {
    shasum -a 256 "$1" | awk '{print $1}'
}

current_status_field() {
    local field="$1"
    python3 - "$STATUS_JSON_PATH" "$field" <<'PY'
import json
import sys
from pathlib import Path

status_path = Path(sys.argv[1])
field = sys.argv[2]
if not status_path.exists():
    sys.exit(1)
data = json.loads(status_path.read_text(encoding="utf-8"))
value = data.get(field, "")
if isinstance(value, bool):
    print("true" if value else "false")
elif value is None:
    print("")
else:
    print(value)
PY
}

current_status_state() {
    current_status_field state
}

current_governed_path_intact() {
    current_status_field governed_path_intact
}

build_run_metadata_file() {
    local metadata_file
    metadata_file="$(mktemp "/tmp/sawmill-run-metadata.XXXXXX")"
    python3 - "$metadata_file" <<'PY'
import json
import os
import sys
from pathlib import Path
import hashlib


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


role_backend_resolution = {
    "spec-agent": os.environ["SPEC_AGENT"],
    "holdout-agent": os.environ["HOLDOUT_AGENT"],
    "builder": os.environ["BUILD_AGENT"],
    "reviewer": os.environ["REVIEW_AGENT"],
    "evaluator": os.environ["EVAL_AGENT"],
    "auditor": os.environ["AUDIT_AGENT"],
    "portal-steward": os.environ["PORTAL_AGENT"],
}

model_policies = {
    "spec-agent": os.environ["SPEC_MODEL_POLICY"],
    "holdout-agent": os.environ["HOLDOUT_MODEL_POLICY"],
    "builder": os.environ["BUILD_MODEL_POLICY"],
    "reviewer": os.environ["REVIEW_MODEL_POLICY"],
    "evaluator": os.environ["EVAL_MODEL_POLICY"],
    "auditor": os.environ["AUDIT_MODEL_POLICY"],
    "portal-steward": os.environ["PORTAL_MODEL_POLICY"],
}

prompt_contract_versions = {
    "builder_prompt_contract": os.environ["BUILDER_PROMPT_CONTRACT_VERSION"],
    "reviewer_prompt_contract": os.environ["REVIEWER_PROMPT_CONTRACT_VERSION"],
}

role_file_hashes = {}
for key in ("SPEC_ROLE_FILE", "HOLDOUT_ROLE_FILE", "BUILD_ROLE_FILE", "REVIEW_ROLE_FILE", "EVAL_ROLE_FILE", "AUDIT_ROLE_FILE", "PORTAL_ROLE_FILE"):
    path = Path(os.environ[key])
    role_file_hashes[path.as_posix()] = sha256_file(path)

prompt_file_hashes = {}
for prompt_key in os.environ["ALL_PROMPT_KEYS"].split():
    env_key = f"PROMPT_{prompt_key.upper()}_PROMPT_FILE"
    path = Path(os.environ[env_key])
    prompt_file_hashes[path.as_posix()] = sha256_file(path)

metadata = {
    "run_id": os.environ["RUN_ID"],
    "framework_id": os.environ["FMWK"],
    "started_at": os.environ["RUN_STARTED_AT"],
    "requested_entry_path": "./sawmill/run.sh",
    "from_turn": os.environ["FROM_TURN"],
    "retry_budget": int(os.environ["MAX_ATTEMPTS"]),
    "role_backend_resolution": role_backend_resolution,
    "model_policies": model_policies,
    "prompt_contract_versions": prompt_contract_versions,
    "role_file_hashes": role_file_hashes,
    "prompt_file_hashes": prompt_file_hashes,
    "artifact_registry_version_hash": sha256_file(Path(os.environ["ARTIFACT_REGISTRY"])),
    "graph_version": "none",
    "operator_mode": os.environ["OPERATOR_MODE"],
}

Path(sys.argv[1]).write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
    printf '%s\n' "$metadata_file"
}

project_status_now() {
    python3 "$RUN_STATUS_PROJECTOR" project-status --run-dir "$RUN_DIR" >/dev/null
}

emit_event() {
    local event_type="$1"
    local outcome="$2"
    local failure_code="$3"
    local parent_event_id="$4"
    local turn="$5"
    local step="$6"
    local role="$7"
    local backend="$8"
    local attempt="$9"
    local summary="${10}"
    shift 10

    local event_id timestamp
    event_id="$(new_event_id)"
    timestamp="$(iso_timestamp)"

    local cmd=(
        python3 "$RUN_STATUS_PROJECTOR" append-event
        --run-dir "$RUN_DIR"
        --event-id "$event_id"
        --run-id "$RUN_ID"
        --timestamp "$timestamp"
        --turn "$turn"
        --step "$step"
        --role "$role"
        --backend "$backend"
        --attempt "$attempt"
        --event-type "$event_type"
        --outcome "$outcome"
        --failure-code "$failure_code"
        --causal-parent-event-id "$parent_event_id"
        --summary "$summary"
    )

    while [ $# -gt 0 ]; do
        case "$1" in
            --evidence-ref)
                cmd+=(--evidence-ref "$2")
                shift 2
                ;;
            --contract-ref)
                cmd+=(--contract-ref "$2")
                shift 2
                ;;
            *)
                fail "Unknown emit_event argument: $1"
                exit 1
                ;;
        esac
    done

    "${cmd[@]}" >/dev/null
    project_status_now
    printf '%s\n' "$event_id"
}

record_run_failed() {
    local parent_event_id="$1"
    local failure_code="$2"
    local summary="$3"
    emit_event "run_failed" "failed" "$failure_code" "$parent_event_id" "${CURRENT_EVENT_TURN:-orchestrator}" "${CURRENT_EVENT_STEP:-run}" "${CURRENT_EVENT_ROLE:-orchestrator}" "${CURRENT_EVENT_BACKEND:-runtime}" "${CURRENT_EVENT_ATTEMPT:-0}" "$summary" >/dev/null
}

fail_preflight() {
    local failure_code="$1"
    local summary="$2"
    CURRENT_EVENT_TURN="orchestrator"
    CURRENT_EVENT_STEP="preflight"
    CURRENT_EVENT_ROLE="orchestrator"
    CURRENT_EVENT_BACKEND="runtime"
    CURRENT_EVENT_ATTEMPT=0
    local preflight_failure
    preflight_failure="$(emit_event "preflight_passed" "failed" "$failure_code" "$RUN_STARTED_EVENT_ID" "orchestrator" "preflight" "orchestrator" "runtime" 0 "$summary")"
    record_run_failed "$preflight_failure" "$failure_code" "$summary"
    fail "$summary"
    exit 1
}

record_escalation() {
    local parent_event_id="$1"
    local failure_code="$2"
    local summary="$3"
    emit_event "escalation_triggered" "escalated" "$failure_code" "$parent_event_id" "${CURRENT_EVENT_TURN:-orchestrator}" "${CURRENT_EVENT_STEP:-run}" "${CURRENT_EVENT_ROLE:-orchestrator}" "${CURRENT_EVENT_BACKEND:-runtime}" "${CURRENT_EVENT_ATTEMPT:-0}" "$summary" >/dev/null
}

record_manual_intervention() {
    local parent_event_id="$1"
    local summary="$2"
    emit_event "manual_intervention_recorded" "recorded" "MANUAL_INTERVENTION" "$parent_event_id" "${CURRENT_EVENT_TURN:-orchestrator}" "${CURRENT_EVENT_STEP:-manual_intervention}" "${CURRENT_EVENT_ROLE:-human}" "${CURRENT_EVENT_BACKEND:-manual}" "${CURRENT_EVENT_ATTEMPT:-0}" "$summary" >/dev/null
}

step_log_prefix() {
    local step_key="$1"
    local attempt="$2"
    local prefix="${step_key}"
    if [ "$step_key" = "portal_stage" ] && [ -n "${STAGE:-}" ]; then
        prefix="${step_key}-$(printf '%s' "$STAGE" | tr '[:upper:] ' '[:lower:]_')"
    fi
    printf '%s/logs/%s.attempt%s' "$RUN_DIR" "$prefix" "$attempt"
}

invocation_prefix() {
    local step_key="$1"
    local attempt="$2"
    local prefix="${step_key}"
    if [ "$step_key" = "portal_stage" ] && [ -n "${STAGE:-}" ]; then
        prefix="${step_key}-$(printf '%s' "$STAGE" | tr '[:upper:] ' '[:lower:]_')"
    fi
    printf '%s/%s.attempt%s' "$RUN_INVOCATIONS_DIR" "$prefix" "$attempt"
}

write_invocation_payload() {
    local payload_path="$1"
    local role_content="$2"
    local prompt="$3"
    mkdir -p "$(dirname "$payload_path")"
    printf '%s\n\n%s' "$role_content" "$prompt" > "$payload_path"
}

write_invocation_meta() {
    local meta_path="$1"
    local payload_path="$2"
    local liveness_path="$3"
    local result_path="$4"
    local stdout_log="$5"
    local stderr_log="$6"
    local heartbeat_file="$7"
    local turn="$8"
    local step="$9"
    local role_name="${10}"
    local backend="${11}"
    local attempt="${12}"
    local prompt_key="${13}"
    local agent_invoked_event_id="${14}"
    local model_policy="${15:-default}"

    python3 - "$meta_path" <<'PY'
import json
import os
import sys
from pathlib import Path

meta_path = Path(sys.argv[1])
payload_path = os.environ["SAWMILL_META_PAYLOAD_PATH"]
liveness_path = os.environ["SAWMILL_META_LIVENESS_PATH"]
result_path = os.environ["SAWMILL_META_RESULT_PATH"]
stdout_log = os.environ["SAWMILL_META_STDOUT_LOG"]
stderr_log = os.environ["SAWMILL_META_STDERR_LOG"]
heartbeat_file = os.environ["SAWMILL_META_HEARTBEAT_FILE"]

meta = {
    "run_id": os.environ["RUN_ID"],
    "framework_id": os.environ["FMWK"],
    "turn": os.environ["SAWMILL_META_TURN"],
    "step": os.environ["SAWMILL_META_STEP"],
    "role": os.environ["SAWMILL_META_ROLE"],
    "backend": os.environ["SAWMILL_META_BACKEND"],
    "attempt": int(os.environ["SAWMILL_META_ATTEMPT"]),
    "timeout_seconds": int(os.environ["SAWMILL_META_TIMEOUT_SECONDS"]),
    "stdout_log": stdout_log,
    "stderr_log": stderr_log,
    "heartbeat_file": heartbeat_file,
    "payload_path": payload_path,
    "prompt_key": os.environ["SAWMILL_META_PROMPT_KEY"],
    "model_policy": os.environ["SAWMILL_META_MODEL_POLICY"],
    "operator_mode": os.environ["OPERATOR_MODE"],
    "agent_invoked_event_id": os.environ["SAWMILL_META_AGENT_INVOKED_EVENT_ID"],
    "result_path": result_path,
    "liveness_path": liveness_path,
    "cwd": Path.cwd().as_posix(),
}
meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

emit_liveness_records() {
    local liveness_path="$1"
    local agent_invoked_event_id="$2"
    local turn="$3"
    local step="$4"
    local role_name="$5"
    local backend="$6"
    local attempt="$7"
    local state_file="$8"

    python3 - "$liveness_path" "$state_file" "$RUN_STATUS_PROJECTOR" "$RUN_DIR" "$agent_invoked_event_id" "$turn" "$step" "$role_name" "$backend" "$attempt" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

liveness_path = Path(sys.argv[1])
state_file = Path(sys.argv[2])
projector = sys.argv[3]
run_dir = sys.argv[4]
parent_id, turn, step, role, backend, attempt = sys.argv[5:11]

if not liveness_path.exists():
    raise SystemExit(0)

seen = 0
if state_file.exists():
    raw = state_file.read_text(encoding="utf-8").strip()
    if raw:
        seen = int(raw)

lines = [line for line in liveness_path.read_text(encoding="utf-8").splitlines() if line.strip()]
new_lines = lines[seen:]
if not new_lines:
    raise SystemExit(0)

for raw in new_lines:
    record = json.loads(raw)
    summary = f"{record['observation']} observed from {record['source']}"
    subprocess.run(
        [
            "python3",
            projector,
            "append-event",
            "--run-dir",
            run_dir,
            "--event-id",
            __import__("uuid").uuid4().hex,
            "--run-id",
            record["run_id"],
            "--timestamp",
            record["timestamp"],
            "--turn",
            turn,
            "--step",
            step,
            "--role",
            role,
            "--backend",
            backend,
            "--attempt",
            attempt,
            "--event-type",
            "agent_liveness_observed",
            "--outcome",
            record["observation"],
            "--failure-code",
            "none",
            "--causal-parent-event-id",
            parent_id,
            "--summary",
            summary,
            "--evidence-ref",
            str(liveness_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["python3", projector, "project-status", "--run-dir", run_dir],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

state_file.write_text(str(len(lines)), encoding="utf-8")
PY
}

validate_evidence_artifact() {
    local kind="$1"
    local artifact_id="$2"
    shift 2
    python3 "$EVIDENCE_VALIDATOR" --kind "$kind" --artifact "$(artifact_path "$artifact_id")" --run-id "$RUN_ID" --attempt "$ATTEMPT" "$@"
}

validate_prompt_step_success() {
    local prompt_key="$1"
    local parent_event_id="$2"
    local turn="$3"
    local role_name="$4"
    local backend="$5"
    local attempt="$6"
    shift 6
    local event_args=()

    if ! verify_prompt_outputs "$prompt_key"; then
        local failure_event_id
        failure_event_id="$(emit_event "output_verified" "failed" "OUTPUT_VERIFICATION_FAILED" "$parent_event_id" "$turn" "$prompt_key" "$role_name" "$backend" "$attempt" "${LAST_PROMPT_VERIFICATION_ERROR:-Output verification failed for ${prompt_key}}")"
        record_run_failed "$failure_event_id" "OUTPUT_VERIFICATION_FAILED" "Output verification failed for ${prompt_key}"
        fail "Output verification failed for ${prompt_key}"
        exit 1
    fi

    while [ $# -gt 0 ]; do
        event_args+=(--evidence-ref "$1")
        shift
    done

    LAST_OUTPUT_VERIFIED_EVENT_ID="$(emit_event "output_verified" "verified" "none" "$parent_event_id" "$turn" "$prompt_key" "$role_name" "$backend" "$attempt" "Outputs verified for ${prompt_key}" "${event_args[@]}")"
}

initialize_run_harness() {
    RUN_STARTED_AT="$(iso_timestamp)"
    RUN_ID="$(new_run_id)"
    RUN_DIR="${SAWMILL_DIR}/runs/${RUN_ID}"
    RUN_JSON_PATH="${RUN_DIR}/run.json"
    STATUS_JSON_PATH="${RUN_DIR}/status.json"
    EVENTS_JSON_PATH="${RUN_DIR}/events.jsonl"
    RUN_LOG_DIR="${RUN_DIR}/logs"
    RUN_INVOCATIONS_DIR="${RUN_DIR}/invocations"
    RUN_HEARTBEATS_DIR="${RUN_DIR}/heartbeats"
    export RUN_ID RUN_DIR RUN_JSON_PATH STATUS_JSON_PATH EVENTS_JSON_PATH RUN_LOG_DIR RUN_INVOCATIONS_DIR RUN_HEARTBEATS_DIR RUN_STARTED_AT

    local metadata_file
    METADATA_FILE="$(build_run_metadata_file)"
    python3 "$RUN_STATUS_PROJECTOR" init-run --run-dir "$RUN_DIR" --metadata-file "$METADATA_FILE" >/dev/null
    rm -f "$METADATA_FILE"
    mkdir -p "$RUN_INVOCATIONS_DIR" "$RUN_HEARTBEATS_DIR"

    local run_started_event
    run_started_event="$(emit_event "run_started" "started" "none" "" "orchestrator" "run" "orchestrator" "runtime" 0 "Run started for ${FMWK}")"
    RUN_STARTED_EVENT_ID="$run_started_event"
    export RUN_STARTED_EVENT_ID
}

ROLE_REGISTRY="sawmill/ROLE_REGISTRY.yaml"
ROLE_REGISTRY_VALIDATOR="sawmill/validate_role_registry.py"
ARTIFACT_REGISTRY="sawmill/ARTIFACT_REGISTRY.yaml"
ARTIFACT_REGISTRY_VALIDATOR="sawmill/validate_artifact_registry.py"
STAGE_ARTIFACT_RESOLVER="sawmill/resolve_stage_artifacts.py"
PROMPT_REGISTRY="sawmill/PROMPT_REGISTRY.yaml"
PROMPT_REGISTRY_VALIDATOR="sawmill/validate_prompt_registry.py"
PROMPT_RENDERER="sawmill/render_prompt.py"
TIMEOUT_RUNNER="sawmill/run_with_timeout.py"
RUNNER="sawmill/runner.py"
BACKEND_ADAPTERS="sawmill/backend_adapters.py"
PORTAL_MIRROR_SYNCER="sawmill/sync_portal_mirrors.py"
RUN_STATUS_PROJECTOR="sawmill/project_run_status.py"
EVIDENCE_VALIDATOR="sawmill/validate_evidence_artifacts.py"
AGENT_TIMEOUT_SECONDS="${SAWMILL_AGENT_TIMEOUT_SECONDS:-1800}"

RUN_ID=""
RUN_DIR=""
RUN_JSON_PATH=""
STATUS_JSON_PATH=""
EVENTS_JSON_PATH=""
RUN_LOG_DIR=""
RUN_INVOCATIONS_DIR=""
RUN_HEARTBEATS_DIR=""
LAST_AGENT_EXIT_EVENT_ID=""
LAST_FAILURE_EVENT_ID=""
LAST_FAILURE_CODE=""
LAST_OUTPUT_VERIFIED_EVENT_ID=""
CURRENT_TURN_EVENT_ID=""
LAST_TURN_COMPLETED_EVENT_ID=""
OPERATOR_MODE=""

resolve_registry_backend() {
    local override_var="$1"
    local default_backend="$2"

    if [ -n "${!override_var:-}" ]; then
        printf '%s\n' "${!override_var}"
    else
        printf '%s\n' "$default_backend"
    fi
}

validate_selected_backend() {
    local selected_backend="$1"
    local allowed_backends="$2"
    local role_name="$3"
    local override_var="$4"

    case " ${allowed_backends} " in
        *" ${selected_backend} "*) ;;
        *)
            fail "Role '${role_name}' resolved backend '${selected_backend}' via ${override_var} is not allowed (${allowed_backends})"
            exit 1
            ;;
    esac
}

require_backend_cli() {
    local agent_label="$1"
    local backend="$2"

    case "$backend" in
        claude) command -v claude >/dev/null 2>&1 || return 1 ;;
        codex)  command -v codex  >/dev/null 2>&1 || return 1 ;;
        gemini) command -v gemini >/dev/null 2>&1 || return 1 ;;
        mock)   [ -f "sawmill/workers/mock_worker.py" ] || return 1 ;;
        *)
            return 1
            ;;
    esac
}

load_role_registry() {
    if [ ! -f "$ROLE_REGISTRY_VALIDATOR" ]; then
        fail "Missing role registry validator: ${ROLE_REGISTRY_VALIDATOR}"
        exit 1
    fi

    python3 "$ROLE_REGISTRY_VALIDATOR" --registry "$ROLE_REGISTRY" >/dev/null
    eval "$(
        python3 "$ROLE_REGISTRY_VALIDATOR" --registry "$ROLE_REGISTRY" --shell-exports
    )"

    SPEC_AGENT="$(resolve_registry_backend "$SPEC_ENV_OVERRIDE" "$SPEC_DEFAULT_BACKEND")"
    BUILD_AGENT="$(resolve_registry_backend "$BUILD_ENV_OVERRIDE" "$BUILD_DEFAULT_BACKEND")"
    HOLDOUT_AGENT="$(resolve_registry_backend "$HOLDOUT_ENV_OVERRIDE" "$HOLDOUT_DEFAULT_BACKEND")"
    REVIEW_AGENT="$(resolve_registry_backend "$REVIEW_ENV_OVERRIDE" "$REVIEW_DEFAULT_BACKEND")"
    EVAL_AGENT="$(resolve_registry_backend "$EVAL_ENV_OVERRIDE" "$EVAL_DEFAULT_BACKEND")"
    AUDIT_AGENT="$(resolve_registry_backend "$AUDIT_ENV_OVERRIDE" "$AUDIT_DEFAULT_BACKEND")"
    PORTAL_AGENT="$(resolve_registry_backend "$PORTAL_ENV_OVERRIDE" "$PORTAL_DEFAULT_BACKEND")"

    validate_selected_backend "$SPEC_AGENT" "$SPEC_ALLOWED_BACKENDS" "spec-agent" "$SPEC_ENV_OVERRIDE"
    validate_selected_backend "$BUILD_AGENT" "$BUILD_ALLOWED_BACKENDS" "builder" "$BUILD_ENV_OVERRIDE"
    validate_selected_backend "$HOLDOUT_AGENT" "$HOLDOUT_ALLOWED_BACKENDS" "holdout-agent" "$HOLDOUT_ENV_OVERRIDE"
    validate_selected_backend "$REVIEW_AGENT" "$REVIEW_ALLOWED_BACKENDS" "reviewer" "$REVIEW_ENV_OVERRIDE"
    validate_selected_backend "$EVAL_AGENT" "$EVAL_ALLOWED_BACKENDS" "evaluator" "$EVAL_ENV_OVERRIDE"
    validate_selected_backend "$AUDIT_AGENT" "$AUDIT_ALLOWED_BACKENDS" "auditor" "$AUDIT_ENV_OVERRIDE"
    validate_selected_backend "$PORTAL_AGENT" "$PORTAL_ALLOWED_BACKENDS" "portal-steward" "$PORTAL_ENV_OVERRIDE"
}

load_artifact_registry() {
    if [ ! -f "$ARTIFACT_REGISTRY_VALIDATOR" ]; then
        fail "Missing artifact registry validator: ${ARTIFACT_REGISTRY_VALIDATOR}"
        exit 1
    fi

    python3 "$ARTIFACT_REGISTRY_VALIDATOR" \
        --registry "$ARTIFACT_REGISTRY" \
        --roles "$ROLE_REGISTRY" >/dev/null
    eval "$(
        python3 "$ARTIFACT_REGISTRY_VALIDATOR" \
            --registry "$ARTIFACT_REGISTRY" \
            --roles "$ROLE_REGISTRY" \
            --shell-exports
    )"
}

load_stage_artifact_metadata() {
    if [ ! -f "$STAGE_ARTIFACT_RESOLVER" ]; then
        fail "Missing stage artifact resolver: ${STAGE_ARTIFACT_RESOLVER}"
        exit 1
    fi

    python3 "$STAGE_ARTIFACT_RESOLVER" --registry "$ARTIFACT_REGISTRY" >/dev/null
    eval "$(
        python3 "$STAGE_ARTIFACT_RESOLVER" \
            --registry "$ARTIFACT_REGISTRY" \
            --shell-exports
    )"
}

load_prompt_registry() {
    if [ ! -f "$PROMPT_REGISTRY_VALIDATOR" ]; then
        fail "Missing prompt registry validator: ${PROMPT_REGISTRY_VALIDATOR}"
        exit 1
    fi

    python3 "$PROMPT_REGISTRY_VALIDATOR" \
        --registry "$PROMPT_REGISTRY" \
        --roles "$ROLE_REGISTRY" \
        --artifacts "$ARTIFACT_REGISTRY" >/dev/null
    eval "$(
        python3 "$PROMPT_REGISTRY_VALIDATOR" \
            --registry "$PROMPT_REGISTRY" \
            --roles "$ROLE_REGISTRY" \
            --artifacts "$ARTIFACT_REGISTRY" \
            --shell-exports
    )"
}

key_to_env() {
    printf '%s' "$1" | tr '[:lower:]' '[:upper:]'
}

artifact_path() {
    local key prefix template_var template
    key="$1"
    prefix="$(key_to_env "$key")"
    template_var="ARTIFACT_${prefix}_PATH_TEMPLATE"
    template="${!template_var}"
    printf '%s\n' "${template//\{FMWK\}/$FMWK}"
}

artifact_kind() {
    local key prefix kind_var
    key="$1"
    prefix="$(key_to_env "$key")"
    kind_var="ARTIFACT_${prefix}_KIND"
    printf '%s\n' "${!kind_var}"
}

stage_all_artifacts() {
    local stage="$1"
    local stage_var="STAGE_${stage}_ALL_ARTIFACTS"
    printf '%s\n' "${!stage_var:-}"
}

stage_required_artifacts() {
    local stage="$1"
    local stage_var="STAGE_${stage}_REQUIRED_ARTIFACTS"
    printf '%s\n' "${!stage_var:-}"
}

prompt_file() {
    local key prefix file_var
    key="$1"
    prefix="$(key_to_env "$key")"
    file_var="PROMPT_${prefix}_PROMPT_FILE"
    printf '%s\n' "${!file_var}"
}

prompt_expected_artifacts() {
    local key prefix expected_var
    key="$1"
    prefix="$(key_to_env "$key")"
    expected_var="PROMPT_${prefix}_EXPECTED_ARTIFACTS"
    printf '%s\n' "${!expected_var}"
}

prompt_required_artifacts() {
    local key prefix required_var
    key="$1"
    prefix="$(key_to_env "$key")"
    required_var="PROMPT_${prefix}_REQUIRED_ARTIFACTS"
    printf '%s\n' "${!required_var}"
}

prompt_freshness_policy() {
    local key prefix policy_var
    key="$1"
    prefix="$(key_to_env "$key")"
    policy_var="PROMPT_${prefix}_FRESHNESS_POLICY"
    printf '%s\n' "${!policy_var}"
}

prompt_role() {
    local key prefix role_var
    key="$1"
    prefix="$(key_to_env "$key")"
    role_var="PROMPT_${prefix}_ROLE"
    printf '%s\n' "${!role_var}"
}

prompt_turn() {
    case "$1" in
        audit_run) printf '%s\n' "audit" ;;
        portal_stage) printf '%s\n' "portal" ;;
        turn_a_spec) printf '%s\n' "A" ;;
        turn_b_plan) printf '%s\n' "B" ;;
        turn_c_holdout) printf '%s\n' "C" ;;
        turn_d_13q|turn_d_review|turn_d_build) printf '%s\n' "D" ;;
        turn_e_eval) printf '%s\n' "E" ;;
        *) printf '%s\n' "orchestrator" ;;
    esac
}

export_artifact_paths() {
    local artifact_id upper
    for artifact_id in $ALL_ARTIFACT_IDS; do
        upper="$(key_to_env "$artifact_id")"
        export "${upper}_PATH=$(artifact_path "$artifact_id")"
    done
}

render_prompt_output() {
    local key template_path
    key="$1"
    template_path="$(prompt_file "$key")"
    python3 "$PROMPT_RENDERER" "$template_path"
}

prompt_sentinel_var() {
    local key="$1"
    printf 'PROMPT_%s_SENTINEL' "$(key_to_env "$key")"
}

prompt_sentinel_path() {
    local key="$1"
    local sentinel_var
    sentinel_var="$(prompt_sentinel_var "$key")"
    printf '%s\n' "${!sentinel_var:-}"
}

snapshot_prompt_outputs() {
    local prompt_key="$1"
    local sentinel_var sentinel_path
    sentinel_path="$(mktemp "/tmp/sawmill-${prompt_key}.XXXXXX")"
    sentinel_var="$(prompt_sentinel_var "$prompt_key")"
    printf -v "$sentinel_var" '%s' "$sentinel_path"
}

cleanup_prompt_sentinel() {
    local prompt_key="$1"
    local sentinel_var sentinel_path
    sentinel_var="$(prompt_sentinel_var "$prompt_key")"
    sentinel_path="${!sentinel_var:-}"
    if [ -n "$sentinel_path" ] && [ -f "$sentinel_path" ]; then
        rm -f "$sentinel_path"
    fi
    printf -v "$sentinel_var" '%s' ""
}

ensure_artifact_exists() {
    local artifact_id label path kind
    artifact_id="$1"
    label="${2:-artifact}"
    path="$(artifact_path "$artifact_id")"
    kind="$(artifact_kind "$artifact_id")"
    if [ "$kind" = "dir" ]; then
        [ -d "$path" ] || return 1
    else
        [ -f "$path" ] || return 1
    fi
}

artifact_exists() {
    local artifact_id="$1"
    local path kind
    path="$(artifact_path "$artifact_id")"
    kind="$(artifact_kind "$artifact_id")"
    if [ "$kind" = "dir" ]; then
        [ -d "$path" ]
    else
        [ -f "$path" ]
    fi
}

artifact_present_for_state() {
    local artifact_id="$1"
    local path kind
    path="$(artifact_path "$artifact_id")"
    kind="$(artifact_kind "$artifact_id")"
    if [ "$kind" = "dir" ]; then
        [ -d "$path" ] || return 1
        find "$path" -mindepth 1 -print -quit 2>/dev/null | grep -q .
    else
        [ -f "$path" ]
    fi
}

ensure_artifact_ids() {
    local label="$1"
    shift
    local artifact_id
    for artifact_id in "$@"; do
        ensure_artifact_exists "$artifact_id" "$label" || {
            LAST_MISSING_ARTIFACT_PATH="$(artifact_path "$artifact_id")"
            LAST_MISSING_ARTIFACT_LABEL="$label"
            return 1
        }
    done
}

ensure_prompt_inputs() {
    local prompt_key="$1"
    local artifact_id
    for artifact_id in $(prompt_required_artifacts "$prompt_key"); do
        ensure_artifact_exists "$artifact_id" "input for ${prompt_key}" || {
            LAST_MISSING_ARTIFACT_PATH="$(artifact_path "$artifact_id")"
            LAST_MISSING_ARTIFACT_LABEL="input for ${prompt_key}"
            return 1
        }
    done
}

stage_has_any_artifacts() {
    local stage="$1"
    local artifact_id
    for artifact_id in $(stage_all_artifacts "$stage"); do
        if artifact_present_for_state "$artifact_id"; then
            return 0
        fi
    done
    return 1
}

stage_is_complete() {
    local stage="$1"
    local artifact_id verdict
    for artifact_id in $(stage_required_artifacts "$stage"); do
        artifact_exists "$artifact_id" || return 1
    done

    if [ "$stage" = "E" ]; then
        verdict="$(evaluation_verdict)"
        [ "$verdict" = "PASS" ] || [ "$verdict" = "FAIL" ] || return 1
    fi
    return 0
}

invalidate_artifact() {
    local artifact_id="$1"
    local path kind
    path="$(artifact_path "$artifact_id")"
    kind="$(artifact_kind "$artifact_id")"

    if [ "$kind" = "dir" ]; then
        [ -d "$path" ] || return 1
        rm -rf "$path"
    else
        [ -f "$path" ] || return 1
        rm -f "$path"
    fi
    return 0
}

invalidate_downstream_artifacts() {
    local start_turn="$1"
    local invalidate_var="INVALIDATE_FROM_${start_turn}_ARTIFACTS"
    local artifact_ids="${!invalidate_var:-}"
    local artifact_id invalidated=0

    if [ -z "$artifact_ids" ]; then
        return 0
    fi

    log "Invalidating stage-owned artifacts for rerun from Turn ${start_turn}"
    for artifact_id in $artifact_ids; do
        if invalidate_artifact "$artifact_id"; then
            log "Invalidated $(artifact_path "$artifact_id")"
            invalidated=$((invalidated + 1))
        fi
    done

    mkdir -p "${SAWMILL_DIR}" "${HOLDOUT_DIR}" "${STAGING_DIR}"
    log "Invalidation complete (${invalidated} artifact paths removed)"
}

artifact_newer_than() {
    local artifact_id="$1"
    local reference_path="$2"
    local path kind
    path="$(artifact_path "$artifact_id")"
    kind="$(artifact_kind "$artifact_id")"
    if [ "$kind" = "dir" ]; then
        find "$path" -mindepth 1 -newer "$reference_path" -print -quit 2>/dev/null | grep -q .
    else
        [ "$path" -nt "$reference_path" ]
    fi
}

verify_prompt_outputs() {
    local prompt_key="$1"
    local artifact_id sentinel_path freshness_policy
    sentinel_path="$(prompt_sentinel_path "$prompt_key")"
    freshness_policy="$(prompt_freshness_policy "$prompt_key")"
    for artifact_id in $(prompt_expected_artifacts "$prompt_key"); do
        ensure_artifact_exists "$artifact_id" "output for ${prompt_key}" || {
            LAST_PROMPT_VERIFICATION_ERROR="Missing required output for ${prompt_key}: $(artifact_path "$artifact_id")"
            cleanup_prompt_sentinel "$prompt_key"
            return 1
        }
        case "$freshness_policy" in
            required)
                if [ -n "$sentinel_path" ] && ! artifact_newer_than "$artifact_id" "$sentinel_path"; then
                    LAST_PROMPT_VERIFICATION_ERROR="Output for ${prompt_key} was not refreshed this run: $(artifact_path "$artifact_id")"
                    cleanup_prompt_sentinel "$prompt_key"
                    return 1
                fi
                ;;
            allow_unchanged)
                ;;
            *)
                LAST_PROMPT_VERIFICATION_ERROR="Prompt '${prompt_key}' has unsupported freshness policy '${freshness_policy}'"
                cleanup_prompt_sentinel "$prompt_key"
                return 1
                ;;
        esac
    done
    cleanup_prompt_sentinel "$prompt_key"
}

invoke_prompt() {
    local backend="$1"
    local role_file="$2"
    local prompt_key="$3"
    local turn_event_id="$4"
    local expected_role prompt_owner rendered_prompt role_name turn attempt log_prefix prompt_event_id

    expected_role="$(basename "$role_file" .md)"
    prompt_owner="$(prompt_role "$prompt_key")"
    role_name="$expected_role"
    turn="$(prompt_turn "$prompt_key")"
    attempt="${ATTEMPT:-1}"
    CURRENT_EVENT_TURN="$turn"
    CURRENT_EVENT_STEP="$prompt_key"
    CURRENT_EVENT_ROLE="$role_name"
    CURRENT_EVENT_BACKEND="$backend"
    CURRENT_EVENT_ATTEMPT="$attempt"

    if [ "$prompt_owner" != "$expected_role" ]; then
        local ownership_failure
        ownership_failure="$(emit_event "prompt_rendered" "failed" "PROMPT_OWNER_MISMATCH" "$turn_event_id" "$turn" "$prompt_key" "$role_name" "$backend" "$attempt" "Prompt '${prompt_key}' owner '${prompt_owner}' did not match role '${expected_role}'" --contract-ref "$(prompt_file "$prompt_key")" --contract-ref "$role_file")"
        record_run_failed "$ownership_failure" "PROMPT_OWNER_MISMATCH" "Prompt '${prompt_key}' owner mismatch"
        fail "Prompt '${prompt_key}' is owned by '${prompt_owner}', but runtime tried to invoke role '${expected_role}'"
        exit 1
    fi

    if ! ensure_prompt_inputs "$prompt_key"; then
        local input_failure
        input_failure="$(emit_event "prompt_rendered" "failed" "MISSING_INPUT_ARTIFACT" "$turn_event_id" "$turn" "$prompt_key" "$role_name" "$backend" "$attempt" "Missing required input for ${prompt_key}: ${LAST_MISSING_ARTIFACT_PATH}" --contract-ref "$(prompt_file "$prompt_key")" --contract-ref "$role_file")"
        record_run_failed "$input_failure" "MISSING_INPUT_ARTIFACT" "Missing required input for ${prompt_key}: ${LAST_MISSING_ARTIFACT_PATH}"
        fail "Missing required ${LAST_MISSING_ARTIFACT_LABEL}: ${LAST_MISSING_ARTIFACT_PATH}"
        exit 1
    fi

    snapshot_prompt_outputs "$prompt_key"
    if ! rendered_prompt="$(render_prompt_output "$prompt_key")"; then
        cleanup_prompt_sentinel "$prompt_key"
        local render_failure
        render_failure="$(emit_event "prompt_rendered" "failed" "PROMPT_RENDER_FAILED" "$turn_event_id" "$turn" "$prompt_key" "$role_name" "$backend" "$attempt" "Failed to render prompt '${prompt_key}' from $(prompt_file "$prompt_key")" --contract-ref "$(prompt_file "$prompt_key")" --contract-ref "$role_file")"
        record_run_failed "$render_failure" "PROMPT_RENDER_FAILED" "Failed to render prompt '${prompt_key}'"
        fail "Failed to render prompt '${prompt_key}' from $(prompt_file "$prompt_key")"
        exit 1
    fi

    prompt_event_id="$(emit_event "prompt_rendered" "rendered" "none" "$turn_event_id" "$turn" "$prompt_key" "$role_name" "$backend" "$attempt" "Rendered prompt '${prompt_key}'" --contract-ref "$(prompt_file "$prompt_key")" --contract-ref "$role_file")"
    if ! invoke_agent "$backend" "$role_file" "$rendered_prompt" "$prompt_key" "$prompt_event_id"; then
        local failure_code failure_parent summary
        failure_code="${LAST_FAILURE_CODE:-AGENT_EXIT_NONZERO}"
        failure_parent="${LAST_FAILURE_EVENT_ID:-$prompt_event_id}"
        summary="Agent execution failed for ${prompt_key}"
        record_run_failed "$failure_parent" "$failure_code" "$summary"
        fail "$summary"
        exit 1
    fi
}

launch_prompt_background() {
    local backend="$1"
    local role_file="$2"
    local prompt_key="$3"
    local turn_event_id="$4"
    (
        invoke_prompt "$backend" "$role_file" "$prompt_key" "$turn_event_id"
        validate_prompt_step_success "$prompt_key" "$LAST_AGENT_EXIT_EVENT_ID" "$(prompt_turn "$prompt_key")" "$(basename "$role_file" .md)" "$backend" "${ATTEMPT:-1}" "$(artifact_path "$(prompt_expected_artifacts "$prompt_key" | awk '{print $1}')")"
    ) &
}

append_retry_context() {
    local artifact_id="$1"
    local title="$2"
    local path
    path="$(artifact_path "$artifact_id")"
    if [ -f "$path" ] && [ -s "$path" ]; then
        RETRY_CONTEXT="${RETRY_CONTEXT}

${title}:
Read ${path} for the latest failures. Fix ONLY what failed. Do not rewrite passing work."
    fi
}

stop_background_pid() {
    local pid="${1:-}"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
    fi
}

FMWK=""
FROM_TURN="A"
RUN_AUDIT=false
INTERACTIVE=false

while [ $# -gt 0 ]; do
    case "$1" in
        --audit)
            RUN_AUDIT=true
            ;;
        --interactive|--require-human-gates)
            INTERACTIVE=true
            ;;
        --unattended|--auto-approve-gates)
            INTERACTIVE=false
            ;;
        --from-turn)
            shift
            if [ $# -eq 0 ]; then
                echo "Missing value for --from-turn" >&2
                usage
                exit 1
            fi
            FROM_TURN="$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')"
            ;;
        -h|--help)
            validate_agent_timeout
            usage
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
        *)
            if [ -n "$FMWK" ]; then
                echo "Unexpected extra argument: $1" >&2
                usage
                exit 1
            fi
            FMWK="$1"
            ;;
    esac
    shift
done

validate_agent_timeout

OPERATOR_MODE="${SAWMILL_OPERATOR_MODE:-}"
if [ -z "$OPERATOR_MODE" ]; then
    if [ "$INTERACTIVE" = true ]; then
        OPERATOR_MODE="interactive"
    else
        OPERATOR_MODE="governed"
    fi
fi
case "$OPERATOR_MODE" in
    governed|interactive|manual_intervention_allowed) ;;
    *)
        fail "SAWMILL_OPERATOR_MODE must be one of: governed, interactive, manual_intervention_allowed"
        exit 1
        ;;
esac
export OPERATOR_MODE

# --- Audit mode --------------------------------------------------------------
if [ "$RUN_AUDIT" = true ]; then
    FMWK="PORTAL-AUDIT"
    SAWMILL_DIR="sawmill/${FMWK}"
    HOLDOUT_DIR=".holdouts/${FMWK}"
    STAGING_DIR="staging/${FMWK}"
    MAX_ATTEMPTS=1
    BRANCH="build/${FMWK}"
    mkdir -p "${SAWMILL_DIR}" "${HOLDOUT_DIR}" "${STAGING_DIR}"

    load_role_registry
    load_artifact_registry
    load_prompt_registry
    load_prompt_contract_versions
    export FMWK SAWMILL_DIR HOLDOUT_DIR STAGING_DIR BRANCH MAX_ATTEMPTS ARTIFACT_REGISTRY
    export SOURCE_MATERIAL_PATH STATUS_PAGE_PATH PORTAL_STATUS_PATH PORTAL_CHANGESET_PATH PORTAL_AUDIT_RESULTS_PATH
    SOURCE_MATERIAL_PATH="${SAWMILL_DIR}/SOURCE_MATERIAL.md"
    STATUS_PAGE_PATH="$(artifact_path status_page)"
    PORTAL_STATUS_PATH="$(artifact_path portal_status)"
    PORTAL_CHANGESET_PATH="$(artifact_path portal_changeset)"
    PORTAL_AUDIT_RESULTS_PATH="$(artifact_path portal_audit_results)"
    export STAGE="" RETRY_CONTEXT=""
    export_artifact_paths
    initialize_run_harness
    log "═══ PORTAL AUDIT ═══"

    if ! require_backend_cli "AUDIT_AGENT" "$AUDIT_AGENT"; then
        fail_preflight "PREFLIGHT_MISSING_CLI" "Missing required agent CLI for AUDIT_AGENT=${AUDIT_AGENT}"
    fi

    CURRENT_EVENT_TURN="orchestrator"
    CURRENT_EVENT_STEP="preflight"
    CURRENT_EVENT_ROLE="orchestrator"
    CURRENT_EVENT_BACKEND="runtime"
    CURRENT_EVENT_ATTEMPT=0
    PREFLIGHT_PASSED_EVENT_ID="$(emit_event "preflight_passed" "passed" "none" "$RUN_STARTED_EVENT_ID" "orchestrator" "preflight" "orchestrator" "runtime" 0 "Preflight passed for ${FMWK}")"
    local_audit_turn_event_id="$(emit_event "turn_started" "started" "none" "$RUN_STARTED_EVENT_ID" "audit" "audit_run" "auditor" "$AUDIT_AGENT" 0 "Portal audit turn started")"
    invoke_prompt "$AUDIT_AGENT" "$AUDIT_ROLE_FILE" audit_run "$local_audit_turn_event_id"
    validate_prompt_step_success audit_run "$LAST_AGENT_EXIT_EVENT_ID" "audit" "auditor" "$AUDIT_AGENT" 0 "$(artifact_path portal_audit_results)"
    LAST_TURN_COMPLETED_EVENT_ID="$(emit_event "turn_completed" "completed" "none" "$LAST_OUTPUT_VERIFIED_EVENT_ID" "audit" "audit_run" "auditor" "$AUDIT_AGENT" 0 "Portal audit turn completed")"
    emit_event "run_completed" "passed" "none" "$LAST_TURN_COMPLETED_EVENT_ID" "orchestrator" "run" "orchestrator" "runtime" 0 "Audit run completed" >/dev/null
    pass "Audit complete. Results: ${PORTAL_AUDIT_RESULTS_PATH}"
    exit 0
fi

if [ -z "$FMWK" ]; then
    usage
    exit 1
fi

case "$FROM_TURN" in
    A|B|C|D|E) ;;
    *)
        echo "Invalid --from-turn value: ${FROM_TURN} (expected A, B, C, D, or E)" >&2
        usage
        exit 1
        ;;
esac

SAWMILL_DIR="sawmill/${FMWK}"
HOLDOUT_DIR=".holdouts/${FMWK}"
STAGING_DIR="staging/${FMWK}"
MAX_ATTEMPTS=3
BRANCH="build/${FMWK}"

turn_rank() {
    case "$1" in
        A) echo 1 ;;
        B) echo 2 ;;
        C) echo 3 ;;
        D) echo 4 ;;
        E) echo 5 ;;
        *)
            return 1
            ;;
    esac
}

FROM_TURN_RANK="$(turn_rank "$FROM_TURN")"

should_run_turn() {
    local turn="$1"
    local turn_rank_value
    turn_rank_value="$(turn_rank "$turn")" || return 1
    [ "$turn_rank_value" -ge "$FROM_TURN_RANK" ]
}

require_files() {
    local label="$1"
    shift

    for f in "$@"; do
        if [ ! -f "$f" ]; then
            fail "Missing required ${label}: $f"
            exit 1
        fi
    done
}

# --- Portal & Audit Functions ------------------------------------------------

update_portal_state() {
    local fmwk="$1"
    local status_page
    status_page="$(artifact_path status_page)"
    local runtime_state governed_path run_id_display

    if [ ! -f "$status_page" ]; then
        mkdir -p "$(dirname "$status_page")"
        cat > "$status_page" <<'PORTAL_STUB_EOF'
<!-- sawmill:auto-status -->
# Pending framework status

**Status:** Not started
PORTAL_STUB_EOF
    fi

    # Only update auto-managed status pages (marker on first line)
    if ! head -1 "$status_page" | grep -qF '<!-- sawmill:auto-status -->'; then
        return 0
    fi

    local spec="PENDING" plan="PENDING" holdout="PENDING" build="PENDING" eval_s="PENDING"
    local summary="Not started"
    runtime_state="running"
    governed_path="true"
    run_id_display="${RUN_ID:-none}"

    if [ -n "${STATUS_JSON_PATH:-}" ] && [ -f "${STATUS_JSON_PATH}" ]; then
        runtime_state="$(current_status_state || echo "running")"
        governed_path="$(current_governed_path_intact || echo "true")"
    fi

    if stage_is_complete A; then
        spec="DONE"; summary="Spec complete"
    fi
    if stage_is_complete B; then
        plan="DONE"; summary="Plan complete"
    fi
    if stage_is_complete C; then
        holdout="DONE"; summary="Holdouts complete"
    fi
    if stage_is_complete D; then
        build="DONE"; summary="Build complete"
    fi
    if stage_is_complete E; then
        if [ "$(evaluation_verdict)" = "PASS" ]; then
            eval_s="PASS"; summary="Evaluation PASS"
        else
            eval_s="FAIL"; summary="Evaluation FAIL"
        fi
    fi

    case "$runtime_state" in
        invalidated) summary="Run invalidated" ;;
        failed) summary="Run failed" ;;
        escalated) summary="Run escalated" ;;
        retrying) summary="Retry in progress" ;;
        passed) summary="Evaluation PASS" ;;
    esac

    cat > "$status_page" << PORTAL_EOF
<!-- sawmill:auto-status -->
# ${fmwk} — Build Status

**Status:** ${summary}
**Run ID:** ${run_id_display}
**Runtime State:** ${runtime_state}
**Governed Path Intact:** ${governed_path}

---

## Stage Completion

| Stage | Status |
|-------|--------|
| Turn A (Spec) | ${spec} |
| Turn B (Plan) | ${plan} |
| Turn C (Holdout) | ${holdout} |
| Turn D (Build) | ${build} |
| Turn E (Eval) | ${eval_s} |

---

*Updated by sawmill/run.sh at $(date -u +%Y-%m-%dT%H:%M:%SZ)*
PORTAL_EOF

    log "Portal updated: ${status_page} (${summary})"
}

run_stage_audit() {
    local fmwk="$1"
    local stage="$2"
    local audit_file="sawmill/${fmwk}/CANARY_AUDIT.md"
    local status_page
    status_page="$(artifact_path status_page)"
    local pc=0 fc=0
    local results=""

    _ck() {
        local desc="$1"; shift
        if "$@" 2>/dev/null; then
            results="${results}| PASS | ${desc} |
"
            pc=$((pc + 1))
        else
            results="${results}| **FAIL** | ${desc} |
"
            fc=$((fc + 1))
        fi
    }

    # Infrastructure checks
    _ck "Status page exists" test -f "$status_page"
    _ck "mkdocs.yml references ${fmwk}" grep -qF "${fmwk}" mkdocs.yml
    _ck "PORTAL_MAP.yaml references ${fmwk}" grep -qF "${fmwk}" docs/PORTAL_MAP.yaml

    # Artifact-to-portal consistency: stage completeness is registry-driven
    local artifact_id
    if stage_has_any_artifacts A; then
        for artifact_id in $(stage_required_artifacts A); do
            _ck "${artifact_id} exists" artifact_exists "$artifact_id"
        done
        _ck "Portal: Turn A DONE" grep -qF "Turn A (Spec) | DONE" "$status_page"
    fi

    if stage_has_any_artifacts B; then
        for artifact_id in $(stage_required_artifacts B); do
            _ck "${artifact_id} exists" artifact_exists "$artifact_id"
        done
        _ck "Portal: Turn B DONE" grep -qF "Turn B (Plan) | DONE" "$status_page"
    fi

    if stage_has_any_artifacts C; then
        for artifact_id in $(stage_required_artifacts C); do
            _ck "${artifact_id} exists" artifact_exists "$artifact_id"
        done
        _ck "Portal: Turn C DONE" grep -qF "Turn C (Holdout) | DONE" "$status_page"
    fi

    if [ -f "$(artifact_path q13_answers)" ]; then
        _ck "13Q answers exist" test -f "$(artifact_path q13_answers)"
    fi

    if [ -f "$(artifact_path review_report)" ]; then
        _ck "REVIEW_REPORT.md exists" test -f "$(artifact_path review_report)"
        _ck "REVIEW_ERRORS.md exists" test -f "$(artifact_path review_errors)"
        _ck "Review verdict parseable" test "$(review_verdict)" != "UNKNOWN"
    fi

    if stage_has_any_artifacts D; then
        for artifact_id in $(stage_required_artifacts D); do
            _ck "${artifact_id} exists" artifact_exists "$artifact_id"
        done
        _ck "Portal: Turn D DONE" grep -qF "Turn D (Build) | DONE" "$status_page"
    fi

    if stage_has_any_artifacts E; then
        for artifact_id in $(stage_required_artifacts E); do
            _ck "${artifact_id} exists" artifact_exists "$artifact_id"
        done
        case "$(evaluation_verdict)" in
            PASS)
                _ck "Portal: Turn E PASS" grep -qF "Turn E (Eval) | PASS" "$status_page"
                ;;
            FAIL)
                _ck "Portal: Turn E FAIL" grep -qF "Turn E (Eval) | FAIL" "$status_page"
                ;;
            *)
                _ck "Evaluation verdict parseable" false
                ;;
        esac
    fi

    # Reverse checks: if portal claims DONE, artifacts MUST exist
    if grep -qF "Turn A (Spec) | DONE" "$status_page" 2>/dev/null; then
        _ck "Portal says A DONE → Turn A complete" stage_is_complete A
    fi
    if grep -qF "Turn B (Plan) | DONE" "$status_page" 2>/dev/null; then
        _ck "Portal says B DONE → Turn B complete" stage_is_complete B
    fi
    if grep -qF "Turn C (Holdout) | DONE" "$status_page" 2>/dev/null; then
        _ck "Portal says C DONE → Turn C complete" stage_is_complete C
    fi
    if grep -qF "Turn D (Build) | DONE" "$status_page" 2>/dev/null; then
        _ck "Portal says D DONE → Turn D complete" stage_is_complete D
    fi
    if grep -qF "Turn E (Eval) | PASS" "$status_page" 2>/dev/null; then
        _ck "Portal says E PASS → Turn E complete" stage_is_complete E
        _ck "Portal says E PASS → evaluation verdict PASS" test "$(evaluation_verdict)" = "PASS"
    fi
    if grep -qF "Turn E (Eval) | FAIL" "$status_page" 2>/dev/null; then
        _ck "Portal says E FAIL → Turn E complete" stage_is_complete E
        _ck "Portal says E FAIL → evaluation verdict FAIL" test "$(evaluation_verdict)" = "FAIL"
    fi

    # Portal-steward output checks
    _ck "PORTAL_STATUS.md exists" test -f "$(artifact_path portal_status)"
    _ck "PORTAL_CHANGESET.md exists" test -f "$(artifact_path portal_changeset)"
    _ck "validate_portal_map.py passes" python3 docs/validate_portal_map.py
    _ck "catalog-info.yaml exists" test -f "catalog-info.yaml"

    # Mirror sync check — driven by PORTAL_MAP.yaml, not handpicked
    local mirror_total=0 mirror_pass=0 mirror_fail=0
    local mirror_failures=""
    if [ -f "docs/PORTAL_MAP.yaml" ] && command -v python3 >/dev/null 2>&1; then
        while IFS='|' read -r src mir; do
            [ -z "$src" ] || [ -z "$mir" ] && continue
            mirror_total=$((mirror_total + 1))
            if [ -f "$src" ] && [ -f "$mir" ] && diff -q "$src" "$mir" >/dev/null 2>&1; then
                mirror_pass=$((mirror_pass + 1))
            else
                mirror_fail=$((mirror_fail + 1))
                mirror_failures="${mirror_failures}  ${src} != ${mir}\n"
            fi
        done < <(python3 -c "
import yaml, sys
with open('docs/PORTAL_MAP.yaml') as f:
    data = yaml.safe_load(f)
for e in data.get('entries', []):
    if e.get('sync') == 'mirror' and 'source' in e and 'mirror' in e:
        print(e['source'] + '|' + e['mirror'])
")

        if [ "$mirror_total" -gt 0 ]; then
            _ck "Mirrors synced: ${mirror_pass}/${mirror_total}" test "$mirror_fail" -eq 0
            if [ "$mirror_fail" -gt 0 ]; then
                results="${results}| **INFO** | Drifted mirrors: $(echo -e "$mirror_failures") |
"
            fi
        fi
    fi

    _ck "portal-steward ran for this stage" test "${_PORTAL_STEWARD_RAN:-false}" = "true"
    if [ "${_PORTAL_STATUS_CHANGED:-false}" = "true" ]; then
        results="${results}| INFO | PORTAL_STATUS.md changed this stage |"$'\n'
    else
        results="${results}| INFO | PORTAL_STATUS.md unchanged this stage (already current) |"$'\n'
    fi
    if [ "${_PORTAL_CHANGESET_CHANGED:-false}" = "true" ]; then
        results="${results}| INFO | PORTAL_CHANGESET.md changed this stage |"$'\n'
    else
        results="${results}| INFO | PORTAL_CHANGESET.md unchanged this stage (already current) |"$'\n'
    fi

    # Write audit file
    cat > "$audit_file" << AUDIT_EOF
# Canary Audit — ${fmwk}

Stage: ${stage}
Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Pass: ${pc}
Fail: ${fc}

## Results

| Status | Check |
|--------|-------|
${results}
## Verdict

$(if [ "$fc" -eq 0 ]; then echo "**PASS** — all ${pc} checks passed"; else echo "**FAIL** — ${fc} check(s) failed"; fi)
AUDIT_EOF

    if [ "$fc" -gt 0 ]; then
        fail "Stage audit FAILED (${fc} failures). See ${audit_file}"
        return 1
    fi
    pass "Stage audit PASSED (${pc} checks)"
}

run_portal_steward() {
    local fmwk="$1"
    local stage="$2"
    local mirror_changes=""
    local portal_turn_event_id

    log "Running portal-steward for ${fmwk} after ${stage}"

    if [ ! -f "$PORTAL_MIRROR_SYNCER" ]; then
        record_run_failed "${LAST_OUTPUT_VERIFIED_EVENT_ID:-$RUN_STARTED_EVENT_ID}" "PORTAL_SYNC_HELPER_MISSING" "Missing portal mirror sync helper: ${PORTAL_MIRROR_SYNCER}"
        fail "Missing portal mirror sync helper: ${PORTAL_MIRROR_SYNCER}"
        exit 1
    fi

    if ! mirror_changes="$(python3 "$PORTAL_MIRROR_SYNCER" --repo-root . 2>&1)"; then
        record_run_failed "${LAST_OUTPUT_VERIFIED_EVENT_ID:-$RUN_STARTED_EVENT_ID}" "PORTAL_MIRROR_SYNC_FAILED" "$mirror_changes"
        fail "$mirror_changes"
        exit 1
    fi
    if [ -n "$mirror_changes" ]; then
        log "Mechanical mirror sync updated:"
        printf '%s\n' "$mirror_changes"
    else
        log "Mechanical mirror sync found no drift"
    fi

    # Snapshot portal outputs before steward runs (for freshness check)
    local pre_status_hash pre_changeset_hash
    pre_status_hash=$(shasum -a 256 "$(artifact_path portal_status)" 2>/dev/null | cut -d' ' -f1 || echo "none")
    pre_changeset_hash=$(shasum -a 256 "$(artifact_path portal_changeset)" 2>/dev/null | cut -d' ' -f1 || echo "none")
    export _PRE_STATUS_HASH="$pre_status_hash" _PRE_CHANGESET_HASH="$pre_changeset_hash"
    export _PORTAL_STEWARD_RAN=true

    export STAGE="$stage"
    portal_turn_event_id="$(emit_event "turn_started" "started" "none" "${LAST_TURN_COMPLETED_EVENT_ID:-$RUN_STARTED_EVENT_ID}" "portal" "portal_stage" "portal-steward" "$PORTAL_AGENT" "${ATTEMPT:-0}" "Portal steward turn started for ${stage}")"
    invoke_prompt "$PORTAL_AGENT" "$PORTAL_ROLE_FILE" portal_stage "$portal_turn_event_id"
    validate_prompt_step_success portal_stage "$LAST_AGENT_EXIT_EVENT_ID" "portal" "portal-steward" "$PORTAL_AGENT" "${ATTEMPT:-0}" "$(artifact_path portal_status)" "$(artifact_path portal_changeset)"

    # Store hashes for audit freshness checks
    export _POST_STATUS_HASH _POST_CHANGESET_HASH _PORTAL_STATUS_CHANGED _PORTAL_CHANGESET_CHANGED
    _POST_STATUS_HASH=$(shasum -a 256 "$(artifact_path portal_status)" 2>/dev/null | cut -d' ' -f1 || echo "none")
    _POST_CHANGESET_HASH=$(shasum -a 256 "$(artifact_path portal_changeset)" 2>/dev/null | cut -d' ' -f1 || echo "none")
    if [ "$_POST_STATUS_HASH" != "$pre_status_hash" ]; then
        _PORTAL_STATUS_CHANGED=true
    else
        _PORTAL_STATUS_CHANGED=false
    fi
    if [ "$_POST_CHANGESET_HASH" != "$pre_changeset_hash" ]; then
        _PORTAL_CHANGESET_CHANGED=true
    else
        _PORTAL_CHANGESET_CHANGED=false
    fi

    # Steward produced outputs?
    if [ -f "$(artifact_path portal_status)" ] && [ "$_PORTAL_STATUS_CHANGED" = true ]; then
        pass "Portal-steward updated PORTAL_STATUS.md"
    elif [ -f "$(artifact_path portal_status)" ]; then
        log "Portal-steward ran but PORTAL_STATUS.md unchanged (may be already current)"
    else
        record_run_failed "${LAST_OUTPUT_VERIFIED_EVENT_ID:-$RUN_STARTED_EVENT_ID}" "PORTAL_STATUS_MISSING" "Portal-steward did not produce PORTAL_STATUS.md"
        fail "Portal-steward did not produce PORTAL_STATUS.md"
    fi
}

run_with_timeout() {
    local label="$1"
    shift

    if [ ! -f "$TIMEOUT_RUNNER" ]; then
        fail "Missing timeout runner: ${TIMEOUT_RUNNER}"
        exit 1
    fi

    if [ "${AGENT_TIMEOUT_SECONDS}" -le 0 ]; then
        "$@"
    else
        python3 "$TIMEOUT_RUNNER" --timeout "$AGENT_TIMEOUT_SECONDS" --label "$label" -- "$@"
    fi
}

# --- Agent Invocation -------------------------------------------------------
#
# Each agent CLI has a different entry point:
#
#   Claude: auto-reads CLAUDE.md, uses --append-system-prompt for role
#   Codex:  auto-reads AGENTS.md, role + prompt go in the exec argument
#   Gemini: auto-reads GEMINI.md, role + prompt go in -p argument
#
# The role file content is ALWAYS injected into the prompt so the agent
# knows its constraints regardless of which context file it auto-loaded.
# The task-specific prompt then tells the agent exactly which files to read.
#
# This means the agent gets context from TWO sources:
#   1. Auto-loaded context file (CLAUDE.md / AGENTS.md / GEMINI.md)
#      → gives: project identity, drift warning, primitives, invariants
#   2. Orchestrator prompt (role file + task instructions)
#      → gives: role constraints, isolation rules, exact files to read
# -----------------------------------------------------------------------

invoke_agent() {
    local backend="$1"
    local role_file="$2"
    local prompt="$3"
    local prompt_key="$4"
    local prompt_event_id="$5"
    local role_content
    role_content="$(cat "$role_file")"

    # Derive role name from file basename (e.g., .claude/agents/spec-agent.md → spec-agent)
    local role_name
    role_name="$(basename "$role_file" .md)"

    log "Invoking ${backend} with role ${role_name} (${role_file})"

    local attempt step_prefix stdout_log stderr_log heartbeat_dir heartbeat_file agent_invoked_event_id turn
    local invocation_prefix payload_path meta_path liveness_path result_path liveness_state_path
    attempt="${ATTEMPT:-1}"
    turn="$(prompt_turn "$prompt_key")"
    step_prefix="$(step_log_prefix "$prompt_key" "$attempt")"
    stdout_log="${step_prefix}.stdout.log"
    stderr_log="${step_prefix}.stderr.log"
    heartbeat_dir="${RUN_HEARTBEATS_DIR}"
    heartbeat_file="${heartbeat_dir}/$(basename "$step_prefix").log"
    invocation_prefix="$(invocation_prefix "$prompt_key" "$attempt")"
    payload_path="${invocation_prefix}.payload.txt"
    meta_path="${invocation_prefix}.meta.json"
    liveness_path="${invocation_prefix}.liveness.jsonl"
    result_path="${invocation_prefix}.result.json"
    liveness_state_path="${invocation_prefix}.liveness.offset"
    mkdir -p "$heartbeat_dir"
    : > "$stdout_log"
    : > "$stderr_log"
    : > "$liveness_path"
    : > "$heartbeat_file"
    write_invocation_payload "$payload_path" "$role_content" "$prompt"

    LAST_AGENT_EXIT_EVENT_ID=""
    LAST_FAILURE_EVENT_ID=""
    LAST_FAILURE_CODE=""
    export SAWMILL_META_PAYLOAD_PATH="$payload_path"
    export SAWMILL_META_LIVENESS_PATH="$liveness_path"
    export SAWMILL_META_RESULT_PATH="$result_path"
    export SAWMILL_META_STDOUT_LOG="$stdout_log"
    export SAWMILL_META_STDERR_LOG="$stderr_log"
    export SAWMILL_META_HEARTBEAT_FILE="$heartbeat_file"
    export SAWMILL_META_TURN="$turn"
    export SAWMILL_META_STEP="$prompt_key"
    export SAWMILL_META_ROLE="$role_name"
    export SAWMILL_META_BACKEND="$backend"
    export SAWMILL_META_ATTEMPT="$attempt"
    export SAWMILL_META_PROMPT_KEY="$prompt_key"
    export SAWMILL_META_MODEL_POLICY="default"
    export SAWMILL_META_TIMEOUT_SECONDS="$AGENT_TIMEOUT_SECONDS"

    agent_invoked_event_id="$(emit_event "agent_invoked" "invoked" "none" "$prompt_event_id" "$turn" "$prompt_key" "$role_name" "$backend" "$attempt" "Invoked ${backend} for ${prompt_key}" --evidence-ref "$stdout_log" --evidence-ref "$stderr_log" --evidence-ref "$payload_path" --evidence-ref "$meta_path" --contract-ref "$role_file" --contract-ref "$(prompt_file "$prompt_key")")"
    export SAWMILL_META_AGENT_INVOKED_EVENT_ID="$agent_invoked_event_id"
    write_invocation_meta "$meta_path" "$payload_path" "$liveness_path" "$result_path" "$stdout_log" "$stderr_log" "$heartbeat_file" "$turn" "$prompt_key" "$role_name" "$backend" "$attempt" "$prompt_key" "$agent_invoked_event_id"

    if [ ! -f "$RUNNER" ]; then
        LAST_FAILURE_CODE="RUNNER_MISSING"
        record_run_failed "$agent_invoked_event_id" "$LAST_FAILURE_CODE" "Missing runner: ${RUNNER}"
        fail "Missing runner: ${RUNNER}"
        exit 1
    fi

    set +e
    python3 "$RUNNER" --meta "$meta_path" &
    local runner_pid=$!
    while kill -0 "$runner_pid" 2>/dev/null; do
        emit_liveness_records "$liveness_path" "$agent_invoked_event_id" "$turn" "$prompt_key" "$role_name" "$backend" "$attempt" "$liveness_state_path"
        sleep 1
    done
    wait "$runner_pid"
    local runner_exit_code=$?
    set -e
    emit_liveness_records "$liveness_path" "$agent_invoked_event_id" "$turn" "$prompt_key" "$role_name" "$backend" "$attempt" "$liveness_state_path"
    rm -f "$liveness_state_path"

    if [ -s "$stdout_log" ]; then
        cat "$stdout_log"
    fi
    if [ -s "$stderr_log" ]; then
        cat "$stderr_log" >&2
    fi
    if [ ! -f "$result_path" ]; then
        LAST_FAILURE_CODE="RUNNER_RESULT_MISSING"
        LAST_FAILURE_EVENT_ID="$(emit_event "agent_exited" "failed" "$LAST_FAILURE_CODE" "$agent_invoked_event_id" "$turn" "$prompt_key" "$role_name" "$backend" "$attempt" "Runner did not produce result.json for ${prompt_key}" --evidence-ref "$stdout_log" --evidence-ref "$stderr_log" --evidence-ref "$meta_path" --evidence-ref "$liveness_path" --contract-ref "$role_file" --contract-ref "$(prompt_file "$prompt_key")")"
        LAST_AGENT_EXIT_EVENT_ID="$LAST_FAILURE_EVENT_ID"
        record_run_failed "$LAST_FAILURE_EVENT_ID" "$LAST_FAILURE_CODE" "Runner did not produce result.json for ${prompt_key}"
        fail "Runner did not produce result.json for ${prompt_key}"
        exit 1
    fi

    local result_outcome result_failure_code result_exit_code result_timed_out
    result_outcome="$(python3 - "$result_path" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["outcome"])
PY
)"
    result_failure_code="$(python3 - "$result_path" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["failure_code"])
PY
)"
    result_exit_code="$(python3 - "$result_path" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["exit_code"])
PY
)"
    result_timed_out="$(python3 - "$result_path" <<'PY'
import json, sys
print("true" if json.load(open(sys.argv[1], encoding="utf-8")).get("timed_out") else "false")
PY
)"

    if [ "$result_timed_out" = "true" ] || [ "$result_outcome" = "timeout" ]; then
        LAST_FAILURE_CODE="AGENT_TIMEOUT"
        LAST_FAILURE_EVENT_ID="$(emit_event "timeout_triggered" "timeout" "AGENT_TIMEOUT" "$agent_invoked_event_id" "$turn" "$prompt_key" "$role_name" "$backend" "$attempt" "Timed out while running ${backend}:${role_name}" --evidence-ref "$stdout_log" --evidence-ref "$stderr_log" --evidence-ref "$result_path" --evidence-ref "$liveness_path" --contract-ref "$role_file" --contract-ref "$(prompt_file "$prompt_key")")"
        return 124
    fi

    if [ "$runner_exit_code" -ne 0 ] || [ "$result_exit_code" -ne 0 ] || [ "$result_outcome" = "failed" ]; then
        LAST_FAILURE_CODE="${result_failure_code:-AGENT_EXIT_NONZERO}"
        LAST_FAILURE_EVENT_ID="$(emit_event "agent_exited" "failed" "$LAST_FAILURE_CODE" "$agent_invoked_event_id" "$turn" "$prompt_key" "$role_name" "$backend" "$attempt" "Agent exited non-zero for ${prompt_key}" --evidence-ref "$stdout_log" --evidence-ref "$stderr_log" --evidence-ref "$result_path" --evidence-ref "$liveness_path" --contract-ref "$role_file" --contract-ref "$(prompt_file "$prompt_key")")"
        LAST_AGENT_EXIT_EVENT_ID="$LAST_FAILURE_EVENT_ID"
        return "${result_exit_code:-1}"
    fi

    LAST_AGENT_EXIT_EVENT_ID="$(emit_event "agent_exited" "succeeded" "none" "$agent_invoked_event_id" "$turn" "$prompt_key" "$role_name" "$backend" "$attempt" "Agent exited successfully for ${prompt_key}" --evidence-ref "$stdout_log" --evidence-ref "$stderr_log" --evidence-ref "$result_path" --evidence-ref "$liveness_path" --contract-ref "$role_file" --contract-ref "$(prompt_file "$prompt_key")")"
    return 0
}

review_verdict() {
    local report_path
    local last_line
    report_path="$(artifact_path review_report)"
    last_line="$(awk 'NF { line=$0 } END { print line }' "$report_path" 2>/dev/null | sed 's/[[:space:]]*$//')"
    case "$last_line" in
        [Rr]eview\ [Vv]erdict:\ PASS) printf '%s\n' "PASS" ;;
        [Rr]eview\ [Vv]erdict:\ RETRY) printf '%s\n' "RETRY" ;;
        [Rr]eview\ [Vv]erdict:\ ESCALATE) printf '%s\n' "ESCALATE" ;;
        *) printf '%s\n' "UNKNOWN" ;;
    esac
}

evaluation_verdict() {
    local report_path
    local last_line
    report_path="$(artifact_path evaluation_report)"
    last_line="$(awk 'NF { line=$0 } END { print line }' "$report_path" 2>/dev/null | sed 's/[[:space:]]*$//')"
    case "$last_line" in
        [Ff]inal\ [Vv]erdict:\ PASS) printf '%s\n' "PASS" ;;
        [Ff]inal\ [Vv]erdict:\ FAIL) printf '%s\n' "FAIL" ;;
        *) printf '%s\n' "UNKNOWN" ;;
    esac
}

extract_exact_version_evidence() {
    local artifact_path="$1"
    local label="$2"
    local value

    local parse_status
    if value="$(
        awk -v label="$label" '
            BEGIN {
                label_count = 0
                valid_count = 0
                label_prefix = label ":"
            }
            {
                line = $0
                sub(/\r$/, "", line)
                if (index(line, label_prefix) == 1) {
                    label_count++
                    value = substr(line, length(label_prefix) + 1)
                    sub(/^[[:space:]]+/, "", value)
                    sub(/[[:space:]]+$/, "", value)
                    if (value ~ /^[0-9A-Za-z._-]+$/) {
                        valid_count++
                        valid_value = value
                    }
                }
            }
            END {
                if (label_count == 0) {
                    exit 2
                }
                if (label_count > 1) {
                    exit 3
                }
                if (valid_count != 1) {
                    exit 4
                }
                print valid_value
            }
        ' "$artifact_path"
    )"; then
        printf '%s\n' "$value"
        return 0
    else
        parse_status=$?
    fi

    case "$parse_status" in
        2)
            fail "Missing required version evidence line in ${artifact_path}: ${label}: <version>"
            return 2
            ;;
        3)
            fail "Multiple '${label}:' lines found in ${artifact_path}; expected exactly one"
            return 3
            ;;
        4)
            fail "Malformed '${label}:' line in ${artifact_path}; expected <version> token"
            return 4
            ;;
        *)
            fail "Unable to parse version evidence from ${artifact_path}"
            return 1
            ;;
    esac
}

require_version_evidence() {
    local artifact_id="$1"
    local label="$2"
    local expected_version="$3"
    local artifact_file_path actual_version

    artifact_file_path="$(artifact_path "$artifact_id")"
    actual_version="$(extract_exact_version_evidence "$artifact_file_path" "$label")" || return 1
    if [ "$actual_version" != "$expected_version" ]; then
        fail "Version evidence mismatch in ${artifact_file_path} for '${label}': expected '${expected_version}', found '${actual_version}'"
        return 1
    fi
}

validate_builder_evidence() {
    validate_evidence_artifact builder builder_evidence \
        --handoff "$(artifact_path builder_handoff)" \
        --q13-answers "$(artifact_path q13_answers)" \
        --results "$(artifact_path results)"
}

validate_reviewer_evidence() {
    validate_evidence_artifact reviewer reviewer_evidence \
        --q13-answers "$(artifact_path q13_answers)"
}

validate_evaluator_evidence() {
    validate_evidence_artifact evaluator evaluator_evidence \
        --holdouts "$(artifact_path d9_holdout_scenarios)" \
        --staging-root "$(artifact_path staging_root)"
}

validate_final_evidence_suite() {
    if stage_is_complete D; then
        validate_builder_evidence
        validate_reviewer_evidence
    fi
    if stage_is_complete E; then
        validate_evaluator_evidence
    fi
}

validate_convergence() {
    project_status_now
    validate_final_evidence_suite
    local runtime_state governed_path
    runtime_state="$(current_status_state)"
    governed_path="$(current_governed_path_intact)"
    update_portal_state "$FMWK"

    if [ -n "$STATUS_PAGE_PATH" ] && [ -f "$STATUS_PAGE_PATH" ]; then
        grep -qF "**Run ID:** ${RUN_ID}" "$STATUS_PAGE_PATH" || {
            fail "Status page does not reflect current run id ${RUN_ID}"
            return 1
        }
        grep -qF "**Runtime State:** ${runtime_state}" "$STATUS_PAGE_PATH" || {
            fail "Status page does not reflect runtime state ${runtime_state}"
            return 1
        }
        grep -qF "**Governed Path Intact:** ${governed_path}" "$STATUS_PAGE_PATH" || {
            fail "Status page does not reflect governed path state ${governed_path}"
            return 1
        }
    fi

    python3 docs/validate_portal_map.py >/dev/null
}

# --- Preflight --------------------------------------------------------------

load_role_registry
load_artifact_registry
load_stage_artifact_metadata
load_prompt_registry

# Create working directories before the harness so the run directory has a home.
mkdir -p "${SAWMILL_DIR}" "${HOLDOUT_DIR}" "${STAGING_DIR}"

export FMWK FROM_TURN SAWMILL_DIR HOLDOUT_DIR STAGING_DIR BRANCH MAX_ATTEMPTS ARTIFACT_REGISTRY
export SOURCE_MATERIAL_PATH STATUS_PAGE_PATH PORTAL_STATUS_PATH PORTAL_CHANGESET_PATH PORTAL_AUDIT_RESULTS_PATH
export STAGE="" RETRY_CONTEXT=""
SOURCE_MATERIAL_PATH="${SAWMILL_DIR}/SOURCE_MATERIAL.md"
STATUS_PAGE_PATH="$(artifact_path status_page)"
PORTAL_STATUS_PATH="$(artifact_path portal_status)"
PORTAL_CHANGESET_PATH="$(artifact_path portal_changeset)"
PORTAL_AUDIT_RESULTS_PATH="$(artifact_path portal_audit_results)"
load_prompt_contract_versions
export SPEC_AGENT BUILD_AGENT HOLDOUT_AGENT REVIEW_AGENT EVAL_AGENT AUDIT_AGENT PORTAL_AGENT
export SPEC_ROLE_FILE HOLDOUT_ROLE_FILE BUILD_ROLE_FILE REVIEW_ROLE_FILE EVAL_ROLE_FILE AUDIT_ROLE_FILE PORTAL_ROLE_FILE
export SPEC_MODEL_POLICY BUILD_MODEL_POLICY HOLDOUT_MODEL_POLICY REVIEW_MODEL_POLICY EVAL_MODEL_POLICY AUDIT_MODEL_POLICY PORTAL_MODEL_POLICY
export ALL_PROMPT_KEYS
for prompt_key in $ALL_PROMPT_KEYS; do
    prompt_prefix="$(key_to_env "$prompt_key")"
    prompt_file_var="PROMPT_${prompt_prefix}_PROMPT_FILE"
    export "$prompt_file_var"
done
export_artifact_paths
initialize_run_harness

log "Sawmill run: ${FMWK}"
log "From turn:     ${FROM_TURN}"
log "Interactive:   ${INTERACTIVE}"
log "Operator mode: ${OPERATOR_MODE}"
log "Spec agent:    ${SPEC_AGENT}"
log "Build agent:   ${BUILD_AGENT}"
log "Holdout agent: ${HOLDOUT_AGENT}"
log "Review agent:  ${REVIEW_AGENT}"
log "Eval agent:    ${EVAL_AGENT}"
log "Audit agent:   ${AUDIT_AGENT}"
log "Portal agent:  ${PORTAL_AGENT}"
echo ""

# Verify required files exist
for f in \
    CLAUDE.md AGENT_BOOTSTRAP.md \
    "$ROLE_REGISTRY" "$ROLE_REGISTRY_VALIDATOR" \
    "$ARTIFACT_REGISTRY" "$ARTIFACT_REGISTRY_VALIDATOR" \
    "$STAGE_ARTIFACT_RESOLVER" \
    "$PROMPT_REGISTRY" "$PROMPT_REGISTRY_VALIDATOR" \
    "$PROMPT_RENDERER" \
    "$PORTAL_MIRROR_SYNCER" \
    "$RUN_STATUS_PROJECTOR" \
    "$EVIDENCE_VALIDATOR" \
    "Templates/BUILDER_PROMPT_CONTRACT.md" \
    "Templates/REVIEWER_PROMPT_CONTRACT.md"; do
    if [ ! -f "$f" ]; then
        fail_preflight "PREFLIGHT_MISSING_FILE" "Missing required file: $f"
    fi
done

# Create context file symlinks if missing (so Codex and Gemini auto-load context)
if [ ! -e "AGENTS.md" ]; then
    log "Creating AGENTS.md → CLAUDE.md symlink (for Codex)"
    ln -s CLAUDE.md AGENTS.md
fi
if [ ! -e "GEMINI.md" ]; then
    log "Creating GEMINI.md → CLAUDE.md symlink (for Gemini)"
    ln -s CLAUDE.md GEMINI.md
fi

# Verify the selected agent CLI is installed
for agent_var in SPEC_AGENT BUILD_AGENT HOLDOUT_AGENT REVIEW_AGENT EVAL_AGENT PORTAL_AGENT; do
    agent_val="${!agent_var}"
    if ! require_backend_cli "$agent_var" "$agent_val"; then
        fail_preflight "PREFLIGHT_MISSING_CLI" "Missing required agent CLI for ${agent_var}=${agent_val}"
    fi
done

# Verify TASK.md exists
if [ ! -f "$(artifact_path task)" ]; then
    fail_preflight "PREFLIGHT_MISSING_TASK" "Missing $(artifact_path task) — create it before running the pipeline."
fi

CURRENT_EVENT_TURN="orchestrator"
CURRENT_EVENT_STEP="preflight"
CURRENT_EVENT_ROLE="orchestrator"
CURRENT_EVENT_BACKEND="runtime"
CURRENT_EVENT_ATTEMPT=0
PREFLIGHT_PASSED_EVENT_ID="$(emit_event "preflight_passed" "passed" "none" "$RUN_STARTED_EVENT_ID" "orchestrator" "preflight" "orchestrator" "runtime" 0 "Preflight passed for ${FMWK}")"
export PREFLIGHT_PASSED_EVENT_ID

log "Preflight passed. Starting pipeline."
echo ""

invalidate_downstream_artifacts "$FROM_TURN"

# Sync portal state with current artifact reality
update_portal_state "$FMWK"

# --- Turn A: Spec Agent (D1-D6) --------------------------------------------

if should_run_turn A; then
    local_turn_a_event_id="$(emit_event "turn_started" "started" "none" "$RUN_STARTED_EVENT_ID" "A" "turn_a_spec" "spec-agent" "$SPEC_AGENT" 1 "Turn A started")"
    log "═══ TURN A: Specification (D1-D6) ═══"
    invoke_prompt "$SPEC_AGENT" "$SPEC_ROLE_FILE" turn_a_spec "$local_turn_a_event_id"
    validate_prompt_step_success turn_a_spec "$LAST_AGENT_EXIT_EVENT_ID" "A" "spec-agent" "$SPEC_AGENT" 1 \
        "$(artifact_path d1_constitution)" "$(artifact_path d6_gap_analysis)"
    pass "Turn A produced D1-D6"

    update_portal_state "$FMWK"
    run_portal_steward "$FMWK" "Turn A"
    if ! run_stage_audit "$FMWK" "Turn A"; then
        record_run_failed "${LAST_OUTPUT_VERIFIED_EVENT_ID:-$local_turn_a_event_id}" "STAGE_AUDIT_FAILED" "Stage audit failed after Turn A"
        exit 1
    fi
    checkpoint "Turn A outputs ready for optional review"
else
    log "Skipping Turn A (--from-turn ${FROM_TURN})"
fi

# --- Turn B + C: Plan + Holdouts (parallel) ---------------------------------

if should_run_turn B || should_run_turn C; then
    log "═══ TURN B + C: Plan (D7-D8-D10) + Holdouts (D9) — parallel ═══"

    PID_B=""
    PID_C=""
    local_turn_b_event_id=""
    local_turn_c_event_id=""

    if should_run_turn B; then
        if [ "$FROM_TURN" = "B" ]; then
            if ! ensure_artifact_ids "Turn A output" \
                d1_constitution d2_specification d3_data_model d4_contracts d5_research d6_gap_analysis; then
                record_run_failed "$RUN_STARTED_EVENT_ID" "MISSING_INPUT_ARTIFACT" "Missing Turn A output: ${LAST_MISSING_ARTIFACT_PATH}"
                exit 1
            fi
        fi

        # Turn B (background)
        local_turn_b_event_id="$(emit_event "turn_started" "started" "none" "$RUN_STARTED_EVENT_ID" "B" "turn_b_plan" "spec-agent" "$SPEC_AGENT" 1 "Turn B started")"
        launch_prompt_background "$SPEC_AGENT" "$SPEC_ROLE_FILE" turn_b_plan "$local_turn_b_event_id"
        PID_B=$!
    else
        log "Skipping Turn B (--from-turn ${FROM_TURN})"
    fi

    if should_run_turn C; then
        if [ "$FROM_TURN" = "C" ]; then
            if ! ensure_artifact_ids "Turn A output" d2_specification d4_contracts; then
                record_run_failed "$RUN_STARTED_EVENT_ID" "MISSING_INPUT_ARTIFACT" "Missing Turn A output: ${LAST_MISSING_ARTIFACT_PATH}"
                exit 1
            fi
        fi

        # Turn C (background)
        local_turn_c_event_id="$(emit_event "turn_started" "started" "none" "$RUN_STARTED_EVENT_ID" "C" "turn_c_holdout" "holdout-agent" "$HOLDOUT_AGENT" 1 "Turn C started")"
        launch_prompt_background "$HOLDOUT_AGENT" "$HOLDOUT_ROLE_FILE" turn_c_holdout "$local_turn_c_event_id"
        PID_C=$!
    else
        log "Skipping Turn C (--from-turn ${FROM_TURN})"
    fi

    if [ -n "$PID_B" ]; then
        if ! wait "$PID_B"; then
            stop_background_pid "$PID_C"
            fail "Turn B failed"
            exit 1
        fi
        pass "Turn B produced D7, D8, D10, BUILDER_HANDOFF"
    fi

    if [ -n "$PID_C" ]; then
        if ! wait "$PID_C"; then
            stop_background_pid "$PID_B"
            fail "Turn C failed"
            exit 1
        fi
        pass "Turn C produced D9 holdout scenarios"
    fi

    update_portal_state "$FMWK"
    run_portal_steward "$FMWK" "Turn BC"
    if ! run_stage_audit "$FMWK" "Turn BC"; then
        record_run_failed "${LAST_OUTPUT_VERIFIED_EVENT_ID:-$RUN_STARTED_EVENT_ID}" "STAGE_AUDIT_FAILED" "Stage audit failed after Turn BC"
        exit 1
    fi

else
    log "Skipping Turn B + C (--from-turn ${FROM_TURN})"
fi

if should_run_turn D && [ "$FROM_TURN_RANK" -le "$(turn_rank C)" ]; then
    if ! ensure_artifact_ids "Turn B/C outputs" \
        d7_plan d8_tasks d10_agent_context builder_handoff d9_holdout_scenarios; then
        record_run_failed "$RUN_STARTED_EVENT_ID" "MISSING_INPUT_ARTIFACT" "Missing Turn B/C output: ${LAST_MISSING_ARTIFACT_PATH}"
        exit 1
    fi
    checkpoint "Turn B/C outputs ready for optional review"
fi

# --- Turn D: Builder (up to 3 attempts) ------------------------------------

BUILD_PASSED=false

if should_run_turn D; then
    if ! ensure_artifact_ids "Turn D input" d10_agent_context builder_handoff; then
        record_run_failed "$RUN_STARTED_EVENT_ID" "MISSING_INPUT_ARTIFACT" "Missing Turn D input: ${LAST_MISSING_ARTIFACT_PATH}"
        exit 1
    fi

    log "═══ TURN D: Build ═══"

    ATTEMPT=0
    TURN_D_EVENT_ID="$(emit_event "turn_started" "started" "none" "${LAST_TURN_COMPLETED_EVENT_ID:-$RUN_STARTED_EVENT_ID}" "D" "turn_d_13q" "builder" "$BUILD_AGENT" 1 "Turn D started")"
    LAST_DECISION_EVENT_ID=""

    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        ATTEMPT=$((ATTEMPT + 1))
        log "Build attempt ${ATTEMPT}/${MAX_ATTEMPTS}"

        # Compose retry context
        RETRY_CONTEXT=""
        append_retry_context review_errors "REVIEW RETRY CONTEXT (attempt ${ATTEMPT})"
        append_retry_context evaluation_errors "EVALUATION RETRY CONTEXT (attempt ${ATTEMPT})"
        export RETRY_CONTEXT

        log "Turn D — Step 1: 13Q Gate"

        invoke_prompt "$BUILD_AGENT" "$BUILD_ROLE_FILE" turn_d_13q "$TURN_D_EVENT_ID"
        if ! require_version_evidence q13_answers "Builder Prompt Contract Version" "$BUILDER_PROMPT_CONTRACT_VERSION"; then
            failure_event_id="$(emit_event "output_verified" "failed" "VERSION_EVIDENCE_FAILED" "$LAST_AGENT_EXIT_EVENT_ID" "D" "turn_d_13q" "builder" "$BUILD_AGENT" "$ATTEMPT" "Builder prompt contract version evidence check failed")"
            record_run_failed "$failure_event_id" "VERSION_EVIDENCE_FAILED" "Builder prompt contract version evidence check failed"
            exit 1
        fi
        validate_prompt_step_success turn_d_13q "$LAST_AGENT_EXIT_EVENT_ID" "D" "builder" "$BUILD_AGENT" "$ATTEMPT" "$(artifact_path q13_answers)"
        pass "Builder produced 13Q answers"

        log "Turn D — Step 1.5: Review 13Q answers"
        invoke_prompt "$REVIEW_AGENT" "$REVIEW_ROLE_FILE" turn_d_review "$TURN_D_EVENT_ID"
        review_agent_exit_event_id="$LAST_AGENT_EXIT_EVENT_ID"
        if ! require_version_evidence review_report "Builder Prompt Contract Version Reviewed" "$BUILDER_PROMPT_CONTRACT_VERSION"; then
            failure_event_id="$(emit_event "output_verified" "failed" "VERSION_EVIDENCE_FAILED" "$review_agent_exit_event_id" "D" "turn_d_review" "reviewer" "$REVIEW_AGENT" "$ATTEMPT" "Reviewer evidence missing builder contract version")"
            record_run_failed "$failure_event_id" "VERSION_EVIDENCE_FAILED" "Reviewer evidence missing builder contract version"
            exit 1
        fi
        if ! require_version_evidence review_report "Reviewer Prompt Contract Version" "$REVIEWER_PROMPT_CONTRACT_VERSION"; then
            failure_event_id="$(emit_event "output_verified" "failed" "VERSION_EVIDENCE_FAILED" "$review_agent_exit_event_id" "D" "turn_d_review" "reviewer" "$REVIEW_AGENT" "$ATTEMPT" "Reviewer evidence missing reviewer contract version")"
            record_run_failed "$failure_event_id" "VERSION_EVIDENCE_FAILED" "Reviewer evidence missing reviewer contract version"
            exit 1
        fi
        if ! validate_reviewer_evidence; then
            failure_event_id="$(emit_event "output_verified" "failed" "EVIDENCE_VALIDATION_FAILED" "$review_agent_exit_event_id" "D" "turn_d_review" "reviewer" "$REVIEW_AGENT" "$ATTEMPT" "Reviewer evidence validation failed")"
            record_run_failed "$failure_event_id" "EVIDENCE_VALIDATION_FAILED" "Reviewer evidence validation failed"
            exit 1
        fi
        validate_prompt_step_success turn_d_review "$review_agent_exit_event_id" "D" "reviewer" "$REVIEW_AGENT" "$ATTEMPT" "$(artifact_path review_report)" "$(artifact_path review_errors)" "$(artifact_path reviewer_evidence)"

        case "$(review_verdict)" in
            PASS)
                LAST_DECISION_EVENT_ID="$(emit_event "review_verdict_recorded" "pass" "none" "$review_agent_exit_event_id" "D" "turn_d_review" "reviewer" "$REVIEW_AGENT" "$ATTEMPT" "Reviewer approved Turn D implementation")"
                pass "Review: PASS"
                ;;
            RETRY)
                LAST_DECISION_EVENT_ID="$(emit_event "review_verdict_recorded" "retry" "REVIEW_RETRY" "$review_agent_exit_event_id" "D" "turn_d_review" "reviewer" "$REVIEW_AGENT" "$ATTEMPT" "Reviewer requested retry")"
                fail "Review: RETRY (attempt ${ATTEMPT}/${MAX_ATTEMPTS})"
                if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
                    record_escalation "$LAST_DECISION_EVENT_ID" "REVIEW_RETRY_EXHAUSTED" "Build failed after ${MAX_ATTEMPTS} attempts. Reviewer never approved implementation."
                    exit 1
                fi
                emit_event "retry_started" "retrying" "REVIEW_RETRY" "$LAST_DECISION_EVENT_ID" "D" "turn_d_retry" "orchestrator" "runtime" "$ATTEMPT" "Retrying Turn D after reviewer RETRY" >/dev/null
                continue
                ;;
            ESCALATE)
                LAST_DECISION_EVENT_ID="$(emit_event "review_verdict_recorded" "escalate" "REVIEW_ESCALATE" "$review_agent_exit_event_id" "D" "turn_d_review" "reviewer" "$REVIEW_AGENT" "$ATTEMPT" "Reviewer escalated the build")"
                record_escalation "$LAST_DECISION_EVENT_ID" "REVIEW_ESCALATE" "Review: ESCALATE. See $(artifact_path review_report) and $(artifact_path review_errors)"
                exit 1
                ;;
            *)
                failure_event_id="$(emit_event "output_verified" "failed" "INVALID_REVIEW_VERDICT" "$review_agent_exit_event_id" "D" "turn_d_review" "reviewer" "$REVIEW_AGENT" "$ATTEMPT" "Reviewer did not produce a parseable verdict")"
                record_run_failed "$failure_event_id" "INVALID_REVIEW_VERDICT" "Reviewer did not produce a parseable verdict in $(artifact_path review_report)"
                exit 1
                ;;
        esac

        log "Turn D — Step 2: DTT Build"
        invoke_prompt "$BUILD_AGENT" "$BUILD_ROLE_FILE" turn_d_build "$TURN_D_EVENT_ID"
        build_agent_exit_event_id="$LAST_AGENT_EXIT_EVENT_ID"
        if ! validate_builder_evidence; then
            failure_event_id="$(emit_event "output_verified" "failed" "EVIDENCE_VALIDATION_FAILED" "$build_agent_exit_event_id" "D" "turn_d_build" "builder" "$BUILD_AGENT" "$ATTEMPT" "Builder evidence validation failed")"
            record_run_failed "$failure_event_id" "EVIDENCE_VALIDATION_FAILED" "Builder evidence validation failed"
            exit 1
        fi
        validate_prompt_step_success turn_d_build "$build_agent_exit_event_id" "D" "builder" "$BUILD_AGENT" "$ATTEMPT" "$(artifact_path results)" "$(artifact_path builder_evidence)" "$(artifact_path staging_root)"
        pass "Builder produced code and RESULTS.md"

        update_portal_state "$FMWK"
        run_portal_steward "$FMWK" "Turn D"
        if ! run_stage_audit "$FMWK" "Turn D"; then
            record_run_failed "${LAST_OUTPUT_VERIFIED_EVENT_ID:-$build_agent_exit_event_id}" "STAGE_AUDIT_FAILED" "Stage audit failed after Turn D"
            exit 1
        fi
        LAST_TURN_COMPLETED_EVENT_ID="$(emit_event "turn_completed" "completed" "none" "$LAST_DECISION_EVENT_ID" "D" "turn_d_build" "builder" "$BUILD_AGENT" "$ATTEMPT" "Turn D completed")"

        if ! should_run_turn E; then
            BUILD_PASSED=true
            emit_event "run_completed" "passed" "none" "$LAST_TURN_COMPLETED_EVENT_ID" "orchestrator" "run" "orchestrator" "runtime" "$ATTEMPT" "Run completed after Turn D" >/dev/null
            validate_convergence || {
                record_run_failed "$LAST_TURN_COMPLETED_EVENT_ID" "CONVERGENCE_FAILED" "Convergence validation failed after Turn D"
                exit 1
            }
            break
        fi

        # --- Turn E: Evaluator --------------------------------------------------

        log "═══ TURN E: Evaluation ═══"
        TURN_E_EVENT_ID="$(emit_event "turn_started" "started" "none" "${LAST_TURN_COMPLETED_EVENT_ID:-$TURN_D_EVENT_ID}" "E" "turn_e_eval" "evaluator" "$EVAL_AGENT" "$ATTEMPT" "Turn E started")"
        invoke_prompt "$EVAL_AGENT" "$EVAL_ROLE_FILE" turn_e_eval "$TURN_E_EVENT_ID"
        eval_agent_exit_event_id="$LAST_AGENT_EXIT_EVENT_ID"
        if ! validate_evaluator_evidence; then
            failure_event_id="$(emit_event "output_verified" "failed" "EVIDENCE_VALIDATION_FAILED" "$eval_agent_exit_event_id" "E" "turn_e_eval" "evaluator" "$EVAL_AGENT" "$ATTEMPT" "Evaluator evidence validation failed")"
            record_run_failed "$failure_event_id" "EVIDENCE_VALIDATION_FAILED" "Evaluator evidence validation failed"
            exit 1
        fi
        validate_prompt_step_success turn_e_eval "$eval_agent_exit_event_id" "E" "evaluator" "$EVAL_AGENT" "$ATTEMPT" "$(artifact_path evaluation_report)" "$(artifact_path evaluation_errors)" "$(artifact_path evaluator_evidence)"

        case "$(evaluation_verdict)" in
            PASS)
                LAST_DECISION_EVENT_ID="$(emit_event "evaluation_verdict_recorded" "pass" "none" "$eval_agent_exit_event_id" "E" "turn_e_eval" "evaluator" "$EVAL_AGENT" "$ATTEMPT" "Evaluator returned PASS")"
                BUILD_PASSED=true
                pass "Evaluation: PASS"
                update_portal_state "$FMWK"
                run_portal_steward "$FMWK" "Turn E"
                if ! run_stage_audit "$FMWK" "Turn E"; then
                    record_run_failed "${LAST_OUTPUT_VERIFIED_EVENT_ID:-$eval_agent_exit_event_id}" "STAGE_AUDIT_FAILED" "Stage audit failed after Turn E"
                    exit 1
                fi
                LAST_TURN_COMPLETED_EVENT_ID="$(emit_event "turn_completed" "completed" "none" "$LAST_DECISION_EVENT_ID" "E" "turn_e_eval" "evaluator" "$EVAL_AGENT" "$ATTEMPT" "Turn E completed")"
                emit_event "run_completed" "passed" "none" "$LAST_TURN_COMPLETED_EVENT_ID" "orchestrator" "run" "orchestrator" "runtime" "$ATTEMPT" "Run completed with PASS verdict" >/dev/null
                validate_convergence || {
                    record_run_failed "$LAST_TURN_COMPLETED_EVENT_ID" "CONVERGENCE_FAILED" "Convergence validation failed at terminal PASS"
                    exit 1
                }
                break
                ;;
            FAIL)
                LAST_DECISION_EVENT_ID="$(emit_event "evaluation_verdict_recorded" "fail" "EVALUATION_FAIL" "$eval_agent_exit_event_id" "E" "turn_e_eval" "evaluator" "$EVAL_AGENT" "$ATTEMPT" "Evaluator returned FAIL")"
                update_portal_state "$FMWK"
                run_portal_steward "$FMWK" "Turn E"
                if ! run_stage_audit "$FMWK" "Turn E"; then
                    record_run_failed "${LAST_OUTPUT_VERIFIED_EVENT_ID:-$eval_agent_exit_event_id}" "STAGE_AUDIT_FAILED" "Stage audit failed after Turn E"
                    exit 1
                fi
                fail "Evaluation: FAIL (attempt ${ATTEMPT}/${MAX_ATTEMPTS})"
                if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
                    record_escalation "$LAST_DECISION_EVENT_ID" "EVALUATION_FAIL_EXHAUSTED" "Build failed after ${MAX_ATTEMPTS} attempts. Returning to spec author."
                    exit 1
                fi
                emit_event "retry_started" "retrying" "EVALUATION_FAIL" "$LAST_DECISION_EVENT_ID" "E" "turn_e_retry" "orchestrator" "runtime" "$ATTEMPT" "Retrying after evaluator FAIL" >/dev/null
                ;;
            *)
                failure_event_id="$(emit_event "output_verified" "failed" "INVALID_EVALUATION_VERDICT" "$eval_agent_exit_event_id" "E" "turn_e_eval" "evaluator" "$EVAL_AGENT" "$ATTEMPT" "Evaluator did not produce a parseable verdict")"
                update_portal_state "$FMWK"
                run_portal_steward "$FMWK" "Turn E"
                if ! run_stage_audit "$FMWK" "Turn E"; then
                    record_run_failed "${LAST_OUTPUT_VERIFIED_EVENT_ID:-$eval_agent_exit_event_id}" "STAGE_AUDIT_FAILED" "Stage audit failed after Turn E"
                    exit 1
                fi
                if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
                    record_escalation "$failure_event_id" "INVALID_EVALUATION_VERDICT" "Evaluator did not produce a parseable verdict in $(artifact_path evaluation_report)"
                    exit 1
                fi
                fail "Evaluator produced an unparseable verdict"
                emit_event "retry_started" "retrying" "INVALID_EVALUATION_VERDICT" "$failure_event_id" "E" "turn_e_retry" "orchestrator" "runtime" "$ATTEMPT" "Retrying after unparseable evaluator verdict" >/dev/null
                ;;
        esac
    done
elif should_run_turn E; then
    if ! ensure_artifact_ids "Turn E input" d9_holdout_scenarios staging_root results; then
        record_run_failed "$RUN_STARTED_EVENT_ID" "MISSING_INPUT_ARTIFACT" "Missing Turn E input: ${LAST_MISSING_ARTIFACT_PATH}"
        exit 1
    fi

    log "═══ TURN E: Evaluation ═══"
    TURN_E_EVENT_ID="$(emit_event "turn_started" "started" "none" "${LAST_TURN_COMPLETED_EVENT_ID:-$RUN_STARTED_EVENT_ID}" "E" "turn_e_eval" "evaluator" "$EVAL_AGENT" 1 "Turn E started")"
    ATTEMPT="${ATTEMPT:-1}"
    invoke_prompt "$EVAL_AGENT" "$EVAL_ROLE_FILE" turn_e_eval "$TURN_E_EVENT_ID"
    eval_agent_exit_event_id="$LAST_AGENT_EXIT_EVENT_ID"
    if ! validate_evaluator_evidence; then
        failure_event_id="$(emit_event "output_verified" "failed" "EVIDENCE_VALIDATION_FAILED" "$eval_agent_exit_event_id" "E" "turn_e_eval" "evaluator" "$EVAL_AGENT" "$ATTEMPT" "Evaluator evidence validation failed")"
        record_run_failed "$failure_event_id" "EVIDENCE_VALIDATION_FAILED" "Evaluator evidence validation failed"
        exit 1
    fi
    validate_prompt_step_success turn_e_eval "$eval_agent_exit_event_id" "E" "evaluator" "$EVAL_AGENT" "$ATTEMPT" "$(artifact_path evaluation_report)" "$(artifact_path evaluation_errors)" "$(artifact_path evaluator_evidence)"

    if [ "$(evaluation_verdict)" = "PASS" ]; then
        LAST_DECISION_EVENT_ID="$(emit_event "evaluation_verdict_recorded" "pass" "none" "$eval_agent_exit_event_id" "E" "turn_e_eval" "evaluator" "$EVAL_AGENT" "$ATTEMPT" "Evaluator returned PASS")"
        BUILD_PASSED=true
        pass "Evaluation: PASS"
        update_portal_state "$FMWK"
        run_portal_steward "$FMWK" "Turn E"
        if ! run_stage_audit "$FMWK" "Turn E"; then
            record_run_failed "${LAST_OUTPUT_VERIFIED_EVENT_ID:-$eval_agent_exit_event_id}" "STAGE_AUDIT_FAILED" "Stage audit failed after standalone Turn E"
            exit 1
        fi
        LAST_TURN_COMPLETED_EVENT_ID="$(emit_event "turn_completed" "completed" "none" "$LAST_DECISION_EVENT_ID" "E" "turn_e_eval" "evaluator" "$EVAL_AGENT" "$ATTEMPT" "Turn E completed")"
        emit_event "run_completed" "passed" "none" "$LAST_TURN_COMPLETED_EVENT_ID" "orchestrator" "run" "orchestrator" "runtime" "$ATTEMPT" "Run completed with PASS verdict" >/dev/null
        validate_convergence || {
            record_run_failed "$LAST_TURN_COMPLETED_EVENT_ID" "CONVERGENCE_FAILED" "Convergence validation failed at terminal PASS"
            exit 1
        }
    else
        LAST_DECISION_EVENT_ID="$(emit_event "evaluation_verdict_recorded" "fail" "EVALUATION_FAIL" "$eval_agent_exit_event_id" "E" "turn_e_eval" "evaluator" "$EVAL_AGENT" "$ATTEMPT" "Evaluator returned FAIL")"
        update_portal_state "$FMWK"
        run_portal_steward "$FMWK" "Turn E"
        if ! run_stage_audit "$FMWK" "Turn E"; then
            record_run_failed "${LAST_OUTPUT_VERIFIED_EVENT_ID:-$eval_agent_exit_event_id}" "STAGE_AUDIT_FAILED" "Stage audit failed after standalone Turn E"
            exit 1
        fi
        record_escalation "$LAST_DECISION_EVENT_ID" "EVALUATION_FAIL" "Evaluation: FAIL"
        exit 1
    fi
else
    record_escalation "$PREFLIGHT_PASSED_EVENT_ID" "NO_WORK" "Nothing to do: --from-turn ${FROM_TURN} skips all pipeline turns"
    exit 1
fi

# --- Final ------------------------------------------------------------------

if [ "$BUILD_PASSED" = true ]; then
    echo ""
    pass "═══ ${FMWK} BUILD COMPLETE ═══"
    log "Done. Framework ${FMWK} completed the pipeline with a PASS verdict."
else
    escalate "═══ ${FMWK} BUILD FAILED ═══"
fi
