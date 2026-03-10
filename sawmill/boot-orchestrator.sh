#!/bin/bash
# Boot Orchestrator — optional launcher for Claude orchestration sessions.
# Sets env vars and writes the sentinel so Claude starts in orchestrator mode.
# Worker execution still happens separately through run.sh or direct Codex dispatch.
#
# Usage:
#   source sawmill/boot-orchestrator.sh [FMWK-ID]
#   ./sawmill/boot-orchestrator.sh FMWK-001-ledger
#
# After sourcing, start Claude in the same shell:
#   claude

set -euo pipefail

FMWK="${1:-}"

export SAWMILL_ACTIVE_ROLE=orchestrator
export SAWMILL_ACTIVE_FMWK="$FMWK"

# Write sentinel for optional Claude-native conversational dispatch
echo "orchestrator" > sawmill/.active-role

echo "[boot] SAWMILL_ACTIVE_ROLE=orchestrator"
[ -n "$FMWK" ] && echo "[boot] SAWMILL_ACTIVE_FMWK=$FMWK"
echo "[boot] Sentinel: sawmill/.active-role -> orchestrator"
echo "[boot] Ready. Start 'claude' in this shell to supervise Codex workers."
