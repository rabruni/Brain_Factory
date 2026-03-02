#!/bin/bash
# ============================================================================
# Sawmill Orchestrator — DoPeJarMo Build Pipeline
# ============================================================================
#
# Usage:  ./sawmill/run.sh <FMWK-ID>
# Example: ./sawmill/run.sh FMWK-001-ledger
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

FMWK="${1:?Usage: ./sawmill/run.sh <FMWK-ID> (e.g., FMWK-001-ledger)}"
SAWMILL_DIR="sawmill/${FMWK}"
HOLDOUT_DIR=".holdouts/${FMWK}"
SRC_DIR="src/${FMWK}"
MAX_ATTEMPTS=3
BRANCH="build/${FMWK}"

# Agent backend selection (override with env vars)
SPEC_AGENT="${SAWMILL_SPEC_AGENT:-claude}"       # claude | codex | gemini
BUILD_AGENT="${SAWMILL_BUILD_AGENT:-claude}"      # claude | codex | gemini
HOLDOUT_AGENT="${SAWMILL_HOLDOUT_AGENT:-claude}"  # claude | codex | gemini
EVAL_AGENT="${SAWMILL_EVAL_AGENT:-codex}"         # claude | codex | gemini

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Helpers ----------------------------------------------------------------

log() { echo -e "${BLUE}[sawmill]${NC} $1"; }
gate() { echo -e "\n${YELLOW}>>> GATE: $1${NC}"; echo -e "${YELLOW}>>> Review the output, then press Enter to continue (or Ctrl+C to abort)${NC}"; read -r; }
pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }

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

    log "Invoking ${backend} with role ${role_file}"

    case "$backend" in
        claude)
            # Claude auto-reads CLAUDE.md from project root.
            # --append-system-prompt adds role constraints to its default system prompt.
            # The task prompt goes as the -p argument.
            # --allowedTools grants file and shell access.
            claude -p "${prompt}" \
                --append-system-prompt "${role_content}" \
                --allowedTools "Read,Edit,Write,Glob,Grep,Bash"
            ;;
        codex)
            # Codex auto-reads AGENTS.md (or CLAUDE.md if symlinked/configured).
            # No --system-prompt flag — everything goes in the exec argument.
            # --full-auto disables approval prompts.
            # Codex runs in a network-disabled sandbox by default.
            codex exec --full-auto \
                "${role_content}

${prompt}"
            ;;
        gemini)
            # Gemini auto-reads GEMINI.md (or CLAUDE.md if configured in settings.json).
            # No --system-prompt flag — everything goes in -p argument.
            # --yolo auto-approves all tool actions.
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

# Create working directories
mkdir -p "${SAWMILL_DIR}" "${HOLDOUT_DIR}" "${SRC_DIR}"

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

# --- Turn A: Spec Agent (D1-D6) --------------------------------------------

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

gate "Review ${SAWMILL_DIR}/D1-D6 for completeness and accuracy"

# --- Turn B + C: Plan + Holdouts (parallel) ---------------------------------

log "═══ TURN B + C: Plan (D7-D8-D10) + Holdouts (D9) — parallel ═══"

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

# Wait for both
wait $PID_B || { fail "Turn B failed"; exit 1; }
wait $PID_C || { fail "Turn C failed"; exit 1; }

# Verify outputs
for d in D7_PLAN D8_TASKS D10_AGENT_CONTEXT BUILDER_HANDOFF; do
    if [ ! -f "${SAWMILL_DIR}/${d}.md" ]; then
        fail "Turn B did not produce ${SAWMILL_DIR}/${d}.md"
        exit 1
    fi
done
pass "Turn B produced D7, D8, D10, BUILDER_HANDOFF"

if [ ! -f "${HOLDOUT_DIR}/D9_HOLDOUT_SCENARIOS.md" ]; then
    fail "Turn C did not produce ${HOLDOUT_DIR}/D9_HOLDOUT_SCENARIOS.md"
    exit 1
fi
pass "Turn C produced D9 holdout scenarios"

# --- Turn D: Builder (up to 3 attempts) ------------------------------------

log "═══ TURN D: Build ═══"

ATTEMPT=0
BUILD_PASSED=false

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
            BUILDER_SESSION=$(claude -p "YOUR TASK: Answer the 13-question comprehension gate.

READING ORDER — read these files in this EXACT sequence:
1. AGENT_BOOTSTRAP.md — orientation (primitives, invariants)
2. ${SAWMILL_DIR}/D10_AGENT_CONTEXT.md — your orientation FIRST
3. ${SAWMILL_DIR}/BUILDER_HANDOFF.md — your task SECOND
4. Files listed in BUILDER_HANDOFF Section 7 (Existing Code to Reference)

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
3. ${SAWMILL_DIR}/BUILDER_HANDOFF.md — your task SECOND
4. Files listed in BUILDER_HANDOFF Section 7 (Existing Code to Reference)

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
                claude -p "Your 13Q answers have been APPROVED. Proceed to implementation.

STEP 2: DTT (Design-Test-Then-implement) per behavior in the Test Plan.
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
3. ${SAWMILL_DIR}/BUILDER_HANDOFF.md
4. ${SAWMILL_DIR}/13Q_ANSWERS.md — your approved answers for reference

DO NOT READ: .holdouts/*, EVALUATION_REPORT.md
${RETRY_CONTEXT}

Proceed directly to DTT. Do NOT re-answer the 13 questions.
STEP 2: DTT per behavior. STEP 3: Full test suite. Write ${SAWMILL_DIR}/RESULTS.md. Open PR on branch ${BRANCH}."
            fi
            ;;
        *)
            invoke_agent "$BUILD_AGENT" ".claude/agents/builder.md" \
"YOUR TASK: Build code. Your 13Q answers were approved.

READING ORDER:
1. AGENT_BOOTSTRAP.md
2. ${SAWMILL_DIR}/D10_AGENT_CONTEXT.md
3. ${SAWMILL_DIR}/BUILDER_HANDOFF.md
4. ${SAWMILL_DIR}/13Q_ANSWERS.md — your approved answers for reference

DO NOT READ: .holdouts/*, EVALUATION_REPORT.md
${RETRY_CONTEXT}

Proceed directly to DTT. Do NOT re-answer the 13 questions.
STEP 2: DTT per behavior. STEP 3: Full test suite. Write ${SAWMILL_DIR}/RESULTS.md. Open PR on branch ${BRANCH}."
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

    # --- Turn E: Evaluator --------------------------------------------------

    log "═══ TURN E: Evaluation ═══"

    invoke_agent "$EVAL_AGENT" ".claude/agents/evaluator.md" \
"YOUR TASK: Run holdout test scenarios against the built code.

YOU ARE THE EVALUATOR. You have STRICT ISOLATION.

READING ORDER — read ONLY these:
1. ${HOLDOUT_DIR}/D9_HOLDOUT_SCENARIOS.md — the test scenarios
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

    # Check verdict — look for explicit verdict line, not just "PASS" anywhere
    if [ -f "${SAWMILL_DIR}/EVALUATION_REPORT.md" ]; then
        if grep -qE "^(##\s*)?Final [Vv]erdict:\s*PASS" "${SAWMILL_DIR}/EVALUATION_REPORT.md"; then
            BUILD_PASSED=true
            pass "Evaluation: PASS"
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
