#!/usr/bin/env bash
# Print the glossary directory for the current repo: ~/at-skills-data/<host>/<org>/<repo>.
set -euo pipefail

root="$HOME/at-skills-data"
git rev-parse --is-inside-work-tree > /dev/null 2>&1 || { echo "not inside a git repo" >&2; exit 1; }

# A worktree shares the main checkout's path through the common git directory.
common="$(cd "$(git rev-parse --git-common-dir)" && pwd -P)"
name="$(bash "$(dirname "${BASH_SOURCE[0]}")/../../scripts/default-branch.sh" --remote || true)"
remote="$(git remote get-url "${name:-origin}" 2> /dev/null || true)"

if [ -z "$remote" ]; then
  echo "$root/local/$(basename "$(dirname "$common")")"
  exit 0
fi

# git@host:org/repo.git, https://user@host/org/repo.git and ssh://git@host:2222/org/repo.git all become host/org/repo.
key="${remote#*://}"
key="${key#*@}"
key="$(echo "$key" | sed -E 's#^([^/:]+):([0-9]+)/#\1/#; s#^([^/:]+):#\1/#')"
echo "$root/${key%.git}"
