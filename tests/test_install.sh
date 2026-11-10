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
  mkdir -p "$C/rules" "$C/skills/mine" "$C/skills/research" "$C/skills/google-review" "$C/skills/design-doc" "$C/skills/investigate-build" "$C/agents" "$C/hooks/clean-gate"
  echo "my own skill" > "$C/skills/mine/SKILL.md"
  echo "loose copy from an earlier install" > "$C/skills/research/SKILL.md"
  echo "loose copy from an earlier install" > "$C/agents/worker.md"
  echo "retired skill from an earlier install" > "$C/skills/google-review/SKILL.md"
  echo "retired skill from an earlier install" > "$C/skills/design-doc/SKILL.md"
  echo "loose skill the diagnose skill replaces" > "$C/skills/investigate-build/SKILL.md"
  echo "retired agent from an earlier install" > "$C/agents/google-code-reviewer.md"
  echo "loose copy from an earlier install" > "$C/hooks/clean-gate/gate.py"
  echo "global rule this repo now keeps to itself" > "$C/rules/plugin-evals.md"
  printf '%s' "$ORIGINAL_CLAUDE_MD" > "$C/CLAUDE.md"
  cat > "$C/settings.json" << 'JSON'
{"theme":"dark","hooks":{
  "PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command","command":"git-ai checkpoint"}]}],
  "PostToolUse":[{"hooks":[{"type":"command","command":"python3 ~/tools/clean-gate/gate.py"}]}],
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
assert d["hooks"]["PostToolUse"][0]["hooks"][0]["command"] == "python3 ~/tools/clean-gate/gate.py", "user hook removed"
assert "Stop" not in d["hooks"], "old clean-gate Stop hook still in settings.json"' "$C/settings.json" \
    || fail "settings.json not as expected"
}

assert_plugin_installed() {
  cmp -s "$ROOT/global/CLAUDE.md" "$C/rules/operating.md" || fail "operating rules not installed"
  assert_eq "$(cat "$C/CLAUDE.md")" "$(printf '%s' "$ORIGINAL_CLAUDE_MD")" "user CLAUDE.md untouched"
  assert_exists "$C/rules/clean-code.md"
  assert_exists "$C/rules/writing.md"
  assert_exists "$C/rules/environment.md"
  assert_exists "$C/skills/at/.claude-plugin/plugin.json"
  assert_exists "$C/skills/at/hooks/hooks.json"
  assert_exists "$C/skills/at/skills/word-salad/SKILL.md"
  assert_exists "$C/skills/at/skills/cone-of-shame/SKILL.md"
  assert_exists "$C/skills/at/skills/tests/SKILL.md"
  ! grep -rlE '^model: *sonnet' "$C/skills/at" || fail "a skill or agent still sets model: sonnet"
  assert_eq "$(cat "$C/skills/at/.source-repo")" "$ROOT" "recorded source repo"
  [ -x "$C/skills/at/hooks/clean-gate/gate.py" ] || fail "gate.py not executable"
  assert_exists "$C/skills/at/hooks/clean-gate/gate.py.lock"
}

assert_loose_copies_removed() {
  assert_gone "$C/skills/research"
  assert_gone "$C/agents/worker.md"
  assert_gone "$C/skills/google-review"
  assert_gone "$C/skills/design-doc"
  assert_gone "$C/skills/investigate-build"
  assert_gone "$C/agents/google-code-reviewer.md"
  assert_gone "$C/hooks/clean-gate"
  assert_gone "$C/rules/plugin-evals.md"
}

test_install() {
  seed_home
  run_install > "$WORK/out.txt"
  assert_plugin_installed
  assert_loose_copies_removed
  assert_settings_kept_without_old_gate
  assert_eq "$(cat "$C/skills/mine/SKILL.md")" "my own skill" "unrelated skill"
  assert_contains "$WORK/out.txt" 'Installed.'
  assert_contains "$WORK/out.txt" '/reload-plugins'
}

test_install_into_claude_md() {
  seed_home
  run_install --rules-in claude-md > /dev/null
  cmp -s "$ROOT/global/CLAUDE.md" "$C/CLAUDE.md" || fail "CLAUDE.md not installed"
  assert_gone "$C/rules/operating.md"
  run_install --rules-in claude-md > /dev/null
  for backup in "$C"/CLAUDE.md.bak-install-*; do assert_contains "$backup" '## Code'; done
  run_install > /dev/null
  assert_eq "$(cat "$C/CLAUDE.md")" "$(printf '%s' "$ORIGINAL_CLAUDE_MD")" "CLAUDE.md restored when rules move back"
  assert_exists "$C/rules/operating.md"
}

test_install_honours_config_dir() {
  seed_home
  local other="$WORK/config"
  rm -rf "$other"
  HOME="$H" CLAUDE_CONFIG_DIR="$other" bash "$ROOT/install.sh" > /dev/null
  assert_exists "$other/rules/operating.md"
  assert_exists "$other/skills/at/.claude-plugin/plugin.json"
  assert_gone "$C/rules/operating.md"
  HOME="$H" CLAUDE_CONFIG_DIR="$other" bash "$ROOT/uninstall.sh" > /dev/null
  assert_gone "$other/skills/at"
}

test_uninstall() {
  seed_home
  run_install --rules-in claude-md > /dev/null
  run_uninstall > "$WORK/out.txt"
  assert_gone "$C/skills/at"
  assert_gone "$C/rules/clean-code.md"
  assert_gone "$C/rules/writing.md"
  assert_gone "$C/rules/operating.md"
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

seed_radar_install() {
  mkdir -p "$C/skills/at/radar" "$C/skills/at/bin" "$C/skills/at/workflows" "$C/skills/at/skills/radar"
  echo '{"vault": "/tmp/vault"}' > "$C/at-radar.json"
}

assert_radar_and_fleet_gone() {
  assert_gone "$C/skills/at/radar"
  assert_gone "$C/skills/at/bin"
  assert_gone "$C/skills/at/workflows"
  for skill in radar intake dispatch fleet; do assert_gone "$C/skills/at/skills/$skill"; done
  assert_gone "$C/at-radar.json"
  python3 -c '
import json, sys
h = json.load(open(sys.argv[1]))["hooks"]
assert sorted(h) == ["PostToolUse", "PreToolUse", "SessionStart", "Stop"], list(h)' "$C/skills/at/hooks/hooks.json" || fail "hooks other than the clean gate, zsh guard, sync and pr-checks installed"
}

test_install_removes_retired_radar() {
  seed_home
  seed_radar_install
  run_install > /dev/null
  assert_radar_and_fleet_gone
}

seed_renamed_skills_install() {
  mkdir -p "$C/skills/at/skills/retro" "$C/skills/at/skills/review"
  echo "renamed skill from an earlier install" > "$C/skills/at/skills/retro/SKILL.md"
  echo "renamed skill from an earlier install" > "$C/skills/at/skills/review/SKILL.md"
}

test_install_replaces_renamed_skills() {
  seed_home
  seed_renamed_skills_install
  run_install > /dev/null
  assert_gone "$C/skills/at/skills/retro"
  assert_gone "$C/skills/at/skills/review"
  assert_exists "$C/skills/at/skills/postmortem/SKILL.md"
  assert_exists "$C/skills/at/skills/code-review/SKILL.md"
}

test_install_rejects_the_retired_radar_flag() {
  seed_home
  local before status=0
  before="$(find "$C" | sort)"
  run_install --radar > "$WORK/out.txt" 2>&1 || status=$?
  assert_eq "$status" 1 "exit status for --radar"
  assert_contains "$WORK/out.txt" 'unknown option'
  assert_eq "$(find "$C" | sort)" "$before" "files changed for --radar"
}

test_uninstall_removes_retired_radar_config() {
  seed_home
  run_install > /dev/null
  echo '{"vault": "/tmp/vault"}' > "$C/at-radar.json"
  run_uninstall > /dev/null
  assert_gone "$C/at-radar.json"
}

test_uninstall_keeps_the_data_store() {
  seed_home
  run_install > /dev/null
  mkdir -p "$H/at-skills-data/github.com/example-org/app"
  echo "term" > "$H/at-skills-data/github.com/example-org/app/GLOSSARY.md"
  run_uninstall > /dev/null
  assert_exists "$H/at-skills-data/github.com/example-org/app/GLOSSARY.md"
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
test_install_into_claude_md; echo "ok install into CLAUDE.md"
test_install_honours_config_dir; echo "ok install honours CLAUDE_CONFIG_DIR"
test_uninstall; echo "ok uninstall"
test_missing_uv; echo "ok missing uv"
test_install_removes_retired_radar; echo "ok install removes retired radar"
test_install_replaces_renamed_skills; echo "ok install replaces renamed skills"
test_install_rejects_the_retired_radar_flag; echo "ok install rejects the retired radar flag"
test_uninstall_removes_retired_radar_config; echo "ok uninstall removes retired radar config"
test_uninstall_keeps_the_data_store; echo "ok uninstall keeps the data store"
test_uninstall_rejects_unknown_option; echo "ok uninstall rejects unknown option"
echo "All install tests passed."
