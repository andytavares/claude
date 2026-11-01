#!/usr/bin/env bash
# SessionStart hook: start work from the latest remote code. Its output becomes session context.
set -uo pipefail

STALE_SECONDS=$((3 * 3600))
export GIT_TERMINAL_PROMPT=0

git rev-parse --is-inside-work-tree > /dev/null 2>&1 || exit 0
branch="$(git branch --show-current)"
[ -n "$branch" ] || exit 0
upstream="$(git rev-parse --abbrev-ref '@{u}' 2> /dev/null)"
remote="${upstream%%/*}"
remote="${remote:-origin}"
git remote get-url "$remote" > /dev/null 2>&1 || exit 0

if ! git fetch --quiet "$remote" 2> /dev/null; then
  echo "sync: git fetch $remote failed, so $branch can be out of date. Pull before you start work."
  exit 0
fi

pull_upstream() {
  [ -n "$upstream" ] || return 0
  local behind
  behind="$(git rev-list --count "HEAD..$upstream")"
  [ "$behind" -gt 0 ] || return 0
  if git merge --ff-only --quiet "$upstream" > /dev/null 2>&1; then
    echo "sync: pulled $behind commit(s) from $upstream."
  else
    echo "sync: $branch is $behind commit(s) behind $upstream and cannot fast-forward. Pull before you start work."
  fi
}

default_branch() {
  git symbolic-ref --quiet --short "refs/remotes/$remote/HEAD" 2> /dev/null && return
  for name in main master; do
    git rev-parse --verify --quiet "$remote/$name" > /dev/null && echo "$remote/$name" && return
  done
}

# First-parent commit time is when a change landed on the default branch, not when it was written.
check_default_branch() {
  local default oldest
  default="$(default_branch)"
  [ -n "$default" ] && [ "$default" != "$upstream" ] && [ "$default" != "$remote/$branch" ] || return 0
  oldest="$(git log --first-parent --reverse --format=%ct "HEAD..$default" | head -1)"
  [ -n "$oldest" ] && [ $(($(date +%s) - oldest)) -gt "$STALE_SECONDS" ] || return 0
  echo "sync: $default has commits from more than 3 hours ago that $branch lacks. Merge $default into $branch before you start work."
}

pull_upstream
check_default_branch
