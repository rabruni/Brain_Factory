#!/bin/bash
# ============================================================================
# Sawmill Orchestrator — DoPeJarMo Build Pipeline
# ============================================================================
#
# Usage:  ./sawmill/run.sh <FMWK-ID> [--from-turn A|B|C|D|E]
# Example: ./sawmill/run.sh FMWK-001-ledger --from-turn D
#
# This script orchestrates the five Sawmill turns (A-E) for a single
# framework. It invokes agents, enforces gates, and manages retries.
#
# Prerequisites:
#   - At least one agent CLI installed: claude, codex, or gemini
#   - Repository is the working directory
#
# Agent selection (override with env vars):
#   SAWMILL_SPEC_AGENT=claude|codex|gemini     (default: claude)
#   SAWMILL_BUILD_AGENT=claude|codex|gemini    (default: claude)
#   SAWMILL_HOLDOUT_AGENT=claude|codex|gemini  (default: claude)
#   SAWMILL_EVAL_AGENT=claude|codex|gemini     (default: codex)
#
# Human gates pause for confirmation. The operator reviews and presses Enter.
# ============================================================================

set -euo pipefail

# --- Configuration ---------------------------------------------------------

usage() {
    echo "Usage: ./sawmill/run.sh <FMWK-ID> [--from-turn A|B|C|D|E]"
    echo "       ./sawmill/run.sh --audit"
    echo "Example: ./sawmill/run.sh FMWK-001-ledger --from-turn D"
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
gate() { echo -e "\n${YELLOW}>>> GATE: $1${NC}"; echo -e "${YELLOW}>>> Review the output, then press Enter to continue (or Ctrl+C to abort)${NC}"; read -r; }
pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }

FMWK=""
FROM_TURN="A"
RUN_AUDIT=false

while [ $# -gt 0 ]; do
    case "$1" in
        --audit)
            RUN_AUDIT=true
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

# --- Audit mode --------------------------------------------------------------
if [ "$RUN_AUDIT" = true ]; then
    AUDIT_AGENT="${SAWMILL_AUDIT_AGENT:-claude}"
    log "═══ PORTAL AUDIT ═══"

    if [ "$AUDIT_AGENT" = "claude" ]; then
        command -v jq >/dev/null 2>&1 || { fail "'jq' is required when audit agent is 'claude'"; exit 1; }
    fi

    case "$AUDIT_AGENT" in
        claude)
            env -u CLAUDECODE \
                SAWMILL_ACTIVE_ROLE=auditor SAWMILL_ACTIVE_FMWK="" \
                claude -p "You are the auditor. Read your role file, then execute every check. Write results to sawmill/PORTAL_AUDIT_RESULTS.md." \
                    --append-system-prompt "$(cat .claude/agents/auditor.md)" \
                    --allowedTools "Read,Glob,Grep,Bash,Write"
            ;;
        codex)
            codex exec --full-auto \
                "$(cat .claude/agents/auditor.md)

You are the auditor. Read your role file above, then execute every check. Write results to sawmill/PORTAL_AUDIT_RESULTS.md."
            ;;
        gemini)
            gemini -p "$(cat .claude/agents/auditor.md)

You are the auditor. Read your role file above, then execute every check. Write results to sawmill/PORTAL_AUDIT_RESULTS.md." \
                --yolo
            ;;
        *)
            fail "Unknown audit agent: ${AUDIT_AGENT}"
            exit 1
            ;;
    esac

    if [ -f "sawmill/PORTAL_AUDIT_RESULTS.md" ]; then
        pass "Audit complete. Results: sawmill/PORTAL_AUDIT_RESULTS.md"
    else
        fail "Auditor did not produce sawmill/PORTAL_AUDIT_RESULTS.md"
        exit 1
    fi
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

# Agent backend selection (override with env vars)
SPEC_AGENT="${SAWMILL_SPEC_AGENT:-claude}"       # claude | codex | gemini
BUILD_AGENT="${SAWMILL_BUILD_AGENT:-claude}"      # claude | codex | gemini
HOLDOUT_AGENT="${SAWMILL_HOLDOUT_AGENT:-claude}"  # claude | codex | gemini
EVAL_AGENT="${SAWMILL_EVAL_AGENT:-codex}"         # claude | codex | gemini

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
    local status_page="docs/sawmill/${fmwk}.md"

    # Only update auto-managed status pages (marker on first line)
    if [ ! -f "$status_page" ] || ! head -1 "$status_page" | grep -qF '<!-- sawmill:auto-status -->'; then
        return 0
    fi

    local sd="sawmill/${fmwk}" hd=".holdouts/${fmwk}"
    local spec="PENDING" plan="PENDING" holdout="PENDING" build="PENDING" eval_s="PENDING"
    local summary="Not started"

    if [ -f "$sd/D1_CONSTITUTION.md" ] && [ -f "$sd/D6_GAP_ANALYSIS.md" ]; then
        spec="DONE"; summary="Spec complete"
    fi
    if [ -f "$sd/D7_PLAN.md" ] && [ -f "$sd/BUILDER_HANDOFF.md" ]; then
        plan="DONE"; summary="Plan complete"
    fi
    if [ -f "$hd/D9_HOLDOUT_SCENARIOS.md" ]; then
        holdout="DONE"; summary="Holdouts complete"
    fi
    if [ -f "$sd/RESULTS.md" ]; then
        build="DONE"; summary="Build complete"
    fi
    if [ -f "$sd/EVALUATION_REPORT.md" ]; then
        if grep -qiE 'Final[[:space:]]+[Vv]erdict.*PASS' "$sd/EVALUATION_REPORT.md" 2>/dev/null; then
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
    local status_page="docs/sawmill/${fmwk}.md"
    local sd="sawmill/${fmwk}"
    local hd=".holdouts/${fmwk}"
    local stg="staging/${fmwk}"
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
    if [ -f "$sd/D1_CONSTITUTION.md" ]; then
        _ck "D1 exists" test -f "$sd/D1_CONSTITUTION.md"
        _ck "D2 exists" test -f "$sd/D2_SPECIFICATION.md"
        _ck "D3 exists" test -f "$sd/D3_DATA_MODEL.md"
        _ck "D4 exists" test -f "$sd/D4_CONTRACTS.md"
        _ck "D5 exists" test -f "$sd/D5_RESEARCH.md"
        _ck "D6 exists" test -f "$sd/D6_GAP_ANALYSIS.md"
        _ck "Portal: Turn A DONE" grep -qF "Turn A (Spec) | DONE" "$status_page"
    fi

    if [ -f "$sd/D7_PLAN.md" ]; then
        _ck "D7 exists" test -f "$sd/D7_PLAN.md"
        _ck "D8 exists" test -f "$sd/D8_TASKS.md"
        _ck "D10 exists" test -f "$sd/D10_AGENT_CONTEXT.md"
        _ck "Handoff exists" test -f "$sd/BUILDER_HANDOFF.md"
        _ck "Portal: Turn B DONE" grep -qF "Turn B (Plan) | DONE" "$status_page"
    fi

    if [ -f "$hd/D9_HOLDOUT_SCENARIOS.md" ]; then
        _ck "D9 exists" test -f "$hd/D9_HOLDOUT_SCENARIOS.md"
        _ck "Portal: Turn C DONE" grep -qF "Turn C (Holdout) | DONE" "$status_page"
    fi

    if [ -f "$sd/RESULTS.md" ]; then
        _ck "RESULTS.md exists" test -f "$sd/RESULTS.md"
        _ck "staging/ has content" test -d "$stg"
        _ck "Portal: Turn D DONE" grep -qF "Turn D (Build) | DONE" "$status_page"
    fi

    if [ -f "$sd/EVALUATION_REPORT.md" ]; then
        _ck "EVALUATION_REPORT.md exists" test -f "$sd/EVALUATION_REPORT.md"
        if grep -qiE 'Final[[:space:]]+[Vv]erdict.*PASS' "$sd/EVALUATION_REPORT.md" 2>/dev/null; then
            _ck "Portal: Turn E PASS" grep -qF "Turn E (Eval) | PASS" "$status_page"
        fi
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
            SAWMILL_ACTIVE_ROLE="$role_name" SAWMILL_ACTIVE_FMWK="$FMWK" \
                codex exec --full-auto \
                    "${role_content}

${prompt}"
            ;;
        gemini)
            # Gemini auto-reads GEMINI.md (or CLAUDE.md if configured in settings.json).
            # No --system-prompt flag — everything goes in -p argument.
            # --yolo auto-approves all tool actions.
            # Env vars set for consistency (Gemini does not use Claude Code hooks).
            SAWMILL_ACTIVE_ROLE="$role_name" SAWMILL_ACTIVE_FMWK="$FMWK" \
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

# --- Preflight --------------------------------------------------------------

log "Sawmill run: ${FMWK}"
log "From turn:     ${FROM_TURN}"
log "Spec agent:    ${SPEC_AGENT}"
log "Build agent:   ${BUILD_AGENT}"
log "Holdout agent: ${HOLDOUT_AGENT}"
log "Eval agent:    ${EVAL_AGENT}"
echo ""

# Verify required files exist
for f in CLAUDE.md AGENT_BOOTSTRAP.md .claude/agents/spec-agent.md \
         .claude/agents/holdout-agent.md .claude/agents/builder.md \
         .claude/agents/evaluator.md; do
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
for agent_var in SPEC_AGENT BUILD_AGENT HOLDOUT_AGENT EVAL_AGENT; do
    agent_val="${!agent_var}"
    case "$agent_val" in
        claude) command -v claude >/dev/null 2>&1 || { fail "${agent_var}=${agent_val} but 'claude' CLI not found"; exit 1; } ;;
        codex)  command -v codex  >/dev/null 2>&1 || { fail "${agent_var}=${agent_val} but 'codex' CLI not found"; exit 1; } ;;
        gemini) command -v gemini >/dev/null 2>&1 || { fail "${agent_var}=${agent_val} but 'gemini' CLI not found"; exit 1; } ;;
    esac
done

needs_jq=false
for _agent_val in "$SPEC_AGENT" "$BUILD_AGENT" "$HOLDOUT_AGENT" "$EVAL_AGENT"; do
    if [ "$_agent_val" = "claude" ]; then needs_jq=true; break; fi
done
if [ "$needs_jq" = true ]; then
    command -v jq >/dev/null 2>&1 || { fail "'jq' is required when any agent backend is 'claude'"; exit 1; }
fi

# Create working directories
mkdir -p "${SAWMILL_DIR}" "${HOLDOUT_DIR}" "${STAGING_DIR}"

# Verify TASK.md exists
if [ ! -f "${SAWMILL_DIR}/TASK.md" ]; then
    fail "Missing ${SAWMILL_DIR}/TASK.md — create it before running the pipeline."
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

    invoke_agent "$SPEC_AGENT" ".claude/agents/spec-agent.md" \
"YOUR TASK: Generate D1-D6 specification documents for a framework.

READING ORDER — read these files in this exact sequence:
1. AGENT_BOOTSTRAP.md — full orientation (primitives, invariants, boot order)
2. architecture/NORTH_STAR.md — WHY (design authority)
3. architecture/BUILDER_SPEC.md — WHAT (nine primitives, build rules)
4. architecture/OPERATIONAL_SPEC.md — HOW (runtime behavior)
5. architecture/FWK-0-DRAFT.md — framework rules, decomposition standard
6. architecture/BUILD-PLAN.md — what gets built, in what order
7. ${SAWMILL_DIR}/TASK.md — YOUR ASSIGNMENT (which framework to spec)
8. ${SAWMILL_DIR}/SOURCE_MATERIAL.md — detailed spec material (if it exists)
9. Templates/compressed/D1_CONSTITUTION.md — output template
10. Templates/compressed/D2_SPECIFICATION.md — output template
11. Templates/compressed/D3_DATA_MODEL.md — output template
12. Templates/compressed/D4_CONTRACTS.md — output template
13. Templates/compressed/D5_RESEARCH.md — output template
14. Templates/compressed/D6_GAP_ANALYSIS.md — output template

OUTPUT: Write D1_CONSTITUTION.md, D2_SPECIFICATION.md, D3_DATA_MODEL.md,
D4_CONTRACTS.md, D5_RESEARCH.md, D6_GAP_ANALYSIS.md to ${SAWMILL_DIR}/

GATE: D6 must have ZERO OPEN items. Every gap must be RESOLVED or ASSUMED."

    # Verify D1-D6 exist
    for d in D1_CONSTITUTION D2_SPECIFICATION D3_DATA_MODEL D4_CONTRACTS D5_RESEARCH D6_GAP_ANALYSIS; do
        if [ ! -f "${SAWMILL_DIR}/${d}.md" ]; then
            fail "Turn A did not produce ${SAWMILL_DIR}/${d}.md"
            exit 1
        fi
    done
    pass "Turn A produced D1-D6"

    update_portal_state "$FMWK"
    run_stage_audit "$FMWK" "Turn A"

    gate "Review ${SAWMILL_DIR}/D1-D6 for completeness and accuracy"
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
            require_files "Turn A output" \
                "${SAWMILL_DIR}/D1_CONSTITUTION.md" \
                "${SAWMILL_DIR}/D2_SPECIFICATION.md" \
                "${SAWMILL_DIR}/D3_DATA_MODEL.md" \
                "${SAWMILL_DIR}/D4_CONTRACTS.md" \
                "${SAWMILL_DIR}/D5_RESEARCH.md" \
                "${SAWMILL_DIR}/D6_GAP_ANALYSIS.md"
        fi

        # Turn B (background)
        invoke_agent "$SPEC_AGENT" ".claude/agents/spec-agent.md" \
"YOUR TASK: Generate D7, D8, D10, and BUILDER_HANDOFF from approved D1-D6.

YOU ARE IN TURN B. Your Turn A output has been approved by the operator.

READING ORDER — read these files in this exact sequence:
1. AGENT_BOOTSTRAP.md — orientation
2. ${SAWMILL_DIR}/D1_CONSTITUTION.md
3. ${SAWMILL_DIR}/D2_SPECIFICATION.md
4. ${SAWMILL_DIR}/D3_DATA_MODEL.md
5. ${SAWMILL_DIR}/D4_CONTRACTS.md
6. ${SAWMILL_DIR}/D5_RESEARCH.md
7. ${SAWMILL_DIR}/D6_GAP_ANALYSIS.md
8. Templates/compressed/D7_PLAN.md — output template
9. Templates/compressed/D8_TASKS.md — output template
10. Templates/compressed/D10_AGENT_CONTEXT.md — output template
11. Templates/compressed/BUILDER_HANDOFF_STANDARD.md — handoff format
12. Templates/compressed/BUILDER_PROMPT_CONTRACT.md — prompt contract

OUTPUT: Write D7_PLAN.md, D8_TASKS.md, D10_AGENT_CONTEXT.md,
and BUILDER_HANDOFF.md to ${SAWMILL_DIR}/" &
        PID_B=$!
    else
        log "Skipping Turn B (--from-turn ${FROM_TURN})"
    fi

    if should_run_turn C; then
        if [ "$FROM_TURN" = "C" ]; then
            require_files "Turn A output" \
                "${SAWMILL_DIR}/D2_SPECIFICATION.md" \
                "${SAWMILL_DIR}/D4_CONTRACTS.md"
        fi

        # Turn C (background)
        invoke_agent "$HOLDOUT_AGENT" ".claude/agents/holdout-agent.md" \
"YOUR TASK: Write holdout test scenarios from D2 and D4 ONLY.

YOU ARE THE HOLDOUT AGENT. You have STRICT ISOLATION.

READING ORDER — read ONLY these files:
1. ${SAWMILL_DIR}/D2_SPECIFICATION.md — behavioral spec
2. ${SAWMILL_DIR}/D4_CONTRACTS.md — interface contracts
3. Templates/compressed/D9_HOLDOUT_SCENARIOS.md — output template

DO NOT READ any other files. Not D1, D3, D5, D6, D7, D8, D10.
Not BUILDER_HANDOFF. Not architecture/. Not src/.

OUTPUT: Write D9_HOLDOUT_SCENARIOS.md to ${HOLDOUT_DIR}/" &
        PID_C=$!
    else
        log "Skipping Turn C (--from-turn ${FROM_TURN})"
    fi

    if [ -n "$PID_B" ]; then
        wait "$PID_B" || { fail "Turn B failed"; exit 1; }

        for d in D7_PLAN D8_TASKS D10_AGENT_CONTEXT BUILDER_HANDOFF; do
            if [ ! -f "${SAWMILL_DIR}/${d}.md" ]; then
                fail "Turn B did not produce ${SAWMILL_DIR}/${d}.md"
                exit 1
            fi
        done
        pass "Turn B produced D7, D8, D10, BUILDER_HANDOFF"
    fi

    if [ -n "$PID_C" ]; then
        wait "$PID_C" || { fail "Turn C failed"; exit 1; }

        if [ ! -f "${HOLDOUT_DIR}/D9_HOLDOUT_SCENARIOS.md" ]; then
            fail "Turn C did not produce ${HOLDOUT_DIR}/D9_HOLDOUT_SCENARIOS.md"
            exit 1
        fi
        pass "Turn C produced D9 holdout scenarios"
    fi

    update_portal_state "$FMWK"
    run_stage_audit "$FMWK" "Turn BC"

else
    log "Skipping Turn B + C (--from-turn ${FROM_TURN})"
fi

if should_run_turn D && [ "$FROM_TURN_RANK" -le "$(turn_rank C)" ]; then
    require_files "Turn B/C outputs" \
        "${SAWMILL_DIR}/D7_PLAN.md" \
        "${SAWMILL_DIR}/D8_TASKS.md" \
        "${SAWMILL_DIR}/D10_AGENT_CONTEXT.md" \
        "${SAWMILL_DIR}/BUILDER_HANDOFF.md" \
        "${HOLDOUT_DIR}/D9_HOLDOUT_SCENARIOS.md"

    gate "Review D7/D8/D10/D9 for completeness"
fi

# --- Turn D: Builder (up to 3 attempts) ------------------------------------

BUILD_PASSED=false

if should_run_turn D; then
    require_files "Turn D input" \
        "${SAWMILL_DIR}/D10_AGENT_CONTEXT.md" \
        "${SAWMILL_DIR}/BUILDER_HANDOFF.md"

    log "═══ TURN D: Build ═══"

    ATTEMPT=0

    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        ATTEMPT=$((ATTEMPT + 1))
        log "Build attempt ${ATTEMPT}/${MAX_ATTEMPTS}"

        # Compose retry context
        RETRY_CONTEXT=""
        if [ -f "${SAWMILL_DIR}/EVALUATION_ERRORS.md" ]; then
            RETRY_CONTEXT="
RETRY CONTEXT (attempt ${ATTEMPT}):
Read ${SAWMILL_DIR}/EVALUATION_ERRORS.md for one-line failure descriptions from the evaluator.
Fix ONLY what failed. Do not rewrite passing code."
        fi

        # --- Turn D is TWO invocations: 13Q gate, then build ---
        #
        # Problem: `claude -p` is atomic — the agent answers, the process exits.
        # We cannot tell a dead process "now continue building."
        #
        # Solution: Split into two calls.
        #   Call 1: Answer 13Q, write answers to file, exit.
        #   Call 2: After human approval, resume session and build.
        #
        # For Claude: use --output-format json to capture session_id, then --resume.
        # For Codex/Gemini: two separate invocations (no session resume).

        log "Turn D — Step 1: 13Q Gate"

        # Step 1: Builder answers 13 questions and writes them to a file
        BUILDER_SESSION=""
        case "$BUILD_AGENT" in
            claude)
                BUILDER_SESSION=$(env -u CLAUDECODE \
                SAWMILL_ACTIVE_ROLE=builder SAWMILL_ACTIVE_FMWK="$FMWK" \
                claude -p "YOUR TASK: Answer the 13-question comprehension gate.

READING ORDER — read these files in this EXACT sequence:
1. AGENT_BOOTSTRAP.md — orientation (primitives, invariants)
2. ${SAWMILL_DIR}/D10_AGENT_CONTEXT.md — your orientation FIRST
3. Templates/TDD_AND_DEBUGGING.md — HOW to code (TDD iron law, debugging protocol)
4. ${SAWMILL_DIR}/BUILDER_HANDOFF.md — your task
5. Files listed in BUILDER_HANDOFF Section 7 (Existing Code to Reference)

DO NOT READ: .holdouts/*, EVALUATION_REPORT.md, other builders' work
${RETRY_CONTEXT}

Answer all 13 questions (10 verification + 3 adversarial) per your role file.
Write your answers to ${SAWMILL_DIR}/13Q_ANSWERS.md.
Then STOP. Do NOT write any code, create any directories, or make any plans." \
                    --append-system-prompt "$(cat .claude/agents/builder.md)" \
                    --allowedTools "Read,Edit,Write,Glob,Grep,Bash" \
                    --output-format json | jq -r '.session_id')
                ;;
            *)
                invoke_agent "$BUILD_AGENT" ".claude/agents/builder.md" \
"YOUR TASK: Answer the 13-question comprehension gate.

READING ORDER — read these files in this EXACT sequence:
1. AGENT_BOOTSTRAP.md — orientation (primitives, invariants)
2. ${SAWMILL_DIR}/D10_AGENT_CONTEXT.md — your orientation FIRST
3. Templates/TDD_AND_DEBUGGING.md — HOW to code (TDD iron law, debugging protocol)
4. ${SAWMILL_DIR}/BUILDER_HANDOFF.md — your task
5. Files listed in BUILDER_HANDOFF Section 7 (Existing Code to Reference)

DO NOT READ: .holdouts/*, EVALUATION_REPORT.md, other builders' work
${RETRY_CONTEXT}

Answer all 13 questions (10 verification + 3 adversarial) per your role file.
Write your answers to ${SAWMILL_DIR}/13Q_ANSWERS.md.
Then STOP. Do NOT write any code."
                ;;
        esac

        # Verify 13Q answers were produced
        if [ ! -f "${SAWMILL_DIR}/13Q_ANSWERS.md" ]; then
            fail "Builder did not produce ${SAWMILL_DIR}/13Q_ANSWERS.md"
            if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
                log "Will retry..."
                continue
            else
                fail "Builder failed after ${MAX_ATTEMPTS} attempts. Returning to spec author."
                exit 1
            fi
        fi
        pass "Builder produced 13Q answers"

        gate "Review ${SAWMILL_DIR}/13Q_ANSWERS.md — approve or reject"

        # Step 2: Builder proceeds to DTT (resume session if Claude, new call otherwise)
        log "Turn D — Step 2: DTT Build"

        case "$BUILD_AGENT" in
            claude)
                if [ -n "$BUILDER_SESSION" ]; then
                    # Resume the same session — builder retains full context
                    env -u CLAUDECODE \
                        SAWMILL_ACTIVE_ROLE=builder SAWMILL_ACTIVE_FMWK="$FMWK" \
                        claude -p "Your 13Q answers have been APPROVED. Proceed to implementation.

STEP 2: DTT (Design-Test-Then-implement) per behavior in the Test Plan.
Follow TDD discipline from Templates/TDD_AND_DEBUGGING.md: red-green-refactor per behavior.
STEP 3: Run full test suite. Write ${SAWMILL_DIR}/RESULTS.md. Open PR on branch ${BRANCH}.

DO NOT re-read the spec. You already have it from Step 1." \
                            --resume "$BUILDER_SESSION" \
                            --allowedTools "Read,Edit,Write,Glob,Grep,Bash"
                else
                    # Fallback: new session with full context
                    invoke_agent "$BUILD_AGENT" ".claude/agents/builder.md" \
"YOUR TASK: Build code. Your 13Q answers were approved.

READING ORDER:
1. AGENT_BOOTSTRAP.md
2. ${SAWMILL_DIR}/D10_AGENT_CONTEXT.md
3. Templates/TDD_AND_DEBUGGING.md — TDD discipline
4. ${SAWMILL_DIR}/BUILDER_HANDOFF.md
5. ${SAWMILL_DIR}/13Q_ANSWERS.md — your approved answers for reference

DO NOT READ: .holdouts/*, EVALUATION_REPORT.md
${RETRY_CONTEXT}

Proceed directly to DTT. Do NOT re-answer the 13 questions.
STEP 2: DTT per behavior (red-green-refactor). STEP 3: Full test suite. Write ${SAWMILL_DIR}/RESULTS.md. Open PR on branch ${BRANCH}."
                fi
                ;;
            *)
                invoke_agent "$BUILD_AGENT" ".claude/agents/builder.md" \
"YOUR TASK: Build code. Your 13Q answers were approved.

READING ORDER:
1. AGENT_BOOTSTRAP.md
2. ${SAWMILL_DIR}/D10_AGENT_CONTEXT.md
3. Templates/TDD_AND_DEBUGGING.md — TDD discipline
4. ${SAWMILL_DIR}/BUILDER_HANDOFF.md
5. ${SAWMILL_DIR}/13Q_ANSWERS.md — your approved answers for reference

DO NOT READ: .holdouts/*, EVALUATION_REPORT.md
${RETRY_CONTEXT}

Proceed directly to DTT. Do NOT re-answer the 13 questions.
STEP 2: DTT per behavior (red-green-refactor). STEP 3: Full test suite. Write ${SAWMILL_DIR}/RESULTS.md. Open PR on branch ${BRANCH}."
                ;;
        esac

        # Verify builder outputs
        if [ ! -f "${SAWMILL_DIR}/RESULTS.md" ]; then
            fail "Builder did not produce RESULTS.md"
            if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
                log "Will retry..."
                continue
            else
                fail "Builder failed after ${MAX_ATTEMPTS} attempts. Returning to spec author."
                exit 1
            fi
        fi

        pass "Builder produced code and RESULTS.md"

        update_portal_state "$FMWK"
        run_stage_audit "$FMWK" "Turn D"

        if ! should_run_turn E; then
            BUILD_PASSED=true
            break
        fi

        # --- Turn E: Evaluator --------------------------------------------------

        log "═══ TURN E: Evaluation ═══"

        invoke_agent "$EVAL_AGENT" ".claude/agents/evaluator.md" \
"YOUR TASK: Run holdout test scenarios against the built code.

YOU ARE THE EVALUATOR. You have STRICT ISOLATION.

READING ORDER — read ONLY these:
1. $(pwd)/${HOLDOUT_DIR}/D9_HOLDOUT_SCENARIOS.md — the test scenarios from the MAIN worktree path (not the build branch worktree)
2. Check out branch ${BRANCH} in a clean worktree — the code to test

DO NOT READ: AGENT_BOOTSTRAP.md, D1-D8, D10, BUILDER_HANDOFF, RESULTS.md,
             builder commit messages, architecture/*, sawmill/* specs

PROCESS:
  For each scenario: run Setup → Execute → Verify → Cleanup, 3 times.
  2/3 pass = scenario PASS.
  Run P0 first — if any P0 FAIL, STOP immediately.
  Then P1, then P2.
  90% overall required.

OUTPUT:
  Write full report to ${SAWMILL_DIR}/EVALUATION_REPORT.md
  Write one-line failure descriptions to ${SAWMILL_DIR}/EVALUATION_ERRORS.md"

        # Check verdict — allow markdown formatting around the verdict line
        if [ -f "${SAWMILL_DIR}/EVALUATION_REPORT.md" ]; then
            if grep -qiE "Final\s*[Vv]erdict.*PASS" "${SAWMILL_DIR}/EVALUATION_REPORT.md"; then
                BUILD_PASSED=true
                pass "Evaluation: PASS"
                update_portal_state "$FMWK"
                run_stage_audit "$FMWK" "Turn E"
                break
            else
                fail "Evaluation: FAIL (attempt ${ATTEMPT}/${MAX_ATTEMPTS})"
                if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
                    fail "Build failed after ${MAX_ATTEMPTS} attempts. Returning to spec author."
                    exit 1
                fi
            fi
        else
            fail "Evaluator did not produce EVALUATION_REPORT.md"
            if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
                fail "Build failed after ${MAX_ATTEMPTS} attempts."
                exit 1
            fi
        fi
    done
elif should_run_turn E; then
    require_files "Turn E input" "${HOLDOUT_DIR}/D9_HOLDOUT_SCENARIOS.md"

    log "═══ TURN E: Evaluation ═══"

    invoke_agent "$EVAL_AGENT" ".claude/agents/evaluator.md" \
"YOUR TASK: Run holdout test scenarios against the built code.

YOU ARE THE EVALUATOR. You have STRICT ISOLATION.

READING ORDER — read ONLY these:
1. $(pwd)/${HOLDOUT_DIR}/D9_HOLDOUT_SCENARIOS.md — the test scenarios from the MAIN worktree path (not the build branch worktree)
2. Check out branch ${BRANCH} in a clean worktree — the code to test

DO NOT READ: AGENT_BOOTSTRAP.md, D1-D8, D10, BUILDER_HANDOFF, RESULTS.md,
             builder commit messages, architecture/*, sawmill/* specs

PROCESS:
  For each scenario: run Setup → Execute → Verify → Cleanup, 3 times.
  2/3 pass = scenario PASS.
  Run P0 first — if any P0 FAIL, STOP immediately.
  Then P1, then P2.
  90% overall required.

OUTPUT:
  Write full report to ${SAWMILL_DIR}/EVALUATION_REPORT.md
  Write one-line failure descriptions to ${SAWMILL_DIR}/EVALUATION_ERRORS.md"

    if [ -f "${SAWMILL_DIR}/EVALUATION_REPORT.md" ]; then
        if grep -qiE "Final\s*[Vv]erdict.*PASS" "${SAWMILL_DIR}/EVALUATION_REPORT.md"; then
            BUILD_PASSED=true
            pass "Evaluation: PASS"
            update_portal_state "$FMWK"
            run_stage_audit "$FMWK" "Turn E"
        else
            fail "Evaluation: FAIL"
            exit 1
        fi
    else
        fail "Evaluator did not produce EVALUATION_REPORT.md"
        exit 1
    fi
else
    fail "Nothing to do: --from-turn ${FROM_TURN} skips all pipeline turns"
    exit 1
fi

# --- Final ------------------------------------------------------------------

if [ "$BUILD_PASSED" = true ]; then
    echo ""
    pass "═══ ${FMWK} BUILD COMPLETE ═══"
    gate "Review EVALUATION_REPORT.md and merge PR on branch ${BRANCH}"
    log "Done. Framework ${FMWK} is built and evaluated."
else
    fail "═══ ${FMWK} BUILD FAILED ═══"
    exit 1
fi
