#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/at/scripts/default-branch.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
export GIT_CONFIG_GLOBAL=/dev/null GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_eq() { [ "$1" = "$2" ] || fail "$3: expected '$2', got '$1'"; }

# A bare remote with one commit on $1, cloned under the remote name $2.
clone() {
  local branch="$1" name="$2" dir="$WORK/$3"
  rm -rf "$WORK/remote.git" "$dir"
  git init -q --bare -b "$branch" "$WORK/remote.git"
  git clone -q "$WORK/remote.git" "$WORK/seed" 2> /dev/null
  git -C "$WORK/seed" commit -q --allow-empty -m first
  git -C "$WORK/seed" push -q origin "$branch"
  rm -rf "$WORK/seed"
  git clone -q -o "$name" "$WORK/remote.git" "$dir"
  echo "$dir"
}

run() { (cd "$1" && bash "$SCRIPT"); }

test_origin_head() {
  assert_eq "$(run "$(clone trunk origin a)")" "origin origin/trunk" "origin/HEAD"
}

test_other_remote_name() {
  assert_eq "$(run "$(clone main upstream b)")" "upstream upstream/main" "remote named upstream"
}

test_no_remote_head_falls_back_to_main() {
  local dir
  dir="$(clone main upstream c)"
  git -C "$dir" remote set-head upstream -d
  assert_eq "$(run "$dir")" "upstream upstream/main" "no upstream/HEAD"
}

test_no_remote_fails() {
  local status=0
  mkdir -p "$WORK/d" && git -C "$WORK/d" init -q
  run "$WORK/d" > "$WORK/out" 2>&1 || status=$?
  assert_eq "$status" 1 "exit status with no remote"
  assert_eq "$(cat "$WORK/out")" "" "output with no remote"
}

test_origin_head; echo "ok origin head"
test_other_remote_name; echo "ok other remote name"
test_no_remote_head_falls_back_to_main; echo "ok no remote head"
test_no_remote_fails; echo "ok no remote"

test_remote_mode_needs_no_fetch() {
  mkdir -p "$WORK/e" && git -C "$WORK/e" init -q
  git -C "$WORK/e" remote add upstream https://example.com/example-org/lib.git
  assert_eq "$(cd "$WORK/e" && bash "$SCRIPT" --remote)" "upstream" "--remote without a fetch"
}
test_remote_mode_needs_no_fetch; echo "ok remote mode"
