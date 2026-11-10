#!/usr/bin/env bash
# Print "<remote> <remote>/<default branch>" for the current repo, or exit 1 when it has no remote.
# With --remote, print only the remote name; it needs no fetched branches.
set -uo pipefail

git rev-parse --is-inside-work-tree > /dev/null 2>&1 || exit 1

pick_remote() {
  local upstream remotes
  upstream="$(git rev-parse --abbrev-ref '@{u}' 2> /dev/null)"
  [ -n "$upstream" ] && echo "${upstream%%/*}" && return
  remotes="$(git remote)"
  grep -qx origin <<< "$remotes" && echo origin && return
  [ "$(grep -c . <<< "$remotes")" -eq 1 ] && echo "$remotes"
}

remote="$(pick_remote)"
[ -n "$remote" ] || exit 1
[ "${1:-}" = "--remote" ] && echo "$remote" && exit 0

default="$(git symbolic-ref --quiet --short "refs/remotes/$remote/HEAD" 2> /dev/null)"
for name in main master; do
  [ -n "$default" ] && break
  git rev-parse --verify --quiet "$remote/$name" > /dev/null && default="$remote/$name"
done
[ -n "$default" ] || exit 1
echo "$remote $default"
