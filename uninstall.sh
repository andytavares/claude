#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE="$HOME/.claude"

remove_path() {
  [ -e "$1" ] || return 0
  rm -rf "$1"
  echo "removed $1"
}

remove_repo_files() {
  for rule in "$REPO"/rules/*.md; do remove_path "$CLAUDE/rules/$(basename "$rule")"; done
  for skill in "$REPO"/skills/*/; do remove_path "$CLAUDE/skills/$(basename "$skill")"; done
  for agent in "$REPO"/agents/*.md; do remove_path "$CLAUDE/agents/$(basename "$agent")"; done
  remove_path "$CLAUDE/hooks/clean-gate"
}

remove_gate_hooks() {
  local settings="$CLAUDE/settings.json"
  [ -f "$settings" ] || return 0
  python3 - "$settings" << 'PY'
import json, sys
path = sys.argv[1]
def is_gate(entry):
    return any("clean-gate/gate.py" in h.get("command", "") for h in entry.get("hooks", []))
data = json.load(open(path))
hooks = data.get("hooks", {})
for event in list(hooks):
    hooks[event] = [e for e in hooks[event] if not is_gate(e)]
    if not hooks[event]:
        del hooks[event]
json.dump(data, open(path, "w"), indent=2)
open(path, "a").write("\n")
PY
  echo "removed clean-gate hooks from $settings"
}

restore_claude_md() {
  local first
  first="$(find "$CLAUDE" -maxdepth 1 -name 'CLAUDE.md.bak-install-*' | sort | head -n 1)"
  if [ -z "$first" ]; then
    echo "no CLAUDE.md backup found; left $CLAUDE/CLAUDE.md as is"
    return 0
  fi
  cp "$first" "$CLAUDE/CLAUDE.md"
  echo "restored $CLAUDE/CLAUDE.md from $first"
}

main() {
  remove_repo_files
  remove_gate_hooks
  restore_claude_md
  echo "Uninstalled."
}

main "$@"
