#!/usr/bin/env bash
# Print the glossary directory for the current repo: ~/at-skills-data/<host>/<org>/<repo>.
set -euo pipefail

root="$HOME/at-skills-data"
git rev-parse --is-inside-work-tree > /dev/null 2>&1 || { echo "not inside a git repo" >&2; exit 1; }

# A worktree shares the main checkout's path through the common git directory.
common="$(cd "$(git rev-parse --git-common-dir)" && pwd -P)"
remote="$(git remote get-url origin 2> /dev/null || true)"

if [ -z "$remote" ]; then
  echo "$root/local/$(basename "$(dirname "$common")")"
  exit 0
fi

# git@host:org/repo.git and https://user@host/org/repo.git both become host/org/repo.
key="${remote#*://}"
key="${key#*@}"
key="${key/:/\/}"
echo "$root/${key%.git}"
