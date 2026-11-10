#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

remove_path() {
  [ -e "$1" ] || return 0
  rm -rf "$1"
  echo "removed $1"
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

uninstall_everything() {
  remove_path "$CLAUDE/skills/at"
  for rule in "$REPO"/rules/*.md; do remove_path "$CLAUDE/rules/$(basename "$rule")"; done
  remove_path "$CLAUDE/rules/operating.md"
  remove_path "$CLAUDE/at-radar.json"
  restore_claude_md
  echo "Uninstalled."
}

main() {
  case "${1:-}" in
    "") uninstall_everything ;;
    *)
      echo "unknown option: $1" >&2
      exit 1
      ;;
  esac
}

main "$@"
