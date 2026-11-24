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

clear_environment() {
  local name
  for name in $(compgen -e); do
    case "$name" in UV_* | VIRTUAL_ENV | CONDA_PREFIX | CONDA_DEFAULT_ENV | PYTHON* | PYENV_VERSION | PIP_*) unset "$name" ;; esac
  done
  export UV_CACHE_DIR="$HOME_DIR/cache"
  export UV_PYTHON_INSTALL_DIR="$HOME_DIR/python"
  export UV_TOOL_DIR="$HOME_DIR/tools"
  export UV_NO_CONFIG=1 UV_NO_PROJECT=1 UV_MANAGED_PYTHON=1 UV_PYTHON="$PYTHON_VERSION"
  export AT_UV="$UV" AT_NODE_PACKAGE="$NODE_PACKAGE"
}

# A mkdir lock, so hooks that start at once download uv one time.
install_uv() {
  [ -x "$UV" ] && return 0
  mkdir -p "$HOME_DIR"
  local lock="$HOME_DIR/uv.lock.d" waited=0
  until mkdir "$lock" 2> /dev/null; do
    sleep 1
    waited=$((waited + 1))
    [ "$waited" -ge 120 ] && rm -rf "$lock"
  done
  if [ ! -x "$UV" ]; then
    curl -LsSf "https://astral.sh/uv/$UV_VERSION/install.sh" | env UV_UNMANAGED_INSTALL="$UV_DIR" sh > /dev/null 2>&1
  fi
  rmdir "$lock"
  [ -x "$UV" ]
}

main() {
  [ "$#" -ge 1 ] || { echo "usage: run.sh <script.py> [args...]" >&2; exit 64; }
  clear_environment
  if ! install_uv; then
    echo "{\"systemMessage\": \"at: $(basename "$1") not measured: could not download uv $UV_VERSION from https://astral.sh/uv/$UV_VERSION/install.sh\"}"
    exit 0
  fi
  exec "$UV" run --quiet --script "$@"
}

main "$@"
