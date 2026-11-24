#!/usr/bin/env bash
# Run a plugin Python script on the plugin's own uv, Python and Node.
# Usage: run.sh <script.py> [args...]
# No uv, Python, Node, uv setting, venv or version file from the shell or the repo can change what it gets.
set -uo pipefail

UV_VERSION=0.11.2
PYTHON_VERSION=3.12
NODE_PACKAGE=nodejs-wheel==22.20.0

# Not CLAUDE_PLUGIN_DATA: Bash tool commands and install.sh do not get it, and all three must share one download.
HOME_DIR="${AT_RUNTIME_DIR:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/at-runtime}"
UV_DIR="$HOME_DIR/uv/$UV_VERSION"
UV="$UV_DIR/uv"
LOCK="$HOME_DIR/uv.lock.d"

# The repo's own commands, such as the can-fail test command, get AT_CALLER_ENV back (hooks/shared/caller.py).
clear_environment() {
  local name
  AT_CALLER_ENV="$(env -0 | base64 | tr -d '\n')"
  export AT_CALLER_ENV
  for name in $(compgen -e); do
    case "$name" in UV_* | VIRTUAL_ENV | CONDA_PREFIX | CONDA_DEFAULT_ENV | PYTHON* | PYENV_VERSION | PIP_*) unset "$name" ;; esac
  done
  export UV_CACHE_DIR="$HOME_DIR/cache" UV_PYTHON_INSTALL_DIR="$HOME_DIR/python" UV_TOOL_DIR="$HOME_DIR/tools"
  export AT_UV="$UV" AT_PYTHON="$PYTHON_VERSION" AT_NODE_PACKAGE="$NODE_PACKAGE"
}

# A lock whose owner is gone is stale: a hook killed by its timeout never removes it.
take_lock() {
  local waited=0 owner
  until mkdir "$LOCK" 2> /dev/null; do
    owner="$(cat "$LOCK/pid" 2> /dev/null)"
    if [ -n "$owner" ] && ! kill -0 "$owner" 2> /dev/null; then rm -rf "$LOCK"; continue; fi
    sleep 1
    waited=$((waited + 1))
    [ "$waited" -ge 30 ] && return 1
  done
  echo $$ > "$LOCK/pid"
}

install_uv() {
  [ -x "$UV" ] && return 0
  mkdir -p "$HOME_DIR"
  take_lock || return 1
  [ -x "$UV" ] || curl -LsSf "https://astral.sh/uv/$UV_VERSION/install.sh" | env UV_UNMANAGED_INSTALL="$UV_DIR" sh > /dev/null 2>&1
  rm -rf "$LOCK"
  [ -x "$UV" ]
}

main() {
  [ "$#" -ge 1 ] || { echo "usage: run.sh <script.py> [args...]" >&2; exit 64; }
  clear_environment
  if ! install_uv; then
    echo "at: $(basename "$1") not run: could not download uv $UV_VERSION from https://astral.sh/uv/$UV_VERSION/install.sh" >&2
    exit 1
  fi
  exec "$UV" run --quiet --no-config --no-project --managed-python --python "$PYTHON_VERSION" --script "$@"
}

main "$@"
