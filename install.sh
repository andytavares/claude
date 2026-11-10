#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
PLUGIN="$CLAUDE/skills/at"
RULES_IN=rules

usage() {
  echo "usage: install.sh [--rules-in rules|claude-md]" >&2
  exit 1
}

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --rules-in)
        [ "${2:-}" = rules ] || [ "${2:-}" = claude-md ] || usage
        RULES_IN="$2"
        shift 2
        ;;
      *)
        echo "unknown option: $1" >&2
        usage
        ;;
    esac
  done
}

require_tools() {
  local missing=()
  command -v uv > /dev/null || missing+=(uv)
  command -v python3 > /dev/null || missing+=(python3)
  if [ "${#missing[@]}" -gt 0 ]; then
    echo "missing required tools: ${missing[*]}" >&2
    exit 1
  fi
}

first_backup() {
  find "$CLAUDE" -maxdepth 1 -name "$(basename "$1").bak-install-*" | sort | head -n 1
}

# Only the first backup holds the pre-install file; later ones would hold installed copies.
backup() {
  local file="$1"
  [ -f "$file" ] || return 0
  if compgen -G "$file.bak-install-*" > /dev/null; then
    echo "kept existing backup of $file"
    return 0
  fi
  local dest
  dest="$file.bak-install-$(date -u +%Y%m%dT%H%M%SZ)"
  cp "$file" "$dest"
  echo "backed up $file to $dest"
}

install_path() {
  local src="$1" dest="$2"
  mkdir -p "$(dirname "$dest")"
  rm -rf "$dest"
  cp -R "$src" "$dest"
  echo "installed $dest"
}

remove_path() {
  [ -e "$1" ] || return 0
  rm -rf "$1"
  echo "removed $1"
}

# Earlier installs copied skills, agents and the gate loose into ~/.claude; the plugin replaces them.
remove_loose_copies() {
  for skill in "$REPO"/at/skills/*/; do remove_path "$CLAUDE/skills/$(basename "$skill")"; done
  for agent in "$REPO"/at/agents/*.md; do remove_path "$CLAUDE/agents/$(basename "$agent")"; done
  remove_path "$CLAUDE/hooks/clean-gate"
  remove_retired_copies
  remove_settings_gate_hooks
}

# Retired from the repo, so the loops above no longer name them.
remove_retired_copies() {
  remove_path "$CLAUDE/skills/google-review"
  remove_path "$CLAUDE/skills/design-doc"
  remove_path "$CLAUDE/skills/investigate-build"
  remove_path "$CLAUDE/agents/google-code-reviewer.md"
  remove_path "$CLAUDE/at-radar.json"
  remove_path "$CLAUDE/rules/plugin-evals.md"
}

remove_settings_gate_hooks() {
  local settings="$CLAUDE/settings.json"
  [ -f "$settings" ] || return 0
  python3 - "$settings" << 'PY'
import json, sys
path = sys.argv[1]
def is_gate(entry):
    return any(".claude/hooks/clean-gate/gate.py" in h.get("command", "") for h in entry.get("hooks", []))
data = json.load(open(path))
hooks = data.get("hooks", {})
for event in list(hooks):
    hooks[event] = [e for e in hooks[event] if not is_gate(e)]
    if not hooks[event]:
        del hooks[event]
json.dump(data, open(path, "w"), indent=2)
open(path, "a").write("\n")
PY
}

# The operating rules go to rules/operating.md by default, which loads in every session
# like CLAUDE.md does, so the user's own CLAUDE.md stays theirs.
install_operating_rules() {
  if [ "$RULES_IN" = claude-md ]; then
    backup "$CLAUDE/CLAUDE.md"
    remove_path "$CLAUDE/rules/operating.md"
    install_path "$REPO/global/CLAUDE.md" "$CLAUDE/CLAUDE.md"
    touch "$CLAUDE/.at-claude-md"
    return
  fi
  restore_claude_md
  install_path "$REPO/global/CLAUDE.md" "$CLAUDE/rules/operating.md"
}

# CLAUDE.md holds installed rules when the marker or a backup exists: installs before the
# marker always replaced CLAUDE.md. A restore uses up the backup, so it cannot run twice.
restore_claude_md() {
  local first
  first="$(find "$CLAUDE" -maxdepth 1 -name 'CLAUDE.md.bak-install-*' | sort | head -n 1)"
  [ -e "$CLAUDE/.at-claude-md" ] || [ -n "$first" ] || return 0
  rm -f "$CLAUDE/.at-claude-md"
  if [ -z "$first" ]; then
    rm -f "$CLAUDE/CLAUDE.md"
    echo "removed $CLAUDE/CLAUDE.md; it held only the installed rules"
    return 0
  fi
  mv "$first" "$CLAUDE/CLAUDE.md"
  echo "restored $CLAUDE/CLAUDE.md from $first"
}

install_repo_files() {
  install_operating_rules
  for rule in "$REPO"/rules/*.md; do install_path "$rule" "$CLAUDE/rules/$(basename "$rule")"; done
  install_path "$REPO/at" "$PLUGIN"
  chmod +x "$PLUGIN/hooks/clean-gate/gate.py"
  # /at:postmortem reads this to find the repo it changes.
  echo "$REPO" > "$PLUGIN/.source-repo"
}

main() {
  parse_args "$@"
  require_tools
  mkdir -p "$CLAUDE"
  backup "$CLAUDE/settings.json"
  remove_loose_copies
  install_repo_files
  echo "Installed. Run /reload-plugins in open Claude Code sessions, or start a new one; skills run as /at:<skill>."
}

main "$@"
