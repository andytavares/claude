#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE="$HOME/.claude"

remove_path() {
  [ -e "$1" ] || return 0
  rm -rf "$1"
  echo "removed $1"
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
  remove_path "$CLAUDE/skills/at"
  for rule in "$REPO"/rules/*.md; do remove_path "$CLAUDE/rules/$(basename "$rule")"; done
  remove_path "$CLAUDE/at-radar.json"
  echo "radar vault and its notes left in place"
  restore_claude_md
  echo "Uninstalled."
}

main "$@"
