#!/bin/bash
# Sawmill State — PreToolUse hook
# Injects compact pipeline state for the orchestrator role.
# Non-orchestrator roles: no-op.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
INPUT=$(cat)

# Resolve active role: env var first, sentinel second
ROLE="${SAWMILL_ACTIVE_ROLE:-$(cat "$PROJECT_DIR/sawmill/.active-role" 2>/dev/null || true)}"
FMWK="${SAWMILL_ACTIVE_FMWK:-}"

# Only inject state for orchestrator
if [ "$ROLE" != "orchestrator" ]; then
    exit 0
fi

# No framework set — nothing to report
if [ -z "$FMWK" ]; then
    exit 0
fi

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)

# Only inject before actions that can change state or commit to a choice.
case "$TOOL_NAME" in
    Write|Edit|Bash) ;;
    *) exit 0 ;;
esac

SAWMILL_DIR="$PROJECT_DIR/sawmill/$FMWK"
HOLDOUT_DIR="$PROJECT_DIR/.holdouts/$FMWK"

has_all() {
    local base_dir="$1"
    shift
    local file
    for file in "$@"; do
        [ -f "$base_dir/$file" ] || return 1
    done
    return 0
}

spec="-"
plan="-"
holdout="-"
build="-"
eval_state="-"

if has_all "$SAWMILL_DIR" \
    D1_CONSTITUTION.md D2_SPECIFICATION.md D3_DATA_MODEL.md \
    D4_CONTRACTS.md D5_RESEARCH.md D6_GAP_ANALYSIS.md; then
    spec="done"
fi

if has_all "$SAWMILL_DIR" \
    D7_PLAN.md D8_TASKS.md D10_AGENT_CONTEXT.md BUILDER_HANDOFF.md; then
    plan="done"
fi

if [ -f "$HOLDOUT_DIR/D9_HOLDOUT_SCENARIOS.md" ]; then
    holdout="done"
fi

if [ -f "$SAWMILL_DIR/RESULTS.md" ]; then
    build="done"
fi

if grep -Eq 'Final[[:space:]]+[Vv]erdict.*PASS' "$SAWMILL_DIR/EVALUATION_REPORT.md" 2>/dev/null; then
    eval_state="PASS"
elif grep -Eq 'Final[[:space:]]+[Vv]erdict.*FAIL' "$SAWMILL_DIR/EVALUATION_REPORT.md" 2>/dev/null; then
    eval_state="FAIL"
fi

STATE_LINE="$FMWK: spec:$spec plan:$plan holdout:$holdout build:$build eval:$eval_state"

jq -nc --arg ctx "[PIPELINE STATE]\n$STATE_LINE\n[/PIPELINE STATE]" '
{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "allow",
    additionalContext: $ctx
  }
}'

exit 0
