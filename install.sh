#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE="$HOME/.claude"

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

install_repo_files() {
  install_path "$REPO/CLAUDE.md" "$CLAUDE/CLAUDE.md"
  for rule in "$REPO"/rules/*.md; do install_path "$rule" "$CLAUDE/rules/$(basename "$rule")"; done
  for skill in "$REPO"/skills/*/; do install_path "$skill" "$CLAUDE/skills/$(basename "$skill")"; done
  for agent in "$REPO"/agents/*.md; do install_path "$agent" "$CLAUDE/agents/$(basename "$agent")"; done
  install_path "$REPO/hooks/clean-gate" "$CLAUDE/hooks/clean-gate"
  chmod +x "$CLAUDE/hooks/clean-gate/gate.py"
}

merge_gate_hooks() {
  local settings="$CLAUDE/settings.json"
  [ -f "$settings" ] || echo '{}' > "$settings"
  python3 - "$settings" << 'PY'
import json, sys
path = sys.argv[1]
gate = 'uv run --script "$HOME/.claude/hooks/clean-gate/gate.py" check --hook '
wanted = {
    "PostToolUse": {"matcher": "Edit|Write|MultiEdit",
                    "hooks": [{"type": "command", "command": gate + "post-tool-use"}]},
    "Stop": {"hooks": [{"type": "command", "command": gate + "stop"}]},
}
def is_gate(entry):
    return any("clean-gate/gate.py" in h.get("command", "") for h in entry.get("hooks", []))
data = json.load(open(path))
hooks = data.setdefault("hooks", {})
for event, entry in wanted.items():
    hooks[event] = [e for e in hooks.get(event, []) if not is_gate(e)] + [entry]
json.dump(data, open(path, "w"), indent=2)
open(path, "a").write("\n")
PY
  echo "merged clean-gate hooks into $settings"
}

main() {
  require_tools
  mkdir -p "$CLAUDE"
  backup "$CLAUDE/settings.json"
  backup "$CLAUDE/CLAUDE.md"
  install_repo_files
  merge_gate_hooks
  echo "Installed. Start a new Claude Code session and run /hooks to confirm."
}

main "$@"
