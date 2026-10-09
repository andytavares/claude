#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
H="$WORK/home"
C="$H/.claude"
ORIGINAL_CLAUDE_MD=$'# Rules\n\n## Code\n\n- keep it small\n'

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_exists() { [ -e "$1" ] || fail "missing $1"; }
assert_gone() { [ ! -e "$1" ] || fail "should not exist: $1"; }
assert_eq() { [ "$1" = "$2" ] || fail "$3: expected '$2', got '$1'"; }
assert_contains() { grep -qF -- "$2" "$1" || fail "$1 lacks '$2'"; }

seed_home() {
  rm -rf "$H"
  mkdir -p "$C/skills/mine"
  echo "my own skill" > "$C/skills/mine/SKILL.md"
  printf '%s' "$ORIGINAL_CLAUDE_MD" > "$C/CLAUDE.md"
  cat > "$C/settings.json" <<'JSON'
{"theme":"dark","hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command","command":"git-ai checkpoint"}]}]}}
JSON
}

run_install() { HOME="$H" bash "$ROOT/install.sh"; }
run_uninstall() { HOME="$H" bash "$ROOT/uninstall.sh"; }

gate_hook_count() {
  python3 -c '
import json, sys
hooks = json.load(open(sys.argv[1])).get("hooks", {}).get(sys.argv[2], [])
print(sum("clean-gate/gate.py" in h["command"] for e in hooks for h in e["hooks"]))' "$C/settings.json" "$1"
}

assert_settings_kept() {
  python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
assert d["theme"] == "dark"
assert d["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "git-ai checkpoint"' "$C/settings.json" \
    || fail "existing settings lost"
}

assert_repo_installed() {
  cmp -s "$ROOT/CLAUDE.md" "$C/CLAUDE.md" || fail "CLAUDE.md not installed"
  for skill in "$ROOT"/skills/*/; do assert_exists "$C/skills/$(basename "$skill")/SKILL.md"; done
  for agent in "$ROOT"/agents/*.md; do assert_exists "$C/agents/$(basename "$agent")"; done
  assert_exists "$C/rules/clean-code.md"
  [ -x "$C/hooks/clean-gate/gate.py" ] || fail "gate.py not executable"
}

test_install() {
  seed_home
  run_install > "$WORK/out.txt"
  assert_repo_installed
  assert_eq "$(gate_hook_count PostToolUse)" 1 "PostToolUse gate hooks"
  assert_eq "$(gate_hook_count Stop)" 1 "Stop gate hooks"
  # shellcheck disable=SC2016
  assert_contains "$C/settings.json" '$HOME/.claude/hooks/clean-gate/gate.py'
  assert_settings_kept
  assert_eq "$(cat "$C/skills/mine/SKILL.md")" "my own skill" "unrelated skill"
  assert_contains "$WORK/out.txt" 'Installed.'
}

test_reinstall_keeps_first_backup() {
  run_install > /dev/null
  assert_eq "$(gate_hook_count PostToolUse)" 1 "PostToolUse after rerun"
  assert_eq "$(gate_hook_count Stop)" 1 "Stop after rerun"
  for backup in "$C"/CLAUDE.md.bak-install-*; do assert_contains "$backup" '## Code'; done
}

test_uninstall() {
  run_uninstall > "$WORK/out.txt"
  for skill in "$ROOT"/skills/*/; do assert_gone "$C/skills/$(basename "$skill")"; done
  for agent in "$ROOT"/agents/*.md; do assert_gone "$C/agents/$(basename "$agent")"; done
  assert_gone "$C/rules/clean-code.md"
  assert_gone "$C/hooks/clean-gate"
  assert_eq "$(gate_hook_count PostToolUse)" 0 "PostToolUse after uninstall"
  assert_settings_kept
  assert_eq "$(cat "$C/CLAUDE.md")" "$(printf '%s' "$ORIGINAL_CLAUDE_MD")" "CLAUDE.md restored"
  assert_eq "$(cat "$C/skills/mine/SKILL.md")" "my own skill" "unrelated skill"
}

test_missing_uv() {
  seed_home
  local bin="$WORK/bin" status=0
  mkdir -p "$bin"
  ln -sf "$(command -v python3)" "$bin/python3"
  if PATH="/bin:/usr/bin" command -v uv > /dev/null; then echo "skip: uv in /usr/bin"; return; fi
  HOME="$H" PATH="$bin:/bin:/usr/bin" /bin/bash "$ROOT/install.sh" > "$WORK/out.txt" 2>&1 || status=$?
  assert_eq "$status" 1 "exit status without uv"
  assert_contains "$WORK/out.txt" 'uv'
}

test_install; echo "ok install"
test_reinstall_keeps_first_backup; echo "ok reinstall"
test_uninstall; echo "ok uninstall"
test_missing_uv; echo "ok missing uv"
echo "All install tests passed."
