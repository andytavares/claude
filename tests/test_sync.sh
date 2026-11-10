#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYNC="$ROOT/at/hooks/sync/sync.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
export GIT_CONFIG_GLOBAL=/dev/null GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_eq() { [ "$1" = "$2" ] || fail "$3: expected '$2', got '$1'"; }
assert_contains() { case "$1" in *"$2"*) ;; *) fail "output lacks '$2': $1" ;; esac; }
assert_lacks() { case "$1" in *"$2"*) fail "output has '$2': $1" ;; esac; }

# A bare remote, a clone to work in, and a second clone that pushes to main.
seed() {
  rm -rf "$WORK/remote.git" "$WORK/work" "$WORK/other"
  git init -q --bare -b main "$WORK/remote.git"
  git clone -q "$WORK/remote.git" "$WORK/other" 2> /dev/null
  git -C "$WORK/other" commit -q --allow-empty -m first
  git -C "$WORK/other" push -q origin main
  git clone -q "$WORK/remote.git" "$WORK/work"
}

push_main() {
  local age_seconds="$1" date
  date="$(($(date +%s) - age_seconds)) +0000"
  GIT_COMMITTER_DATE="$date" git -C "$WORK/other" commit -q --allow-empty -m "main $age_seconds"
  git -C "$WORK/other" push -q origin main
}

feature_branch() {
  git -C "$WORK/work" switch -q -c feat/x
  git -C "$WORK/work" commit -q --allow-empty -m feature
  git -C "$WORK/work" push -q -u origin feat/x 2> /dev/null
}

run_sync() { (cd "$1" && bash "$SYNC"); }

test_main_is_pulled() {
  seed
  push_main 60
  local out
  out="$(run_sync "$WORK/work")"
  assert_contains "$out" "pulled 1 commit(s) from origin/main"
  assert_eq "$(git -C "$WORK/work" rev-parse HEAD)" "$(git -C "$WORK/other" rev-parse HEAD)" "main HEAD"
}

test_feature_branch_is_pulled() {
  seed
  feature_branch
  git clone -q -b feat/x "$WORK/remote.git" "$WORK/pusher"
  git -C "$WORK/pusher" commit -q --allow-empty -m "teammate"
  git -C "$WORK/pusher" push -q origin feat/x
  rm -rf "$WORK/pusher"
  local out
  out="$(run_sync "$WORK/work")"
  assert_contains "$out" "pulled 1 commit(s) from origin/feat/x"
}

test_stale_main_asks_for_merge() {
  seed
  feature_branch
  push_main $((4 * 3600))
  local out
  out="$(run_sync "$WORK/work")"
  assert_contains "$out" "Merge origin/main into feat/x"
}

test_fresh_main_does_not_ask_for_merge() {
  seed
  feature_branch
  push_main 3600
  local out
  out="$(run_sync "$WORK/work")"
  assert_lacks "$out" "Merge"
}

test_diverged_branch_is_reported() {
  seed
  push_main 60
  git -C "$WORK/work" commit -q --allow-empty -m local
  local out
  out="$(run_sync "$WORK/work")"
  assert_contains "$out" "cannot fast-forward"
}

test_outside_a_repo_is_silent() {
  mkdir -p "$WORK/plain"
  assert_eq "$(run_sync "$WORK/plain")" "" "output outside a repo"
}

test_branch_is_pulled_without_a_default_branch() {
  rm -rf "$WORK/remote.git" "$WORK/work" "$WORK/other"
  git init -q --bare -b develop "$WORK/remote.git"
  git clone -q "$WORK/remote.git" "$WORK/other" 2> /dev/null
  git -C "$WORK/other" commit -q --allow-empty -m first
  git -C "$WORK/other" push -q origin develop
  git clone -q "$WORK/remote.git" "$WORK/work"
  git -C "$WORK/work" remote set-head origin -d
  git -C "$WORK/other" commit -q --allow-empty -m second
  git -C "$WORK/other" push -q origin develop
  local out
  out="$(run_sync "$WORK/work")"
  assert_contains "$out" "pulled 1 commit(s) from origin/develop"
}

test_main_is_pulled; echo "ok main is pulled"
test_branch_is_pulled_without_a_default_branch; echo "ok pulled without a default branch"
test_feature_branch_is_pulled; echo "ok feature branch is pulled"
test_stale_main_asks_for_merge; echo "ok stale main asks for merge"
test_fresh_main_does_not_ask_for_merge; echo "ok fresh main does not ask for merge"
test_diverged_branch_is_reported; echo "ok diverged branch is reported"
test_outside_a_repo_is_silent; echo "ok outside a repo is silent"
echo "All sync tests passed."
