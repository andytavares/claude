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

test_failed_download_is_not_measured() {
  local out status=0
  printf '#!/bin/sh\nexit 1\n' > "$WORK/bin/curl"
  chmod +x "$WORK/bin/curl"
  out="$(AT_RUNTIME_DIR="$WORK/empty-data" PATH="$WORK/bin:/usr/bin:/bin" bash "$SCRIPT" "$WORK/probe.py")" || status=$?
  rm "$WORK/bin/curl"
  assert_eq "$status" 0 "exit status when uv cannot download"
  assert_contains "$out" "not measured: could not download uv" "message when uv cannot download"
}

setup_hostile
test_runs_plugin_python_and_node; echo "ok plugin python and node"
test_writes_nothing_into_the_repo; echo "ok repo untouched"
test_no_args_is_a_usage_error; echo "ok usage error"
test_failed_download_is_not_measured; echo "ok failed download"
