#!/bin/bash
# Sawmill Guard — PreToolUse hook
# Denies Write/Edit outside the active role's file-ownership lane.
#
# Role resolution: env var first, sentinel second, neither = interactive (allow all).
#
# Residual risks (accepted):
#   - Bash tool can mutate files without Write/Edit — not enforceable by hooks
#   - Orchestrator sets its own subagent's role (fox writes the label)
#   - Non-Claude backends (Codex, Gemini) are instruction-enforced only
#   - No nested subagent support

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Read tool input from stdin
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)

# Only guard Write and Edit
case "$TOOL_NAME" in
    Write|Edit) ;;
    *) exit 0 ;;
esac

# No file path = nothing to guard
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Resolve active role: env var first, sentinel second
ROLE="${SAWMILL_ACTIVE_ROLE:-$(cat "$PROJECT_DIR/sawmill/.active-role" 2>/dev/null || true)}"

# No role set = interactive mode, allow everything
if [ -z "$ROLE" ]; then
    exit 0
fi

# Normalize to relative path (strip project dir prefix)
REL_PATH="$FILE_PATH"
if [[ "$FILE_PATH" == "$PROJECT_DIR/"* ]]; then
    REL_PATH="${FILE_PATH#$PROJECT_DIR/}"
fi

# Check allowlist per role
check_allowed() {
    local role="$1"
    local path="$2"

    case "$role" in
        orchestrator)
            [[ "$path" == sawmill/*/TASK.md ]] && return 0
            [[ "$path" == sawmill/.active-role ]] && return 0
            ;;
        spec-agent)
            [[ "$path" == sawmill/*/D[0-9]*.md ]] && return 0
            [[ "$path" == sawmill/*/BUILDER_HANDOFF.md ]] && return 0
            ;;
        holdout-agent)
            [[ "$path" == .holdouts/* ]] && return 0
            ;;
        builder)
            [[ "$path" == staging/* ]] && return 0
            [[ "$path" == sawmill/*/RESULTS.md ]] && return 0
            [[ "$path" == sawmill/*/13Q_ANSWERS.md ]] && return 0
            [[ "$path" == sawmill/*/builder_evidence.json ]] && return 0
            ;;
        reviewer)
            [[ "$path" == sawmill/*/REVIEW_REPORT.md ]] && return 0
            [[ "$path" == sawmill/*/REVIEW_ERRORS.md ]] && return 0
            [[ "$path" == sawmill/*/reviewer_evidence.json ]] && return 0
            ;;
        evaluator)
            [[ "$path" == sawmill/*/EVALUATION_REPORT.md ]] && return 0
            [[ "$path" == sawmill/*/EVALUATION_ERRORS.md ]] && return 0
            [[ "$path" == sawmill/*/evaluator_evidence.json ]] && return 0
            ;;
        auditor)
            [[ "$path" == sawmill/*/CANARY_AUDIT.md ]] && return 0
            ;;
    esac
    return 1
}

if check_allowed "$ROLE" "$REL_PATH"; then
    exit 0
else
    jq -nc --arg reason "Role [$ROLE] cannot write to [$REL_PATH]. Dispatch the appropriate agent." '
    {
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: $reason
      }
    }'
    exit 0
fi
