#!/usr/bin/env bash
# PreToolUse hook: soft nudge for active vibe phases.
#
# Fires on Bash tool use. If the command is a git add/commit and there's
# an active vibe phase (size=vibe, build=in_progress), injects a reminder
# to record decisions and use D-nnn commit format.
#
# Non-git commands and repos without active vibe phases are ignored.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Read stdin JSON
INPUT=$(cat)

# Extract the bash command from tool_input
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('command', ''))
" 2>/dev/null || echo "")

# Early exit if not a git add/commit command
if ! echo "$COMMAND" | grep -qE '\bgit\s+(add|commit)\b'; then
  exit 0
fi

# Check for active vibe phase via pw.sh
PHASES=$("$SCRIPT_DIR/pw.sh" list-phases --status started --json 2>/dev/null) || exit 0

# Find active vibe phase (size=vibe, build=in_progress)
VIBE_INFO=$(echo "$PHASES" | python3 -c "
import sys, json
phases = json.load(sys.stdin)
for p in phases:
    if p.get('size') == 'vibe':
        steps = p.get('steps', {})
        if steps.get('build') == 'in_progress':
            num = p.get('number', '?')
            title = p.get('title', 'Untitled')
            phase_dir = p.get('phase_dir', '')
            print(json.dumps({'number': num, 'title': title, 'phase_dir': phase_dir}))
            sys.exit(0)
sys.exit(1)
" 2>/dev/null) || exit 0

# Parse vibe phase info
PHASE_NUM=$(echo "$VIBE_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin)['number'])")
PHASE_TITLE=$(echo "$VIBE_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin)['title'])")
PHASE_DIR=$(echo "$VIBE_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin)['phase_dir'])")

# Output additionalContext nudge
python3 -c "
import json, sys

num = sys.argv[1]
title = sys.argv[2]
phase_dir = sys.argv[3]

context = f'''## Active Vibe Phase Detected (auto-injected)

**Phase {num} — {title}** is an active vibe phase with build in progress.

You MUST follow the vibe workflow for this commit:

1. **Record the decision** in \`{phase_dir}/DECISIONS.md\`:
   - Assign next D-nnn ID (check the file for the current count)
   - Auto-classify as \`change\` (new/altered requirement) or \`fix\` (correcting broken behavior)
   - Record: instruction, what changed, files modified, commit hash

2. **Use D-nnn commit format**: \`D-nnn: short description\`

3. **Update the summary table** at the top of DECISIONS.md

4. If you have not loaded the full vibe workflow yet, invoke \`/pew-vibe\` to resume the phase with full orchestration.
'''

output = {
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'allow',
        'additionalContext': context
    }
}
print(json.dumps(output))
" "$PHASE_NUM" "$PHASE_TITLE" "$PHASE_DIR"
