#!/bin/bash
# Workspace Check — Stop hook
# Prevents agent from going idle when there are workspace items addressed to it.
# Checks the workspace for sent items and blocks stop if work is waiting.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Check if workspace module exists
if [ ! -f "$PROJECT_DIR/workspace.py" ]; then
    exit 0
fi

# Check for pending workspace items addressed to any registered agent name
PENDING=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
import workspace as ws

# Check all registered agents for this CLI
agents = ws.list_agents()
for agent in agents:
    if agent.get('cli') == 'claude':
        items = ws.list_items(status='sent', to=agent['name'])
        if items:
            print(f'{len(items)} items waiting for {agent[\"name\"]}')
            for it in items:
                print(f'  {it[\"id\"]}: {it.get(\"summary\",\"\")[:60]}')
            sys.exit(0)
print('')
" 2>/dev/null || echo "")

if [ -n "$PENDING" ]; then
    jq -nc --arg reason "Workspace has items waiting: $PENDING. Check the workspace before stopping." '
    {
      decision: "block",
      reason: $reason
    }'
    exit 0
fi

exit 0
