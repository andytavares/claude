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
  mkdir -p "$C/skills/mine" "$C/skills/research" "$C/agents" "$C/hooks/clean-gate"
  echo "my own skill" > "$C/skills/mine/SKILL.md"
  echo "loose copy from an earlier install" > "$C/skills/research/SKILL.md"
  echo "loose copy from an earlier install" > "$C/agents/worker.md"
  echo "loose copy from an earlier install" > "$C/hooks/clean-gate/gate.py"
  printf '%s' "$ORIGINAL_CLAUDE_MD" > "$C/CLAUDE.md"
  cat > "$C/settings.json" << 'JSON'
{"theme":"dark","hooks":{
  "PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command","command":"git-ai checkpoint"}]}],
  "Stop":[{"hooks":[{"type":"command","command":"uv run --script \"$HOME/.claude/hooks/clean-gate/gate.py\" check --hook stop"}]}]}}
JSON
}

run_install() { HOME="$H" bash "$ROOT/install.sh" "$@"; }
run_uninstall() { HOME="$H" bash "$ROOT/uninstall.sh" "$@"; }

assert_settings_kept_without_old_gate() {
  python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
assert d["theme"] == "dark"
assert d["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "git-ai checkpoint"
assert "Stop" not in d["hooks"], "old clean-gate Stop hook still in settings.json"' "$C/settings.json" \
    || fail "settings.json not as expected"
}

assert_plugin_installed() {
  cmp -s "$ROOT/CLAUDE.md" "$C/CLAUDE.md" || fail "CLAUDE.md not installed"
  assert_exists "$C/rules/clean-code.md"
  assert_exists "$C/skills/at/.claude-plugin/plugin.json"
  assert_exists "$C/skills/at/hooks/hooks.json"
  assert_exists "$C/skills/at/skills/word-salad/SKILL.md"
  [ -x "$C/skills/at/hooks/clean-gate/gate.py" ] || fail "gate.py not executable"
}

assert_loose_copies_removed() {
  assert_gone "$C/skills/research"
  assert_gone "$C/agents/worker.md"
  assert_gone "$C/hooks/clean-gate"
}

test_install() {
  seed_home
  run_install > "$WORK/out.txt"
  assert_plugin_installed
  assert_loose_copies_removed
  assert_settings_kept_without_old_gate
  assert_eq "$(cat "$C/skills/mine/SKILL.md")" "my own skill" "unrelated skill"
  assert_contains "$WORK/out.txt" 'Installed.'
}

test_reinstall_keeps_first_backup() {
  run_install > /dev/null
  assert_plugin_installed
  for backup in "$C"/CLAUDE.md.bak-install-*; do assert_contains "$backup" '## Code'; done
}

test_uninstall() {
  run_uninstall > "$WORK/out.txt"
  assert_gone "$C/skills/at"
  assert_gone "$C/rules/clean-code.md"
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

assert_hooks_have_radar() {
  python3 -c '
import json, sys
h = json.load(open(sys.argv[1]))["hooks"]
for event, verb in (("SessionEnd", "capture"), ("SessionStart", "nudge")):
    cmds = [x["command"] for e in h[event] for x in e["hooks"]]
    assert any("bin/radar" in c and verb in c for c in cmds), event' "$C/skills/at/hooks/hooks.json" \
    || fail "radar hooks missing"
}

assert_radar_files_gone() {
  assert_gone "$C/skills/at/radar"
  assert_gone "$C/skills/at/bin/radar"
  assert_gone "$C/skills/at/skills/radar"
  if grep -qF 'bin/radar' "$C/skills/at/hooks/hooks.json"; then fail "radar hook still installed"; fi
  assert_contains "$C/skills/at/hooks/hooks.json" 'clean-gate/gate.py\" check --hook stop'
  assert_contains "$C/skills/at/hooks/hooks.json" 'clean-gate/gate.py\" check --hook post-tool-use'
}

test_install_without_radar() {
  seed_home
  run_install > "$WORK/out.txt"
  assert_radar_files_gone
  assert_contains "$WORK/out.txt" 'radar: not installed (use --radar --vault <dir>)'
  assert_gone "$C/at-radar.json"
}

test_install_with_radar() {
  seed_home
  mkdir -p "$WORK/vault"
  run_install --radar --vault "$WORK/vault" > "$WORK/out.txt"
  assert_exists "$C/skills/at/radar/radar.py"
  assert_exists "$C/skills/at/bin/radar"
  assert_hooks_have_radar
  assert_contains "$C/at-radar.json" "$WORK/vault"
  assert_exists "$WORK/vault/Radar Config.md"
  assert_exists "$WORK/vault/Radar/Blind spots"
  assert_contains "$WORK/out.txt" 'Radar uses'
}

test_reinstall_keeps_config_edit() {
  echo "my edit" >> "$WORK/vault/Radar Config.md"
  run_install --radar --vault "$WORK/vault" > /dev/null
  assert_contains "$WORK/vault/Radar Config.md" 'my edit'
}

test_reinstall_without_radar_keeps_vault() {
  run_install > "$WORK/out.txt"
  assert_radar_files_gone
  assert_exists "$C/at-radar.json"
  assert_contains "$WORK/vault/Radar Config.md" 'my edit'
  assert_contains "$WORK/out.txt" 'vault kept'
}

test_flag_pairing_errors_change_nothing() {
  seed_home
  local before after status
  before="$(find "$C" | sort)"
  for args in "--radar" "--vault $WORK/vault"; do
    status=0
    # shellcheck disable=SC2086
    run_install $args > "$WORK/out.txt" 2>&1 || status=$?
    assert_eq "$status" 1 "exit status for: $args"
    after="$(find "$C" | sort)"
    assert_eq "$after" "$before" "files changed for: $args"
  done
}

test_missing_vault_is_created() {
  seed_home
  run_install --radar --vault "$WORK/new/vault" > /dev/null
  assert_exists "$WORK/new/vault/.obsidian"
  assert_exists "$WORK/new/vault/Radar Config.md"
}

test_uninstall_leaves_vault() {
  run_install --radar --vault "$WORK/vault" > /dev/null
  run_uninstall > "$WORK/out.txt"
  assert_gone "$C/at-radar.json"
  assert_exists "$WORK/vault/Radar Config.md"
  assert_contains "$WORK/out.txt" 'vault'
}

test_uninstall_only_radar() {
  seed_home
  run_install --radar --vault "$WORK/vault" > /dev/null
  local claude_md_before
  claude_md_before="$(cat "$C/CLAUDE.md")"
  run_uninstall --radar > "$WORK/out.txt"
  assert_radar_files_gone
  assert_gone "$C/at-radar.json"
  assert_exists "$C/skills/at/skills/brief/SKILL.md"
  assert_exists "$C/rules/clean-code.md"
  assert_eq "$(cat "$C/CLAUDE.md")" "$claude_md_before" "CLAUDE.md untouched"
  assert_exists "$WORK/vault/Radar Config.md"
  assert_contains "$WORK/out.txt" 'Radar uninstalled'
}

test_uninstall_rejects_unknown_option() {
  seed_home
  run_install > /dev/null
  local status=0
  run_uninstall --bogus > "$WORK/out.txt" 2>&1 || status=$?
  assert_eq "$status" 1 "exit status for an unknown option"
  assert_exists "$C/skills/at"
}

test_install; echo "ok install"
test_reinstall_keeps_first_backup; echo "ok reinstall"
test_uninstall; echo "ok uninstall"
test_missing_uv; echo "ok missing uv"
test_install_without_radar; echo "ok install without radar"
test_install_with_radar; echo "ok install with radar"
test_reinstall_keeps_config_edit; echo "ok config edit kept"
test_reinstall_without_radar_keeps_vault; echo "ok reinstall without radar"
test_flag_pairing_errors_change_nothing; echo "ok flag pairing errors"
test_missing_vault_is_created; echo "ok missing vault created"
test_uninstall_leaves_vault; echo "ok uninstall leaves vault"
test_uninstall_only_radar; echo "ok uninstall only radar"
test_uninstall_rejects_unknown_option; echo "ok uninstall rejects unknown option"
echo "All install tests passed."
