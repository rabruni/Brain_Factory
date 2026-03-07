#!/bin/bash
# Sawmill Stop — Stop hook
# Prevents orchestrator from quitting when a dispatch has TASK.md but no
# downstream output, meaning work was requested but never completed.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
INPUT=$(cat)

# Stop hooks must allow the second stop attempt to avoid recursion loops.
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null || echo false)
if [ "$STOP_ACTIVE" = "true" ]; then
    exit 0
fi

# Resolve active role: env var first, sentinel second
ROLE="${SAWMILL_ACTIVE_ROLE:-$(cat "$PROJECT_DIR/sawmill/.active-role" 2>/dev/null || true)}"
FMWK="${SAWMILL_ACTIVE_FMWK:-}"

# Only applies to orchestrator
if [ "$ROLE" != "orchestrator" ]; then
    exit 0
fi

# No framework = nothing to check
if [ -z "$FMWK" ]; then
    exit 0
fi

SAWMILL_DIR="$PROJECT_DIR/sawmill/$FMWK"

# If TASK.md exists, check for any downstream output
if [ -f "$SAWMILL_DIR/TASK.md" ]; then
    for f in D1_CONSTITUTION.md D2_SPECIFICATION.md RESULTS.md EVALUATION_REPORT.md; do
        if [ -f "$SAWMILL_DIR/$f" ]; then
            exit 0
        fi
    done

    jq -nc --arg reason "Orchestrator has TASK.md for $FMWK but no downstream output yet. Dispatch an agent before stopping." '
    {
      decision: "block",
      reason: $reason
    }'
    exit 0
fi

exit 0
