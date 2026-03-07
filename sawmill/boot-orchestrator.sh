#!/bin/bash
# Boot Orchestrator — optional launcher for conversational orchestrator sessions.
# Sets env vars and writes sentinel so hooks enforce the orchestrator role.
#
# Usage:
#   source sawmill/boot-orchestrator.sh [FMWK-ID]
#   ./sawmill/boot-orchestrator.sh FMWK-001-ledger
#
# After sourcing, start claude in the same shell:
#   claude

set -euo pipefail

FMWK="${1:-}"

export SAWMILL_ACTIVE_ROLE=orchestrator
export SAWMILL_ACTIVE_FMWK="$FMWK"

# Write sentinel for conversational sessions (Agent tool subagent dispatch)
echo "orchestrator" > sawmill/.active-role

echo "[boot] SAWMILL_ACTIVE_ROLE=orchestrator"
[ -n "$FMWK" ] && echo "[boot] SAWMILL_ACTIVE_FMWK=$FMWK"
echo "[boot] Sentinel: sawmill/.active-role -> orchestrator"
echo "[boot] Ready. Start 'claude' in this shell."
