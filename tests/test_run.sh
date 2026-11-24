#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/at/scripts/run.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
# One plugin data folder for every run, so uv, Python and Node download once.
export AT_RUNTIME_DIR="${AT_TEST_PLUGIN_DATA:-$HOME/.cache/at-test-plugin-data}"

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_eq() { [ "$1" = "$2" ] || fail "$3: expected '$2', got '$1'"; }
assert_contains() { grep -qF -- "$2" <<< "$1" || fail "$3: '$2' not in '$1'"; }

# A repo and shell that ask for Python 3.10 everywhere, with broken tools first on PATH.
setup_hostile() {
  mkdir -p "$WORK/repo" "$WORK/bin"
  echo 3.10 > "$WORK/repo/.python-version"
  echo 'python-preference = "only-system"' > "$WORK/repo/uv.toml"
  for tool in uv uvx python3 python node npx; do
    printf '#!/bin/sh\necho broken >&2\nexit 1\n' > "$WORK/bin/$tool"
    chmod +x "$WORK/bin/$tool"
  done
  printf '# /// script\n# requires-python = ">=3.12"\n# dependencies = []\n# ///\n%s\n' \
    'import os, subprocess, sys; print(sys.version_info[:2] >= (3, 12), sys.argv[1:]); print(subprocess.run([os.environ["AT_UV"], "tool", "run", "--from", os.environ["AT_NODE_PACKAGE"], "node", "--version"], capture_output=True, text=True).stdout.strip())' \
    > "$WORK/probe.py"
}

hostile() {
  (cd "$WORK/repo" && env PATH="$WORK/bin:/usr/bin:/bin" UV_PYTHON=3.10 VIRTUAL_ENV=/nowhere \
    PYTHONPATH=/nowhere UV_PYTHON_PREFERENCE=only-system bash "$SCRIPT" "$@")
}

test_runs_plugin_python_and_node() {
  local out
  out="$(hostile "$WORK/probe.py" --flag value 2>&1)"
  assert_eq "$(sed -n 1p <<< "$out")" "True ['--flag', 'value']" "python and args"
  assert_eq "$(sed -n 2p <<< "$out")" "v22.20.0" "node version"
}

test_writes_nothing_into_the_repo() {
  assert_eq "$(cd "$WORK/repo" && find . -mindepth 1 | sort | tr '\n' ' ')" "./.python-version ./uv.toml " "repo files"
}

test_no_args_is_a_usage_error() {
  local status=0
  bash "$SCRIPT" > /dev/null 2>&1 || status=$?
  assert_eq "$status" 64 "exit status with no script"
}

test_failed_download_fails() {
  local out status=0
  printf '#!/bin/sh\nexit 1\n' > "$WORK/bin/curl"
  chmod +x "$WORK/bin/curl"
  out="$(AT_RUNTIME_DIR="$WORK/empty-data" PATH="$WORK/bin:/usr/bin:/bin" bash "$SCRIPT" "$WORK/probe.py" 2>&1)" || status=$?
  rm "$WORK/bin/curl"
  assert_eq "$status" 1 "exit status when uv cannot download"
  assert_contains "$out" "could not download uv" "message when uv cannot download"
}

test_stale_lock_is_taken_over() {
  local data="$WORK/stale-data"
  mkdir -p "$data/uv.lock.d"
  cp -R "$AT_RUNTIME_DIR/uv" "$data/uv"
  rm "$data/uv/0.11.2/uv"
  cp "$AT_RUNTIME_DIR/uv/0.11.2/uv" "$WORK/real-uv"
  echo 999999 > "$data/uv.lock.d/pid"
  # shellcheck disable=SC2016 # the fake installer expands $UV_UNMANAGED_INSTALL when run.sh pipes it to sh
  printf '#!/bin/sh\ncp %s "$UV_UNMANAGED_INSTALL/uv"\n' "$WORK/real-uv" > "$WORK/fake-installer"
  printf '#!/bin/sh\ncat %s\n' "$WORK/fake-installer" > "$WORK/bin/curl"
  chmod +x "$WORK/bin/curl"
  SECONDS=0
  AT_RUNTIME_DIR="$data" PATH="$WORK/bin:/usr/bin:/bin" bash "$SCRIPT" "$WORK/caller.py" > /dev/null 2>&1 \
    || { rm "$WORK/bin/curl"; fail "stale lock blocked the run"; }
  rm "$WORK/bin/curl"
  [ "$SECONDS" -lt 10 ] || fail "stale lock wait took $SECONDS seconds"
}

test_repo_command_gets_the_caller_environment() {
  local out
  printf '# /// script\n# dependencies = []\n# ///\n%s\n' \
    "import subprocess, sys; from pathlib import Path; sys.path.insert(0, '$ROOT/at/hooks/harness'); import harness; print(subprocess.run(harness.as_caller('echo \"\$UV_PYTHON|\$UV_NO_CONFIG|\$AT_PROBE\"'), shell=True, capture_output=True, text=True).stdout.strip())" \
    > "$WORK/caller.py"
  out="$(cd "$WORK/repo" && UV_PYTHON=3.10 AT_PROBE=kept bash "$SCRIPT" "$WORK/caller.py" 2>&1)"
  assert_eq "$out" "3.10||kept" "environment of the repo's command"
}

# Some bash builds, such as the one Nix installs, have no compgen builtin.
test_clears_caller_settings_without_compgen() {
  local out
  printf '# /// script\n# dependencies = []\n# ///\n%s\n' \
    'import os; print(os.environ.get("UV_PYTHON"), os.environ.get("PIP_INDEX_URL"))' > "$WORK/settings.py"
  # shellcheck disable=SC2016 # $0 and $@ expand in the inner bash
  out="$(UV_PYTHON=3.10 PIP_INDEX_URL=https://nowhere.invalid bash -c 'enable -n compgen 2> /dev/null; . "$0" "$@"' "$SCRIPT" "$WORK/settings.py" 2>&1)"
  assert_eq "$out" "None None" "caller settings in a bash without compgen"
}

setup_hostile
test_clears_caller_settings_without_compgen; echo "ok no compgen"
test_runs_plugin_python_and_node; echo "ok plugin python and node"
test_writes_nothing_into_the_repo; echo "ok repo untouched"
test_no_args_is_a_usage_error; echo "ok usage error"
test_failed_download_fails; echo "ok failed download"
test_repo_command_gets_the_caller_environment; echo "ok caller environment"
test_stale_lock_is_taken_over; echo "ok stale lock"
