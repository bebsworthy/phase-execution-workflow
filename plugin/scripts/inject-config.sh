#!/usr/bin/env bash
# SubagentStart hook: auto-inject resolved pew.yaml config into PEW agents.
#
# Reads agent_type from stdin JSON, maps to a config scope, runs
# pw.sh dump-config, and outputs additionalContext for Claude Code
# to inject into the agent's context window.
#
# Non-PEW agents (Explore, Plan, general-purpose) are ignored.
# Exits silently if no pew.yaml exists (non-PEW project).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Read stdin JSON and extract agent_type
INPUT=$(cat)
AGENT_TYPE=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent_type',''))" 2>/dev/null || echo "")

if [[ -z "$AGENT_TYPE" ]]; then
  exit 0
fi

# Map agent type to config scope.
# Research agents need competitors + stack; council agents need council config;
# all other PEW agents get the standard agent scope.
case "$AGENT_TYPE" in
  build-feature-benchmarker|build-ux-researcher|build-ux-designer)
    SCOPE="research"
    ;;
  council-*)
    SCOPE="council"
    ;;
  build-*|ux-audit-*|test-audit-*|react-audit-*)
    SCOPE="agent"
    ;;
  *)
    # Not a PEW agent — skip silently
    exit 0
    ;;
esac

# Get scoped config via pw.sh. If pw.sh fails (no pew.yaml, no venv yet),
# exit silently — the project may not use PEW.
CONFIG=$("$SCRIPT_DIR/pw.sh" dump-config --scope "$SCOPE" 2>/dev/null) || exit 0

if [[ -z "$CONFIG" ]]; then
  exit 0
fi

# Output additionalContext for Claude Code to inject into the agent's context.
python3 -c "
import json, sys
config = sys.argv[1]
output = {
    'hookSpecificOutput': {
        'hookEventName': 'SubagentStart',
        'additionalContext': '## PEW Project Configuration (auto-injected)\n\nThis config was loaded from pew.yaml. Reference these values as config.* fields.\n\n\`\`\`json\n' + config + '\n\`\`\`'
    }
}
print(json.dumps(output))
" "$CONFIG"
