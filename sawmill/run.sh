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

ROLE_REGISTRY="sawmill/ROLE_REGISTRY.yaml"
ROLE_REGISTRY_VALIDATOR="sawmill/validate_role_registry.py"
ARTIFACT_REGISTRY="sawmill/ARTIFACT_REGISTRY.yaml"
ARTIFACT_REGISTRY_VALIDATOR="sawmill/validate_artifact_registry.py"
PROMPT_REGISTRY="sawmill/PROMPT_REGISTRY.yaml"
PROMPT_REGISTRY_VALIDATOR="sawmill/validate_prompt_registry.py"
PROMPT_RENDERER="sawmill/render_prompt.py"
TIMEOUT_RUNNER="sawmill/run_with_timeout.py"
AGENT_TIMEOUT_SECONDS="${SAWMILL_AGENT_TIMEOUT_SECONDS:-1800}"

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
        claude) command -v claude >/dev/null 2>&1 || { fail "${agent_label}=${backend} but 'claude' CLI not found"; exit 1; } ;;
        codex)  command -v codex  >/dev/null 2>&1 || { fail "${agent_label}=${backend} but 'codex' CLI not found"; exit 1; } ;;
        gemini) command -v gemini >/dev/null 2>&1 || { fail "${agent_label}=${backend} but 'gemini' CLI not found"; exit 1; } ;;
        *)
            fail "Unknown agent backend: ${backend}"
            exit 1
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
        [ -d "$path" ] || escalate "Missing required ${label}: ${path}"
    else
        [ -f "$path" ] || escalate "Missing required ${label}: ${path}"
    fi
}

ensure_artifact_ids() {
    local label="$1"
    shift
    local artifact_id
    for artifact_id in "$@"; do
        ensure_artifact_exists "$artifact_id" "$label"
    done
}

ensure_prompt_inputs() {
    local prompt_key="$1"
    local artifact_id
    for artifact_id in $(prompt_required_artifacts "$prompt_key"); do
        ensure_artifact_exists "$artifact_id" "input for ${prompt_key}"
    done
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
        ensure_artifact_exists "$artifact_id" "output for ${prompt_key}"
        case "$freshness_policy" in
            required)
                if [ -n "$sentinel_path" ] && ! artifact_newer_than "$artifact_id" "$sentinel_path"; then
                    cleanup_prompt_sentinel "$prompt_key"
                    escalate "Output for ${prompt_key} was not refreshed this run: $(artifact_path "$artifact_id")"
                fi
                ;;
            allow_unchanged)
                ;;
            *)
                cleanup_prompt_sentinel "$prompt_key"
                escalate "Prompt '${prompt_key}' has unsupported freshness policy '${freshness_policy}'"
                ;;
        esac
    done
    cleanup_prompt_sentinel "$prompt_key"
}

invoke_prompt() {
    local backend="$1"
    local role_file="$2"
    local prompt_key="$3"
    local expected_role prompt_owner rendered_prompt

    expected_role="$(basename "$role_file" .md)"
    prompt_owner="$(prompt_role "$prompt_key")"
    if [ "$prompt_owner" != "$expected_role" ]; then
        escalate "Prompt '${prompt_key}' is owned by '${prompt_owner}', but runtime tried to invoke role '${expected_role}'"
    fi

    ensure_prompt_inputs "$prompt_key"
    snapshot_prompt_outputs "$prompt_key"
    if ! rendered_prompt="$(render_prompt_output "$prompt_key")"; then
        cleanup_prompt_sentinel "$prompt_key"
        escalate "Failed to render prompt '${prompt_key}' from $(prompt_file "$prompt_key")"
    fi

    invoke_agent "$backend" "$role_file" "$rendered_prompt"
}

launch_prompt_background() {
    local backend="$1"
    local role_file="$2"
    local prompt_key="$3"
    local expected_role prompt_owner rendered_prompt

    expected_role="$(basename "$role_file" .md)"
    prompt_owner="$(prompt_role "$prompt_key")"
    if [ "$prompt_owner" != "$expected_role" ]; then
        escalate "Prompt '${prompt_key}' is owned by '${prompt_owner}', but runtime tried to invoke role '${expected_role}'"
    fi

    ensure_prompt_inputs "$prompt_key"
    snapshot_prompt_outputs "$prompt_key"
    if ! rendered_prompt="$(render_prompt_output "$prompt_key")"; then
        cleanup_prompt_sentinel "$prompt_key"
        escalate "Failed to render prompt '${prompt_key}' from $(prompt_file "$prompt_key")"
    fi

    invoke_agent "$backend" "$role_file" "$rendered_prompt" &
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

# --- Audit mode --------------------------------------------------------------
if [ "$RUN_AUDIT" = true ]; then
    load_role_registry
    load_artifact_registry
    load_prompt_registry
    log "═══ PORTAL AUDIT ═══"

    require_backend_cli "AUDIT_AGENT" "$AUDIT_AGENT"
    export FMWK=""
    export PORTAL_AUDIT_RESULTS_PATH
    PORTAL_AUDIT_RESULTS_PATH="$(artifact_path portal_audit_results)"
    invoke_prompt "$AUDIT_AGENT" "$AUDIT_ROLE_FILE" audit_run
    verify_prompt_outputs audit_run
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

    if [ -f "$(artifact_path d1_constitution)" ] && [ -f "$(artifact_path d6_gap_analysis)" ]; then
        spec="DONE"; summary="Spec complete"
    fi
    if [ -f "$(artifact_path d7_plan)" ] && [ -f "$(artifact_path builder_handoff)" ]; then
        plan="DONE"; summary="Plan complete"
    fi
    if [ -f "$(artifact_path d9_holdout_scenarios)" ]; then
        holdout="DONE"; summary="Holdouts complete"
    fi
    if [ -f "$(artifact_path results)" ]; then
        build="DONE"; summary="Build complete"
    fi
    if [ -f "$(artifact_path evaluation_report)" ]; then
        if [ "$(evaluation_verdict)" = "PASS" ]; then
            eval_s="PASS"; summary="Evaluation PASS"
        else
            eval_s="FAIL"; summary="Evaluation FAIL"
        fi
    fi

    cat > "$status_page" << PORTAL_EOF
<!-- sawmill:auto-status -->
# ${fmwk} — Build Status

**Status:** ${summary}

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

    # Artifact-to-portal consistency: if artifacts exist, portal must reflect them
    if [ -f "$(artifact_path d1_constitution)" ]; then
        _ck "D1 exists" test -f "$(artifact_path d1_constitution)"
        _ck "D2 exists" test -f "$(artifact_path d2_specification)"
        _ck "D3 exists" test -f "$(artifact_path d3_data_model)"
        _ck "D4 exists" test -f "$(artifact_path d4_contracts)"
        _ck "D5 exists" test -f "$(artifact_path d5_research)"
        _ck "D6 exists" test -f "$(artifact_path d6_gap_analysis)"
        _ck "Portal: Turn A DONE" grep -qF "Turn A (Spec) | DONE" "$status_page"
    fi

    if [ -f "$(artifact_path d7_plan)" ]; then
        _ck "D7 exists" test -f "$(artifact_path d7_plan)"
        _ck "D8 exists" test -f "$(artifact_path d8_tasks)"
        _ck "D10 exists" test -f "$(artifact_path d10_agent_context)"
        _ck "Handoff exists" test -f "$(artifact_path builder_handoff)"
        _ck "Portal: Turn B DONE" grep -qF "Turn B (Plan) | DONE" "$status_page"
    fi

    if [ -f "$(artifact_path d9_holdout_scenarios)" ]; then
        _ck "D9 exists" test -f "$(artifact_path d9_holdout_scenarios)"
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

    if [ -f "$(artifact_path results)" ]; then
        _ck "RESULTS.md exists" test -f "$(artifact_path results)"
        _ck "13Q answers exist before build" test -f "$(artifact_path q13_answers)"
        _ck "REVIEW_REPORT.md exists before build" test -f "$(artifact_path review_report)"
        _ck "staging/ has content" test -d "$(artifact_path staging_root)"
        _ck "Portal: Turn D DONE" grep -qF "Turn D (Build) | DONE" "$status_page"
    fi

    if [ -f "$(artifact_path evaluation_report)" ]; then
        _ck "EVALUATION_REPORT.md exists" test -f "$(artifact_path evaluation_report)"
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
        _ck "Portal says A DONE → D1 exists" test -f "$(artifact_path d1_constitution)"
        _ck "Portal says A DONE → D6 exists" test -f "$(artifact_path d6_gap_analysis)"
    fi
    if grep -qF "Turn B (Plan) | DONE" "$status_page" 2>/dev/null; then
        _ck "Portal says B DONE → D7 exists" test -f "$(artifact_path d7_plan)"
        _ck "Portal says B DONE → Handoff exists" test -f "$(artifact_path builder_handoff)"
    fi
    if grep -qF "Turn C (Holdout) | DONE" "$status_page" 2>/dev/null; then
        _ck "Portal says C DONE → D9 exists" test -f "$(artifact_path d9_holdout_scenarios)"
    fi
    if grep -qF "Turn D (Build) | DONE" "$status_page" 2>/dev/null; then
        _ck "Portal says D DONE → RESULTS.md exists" test -f "$(artifact_path results)"
        _ck "Portal says D DONE → REVIEW_REPORT.md exists" test -f "$(artifact_path review_report)"
        _ck "Portal says D DONE → staging/ exists" test -d "$(artifact_path staging_root)"
    fi
    if grep -qF "Turn E (Eval) | PASS" "$status_page" 2>/dev/null; then
        _ck "Portal says E PASS → EVALUATION_REPORT.md exists" test -f "$(artifact_path evaluation_report)"
    fi
    if grep -qF "Turn E (Eval) | FAIL" "$status_page" 2>/dev/null; then
        _ck "Portal says E FAIL → EVALUATION_REPORT.md exists" test -f "$(artifact_path evaluation_report)"
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

    log "Running portal-steward for ${fmwk} after ${stage}"

    # Snapshot portal outputs before steward runs (for freshness check)
    local pre_status_hash pre_changeset_hash
    pre_status_hash=$(shasum -a 256 "$(artifact_path portal_status)" 2>/dev/null | cut -d' ' -f1 || echo "none")
    pre_changeset_hash=$(shasum -a 256 "$(artifact_path portal_changeset)" 2>/dev/null | cut -d' ' -f1 || echo "none")
    export _PRE_STATUS_HASH="$pre_status_hash" _PRE_CHANGESET_HASH="$pre_changeset_hash"
    export _PORTAL_STEWARD_RAN=true

    export STAGE="$stage"
    invoke_prompt "$PORTAL_AGENT" "$PORTAL_ROLE_FILE" portal_stage
    verify_prompt_outputs portal_stage

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
    local role_content
    role_content="$(cat "$role_file")"

    # Derive role name from file basename (e.g., .claude/agents/spec-agent.md → spec-agent)
    local role_name
    role_name="$(basename "$role_file" .md)"

    log "Invoking ${backend} with role ${role_name} (${role_file})"

    case "$backend" in
        claude)
            # Claude auto-reads CLAUDE.md from project root.
            # --append-system-prompt adds role constraints to its default system prompt.
            # The task prompt goes as the -p argument.
            # --allowedTools grants file and shell access.
            # SAWMILL_ACTIVE_ROLE + SAWMILL_ACTIVE_FMWK enforce hooks per role.
            run_with_timeout "${backend}:${role_name}" \
                env -u CLAUDECODE \
                    SAWMILL_ACTIVE_ROLE="$role_name" SAWMILL_ACTIVE_FMWK="$FMWK" \
                    claude -p "${prompt}" \
                        --append-system-prompt "${role_content}" \
                        --allowedTools "Read,Edit,Write,Glob,Grep,Bash"
            ;;
        codex)
            # Codex auto-reads AGENTS.md (or CLAUDE.md if symlinked/configured).
            # No --system-prompt flag — everything goes in the exec argument.
            # --full-auto disables approval prompts.
            # Codex runs in a network-disabled sandbox by default.
            # Env vars set for consistency (Codex does not use Claude Code hooks).
            run_with_timeout "${backend}:${role_name}" \
                env \
                    SAWMILL_ACTIVE_ROLE="$role_name" \
                    SAWMILL_ACTIVE_FMWK="$FMWK" \
                    codex exec --full-auto \
                        "${role_content}

${prompt}"
            ;;
        gemini)
            # Gemini auto-reads GEMINI.md (or CLAUDE.md if configured in settings.json).
            # No --system-prompt flag — everything goes in -p argument.
            # --yolo auto-approves all tool actions.
            # Env vars set for consistency (Gemini does not use Claude Code hooks).
            run_with_timeout "${backend}:${role_name}" \
                env \
                    SAWMILL_ACTIVE_ROLE="$role_name" \
                    SAWMILL_ACTIVE_FMWK="$FMWK" \
                    gemini -p "${role_content}

${prompt}" \
                        --yolo
            ;;
        *)
            fail "Unknown agent backend: ${backend}"
            exit 1
            ;;
    esac
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
    actual_version="$(extract_exact_version_evidence "$artifact_file_path" "$label")" || escalate \
        "Version evidence check failed for ${artifact_file_path}"
    if [ "$actual_version" != "$expected_version" ]; then
        fail "Version evidence mismatch in ${artifact_file_path} for '${label}': expected '${expected_version}', found '${actual_version}'"
        escalate "Prompt contract version evidence mismatch"
    fi
}

# --- Preflight --------------------------------------------------------------

load_role_registry
load_artifact_registry
load_prompt_registry

log "Sawmill run: ${FMWK}"
log "From turn:     ${FROM_TURN}"
log "Interactive:   ${INTERACTIVE}"
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
    "$PROMPT_REGISTRY" "$PROMPT_REGISTRY_VALIDATOR" \
    "$PROMPT_RENDERER" \
    "Templates/BUILDER_PROMPT_CONTRACT.md" \
    "Templates/REVIEWER_PROMPT_CONTRACT.md"; do
    if [ ! -f "$f" ]; then
        fail "Missing required file: $f"
        exit 1
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
    require_backend_cli "$agent_var" "$agent_val"
done

# Create working directories
mkdir -p "${SAWMILL_DIR}" "${HOLDOUT_DIR}" "${STAGING_DIR}"

export FMWK SAWMILL_DIR HOLDOUT_DIR STAGING_DIR BRANCH
export SOURCE_MATERIAL_PATH STATUS_PAGE_PATH PORTAL_STATUS_PATH PORTAL_CHANGESET_PATH PORTAL_AUDIT_RESULTS_PATH
export STAGE="" RETRY_CONTEXT=""
SOURCE_MATERIAL_PATH="${SAWMILL_DIR}/SOURCE_MATERIAL.md"
STATUS_PAGE_PATH="$(artifact_path status_page)"
PORTAL_STATUS_PATH="$(artifact_path portal_status)"
PORTAL_CHANGESET_PATH="$(artifact_path portal_changeset)"
PORTAL_AUDIT_RESULTS_PATH="$(artifact_path portal_audit_results)"
load_prompt_contract_versions
export_artifact_paths

# Verify TASK.md exists
if [ ! -f "$(artifact_path task)" ]; then
    fail "Missing $(artifact_path task) — create it before running the pipeline."
    echo ""
    echo "TASK.md tells the spec agent which framework to spec."
    echo "See sawmill/COLD_START.md for the template."
    exit 1
fi

log "Preflight passed. Starting pipeline."
echo ""

# Sync portal state with current artifact reality
update_portal_state "$FMWK"

# --- Turn A: Spec Agent (D1-D6) --------------------------------------------

if should_run_turn A; then
    log "═══ TURN A: Specification (D1-D6) ═══"
    invoke_prompt "$SPEC_AGENT" "$SPEC_ROLE_FILE" turn_a_spec
    verify_prompt_outputs turn_a_spec
    pass "Turn A produced D1-D6"

    update_portal_state "$FMWK"
    run_portal_steward "$FMWK" "Turn A"
    run_stage_audit "$FMWK" "Turn A"
    checkpoint "Turn A outputs ready for optional review"
else
    log "Skipping Turn A (--from-turn ${FROM_TURN})"
fi

# --- Turn B + C: Plan + Holdouts (parallel) ---------------------------------

if should_run_turn B || should_run_turn C; then
    log "═══ TURN B + C: Plan (D7-D8-D10) + Holdouts (D9) — parallel ═══"

    PID_B=""
    PID_C=""

    if should_run_turn B; then
        if [ "$FROM_TURN" = "B" ]; then
            ensure_artifact_ids "Turn A output" \
                d1_constitution d2_specification d3_data_model d4_contracts d5_research d6_gap_analysis
        fi

        # Turn B (background)
        launch_prompt_background "$SPEC_AGENT" "$SPEC_ROLE_FILE" turn_b_plan
        PID_B=$!
    else
        log "Skipping Turn B (--from-turn ${FROM_TURN})"
    fi

    if should_run_turn C; then
        if [ "$FROM_TURN" = "C" ]; then
            ensure_artifact_ids "Turn A output" d2_specification d4_contracts
        fi

        # Turn C (background)
        launch_prompt_background "$HOLDOUT_AGENT" "$HOLDOUT_ROLE_FILE" turn_c_holdout
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
        verify_prompt_outputs turn_b_plan
        pass "Turn B produced D7, D8, D10, BUILDER_HANDOFF"
    fi

    if [ -n "$PID_C" ]; then
        if ! wait "$PID_C"; then
            stop_background_pid "$PID_B"
            fail "Turn C failed"
            exit 1
        fi
        verify_prompt_outputs turn_c_holdout
        pass "Turn C produced D9 holdout scenarios"
    fi

    update_portal_state "$FMWK"
    run_portal_steward "$FMWK" "Turn BC"
    run_stage_audit "$FMWK" "Turn BC"

else
    log "Skipping Turn B + C (--from-turn ${FROM_TURN})"
fi

if should_run_turn D && [ "$FROM_TURN_RANK" -le "$(turn_rank C)" ]; then
    ensure_artifact_ids "Turn B/C outputs" \
        d7_plan d8_tasks d10_agent_context builder_handoff d9_holdout_scenarios
    checkpoint "Turn B/C outputs ready for optional review"
fi

# --- Turn D: Builder (up to 3 attempts) ------------------------------------

BUILD_PASSED=false

if should_run_turn D; then
    ensure_artifact_ids "Turn D input" d10_agent_context builder_handoff

    log "═══ TURN D: Build ═══"

    ATTEMPT=0

    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        ATTEMPT=$((ATTEMPT + 1))
        log "Build attempt ${ATTEMPT}/${MAX_ATTEMPTS}"

        # Compose retry context
        RETRY_CONTEXT=""
        append_retry_context review_errors "REVIEW RETRY CONTEXT (attempt ${ATTEMPT})"
        append_retry_context evaluation_errors "EVALUATION RETRY CONTEXT (attempt ${ATTEMPT})"
        export RETRY_CONTEXT

        log "Turn D — Step 1: 13Q Gate"

        invoke_prompt "$BUILD_AGENT" "$BUILD_ROLE_FILE" turn_d_13q
        verify_prompt_outputs turn_d_13q
        require_version_evidence q13_answers "Builder Prompt Contract Version" "$BUILDER_PROMPT_CONTRACT_VERSION"
        pass "Builder produced 13Q answers"

        log "Turn D — Step 1.5: Review 13Q answers"
        invoke_prompt "$REVIEW_AGENT" "$REVIEW_ROLE_FILE" turn_d_review
        verify_prompt_outputs turn_d_review
        require_version_evidence review_report "Builder Prompt Contract Version Reviewed" "$BUILDER_PROMPT_CONTRACT_VERSION"
        require_version_evidence review_report "Reviewer Prompt Contract Version" "$REVIEWER_PROMPT_CONTRACT_VERSION"

        case "$(review_verdict)" in
            PASS)
                pass "Review: PASS"
                ;;
            RETRY)
                fail "Review: RETRY (attempt ${ATTEMPT}/${MAX_ATTEMPTS})"
                if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
                    escalate "Build failed after ${MAX_ATTEMPTS} attempts. Reviewer never approved implementation."
                fi
                continue
                ;;
            ESCALATE)
                escalate "Review: ESCALATE. See $(artifact_path review_report) and $(artifact_path review_errors)"
                ;;
            *)
                escalate "Reviewer did not produce a parseable verdict in $(artifact_path review_report)"
                ;;
        esac

        log "Turn D — Step 2: DTT Build"
        invoke_prompt "$BUILD_AGENT" "$BUILD_ROLE_FILE" turn_d_build
        verify_prompt_outputs turn_d_build
        pass "Builder produced code and RESULTS.md"

        update_portal_state "$FMWK"
        run_portal_steward "$FMWK" "Turn D"
        run_stage_audit "$FMWK" "Turn D"

        if ! should_run_turn E; then
            BUILD_PASSED=true
            break
        fi

        # --- Turn E: Evaluator --------------------------------------------------

        log "═══ TURN E: Evaluation ═══"

        invoke_prompt "$EVAL_AGENT" "$EVAL_ROLE_FILE" turn_e_eval
        verify_prompt_outputs turn_e_eval

        case "$(evaluation_verdict)" in
            PASS)
                BUILD_PASSED=true
                pass "Evaluation: PASS"
                update_portal_state "$FMWK"
                run_portal_steward "$FMWK" "Turn E"
                run_stage_audit "$FMWK" "Turn E"
                break
                ;;
            FAIL)
                update_portal_state "$FMWK"
                run_portal_steward "$FMWK" "Turn E"
                run_stage_audit "$FMWK" "Turn E"
                fail "Evaluation: FAIL (attempt ${ATTEMPT}/${MAX_ATTEMPTS})"
                if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
                    escalate "Build failed after ${MAX_ATTEMPTS} attempts. Returning to spec author."
                fi
                ;;
            *)
                update_portal_state "$FMWK"
                run_portal_steward "$FMWK" "Turn E"
                run_stage_audit "$FMWK" "Turn E"
                if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
                    escalate "Evaluator did not produce a parseable verdict in $(artifact_path evaluation_report)"
                fi
                fail "Evaluator produced an unparseable verdict"
                ;;
        esac
    done
elif should_run_turn E; then
    ensure_artifact_ids "Turn E input" d9_holdout_scenarios staging_root results

    log "═══ TURN E: Evaluation ═══"

    invoke_prompt "$EVAL_AGENT" "$EVAL_ROLE_FILE" turn_e_eval
    verify_prompt_outputs turn_e_eval

    if [ "$(evaluation_verdict)" = "PASS" ]; then
        BUILD_PASSED=true
        pass "Evaluation: PASS"
        update_portal_state "$FMWK"
        run_portal_steward "$FMWK" "Turn E"
        run_stage_audit "$FMWK" "Turn E"
    else
        update_portal_state "$FMWK"
        run_portal_steward "$FMWK" "Turn E"
        run_stage_audit "$FMWK" "Turn E"
        escalate "Evaluation: FAIL"
    fi
else
    escalate "Nothing to do: --from-turn ${FROM_TURN} skips all pipeline turns"
fi

# --- Final ------------------------------------------------------------------

if [ "$BUILD_PASSED" = true ]; then
    echo ""
    pass "═══ ${FMWK} BUILD COMPLETE ═══"
    log "Done. Framework ${FMWK} completed the pipeline with a PASS verdict."
else
    escalate "═══ ${FMWK} BUILD FAILED ═══"
fi
