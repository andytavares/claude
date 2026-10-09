#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE="$HOME/.claude"
PLUGIN="$CLAUDE/skills/at"
WITH_RADAR=0
VAULT=""

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --radar) WITH_RADAR=1 ;;
      --vault)
        [ "$#" -ge 2 ] || { echo "--vault needs a directory" >&2; exit 1; }
        VAULT="$2"
        shift
        ;;
      *)
        echo "unknown option: $1" >&2
        exit 1
        ;;
    esac
    shift
  done
  if [ "$WITH_RADAR" = 1 ] && [ -z "$VAULT" ]; then
    echo "--radar needs --vault <dir>" >&2
    exit 1
  fi
  if [ "$WITH_RADAR" = 0 ] && [ -n "$VAULT" ]; then
    echo "--vault only works together with --radar" >&2
    exit 1
  fi
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
  remove_settings_gate_hooks
}

remove_settings_gate_hooks() {
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
}

install_repo_files() {
  install_path "$REPO/CLAUDE.md" "$CLAUDE/CLAUDE.md"
  for rule in "$REPO"/rules/*.md; do install_path "$rule" "$CLAUDE/rules/$(basename "$rule")"; done
  install_path "$REPO/at" "$PLUGIN"
  chmod +x "$PLUGIN/hooks/clean-gate/gate.py"
}

strip_radar_hooks() {
  python3 - "$PLUGIN/hooks/hooks.json" << 'PY'
import json, sys
path = sys.argv[1]
def is_radar(entry):
    return any("bin/radar" in h.get("command", "") for h in entry.get("hooks", []))
data = json.load(open(path))
hooks = data.get("hooks", {})
for event in list(hooks):
    hooks[event] = [e for e in hooks[event] if not is_radar(e)]
    if not hooks[event]:
        del hooks[event]
json.dump(data, open(path, "w"), indent=2)
open(path, "a").write("\n")
PY
}

drop_radar() {
  rm -rf "$PLUGIN/skills/radar" "$PLUGIN/radar" "$PLUGIN/bin/radar"
  strip_radar_hooks
  echo "radar: not installed (use --radar --vault <dir>)"
  if [ -f "$CLAUDE/at-radar.json" ]; then
    echo "radar: vault kept; $CLAUDE/at-radar.json untouched"
  fi
}

setup_radar() {
  "$PLUGIN/bin/radar" init "$VAULT"
}

main() {
  parse_args "$@"
  require_tools
  mkdir -p "$CLAUDE"
  backup "$CLAUDE/settings.json"
  backup "$CLAUDE/CLAUDE.md"
  remove_loose_copies
  install_repo_files
  if [ "$WITH_RADAR" = 1 ]; then setup_radar; else drop_radar; fi
  echo "Installed. Start a new Claude Code session; skills run as /at:<skill>."
}

main "$@"
